# -*- coding: utf-8 -*-
"""ตรวจ Ollama — แจ้งวิธีรัน และถามว่าจะสตาร์ทให้ไหม"""

import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

from .config import get_config
from .confirm import ask


def _ping(host: str) -> tuple[bool, list[str]]:
    try:
        with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=3) as r:
            names = [m["name"] for m in json.loads(r.read()).get("models", [])]
        return True, names
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return False, []


def _start_serve() -> bool:
    if not shutil.which("ollama"):
        print("❌ ไม่พบคำสั่ง ollama — ติดตั้งจาก https://ollama.com/download")
        return False
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as e:
        print(f"❌ สตาร์ท ollama serve ไม่ได้: {e}")
        return False

    host = get_config()["ollama_host"]
    print("  กำลังรอ Ollama…")
    for _ in range(15):
        time.sleep(1)
        if _ping(host)[0]:
            print("  ✓ Ollama พร้อมแล้ว")
            return True
    print("  ⏳ รอนานเกินไป — ลองรัน ollama serve ในเทอร์มินัลอื่น")
    return False


def ensure_ollama(*, interactive: bool | None = None) -> str | None:
    """
    ตรวจว่า Ollama รันและมีโมเดล — คืนข้อความ error หรือ None ถ้าพร้อม
    interactive: ถามสตาร์ท ollama serve อัตโนมัติ (default = มี TTY)
    """
    if interactive is None:
        interactive = sys.stdin.isatty()

    cfg = get_config()
    host, model = cfg["ollama_host"], cfg["model"]
    ok, names = _ping(host)

    if not ok:
        print(f"\n❌ Ollama ยังไม่รัน — ต่อ {host} ไม่ได้")
        print("   ต้องเปิด server ก่อนด้วยคำสั่ง:")
        print("     ollama serve")
        if interactive:
            ans = ask("  ให้รัน ollama serve เลยไหม? [y/N] ").strip().lower()
            if ans in ("y", "yes", "ใช่"):
                if _start_serve():
                    ok, names = _ping(host)
        if not ok:
            return "ยกเลิก — รัน ollama serve ก่อน แล้วลอง mali อีกครั้ง"

    if model not in names and not any(
        n.split(":")[0] == model.split(":")[0] for n in names
    ):
        return (
            f"❌ ยังไม่มีโมเดล '{model}'\n"
            f"   ดูวิธีติดตั้ง: ~/Desktop/thai-cli-train/dist/INSTALL.md"
        )

    return None
