"""ตรวจว่าผู้ใช้พิมพ์คำสั่ง shell ตรง ๆ (ข้ามโมเดล)"""

import shlex

from .safety import GREEN_BINS, YELLOW_BINS

_KNOWN = GREEN_BINS | YELLOW_BINS | {"sudo", "doas"}


def extract_shell_command(text: str) -> str | None:
    """
    คืนคำสั่ง shell ถ้าผู้ใช้พิมพ์ตรง ๆ เช่น ps aux, apt list --installed, !git log
    คืน None ถ้าเป็นคำขอภาษาไทยปกติ
    """
    text = (text or "").strip()
    if not text:
        return None
    if text.startswith("!"):
        cmd = text[1:].strip()
        return cmd or None
    try:
        toks = shlex.split(text)
    except ValueError:
        toks = text.split()
    if not toks:
        return None
    head = toks[0].split("/")[-1]
    if head in ("sudo", "doas") and len(toks) > 1:
        head = toks[1].split("/")[-1]
    if head == "git" or head in _KNOWN:
        return text
    return None
