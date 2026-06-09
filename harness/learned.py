# -*- coding: utf-8 -*-
"""Learned store — คำสั่งที่ระบบเรียนรู้จากผู้ใช้"""

import json
import os
import time

from .config import CONFIG_DIR

LEARNED_FILE = os.path.join(CONFIG_DIR, "learned.jsonl")
_MAX = 300


def _bigrams(s: str) -> set:
    s = "".join(s.split())
    return {s[i : i + 2] for i in range(len(s) - 1)}


def load() -> list[dict]:
    out = []
    try:
        with open(LEARNED_FILE, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    try:
                        out.append(json.loads(ln))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass
    return out


def add(req: str, good_cmd: str, bad_cmd: str = "", source: str = "user", verified: bool = True) -> None:
    req = " ".join((req or "").split()).strip()
    good_cmd = (good_cmd or "").strip()
    if not req or not good_cmd:
        return
    rows = [r for r in load() if r.get("req") != req and r.get("verified")]
    rows.append(
        {
            "req": req,
            "good_cmd": good_cmd,
            "bad_cmd": bad_cmd,
            "source": source,
            "verified": bool(verified),
            "ts": int(time.time()),
        }
    )
    rows = rows[-_MAX:]
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(LEARNED_FILE, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def matching(req: str, k: int = 2, min_score: int = 3) -> list[dict]:
    rb = _bigrams(req)
    if not rb:
        return []
    scored = []
    for r in load():
        if not r.get("verified") or not r.get("good_cmd"):
            continue
        s = len(rb & _bigrams(r.get("req", "")))
        if s >= min_score:
            scored.append((s, r))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:k]]
