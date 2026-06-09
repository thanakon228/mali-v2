# -*- coding: utf-8 -*-
"""CLI entry point สำหรับ mali"""

import json
import os
import sys
import urllib.error
import urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from harness.loop import run  # noqa: E402

HELP = """\
mali — ผู้ช่วย terminal ภาษาไทย (Ollama / thai-cli-3b-r2)

ใช้งาน:
  mali                       เข้าโหมดคุยกับโมเดล (REPL) มี banner + คำแนะนำ
  mali "คำขอภาษาไทย"          สั่งงานครั้งเดียว เช่น  mali "เช็คพื้นที่ดิสก์"
  echo "คำขอ" | mali           อ่านคำขอจาก stdin
  mali setup                   ตั้งค่า (โมเดล, host, ฯลฯ)
  mali remember "..."          จำความชอบ เช่น mali remember "ใช้ pnpm ไม่ใช่ npm"
  mali prefs | forget [เลข]   ดู / ลืมความชอบ
  mali --help | -h             แสดงวิธีใช้นี้
  mali --version | -v          แสดงเวอร์ชัน

ตัวแปรสภาพแวดล้อม: MALI_MODEL, MALI_OLLAMA, MALI_YES, MALI_TIMEOUT
"""


def _health_check() -> str | None:
    from harness.config import get_config

    cfg = get_config()
    host, model = cfg["ollama_host"], cfg["model"]
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=3) as r:
            names = [m["name"] for m in json.loads(r.read()).get("models", [])]
    except (urllib.error.URLError, OSError, ValueError):
        return (
            f"❌ ต่อ Ollama ที่ {host} ไม่ได้\n"
            f"   ลองสั่ง:  ollama serve"
        )
    if model not in names and not any(
        n.split(":")[0] == model.split(":")[0] for n in names
    ):
        return (
            f"❌ ยังไม่มีโมเดล '{model}'\n"
            f"   ดูวิธีติดตั้ง: ~/Desktop/thai-cli-train/dist/INSTALL.md"
        )
    return None


def main() -> int:
    args = sys.argv[1:]

    if args and args[0] in ("--help", "-h", "help", "/help"):
        print(HELP)
        return 0
    if args and args[0] in ("--version", "-v", "version"):
        from harness import __version__

        print(f"mali v{__version__}")
        return 0

    if args and args[0] in ("remember", "จำ"):
        from harness.prefs import add_pref

        text = " ".join(args[1:])
        print(f"✓ จำไว้แล้ว: {text}" if add_pref(text) else "ไม่ได้จำ (ว่างหรือซ้ำ)")
        return 0
    if args and args[0] in ("prefs", "preferences"):
        from harness.prefs import PREFS_FILE, load_prefs

        ps = load_prefs()
        print(
            "ความชอบที่จำไว้:"
            if ps
            else 'ยังไม่มีความชอบที่จำไว้ (เพิ่มด้วย: mali remember "...")'
        )
        for i, p in enumerate(ps):
            print(f"  {i}) {p}")
        if ps:
            print(f"  {PREFS_FILE}")
        return 0
    if args and args[0] in ("forget", "ลืม"):
        from harness.prefs import clear_prefs, remove_pref

        rest = args[1:]
        if rest and rest[0].isdigit():
            gone = remove_pref(int(rest[0]))
            print(f"✓ ลืม: {gone}" if gone else "ไม่พบลำดับนั้น")
        else:
            clear_prefs()
            print("✓ ล้างความชอบทั้งหมดแล้ว")
        return 0

    if args and args[0] in ("setup", "config", "--setup"):
        if not sys.stdin.isatty():
            print("mali setup ต้องรันในเทอร์มินัล (interactive)")
            return 64
        from harness.setup_menu import main as setup

        setup()
        return 0

    if not args and sys.stdin.isatty():
        err = _health_check()
        if err:
            print(err)
            return 1
        from harness.session import repl

        return repl()

    if args:
        request = " ".join(args)
    elif not sys.stdin.isatty():
        request = sys.stdin.read().strip()
    else:
        print('ใช้งาน: mali "คำขอภาษาไทย"   เช่น  mali "เช็คพื้นที่ดิสก์"')
        return 64

    if not request:
        print("ไม่มีคำขอ")
        return 64

    err = _health_check()
    if err:
        print(err)
        return 1

    try:
        return run(request)
    except KeyboardInterrupt:
        print("\nยกเลิก")
        return 130
