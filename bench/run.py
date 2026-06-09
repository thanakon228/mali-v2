# -*- coding: utf-8 -*-
"""Benchmark runner — วัด accuracy, tool_rate (หลัง parse), latency

ใช้งาน:
    python3 bench/run.py thai-cli-3b-r2
    python3 bench/run.py
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bench.questions import QUESTIONS
from harness.model import parse_tool_calls

HOST = os.environ.get("MALI_OLLAMA", "http://localhost:11434").rstrip("/")
RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")

SYSTEM = (
    "คุณคือผู้ช่วย terminal ภาษาไทย เมื่อผู้ใช้ขอ ให้แปลงเป็นคำสั่ง shell "
    "แล้วเรียก tool run_command พร้อม field cmd เสมอ ตอบคำสั่งเดียวที่ตรงที่สุด "
    "อย่าอธิบายยาว อย่าถามกลับ"
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "รันคำสั่ง shell บนเครื่องผู้ใช้",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "คำสั่ง shell ที่จะรัน"},
                },
                "required": ["cmd"],
            },
        },
    }
]


def ask(model: str, q: str) -> tuple[str | None, str, float, bool]:
    """คืน (cmd, content, latency, parsed_tool) — parsed_tool = parse_tool_calls ได้ cmd"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": q},
        ],
        "tools": TOOLS,
        "stream": False,
        "think": False,
        "options": {"temperature": 0},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{HOST}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        return None, f"<error: {e}>", time.monotonic() - t0, False
    dt = time.monotonic() - t0

    msg = body.get("message", {})
    content = (msg.get("content") or "").strip()
    cmd = None
    parsed = False
    for call in parse_tool_calls(msg):
        if call["name"] == "run_command":
            c = (call.get("arguments") or {}).get("cmd", "").strip()
            if c:
                cmd = c
                parsed = True
                break
    return cmd, content, dt, parsed


def score(cmd: str | None, must: list[str]) -> bool:
    if not cmd:
        return False
    return all(re.search(p, cmd, re.IGNORECASE) for p in must)


def run_model(model: str) -> dict:
    print(f"\n=== {model} ===", flush=True)
    items = []
    correct = parsed_tools = 0
    total_lat = 0.0
    for q in QUESTIONS:
        cmd, content, lat, parsed = ask(model, q["q"])
        ok = score(cmd, q["must"])
        correct += ok
        parsed_tools += 1 if parsed else 0
        total_lat += lat
        items.append(
            {
                "id": q["id"],
                "cat": q["cat"],
                "q": q["q"],
                "cmd": cmd,
                "ok": ok,
                "lat": round(lat, 2),
                "must": q["must"],
            }
        )
        mark = "✓" if ok else ("·" if cmd else "✗")
        print(
            f"  {mark} [{q['id']:3}] {q['q'][:34]:36} → {(cmd or '(ไม่เสนอคำสั่ง)')[:46]}",
            flush=True,
        )

    n = len(QUESTIONS)
    summary = {
        "model": model,
        "accuracy": round(100 * correct / n, 1),
        "tool_rate": round(100 * parsed_tools / n, 1),
        "avg_latency": round(total_lat / n, 2),
        "correct": correct,
        "total": n,
    }
    print(
        f"  → accuracy {summary['accuracy']}%  | tool_rate {summary['tool_rate']}%  | {summary['avg_latency']}s/ข้อ",
        flush=True,
    )
    return {"summary": summary, "items": items}


def main():
    models = sys.argv[1:] or ["thai-cli-3b-r2"]
    out = {"models": [], "by_category": {}}
    for m in models:
        out["models"].append(run_model(m))

    cats = sorted({q["cat"] for q in QUESTIONS})
    for cat in cats:
        ids = {q["id"] for q in QUESTIONS if q["cat"] == cat}
        row = {}
        for mr in out["models"]:
            oks = sum(1 for it in mr["items"] if it["id"] in ids and it["ok"])
            row[mr["summary"]["model"]] = f"{oks}/{len(ids)}"
        out["by_category"][cat] = row

    with open(RESULTS, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nบันทึกผลที่ {RESULTS}")


if __name__ == "__main__":
    main()
