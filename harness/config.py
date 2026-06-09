"""ค่าตั้งทั้งหมด — env MALI_* > ~/.config/mali-v2/settings.json > DEFAULTS"""

import json
import os
import re

CONFIG_DIR = os.path.expanduser("~/.config/mali-v2")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")

DEFAULTS = {
    "model": "thai-cli-3b-r2",
    "ollama_host": "http://localhost:11434",
    "think": False,
    "max_steps": 8,
    "max_output_chars": 4000,
    "request_timeout": 120,
    "auto_yes": False,
    "suggest_only": "auto",
    "learn": True,
    "history_log": True,
}

_SMALL_MODEL = re.compile(r"(?:^|[:\-])(0\.\d+|1\.\d+|[0-3])b\b", re.IGNORECASE)
# โมเดลที่เทรนมาให้รัน tool ได้ — ไม่เปิด suggest_only แม้จะเป็น 3B
_TRAINED_CLI = ("thai-cli-3b-r2", "thai-cli-3b", "thai-cli")

_resolved: dict | None = None


def is_small_model(name: str) -> bool:
    base = (name or "").split(":")[0]
    if base in _TRAINED_CLI or base.startswith("thai-cli"):
        return False
    return bool(_SMALL_MODEL.search(name or ""))


def is_suggest_only(model: str) -> bool:
    v = str(load_settings().get("suggest_only", "auto")).lower()
    if v in ("on", "true", "1", "yes"):
        return True
    if v in ("off", "false", "0", "no"):
        return False
    return is_small_model(model)


def save_model(name: str) -> None:
    save_settings({"model": name.strip()})


def normalize_host(s: str) -> str | None:
    from urllib.parse import urlparse

    s = (s or "").strip().rstrip("/")
    if not s:
        return None
    if s.isdigit():
        return f"http://localhost:{s}"
    if "://" not in s:
        s = "http://" + s
    p = urlparse(s)
    if p.scheme in ("http", "https") and p.netloc:
        return s
    return None


def invalidate_config() -> None:
    global _resolved
    _resolved = None


def load_settings() -> dict:
    s = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            s.update({k: v for k, v in json.load(f).items() if k in DEFAULTS})
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    return s


def save_settings(updates: dict) -> dict:
    s = load_settings()
    s.update({k: v for k, v in updates.items() if k in DEFAULTS})
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    invalidate_config()
    return s


def _env(name: str):
    v = os.environ.get(name)
    return v if v not in (None, "") else None


def _env_bool(name: str):
    v = os.environ.get(name)
    if v in (None, ""):
        return None
    return v.lower() in ("1", "true", "yes")


def get_config() -> dict:
    global _resolved
    if _resolved is not None:
        return dict(_resolved)

    s = load_settings()
    _think_on = _env_bool("MALI_THINK")
    _think_on = _think_on if _think_on is not None else bool(s["think"])
    _yes = _env_bool("MALI_YES")

    _resolved = {
        "ollama_host": _env("MALI_OLLAMA") or s["ollama_host"],
        "model": _env("MALI_MODEL") or s["model"],
        "request_timeout": int(_env("MALI_TIMEOUT") or s["request_timeout"]),
        "max_steps": int(_env("MALI_MAX_STEPS") or s["max_steps"]),
        "max_output_chars": int(_env("MALI_MAX_OUTPUT") or s["max_output_chars"]),
        "think": None if _think_on else False,
        "auto_yes": _yes if _yes is not None else bool(s["auto_yes"]),
        "suggest_only": s.get("suggest_only", "auto"),
        "learn": bool(s.get("learn", True)),
        "history_log": bool(s.get("history_log", True)),
    }
    return dict(_resolved)
