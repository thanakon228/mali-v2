# -*- coding: utf-8 -*-
"""เมนูตั้งค่า — เปิดด้วย `mali setup`"""

import json
import re
import urllib.error
import urllib.request

from .config import (
    DEFAULTS,
    SETTINGS_FILE,
    get_config,
    load_settings,
    normalize_host,
    save_model,
    save_settings,
)

R = "\033[0m"
B = "\033[1m"
D = "\033[2m"
CY = "\033[96m"
GR = "\033[92m"
YE = "\033[93m"
RE = "\033[91m"
AC = "\033[94m"

_INCOMPAT = re.compile(r"embed|bge|vl:|\dvl|llava|vision|clip|rerank|minilm|nomic", re.I)


def _ask_line(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "q"


def _models() -> list[str]:
    try:
        with urllib.request.urlopen(f"{get_config()['ollama_host']}/api/tags", timeout=5) as r:
            data = json.loads(r.read().decode())
        return sorted(m["name"] for m in data.get("models", []))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return []


def choose_model(current: str) -> str:
    models = _models()
    if not models:
        print(f"{RE}ต่อ Ollama ไม่ได้ — เช็คว่า `ollama serve` รันอยู่{R}")
        return current
    print(f"\n{B}เลือกโมเดล{R}  {D}(หลักตอนนี้: {current}){R}")
    for i, m in enumerate(models, 1):
        mark = f"{GR} ●{R}" if m == current else "  "
        warn = f"  {YE}⚠ อาจไม่รองรับ tool-calling{R}" if _INCOMPAT.search(m) else ""
        print(f"{mark} {i:2}) {m}{warn}")
    sel = _ask_line("\nพิมพ์เลข (Enter เพื่อยกเลิก): ")
    if sel.isdigit() and 1 <= int(sel) <= len(models):
        chosen = models[int(sel) - 1]
        if _INCOMPAT.search(chosen):
            ans = _ask_line(
                f"  {YE}{chosen} น่าจะใช้กับผู้ช่วยนี้ไม่ได้ (ต้องรองรับ tool-calling) เลือกจริงไหม? [y/N]{R} "
            )
            if ans.lower() not in ("y", "yes", "ใช่"):
                print(f"{D}ยกเลิก{R}")
                return current
        save_model(chosen)
        print(f"{GR}✓ ตั้ง {chosen} เป็นโมเดลหลักแล้ว{R}")
        return chosen
    print(f"{D}ยกเลิก{R}")
    return current


def header():
    w = 44
    c = CY

    def line(s=""):
        return f"{c}   │{R}{s.center(w)}{c}│{R}"

    print()
    print(f"{c}   ╭{'─' * w}╮{R}")
    print(line())
    print(f"{c}   │{R}{B}{'M A L I   v 2'.center(w)}{R}{c}│{R}")
    print(f"{c}   │{R}{D}{'· · · · · · · · · · · · · · ·'.center(w)}{R}{c}│{R}")
    print(f"{c}   │{R}{B}{CY}{'S E T U P'.center(w)}{R}{c}│{R}")
    print(line())
    print(f"{c}   ╰{'─' * w}╯{R}")
    print(f"{D}        🇹🇭 ตั้งค่าผู้ช่วยเทอร์มินัล · {SETTINGS_FILE}{R}\n")


def _fmt(s: dict):
    onoff = lambda b: f"{GR}เปิด{R}" if b else f"{D}ปิด{R}"
    return [
        ("1", "โมเดลที่ใช้", s["model"]),
        ("2", "Ollama host", s["ollama_host"]),
        ("3", "โหมดคิด (thinking)", onoff(s["think"]) + f" {D}(ปิด=เร็วกว่า){R}"),
        ("4", "จำนวนรอบสูงสุด/คำขอ", str(s["max_steps"])),
        ("5", "ความยาว output สูงสุด", f"{s['max_output_chars']} ตัวอักษร"),
        ("6", "timeout ต่อคำขอ", f"{s['request_timeout']} วินาที"),
        ("7", "ข้ามการยืนยัน (auto-yes)", onoff(s["auto_yes"]) + (f"  {RE}⚠ อันตราย{R}" if s["auto_yes"] else "")),
        ("8", "โหมดแนะนำคำสั่งเท่านั้น", f"{s['suggest_only']} {D}(auto=เปิดเองเมื่อโมเดลเล็ก){R}"),
        ("9", "เรียนรู้จากการแก้คำสั่ง", onoff(s["learn"])),
        ("10", "บันทึกประวัติคำสั่ง (history.log)", onoff(s.get("history_log", True)) + f" {D}(redact ข้อมูลลับ){R}"),
    ]


def _edit_int(s, key, label):
    cur = s[key]
    v = _ask_line(f"  {label} (ตอนนี้ {cur}, Enter=คงเดิม): ").strip()
    if v.isdigit() and int(v) > 0:
        save_settings({key: int(v)})
        s[key] = int(v)
        print(f"{GR}✓ ตั้ง {label} = {v}{R}")
    elif v:
        print(f"{RE}ต้องเป็นเลขจำนวนเต็มบวก{R}")


def main():
    s = load_settings()
    while True:
        header()
        for num, label, val in _fmt(s):
            print(f"  {AC}{num}{R}) {label:26} {D}…{R} {val}")
        print(f"\n  {AC}r{R}) รีเซ็ตเป็นค่าเริ่มต้น   {AC}v{R}) ดูไฟล์ settings   {AC}q{R}) บันทึก & ออก")
        c = _ask_line(f"\n{B}เลือก ›{R} ").strip().lower()

        if c == "1":
            s["model"] = choose_model(s["model"])
        elif c == "2":
            v = _ask_line(
                f"  Ollama host (ตอนนี้ {s['ollama_host']}, เช่น localhost:11434 หรือ 11434): "
            ).strip()
            if v:
                host = normalize_host(v)
                if host:
                    save_settings({"ollama_host": host})
                    s["ollama_host"] = host
                    print(f"{GR}✓ ตั้ง host = {host}{R}")
                else:
                    print(f"{RE}ที่อยู่ไม่ถูกต้อง: '{v}'{R}")
        elif c == "3":
            s["think"] = not s["think"]
            save_settings({"think": s["think"]})
            print(f"{GR}✓ โหมดคิด: {'เปิด' if s['think'] else 'ปิด'}{R}")
        elif c == "4":
            _edit_int(s, "max_steps", "จำนวนรอบสูงสุด")
        elif c == "5":
            _edit_int(s, "max_output_chars", "ความยาว output สูงสุด")
        elif c == "6":
            _edit_int(s, "request_timeout", "timeout (วินาที)")
        elif c == "7":
            nv = not s["auto_yes"]
            if nv:
                warn = _ask_line(
                    f"  {RE}auto-yes จะรันคำสั่งปลอดภัย (green) โดยไม่ถาม — yellow/red ยังถามอยู่\n"
                    f"  พิมพ์ 'ยืนยัน' เพื่อเปิด: {R}"
                )
                if warn.strip() != "ยืนยัน":
                    print(f"{D}ยกเลิก{R}")
                    continue
            s["auto_yes"] = nv
            save_settings({"auto_yes": nv})
            print(f"{GR}✓ auto-yes: {'เปิด (เฉพาะ green)' if nv else 'ปิด'}{R}")
        elif c == "8":
            nxt = {"auto": "on", "on": "off", "off": "auto"}.get(str(s["suggest_only"]), "auto")
            s["suggest_only"] = nxt
            save_settings({"suggest_only": nxt})
            print(f"{GR}✓ โหมดแนะนำเท่านั้น: {nxt}{R}")
        elif c == "9":
            s["learn"] = not s["learn"]
            save_settings({"learn": s["learn"]})
            print(f"{GR}✓ เรียนรู้จากการแก้: {'เปิด' if s['learn'] else 'ปิด'}{R}")
        elif c == "10":
            s["history_log"] = not s.get("history_log", True)
            save_settings({"history_log": s["history_log"]})
            print(f"{GR}✓ บันทึกประวัติคำสั่ง: {'เปิด' if s['history_log'] else 'ปิด'}{R}")
        elif c == "r":
            if _ask_line("  รีเซ็ตทุกค่าเป็นค่าเริ่มต้น? [y/N] ").lower() in ("y", "yes", "ใช่"):
                save_settings(DEFAULTS)
                s = load_settings()
                print(f"{GR}✓ รีเซ็ตแล้ว{R}")
        elif c == "v":
            print(f"\n{D}{json.dumps(load_settings(), ensure_ascii=False, indent=2)}{R}")
        elif c in ("q", "quit", "exit", "ออก", ""):
            print(f"{GR}บันทึกแล้ว{R} {D}→ {SETTINGS_FILE}{R}\n")
            return
        else:
            print(f"{D}พิมพ์ตัวเลือกที่มีในเมนู{R}")
