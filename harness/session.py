# -*- coding: utf-8 -*-
"""REPL — โหมดคุยต่อเนื่อง จำบทสนทนา ปลดโมเดลตอนออก"""

import atexit
import signal
import sys

from . import loop, prefs, ui
from .config import get_config
from .model import unload
from .setup_menu import main as setup_menu

D = "\033[2m"
CY = "\033[96m"
GR = "\033[92m"
B = "\033[1m"
AC = "\033[94m"
R = "\033[0m"


def _help():
    print(f"""
  {B}วิธีใช้:{R} พิมพ์คำขอเป็นภาษาไทยแล้วกด Enter เช่น "เช็คดิสก์", "ติดตั้ง htop"
  {B}คำสั่งพิเศษ:{R}
    {AC}/setup{R}           ตั้งค่า
    {AC}/remember <ข้อความ>{R} จำความชอบ เช่น /remember ใช้ pnpm ไม่ใช่ npm
    {AC}/prefs{R}           ดูความชอบที่จำไว้   {AC}/forget [เลข]{R} ลืม
    {AC}/clear{R}           ล้างความจำบทสนทนา
    {AC}/help{R}            ช่วยเหลือ
    {AC}exit{R}             ออก (ปลดโมเดลออกจากหน่วยความจำทันที)
""")


def repl(model: str | None = None) -> int:
    """เข้าโหมด REPL — คืน exit code"""
    session = loop.Session(model)
    state = {"unloaded": False}

    def cleanup():
        if state["unloaded"]:
            return
        state["unloaded"] = True
        print(f"\n{D}ปิดการใช้งานโมเดล {session.model} · คืนหน่วยความจำ…{R}")
        unload(session.model)

    atexit.register(cleanup)
    for sig in (signal.SIGTERM, signal.SIGHUP):
        try:
            signal.signal(sig, lambda *_: sys.exit(0))
        except (ValueError, OSError):
            pass

    ui.welcome(session.model)
    while True:
        try:
            print(f"\n{ui.statusline(session.model)}")
            q = input(f"{CY}{B}›{R} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not q:
            continue
        low = q.lower()
        if low in ("exit", "quit", "ออก", "/exit", "/quit", "/q"):
            return 0
        if low in ("/help", "help", "/?"):
            _help()
            continue
        if low in ("/clear", "clear"):
            session = loop.Session(session.model)
            print(f"{D}ล้างความจำแล้ว เริ่มบทสนทนาใหม่{R}")
            continue
        if low.startswith("/remember") or low.startswith("/จำ"):
            text = q.split(" ", 1)[1].strip() if " " in q else ""
            if prefs.add_pref(text):
                session.refresh_system()
                print(f"{GR}✓ จำไว้แล้ว: {text}{R}")
            else:
                print(f"{D}ใช้: /remember <สิ่งที่อยากให้จำ>{R}")
            continue
        if low in ("/prefs", "/preferences"):
            ps = prefs.load_prefs()
            print(f"{B}ความชอบที่จำไว้:{R}" if ps else f"{D}ยังไม่มี — เพิ่มด้วย /remember ...{R}")
            for i, p in enumerate(ps):
                print(f"  {AC}{i}{R}) {p}")
            continue
        if low.startswith("/forget") or low.startswith("/ลืม"):
            rest = q.split(" ", 1)[1].strip() if " " in q else ""
            if rest.isdigit():
                gone = prefs.remove_pref(int(rest))
                print(f"{GR}✓ ลืม: {gone}{R}" if gone else f"{D}ไม่พบลำดับนั้น{R}")
            else:
                prefs.clear_prefs()
                print(f"{GR}✓ ล้างความชอบทั้งหมดแล้ว{R}")
            session.refresh_system()
            continue
        if low in ("/setup", "setup"):
            setup_menu()
            cfg = get_config()
            if cfg["model"] != session.model or cfg["ollama_host"] != session.chat.host:
                session = loop.Session(cfg["model"])
                print(f"{GR}ซิงก์การตั้งค่าแล้ว — โมเดล {cfg['model']}{R}")
            continue
        try:
            session.ask(q)
        except KeyboardInterrupt:
            print(f"\n{D}(ยกเลิกคำขอนี้){R}")
