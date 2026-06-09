# -*- coding: utf-8 -*-
"""ชุดคำถาม benchmark — โหลดจาก data/examples.jsonl"""

import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLES = os.path.join(_ROOT, "data", "examples.jsonl")


def _load() -> list[dict]:
    out = []
    with open(_EXAMPLES, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
    return out


QUESTIONS = _load()

__all__ = ["QUESTIONS"]
