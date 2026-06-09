# -*- coding: utf-8 -*-
"""Preference memory — จำความชอบของผู้ใช้ข้าม session"""

import os

from .config import CONFIG_DIR

PREFS_FILE = os.path.join(CONFIG_DIR, "preferences.md")
_MAX = 40


def load_prefs() -> list[str]:
    try:
        with open(PREFS_FILE, encoding="utf-8") as f:
            return [
                ln.strip()[1:].strip()
                for ln in f
                if ln.strip().startswith("-") and ln.strip()[1:].strip()
            ]
    except OSError:
        return []


def add_pref(text: str) -> bool:
    text = " ".join((text or "").split()).strip()
    if not text:
        return False
    prefs = load_prefs()
    if text in prefs:
        return False
    prefs.append(text)
    prefs = prefs[-_MAX:]
    _write(prefs)
    return True


def remove_pref(index: int) -> str | None:
    prefs = load_prefs()
    if 0 <= index < len(prefs):
        gone = prefs.pop(index)
        _write(prefs)
        return gone
    return None


def clear_prefs() -> None:
    _write([])


def _write(prefs: list[str]) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(PREFS_FILE, "w", encoding="utf-8") as f:
        f.write("# ความชอบของผู้ใช้ (mali preferences)\n\n")
        for p in prefs:
            f.write(f"- {p}\n")


def prefs_block() -> str:
    prefs = load_prefs()
    if not prefs:
        return ""
    lines = "\n".join(f"- {p}" for p in prefs)
    return f"ความชอบ/ข้อกำหนดของผู้ใช้ (ต้องทำตามนี้เสมอ):\n{lines}"
