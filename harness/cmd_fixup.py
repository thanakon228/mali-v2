# -*- coding: utf-8 -*-
"""แก้คำสั่งที่โมเดลเล็กสร้างผิดก่อนถามยืนยัน"""

import re
import shlex

# ชื่อ process ที่โมเดลมักแยกผิด — รวมเฉพาะคู่ที่รู้จัก
_KNOWN_SPLIT: dict[tuple[str, ...], str] = {
    ("ol", "llama"): "ollama",
    ("no", "de"): "node",
}

# คำสั่ง Windows ที่ห้ามใช้บน Linux → แทนที่
_WIN_REWRITES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^taskmgr\b", re.I), "htop"),
    (re.compile(r"^notepad\b", re.I), "nano"),
    (re.compile(r"^start\s+", re.I), "xdg-open "),
    (re.compile(r"^wsl\s+--update\b", re.I), "sudo apt update"),
    (re.compile(r"%LOCALAPPDATA%\\Downloads", re.I), "$HOME/Downloads"),
    (re.compile(r"%([A-Z_]+)%", re.I), r"$\1"),
    (re.compile(r"^cmd\.exe\b", re.I), "bash"),
    (re.compile(r"^powershell\b", re.I), "bash"),
]


def _split_flags_rest(toks: list[str]) -> tuple[list[str], list[str]]:
    flags, rest = [], []
    for t in toks:
        if t.startswith("-") and not rest:
            flags.append(t)
        else:
            rest.append(t)
    return flags, rest


def _merge_pkill_pattern(flags: list[str], rest: list[str]) -> tuple[str, str] | None:
    if len(rest) <= 1:
        return None
    key = tuple(rest)
    pat = _KNOWN_SPLIT.get(key)
    if not pat:
        return None
    flag_s = " ".join(flags)
    if "-f" in flags:
        return f"pkill {flag_s} {shlex.quote(pat)}", f"รวม '{' '.join(rest)}' → '{pat}'"
    return f"pkill -f {shlex.quote(pat)}", f"รวม '{' '.join(rest)}' → '{pat}'"


def normalize_cmd(cmd: str) -> tuple[str, str | None]:
    """
    คืน (cmd ที่แก้แล้ว, ข้อความอธิบายการแก้ หรือ None)
    """
    c = (cmd or "").strip()
    if not c:
        return c, None

    notes: list[str] = []

    for pat, repl in _WIN_REWRITES:
        if pat.search(c):
            c = pat.sub(repl, c)
            notes.append("แทนคำสั่ง Windows ด้วยคำสั่ง Linux")

    if re.search(r"\bol\s+llama\b", c, re.I):
        c = re.sub(r"\bol\s+llama\b", "ollama", c, flags=re.I)
        notes.append("แก้ชื่อ process 'ol llama' → 'ollama'")

    head = c.split(None, 1)[0].lower() if c.split() else ""
    if head == "pkill":
        try:
            toks = shlex.split(c)
        except ValueError:
            toks = c.split()
        if len(toks) > 1:
            flags, rest = _split_flags_rest(toks[1:])
            merged = _merge_pkill_pattern(flags, rest)
            if merged:
                c, note = merged
                notes.append(note)

    note = " · ".join(notes) if notes else None
    return c, note
