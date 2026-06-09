# -*- coding: utf-8 -*-
"""Banner, Spinner, สี ANSI"""

import itertools
import os
import subprocess
import sys
import threading

from . import __version__
from . import tools

R = "\033[0m"
B = "\033[1m"
D = "\033[2m"
CY = "\033[96m"
GR = "\033[92m"
YE = "\033[93m"
RED = "\033[38;5;196m"
WHITE = "\033[97m"
BLUE = "\033[38;5;27m"
LEAF = "\033[38;5;34m"

NAME = "mali"

FLOWER = [
    f"{RED}     ❀ ❀ ❀{R}",
    f"{RED}   ❀{WHITE} ✿ ✿ ✿ {RED}❀{R}",
    f"{RED}   ❀{WHITE} ✿{BLUE}◉{WHITE}✿ {RED}❀{R}",
    f"{RED}   ❀{WHITE} ✿ ✿ ✿ {RED}❀{R}",
    f"{RED}     ❀ ❀ ❀{R}",
    f"{LEAF}       ┃{R}",
    f"{LEAF}      ╲┃╱{R}",
]

SUGGESTIONS = [
    "เช็คพื้นที่ดิสก์ที่เหลือ",
    "หาไฟล์ใหญ่สุด 5 อันในโฟลเดอร์นี้",
    "ดู process ที่กินแรมเยอะสุด",
    "ติดตั้ง htop",
]

_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_CYAN = "\033[96m"
_OFF = "\033[0m"


class Spinner:
    def __init__(self, text: str = "กำลังคิด"):
        self.text = text
        self._stop = threading.Event()
        self._thread = None
        self._active = sys.stderr.isatty()

    def __enter__(self):
        if self._active:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        else:
            # ไม่มี TTY (pipe/CI) — อย่าเงียบ ไม่งั้นดูเหมือนค้าง
            print(f"{_CYAN}… {self.text}{_OFF}", flush=True)
        return self

    def _run(self):
        for ch in itertools.cycle(_FRAMES):
            if self._stop.is_set():
                break
            sys.stderr.write(f"\r{_CYAN}{ch}{_OFF} {self.text}…  ")
            sys.stderr.flush()
            self._stop.wait(0.08)

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        if self._active:
            sys.stderr.write("\r\033[K")
            sys.stderr.flush()
        return False


def _short(path: str) -> str:
    home = os.path.expanduser("~")
    return path.replace(home, "~", 1) if path.startswith(home) else path


def _git_branch(cwd: str) -> str | None:
    try:
        b = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if b.returncode != 0:
            return None
        dirty = subprocess.run(
            ["git", "-C", cwd, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()
        return b.stdout.strip() + ("*" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        return None


def statusline(model: str) -> str:
    sep = f" {D}│{R} "
    cwd = _short(tools._CWD)
    parts = [f"{RED}❀{R} {CY}{model}{R}", f"{D}{cwd}{R}"]
    branch = _git_branch(tools._CWD)
    if branch:
        parts.append(f"{LEAF}⎇ {branch}{R}")
    if tools.SUGGEST_ONLY:
        parts.append(f"{YE}แนะนำเท่านั้น{R}")
    parts.append(f"{D}/help · exit{R}")
    return "  " + sep.join(parts)


def welcome(model: str, cwd: str | None = None):
    from .config import is_suggest_only

    cwd = _short(cwd or os.getcwd())
    print()
    for line in FLOWER:
        print(line)
    print()
    print(f"  {B}{NAME}{R} {D}·{R} ผู้ช่วย terminal ภาษาไทย   {D}v{__version__}{R}")
    print(f"  {CY}{model}{R} {D}· Ollama (local) ·{R} {D}{cwd}{R}")
    if is_suggest_only(model):
        print(
            f"  {YE}⚠ โหมดแนะนำคำสั่งเท่านั้น — โมเดลนี้เล็ก "
            f"จะเสนอคำสั่งให้คัดลอกไปรันเอง (ไม่รันให้){R}"
        )
    print()
    print(f"  {D}ลองพิมพ์เป็นภาษาไทยได้เลย เช่น:{R}")
    for s in SUGGESTIONS:
        print(f"    {GR}›{R} {s}")
    print()
    print(f"  {D}/setup · /help · พิมพ์ exit เพื่อออก{R}")
    print()
