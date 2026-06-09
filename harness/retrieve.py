# -*- coding: utf-8 -*-
"""Few-shot retrieval — หาตัวอย่างคล้าย ๆ จาก data/examples.jsonl + learned store"""

import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLES = os.path.join(_ROOT, "data", "examples.jsonl")

_QUESTIONS: list[dict] | None = None


def _load_questions() -> list[dict]:
    global _QUESTIONS
    if _QUESTIONS is not None:
        return _QUESTIONS
    out = []
    try:
        with open(_EXAMPLES, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    out.append(json.loads(ln))
    except OSError:
        pass
    _QUESTIONS = out
    return out


def _bigrams(s: str) -> set:
    s = "".join(s.split())
    return {s[i : i + 2] for i in range(len(s) - 1)}


def similar_examples(req: str, k: int = 3, min_score: int = 3) -> list[dict]:
    rb = _bigrams(req)
    if not rb:
        return []
    scored = []
    for q in _load_questions():
        score = len(rb & _bigrams(q["q"]))
        if score >= min_score:
            scored.append((score, q))
    scored.sort(key=lambda x: -x[0])
    return [q for _, q in scored[:k]]


def format_examples(req: str) -> str:
    from . import learned

    lines = []
    for r in learned.matching(req):
        lines.append(f'- "{r["req"]}" → {r["good_cmd"]}')
    for q in similar_examples(req):
        line = f'- "{q["q"]}" → {q["ex"]}'
        if line not in lines:
            lines.append(line)
    if not lines:
        return ""
    return "ตัวอย่างคำขอคล้าย ๆ กันและคำสั่งที่ถูกต้อง (ใช้เป็นแนวทาง):\n" + "\n".join(lines[:5])
