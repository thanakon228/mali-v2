"""Model adapter — Ollama /api/chat + parse_tool_calls() สำหรับโมเดล 3B"""

import json
import re
import urllib.error
import urllib.request

from .config import get_config

_TOOL_CALL_TAG = re.compile(
    r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
    re.DOTALL | re.IGNORECASE,
)
_BASH_BLOCK = re.compile(
    r"```(?:bash|sh|shell)?\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)
_TOOL_NAMES = frozenset({"run_command", "explain_command"})


class ModelError(RuntimeError):
    pass


def _parse_arguments(args) -> dict:
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
            return parsed if isinstance(parsed, dict) else {"cmd": args}
        except json.JSONDecodeError:
            return {"cmd": args}
    return {}


def _normalize_call(name: str, arguments) -> dict | None:
    name = (name or "").strip()
    if not name:
        return None
    return {"name": name, "arguments": _parse_arguments(arguments)}


def _find_json_objects(text: str) -> list[str]:
    """หา JSON object ที่มี balanced braces (รองรับ nested arguments)"""
    objects: list[str] = []
    i, n = 0, len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        start = i
        in_str = esc = False
        for j in range(i, n):
            ch = text[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    objects.append(text[start : j + 1])
                    i = j + 1
                    break
        else:
            i += 1
    return objects


def _embedded_tool_calls(content: str) -> list[dict]:
    for raw in _find_json_objects(content):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        name = (obj.get("name") or "").strip()
        if name not in _TOOL_NAMES:
            fn = obj.get("function")
            if isinstance(fn, dict):
                name = (fn.get("name") or "").strip()
        if name not in _TOOL_NAMES:
            continue
        parsed = _from_json_obj(obj)
        if parsed:
            return parsed
    return []


def _from_json_obj(obj: dict) -> list[dict]:
    if not isinstance(obj, dict):
        return []
    if "name" in obj:
        call = _normalize_call(obj["name"], obj.get("arguments", obj.get("args", {})))
        return [call] if call else []
    fn = obj.get("function")
    if isinstance(fn, dict) and fn.get("name"):
        call = _normalize_call(fn["name"], fn.get("arguments", {}))
        return [call] if call else []
    return []


def parse_tool_calls(msg: dict) -> list[dict]:
    """
    คืน list ของ {name, arguments} จาก message ของ Ollama
    ลำดับ: tool_calls → JSON ใน content → <tool_call> tag → bash code block
    """
    # 1. native tool_calls
    results: list[dict] = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        call = _normalize_call(fn.get("name", ""), fn.get("arguments", {}))
        if call:
            results.append(call)
    if results:
        return results

    content = (msg.get("content") or "").strip()
    if not content:
        return []

    # 2. JSON ใน content (ทั้งก้อน)
    try:
        obj = json.loads(content)
        parsed = _from_json_obj(obj)
        if parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    # 3. <tool_call> tag
    tag_match = _TOOL_CALL_TAG.search(content)
    if tag_match:
        try:
            parsed = _from_json_obj(json.loads(tag_match.group(1)))
            if parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    # 4. JSON ฝังใน content (รองรับ nested + garbage prefix เช่น );\r\n{...})
    parsed = _embedded_tool_calls(content)
    if parsed:
        return parsed

    # 5. bash code block — fallback suggest-only
    block_match = _BASH_BLOCK.search(content)
    if block_match:
        cmd = block_match.group(1).strip()
        if cmd:
            call = _normalize_call("run_command", {"cmd": cmd, "explain": ""})
            if call:
                call["suggest_only"] = True
                return [call]

    return []


class OllamaChat:
    def __init__(self, host: str | None = None, model: str | None = None):
        cfg = get_config()
        self.host = (host or cfg["ollama_host"]).rstrip("/")
        self.model = model or cfg["model"]

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        options: dict | None = None,
    ) -> dict:
        """ส่ง messages + tools ไปหาโมเดล คืน message dict"""
        opts = {"temperature": 0}
        if options:
            opts.update(options)
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": opts,
        }
        if tools:
            payload["tools"] = tools
        cfg = get_config()
        if cfg["think"] is False:
            payload["think"] = False

        data = json.dumps(payload).encode("utf-8")
        try:
            req = urllib.request.Request(
                f"{self.host}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=cfg["request_timeout"]) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except ValueError as e:
            raise ModelError(
                f"ที่อยู่ Ollama ไม่ถูกต้อง: '{self.host}' ({e}). "
                f"แก้ด้วย `mali setup` (เช่น http://localhost:11434)"
            ) from e
        except urllib.error.HTTPError as e:
            if e.code == 400:
                raise ModelError(
                    f"โมเดล '{self.model}' ใช้กับผู้ช่วยนี้ไม่ได้ (HTTP 400) — "
                    f"น่าจะไม่รองรับ tool-calling"
                ) from e
            raise ModelError(f"Ollama ตอบ HTTP {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise ModelError(
                f"ต่อ Ollama ที่ {self.host} ไม่ได้: {e}. "
                f"ลองสั่ง `ollama serve` หรือเช็คว่ารันโมเดล '{self.model}' อยู่"
            ) from e
        except json.JSONDecodeError as e:
            raise ModelError(f"Ollama ตอบไม่ใช่ JSON: {e}") from e

        msg = body.get("message")
        if not msg:
            raise ModelError(f"ไม่พบ message ในคำตอบ: {body}")
        return msg


def unload(model: str, host: str | None = None) -> bool:
    """บอก Ollama ให้ปลดโมเดลออกจากหน่วยความจำ (keep_alive=0)"""
    host = host or get_config()["ollama_host"]
    payload = json.dumps({"model": model, "keep_alive": 0}).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"{host.rstrip('/')}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10):
            return True
    except (urllib.error.URLError, ValueError, TimeoutError, OSError):
        return False
