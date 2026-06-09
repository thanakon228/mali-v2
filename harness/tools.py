"""Tool execution + safety gate"""

import os
import re
import shlex
import subprocess

from .cmd_fixup import normalize_cmd
from .config import CONFIG_DIR, get_config
from .confirm import C_BOLD, C_CYAN, C_DIM, C_GRN, C_OFF, ask, confirm
from .safety import Risk, classify

SUGGEST_ONLY = False
CURRENT_REQUEST = ""

_CWD = os.getcwd()
_SENTINEL = "__MALI_CWD__"
_HISTORY = os.path.join(CONFIG_DIR, "history.log")

_REDACT_PATTERNS = [
    (re.compile(r"(?i)(password|passwd|token|secret|api[_-]?key)\s*[=:]\s*\S+"), r"\1=[REDACTED]"),
    (re.compile(r"(?i)(-d\b|--data)\s+@?\S*\.ssh/\S+"), r"\1 [REDACTED]"),
    (re.compile(r"(?i)(AWS_|GITHUB_|OPENAI_)[A-Z0-9_]+=\S+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)Bearer\s+\S+"), "Bearer [REDACTED]"),
]

_INTENT = {
    "mkdir": "สร้างโฟลเดอร์", "rm": "ลบไฟล์/โฟลเดอร์", "rmdir": "ลบโฟลเดอร์",
    "mv": "ย้ายหรือเปลี่ยนชื่อไฟล์", "cp": "คัดลอกไฟล์", "touch": "สร้างไฟล์เปล่า",
    "ln": "สร้างลิงก์ไฟล์", "chmod": "เปลี่ยนสิทธิ์ไฟล์", "chown": "เปลี่ยนเจ้าของไฟล์",
    "chgrp": "เปลี่ยนกลุ่มเจ้าของไฟล์", "kill": "ปิด process", "pkill": "ปิด process",
    "killall": "ปิด process ทั้งหมดตามชื่อ", "dd": "เขียนข้อมูลระดับดิสก์",
    "systemctl": "ควบคุม service ของระบบ", "service": "ควบคุม service",
    "mount": "เมานต์ดิสก์", "umount": "ยกเลิกเมานต์ดิสก์",
    "curl": "ดาวน์โหลด/เรียกข้อมูลจากอินเทอร์เน็ต", "wget": "ดาวน์โหลดไฟล์",
    "tar": "บีบอัด/แตกไฟล์", "zip": "บีบอัดไฟล์", "unzip": "แตกไฟล์ zip",
    "gzip": "บีบอัดไฟล์", "gunzip": "แตกไฟล์", "git": "จัดการ git",
    "pip": "ติดตั้ง/จัดการแพ็กเกจ Python", "pip3": "ติดตั้ง/จัดการแพ็กเกจ Python",
    "npm": "ติดตั้ง/จัดการแพ็กเกจ Node", "make": "build โปรเจกต์",
    "useradd": "เพิ่มผู้ใช้", "userdel": "ลบผู้ใช้", "crontab": "ตั้งงานตามเวลา",
}


def _redact_history(cmd: str) -> str:
    out = cmd
    for pat, repl in _REDACT_PATTERNS:
        out = pat.sub(repl, out)
    return out


def _log_history(cmd: str, code: int) -> None:
    if not get_config().get("history_log", True):
        return
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        safe = _redact_history(cmd)
        with open(_HISTORY, "a", encoding="utf-8") as f:
            f.write(f"{_CWD}\t[{code}]\t{safe}\n")
    except OSError:
        pass


def _truncate(text: str) -> str:
    limit = get_config()["max_output_chars"]
    if len(text) <= limit:
        return text
    half = limit // 2
    return (
        text[:half]
        + f"\n{C_DIM}…[ตัด {len(text) - limit} ตัวอักษรตรงกลาง]…{C_OFF}\n"
        + text[-half:]
    )


def _intent_fallback(cmd: str) -> str:
    try:
        toks = shlex.split(cmd)
    except ValueError:
        toks = cmd.split()
    if not toks:
        return "รันคำสั่งด้านล่าง"
    head = toks[0].split("/")[-1]
    if head in ("sudo", "doas") and len(toks) > 1:
        head = toks[1].split("/")[-1]
    if head in ("apt", "apt-get", "dnf", "yum", "pacman"):
        if "install" in toks:
            pkgs = " ".join(
                t for t in toks
                if not t.startswith("-") and t not in (head, "install", "sudo", "apt", "apt-get", "-y")
            )
            return f"ติดตั้งโปรแกรม {pkgs}".strip()
        if "remove" in toks or "uninstall" in toks:
            return "ถอนโปรแกรมออก"
        if "update" in toks or "upgrade" in toks:
            return "อัปเดตแพ็กเกจของระบบ"
        if "list" in toks:
            return "ดูรายการแพ็กเกจที่ติดตั้ง"
    return _INTENT.get(head, f"รันคำสั่ง {head}")


def exit_code_from_result(result: str) -> int:
    """ดึง exit code จากข้อความคืนของ run_command"""
    if not result:
        return 1
    first = result.split("\n", 1)[0]
    if first.startswith("exit_code="):
        try:
            return int(first.split("=", 1)[1])
        except ValueError:
            return 1
    if first.startswith("ผู้ใช้ปฏิเสธ"):
        return 130
    return 1


def run_direct_command(cmd: str) -> str:
    """ผู้ใช้พิมพ์ shell ตรง ๆ — อธิบายก่อน แล้วถามยืนยัน"""
    intent = _intent_fallback(cmd)
    print(f"\n{C_DIM}↳ คุณพิมพ์คำสั่ง shell เอง — ไม่ผ่านโมเดล{C_OFF}")
    print(f"  {C_CYAN}จะทำ: {intent}{C_OFF}")
    return run_command({"cmd": cmd, "explain": intent})


def _on_reject(bad_cmd: str) -> str | None:
    """หลังผู้ใช้ปฏิเสธ → ถามเหตุผล แล้วเรียนรู้ คืนคำสั่งทดแทนถ้าจะรันต่อ"""
    from .config import load_settings
    from . import learned

    if not load_settings().get("learn", True):
        return None

    print(
        f"  {C_DIM}ยกเลิกเพราะ?  [1] คำสั่งผิด  [2] อันตราย  [3] เปลี่ยนใจ  [4] พิมพ์คำสั่งที่ถูกเอง{C_OFF}"
    )
    r = ask("  เลือก › ").strip()

    if r == "4":
        good = ask("  พิมพ์คำสั่งที่ถูก: ").strip()
        if good:
            learned.add(CURRENT_REQUEST or bad_cmd, good, bad_cmd, source="user")
            print(f"  {C_GRN}✓ จำไว้แล้ว คราวหน้าจะแนะนำคำสั่งนี้{C_OFF}")
            if ask("  รันคำสั่งนี้เลยไหม? [y/N] ").strip().lower() in ("y", "yes", "ใช่"):
                return good
    elif r == "2":
        print(f"  {C_DIM}รับทราบว่าคำสั่งนี้อันตราย จะระวังคราวหน้า{C_OFF}")
    elif r == "1":
        print(f"  {C_DIM}รับทราบ — คราวหน้าจะพยายามเสนอคำสั่งที่ถูกกว่า{C_OFF}")
    return None


def run_command(args: dict) -> str:
    cmd = (args or {}).get("cmd", "").strip()
    explain = (args or {}).get("explain", "")
    suggest = SUGGEST_ONLY or bool((args or {}).get("_suggest_only"))

    if not cmd:
        print(f"  {C_DIM}(โมเดลส่งคำสั่งว่างมา — ข้าม){C_OFF}")
        return "ไม่มีคำสั่งให้รัน (args.cmd ว่าง) — โปรดส่งคำสั่ง shell จริงใน field cmd"

    fixed, fix_note = normalize_cmd(cmd)
    if fix_note and fixed != cmd:
        print(f"  {C_DIM}↳ แก้คำสั่งอัตโนมัติ: {fix_note}{C_OFF}")
        print(f"  {C_DIM}  เดิม: {cmd}{C_OFF}")
        cmd = fixed

    intent = explain.strip()
    while intent.startswith("คุณกำลังจะ"):
        intent = intent[len("คุณกำลังจะ"):].lstrip(". ").strip()
    intent = intent or _intent_fallback(cmd)

    risk, why = classify(cmd)

    if suggest:
        from .confirm import _BADGE

        print(f"\n  {C_CYAN}แนะนำให้รัน: {intent}{C_OFF}")
        print(f"  {_BADGE[risk]}  {C_BOLD}$ {cmd}{C_OFF}")
        print(f"  {C_DIM}↳ คัดลอกไปรันเองได้ (โหมดนี้ไม่รันให้){C_OFF}")
        _log_history(f"[แนะนำ] {cmd}", -1)
        return (
            f"แสดงคำสั่งให้ผู้ใช้แล้วในโหมดแนะนำ (ไม่ได้รัน): {cmd}\n"
            "สรุปสั้น ๆ ให้ผู้ใช้ว่าแนะนำคำสั่งอะไรและทำอะไร แล้วจบ ไม่ต้องเรียก tool อีก"
        )

    if not confirm(cmd, risk, why, intent):
        replacement = _on_reject(cmd)
        if not replacement:
            return f"ผู้ใช้ปฏิเสธไม่ให้รันคำสั่ง: {cmd}"
        cmd = replacement.strip()
        risk, why = classify(cmd)
        if not confirm(cmd, risk, why, "คำสั่งที่คุณให้มา"):
            return f"ผู้ใช้ปฏิเสธไม่ให้รันคำสั่ง: {cmd}"

    global _CWD
    wrapped = f"{cmd}\n__rc=$?; printf '\\n{_SENTINEL}%s\\n' \"$PWD\"; exit $__rc"
    timeout = get_config()["request_timeout"]
    try:
        proc = subprocess.run(
            wrapped,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=_CWD if os.path.isdir(_CWD) else None,
        )
    except subprocess.TimeoutExpired:
        return f"คำสั่ง '{cmd}' รันนานเกิน {timeout} วินาที ถูกยกเลิก"
    except OSError as e:
        return f"รันคำสั่งไม่ได้: {e}"

    out = (proc.stdout or "") + (proc.stderr or "")
    new_cwd = None
    lines = out.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith(_SENTINEL):
            new_cwd = ln[len(_SENTINEL):].strip()
            del lines[i]
            break
    if new_cwd and os.path.isdir(new_cwd):
        _CWD = new_cwd
    out = _truncate("\n".join(lines).strip())

    if out:
        print(out)
    print(f"{C_DIM}[exit {proc.returncode}]  {C_DIM}{_CWD}{C_OFF}")
    _log_history(cmd, proc.returncode)

    return f"exit_code={proc.returncode}\ncwd={_CWD}\n{out or '(ไม่มี output)'}"


def explain_command(args: dict) -> str:
    cmd = (args or {}).get("cmd", "").strip()
    risk, why = classify(cmd)
    print(f"\n  {C_DIM}อธิบายคำสั่ง (ไม่รัน): {C_BOLD}{cmd or '(ว่าง)'}{C_OFF}")
    return (
        f"(โหมดอธิบาย ไม่รันจริง) คำสั่ง: {cmd}\n"
        f"ระดับความเสี่ยง: {risk.value} — {why}\n"
        f"จงอธิบายเป็นภาษาไทยให้ผู้ใช้ในข้อความตอบกลับ (ไม่ต้องเรียก tool อีก)"
    )


DISPATCH = {
    "run_command": run_command,
    "explain_command": explain_command,
}


def call(name: str, args: dict) -> str:
    fn = DISPATCH.get(name)
    if not fn:
        print(f"  {C_DIM}(โมเดลเรียก tool ที่ไม่มี: {name!r} — ข้าม){C_OFF}")
        return f"ไม่รู้จัก tool '{name}' — มีแค่ run_command กับ explain_command"
    return fn(args)
