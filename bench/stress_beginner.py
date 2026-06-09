# -*- coding: utf-8 -*-
"""รัน 1000 คำถามมือใหม่ผ่าน harness — หาจุดอ่อน (ไม่ต้องรัน shell จริง)

ใช้งาน:
    python3 bench/stress_beginner.py              # harness only (~1 วินาที)
    python3 bench/stress_beginner.py --model 50   # ทดสอบโมเดล 50 ข้อแรก (ต้อง ollama serve)
    python3 bench/stress_beginner.py --model      # ทดสอบโมเดลครบ 1000 (ช้ามาก)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from bench.beginner_1000 import load, save
from harness.cmd_fixup import normalize_cmd
from harness.quick_route import try_route
from harness.retrieve import format_examples, similar_examples
from harness.shell_input import extract_shell_command
from harness.safety import Risk, classify

REPORT = os.path.join(os.path.dirname(__file__), "stress_beginner_report.json")


def _path_label(q: str) -> str:
    if extract_shell_command(q):
        return "direct_shell"
    if try_route(q):
        return "quick_route"
    return "model_only"


def _weaknesses(q: dict) -> list[str]:
    issues = []
    text = q["q"]
    path = _path_label(text)

    if path == "model_only":
        ex = format_examples(text)
        if not ex:
            issues.append("no_fewshot")
        elif len(similar_examples(text)) == 1:
            issues.append("weak_fewshot")

    if q["cat"] == "win_vague":
        issues.append("vague_request")

    if q["cat"].startswith("win_") and path == "model_only" and not format_examples(text):
        issues.append("win_term_no_examples")

    if _WIN_TERMS.search(text) and path == "model_only":
        sim = similar_examples(text, k=1, min_score=3)
        if not sim or sim[0]["cat"] not in ("proc", "file", "disk", "net", "pkg", "perm", "misc", "system"):
            issues.append("win_metaphor_weak_match")

    # คำถาม meta/GUI ที่ terminal ช่วยไม่ได้
    gui_markers = [
        "ctrl", "กดอะไร", "เปิด terminal ยังไง", "Print Screen",
        "Calculator", "Control Panel", "Registry",
    ]
    if any(m.lower() in text.lower() for m in gui_markers):
        issues.append("likely_not_terminal")

    return issues


_WIN_TERMS = re.compile(
    r"task manager|control panel|registry|ไดรฟ์\s*c|disk cleanup|"
    r"run as administrator|ถังขยะ|blue screen|device manager|"
    r"windows update|notepad|print screen|calculator|wifi|bluetooth",
    re.I,
)


def harness_pass(questions: list[dict]) -> dict:
    paths = Counter()
    issues = Counter()
    by_cat_issues: dict[str, Counter] = defaultdict(Counter)
    samples: dict[str, list] = defaultdict(list)

    for q in questions:
        p = _path_label(q["q"])
        paths[p] += 1
        ws = _weaknesses(q)
        for w in ws:
            issues[w] += 1
            by_cat_issues[q["cat"]][w] += 1
            if len(samples[w]) < 5:
                samples[w].append({"id": q["id"], "q": q["q"], "cat": q["cat"]})

    # cmd_fixup regression spot-check บนคำถามที่มี kill
    fixup_bugs = []
    for q in questions:
        if "chrome firefox" in q["q"].lower() or "ปิดทั้งหมด" in q["q"]:
            fixed, note = normalize_cmd("pkill chrome firefox")
            if "chromefirefox" in fixed:
                fixup_bugs.append(q["id"])

    return {
        "total": len(questions),
        "paths": dict(paths),
        "issues": dict(issues),
        "by_category": {k: dict(v) for k, v in sorted(by_cat_issues.items())},
        "samples": dict(samples),
        "fixup_regression_ids": fixup_bugs,
        "coverage": {
            "model_only_pct": round(100 * paths["model_only"] / len(questions), 1),
            "no_fewshot_pct": round(100 * issues.get("no_fewshot", 0) / len(questions), 1),
            "vague_pct": round(100 * issues.get("vague_request", 0) / len(questions), 1),
        },
    }


def model_pass(questions: list[dict], model: str, limit: int | None) -> dict:
    from bench.run import ask, score
    from harness.model import parse_tool_calls

    subset = questions[:limit] if limit else questions
    items = []
    no_tool = wrong_hint = ok_hint = 0
    lat_total = 0.0
    cat_stats: dict[str, list[bool]] = defaultdict(list)

    for q in subset:
        cmd, content, lat, parsed = ask(model, q["q"])
        lat_total += lat
        hints = q.get("hints") or []
        hint_ok = True
        if hints and cmd:
            hint_ok = any(re.search(h, cmd, re.I) for h in hints)
        elif hints and not cmd:
            hint_ok = False

        if not parsed:
            no_tool += 1
        elif hints and not hint_ok:
            wrong_hint += 1
        elif hints and hint_ok:
            ok_hint += 1

        cat_stats[q["cat"]].append(parsed and (hint_ok or not hints))
        items.append(
            {
                "id": q["id"],
                "cat": q["cat"],
                "q": q["q"],
                "cmd": cmd,
                "parsed": parsed,
                "hint_ok": hint_ok,
                "content_preview": (content or "")[:120],
            }
        )
        mark = "✓" if parsed and hint_ok else ("·" if parsed else "✗")
        print(
            f"  {mark} [{q['id']:4}] {q['q'][:40]:42} → {(cmd or '(text)')[:40]}",
            flush=True,
        )

    n = len(subset)
    return {
        "model": model,
        "tested": n,
        "tool_rate_pct": round(100 * (n - no_tool) / n, 1),
        "hint_match_pct": round(100 * ok_hint / max(1, sum(1 for q in subset if q.get("hints"))), 1),
        "no_tool_call": no_tool,
        "wrong_cmd_vs_hint": wrong_hint,
        "avg_latency_s": round(lat_total / n, 2),
        "by_category": {
            c: round(100 * sum(v) / len(v), 1) for c, v in sorted(cat_stats.items())
        },
        "fail_samples": [it for it in items if not it["parsed"]][:30],
        "wrong_samples": [it for it in items if it["parsed"] and not it["hint_ok"] and (subset[[x["id"] for x in subset].index(it["id"])].get("hints"))][:30],
    }


def print_report(h: dict, m: dict | None):
    print("\n" + "=" * 60)
    print("สรุปจุดอ่อน harness (1000 คำถามมือใหม่ / ย้ายจาก Windows)")
    print("=" * 60)
    print(f"\nเส้นทางประมวลผล:")
    for k, v in sorted(h["paths"].items(), key=lambda x: -x[1]):
        print(f"  {k:20} {v:4} ({100*v/h['total']:.1f}%)")

    print(f"\nปัญหาที่พบ (เรียงตามความถี่):")
    for issue, cnt in sorted(h["issues"].items(), key=lambda x: -x[1]):
        print(f"  {issue:25} {cnt:4} ({100*cnt/h['total']:.1f}%)")
        for s in h["samples"].get(issue, [])[:2]:
            print(f"      → [{s['id']}] {s['q'][:70]}")

    print(f"\nหมวดที่เจอปัญหาเยอะสุด (no_fewshot):")
    cat_nf = [
        (cat, c.get("no_fewshot", 0))
        for cat, c in h["by_category"].items()
        if c.get("no_fewshot", 0)
    ]
    for cat, cnt in sorted(cat_nf, key=lambda x: -x[1])[:10]:
        print(f"  {cat:15} {cnt}")

    print(f"\nสรุป coverage:")
    for k, v in h["coverage"].items():
        print(f"  {k}: {v}%")

    if m:
        print(f"\n--- โมเดล {m['model']} ({m['tested']} ข้อ) ---")
        print(f"  tool_rate: {m['tool_rate_pct']}%")
        print(f"  hint_match: {m['hint_match_pct']}%")
        print(f"  ไม่ส่ง tool: {m['no_tool_call']}")
        print(f"  คำสั่งไม่ตรง hint: {m['wrong_cmd_vs_hint']}")
        print(f"  latency เฉลี่ย: {m['avg_latency_s']}s")
        print("  หมวดที่แย่สุด (parsed+hint):")
        for cat, pct in sorted(m["by_category"].items(), key=lambda x: x[1])[:8]:
            print(f"    {cat}: {pct}%")

    print("\nจุดอ่อนหลักของโปรแกรม (สรุป):")
    weaknesses = [
        f"quick_route ครอบคลุมแค่ {h['paths'].get('quick_route', 0)} ข้อ — เกือบทั้งหมดพึ่งโมเดล 3B",
        f"ไม่มี few-shot สำหรับ {h['issues'].get('no_fewshot', 0)} คำถาม ({h['coverage']['no_fewshot_pct']}%)",
        f"คำถามกำกวม {h['issues'].get('vague_request', 0)} ข้อ — โมเดลมักตอบข้อความ",
        f"คำถาม Windows metaphor ไม่มีตัวอย่าง {h['issues'].get('win_term_no_examples', 0)} ข้อ",
        f"Windows term จับ few-shot ไม่ตรง {h['issues'].get('win_metaphor_weak_match', 0)} ข้อ",
        f"คำถาม GUI/meta {h['issues'].get('likely_not_terminal', 0)} ข้อ — terminal ช่วยไม่ได้จริง",
    ]
    if m:
        weaknesses.append(f"โมเดลไม่ส่ง tool {m['no_tool_call']}/{m['tested']} ข้อ ({100-m['tool_rate_pct']:.0f}% text-only)")
    for i, w in enumerate(weaknesses, 1):
        print(f"  {i}. {w}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", nargs="?", const=1000, type=int, help="ทดสอบโมเดล N ข้อ (default 1000 ถ้าใส่แค่ --model)")
    ap.add_argument("--regen", action="store_true", help="สร้าง beginner_1000.jsonl ใหม่")
    args = ap.parse_args()

    path = save() if args.regen or not os.path.isfile(
        os.path.join(_ROOT, "data", "beginner_1000.jsonl")
    ) else os.path.join(_ROOT, "data", "beginner_1000.jsonl")
    questions = load(path)
    print(f"โหลด {len(questions)} คำถามจาก {path}")

    t0 = time.monotonic()
    h = harness_pass(questions)
    print(f"harness scan เสร็จใน {time.monotonic()-t0:.2f}s")

    m = None
    if args.model is not None:
        from harness.config import get_config

        model = get_config()["model"]
        limit = None if args.model == 1000 else args.model
        print(f"\nทดสอบโมเดล {model} ({limit or len(questions)} ข้อ)…")
        try:
            m = model_pass(questions, model, limit)
        except Exception as e:
            print(f"⚠ ทดสอบโมเดลไม่ได้: {e}")
            print("  (ต้องรัน ollama serve + มีโมเดล thai-cli-3b-r2)")

    report = {"harness": h, "model": m, "generated": len(questions)}
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print_report(h, m)
    print(f"\nบันทึกรายงาน: {REPORT}")


if __name__ == "__main__":
    main()
