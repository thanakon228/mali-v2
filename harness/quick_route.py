# -*- coding: utf-8 -*-
"""แมปคำขอภาษาไทยที่รู้จัก → คำสั่ง shell (ข้ามโมเดลเมื่อชัดเจน)"""

import re

# (regex, cmd, explain) — เรียงจากเฉพาะ → กว้าง
_ROUTES: list[tuple[re.Pattern, str, str]] = [
    # process / ollama
    (re.compile(r"ปิด\s*ollama|หยุด\s*ollama|kill\s*ollama", re.I), "pkill -f ollama", "ปิด process ollama"),
    (re.compile(r"pgrep.*ollama|หา.*process.*ollama|ดู.*process.*ollama", re.I), "pgrep -a ollama", "หา process ollama"),
    # Windows → Linux ยอดนิยม
    (re.compile(r"task\s*manager|ดูโปรแกรมค้าง|โปรแกรมค้าง", re.I), "htop", "ดู process (Task Manager)"),
    (re.compile(r"ถังขยะ|recycle\s*bin|กู้ไฟล์ที่ลบ", re.I), "ls -la ~/.local/share/Trash/files 2>/dev/null || ls -la ~/.local/share/Trash 2>/dev/null || echo 'ไม่พบถังขยะ'", "ดูถังขยะ"),
    (re.compile(r"desktop.*(อยู่|path)|โฟลเดอร์\s*desktop", re.I), "xdg-user-dir DESKTOP", "หา path Desktop"),
    (re.compile(r"downloads.*(อยู่|path)|โฟลเดอร์\s*downloads", re.I), "xdg-user-dir DOWNLOAD", "หา path Downloads"),
    (re.compile(r"documents.*(อยู่|path)|โฟลเดอร์\s*documents|โฟลเดอร์เอกสาร", re.I), "xdg-user-dir DOCUMENTS", "หา path Documents"),
    (re.compile(r"ไดรฟ์\s*c|drive\s*c", re.I), "df -h /", "ดูพาร์ทิชันหลัก (เทียบไดรฟ์ C)"),
    (re.compile(r"disk\s*cleanup|ทำความสะอาดดิสก์", re.I), "sudo apt autoremove -y && sudo journalctl --vacuum-time=7d", "ทำความสะอาดดิสก์"),
    (re.compile(r"windows\s*update|อัปเดต\s*windows", re.I), "sudo apt update && sudo apt upgrade -y", "อัปเดตแพ็กเกจระบบ"),
    (re.compile(r"run\s*as\s*administrator|รันแบบ\s*admin", re.I), "sudo -v", "เตรียมสิทธิ์ sudo (เทียบ Run as administrator)"),
    (re.compile(r"registry|รีจิสทรี", re.I), "ls /etc | head -20", "ดู config ระบบ (เทียบ Registry)"),
    (re.compile(r"control\s*panel|แผงควบคุม", re.I), "xdg-open gnome-control-center 2>/dev/null || xdg-open systemsettings 2>/dev/null || echo 'เปิด Settings จากเมนูระบบ'", "เปิด Settings"),
    (re.compile(r"device\s*manager|ดูอุปกรณ์", re.I), "lspci && lsusb", "ดูอุปกรณ์ (Device Manager)"),
    (re.compile(r"print\s*screen|จับภาพหน้าจอ", re.I), "scrot ~/screenshot-$(date +%Y%m%d-%H%M%S).png 2>/dev/null || gnome-screenshot -f ~/screenshot.png", "จับภาพหน้าจอ"),
    (re.compile(r"bluetooth.*เปิด|เปิด\s*bluetooth", re.I), "bluetoothctl show", "ดูสถานะ Bluetooth"),
    (re.compile(r"wifi.*(เช็ค|ต่อ)|เช็ค.*wifi|ต่อ.*wifi", re.I), "nmcli device wifi list 2>/dev/null || iwconfig 2>/dev/null", "ดู WiFi"),
    (re.compile(r"blue\s*screen|จอฟ้า|kernel\s*panic", re.I), "journalctl -k -b -1 --no-pager | tail -30", "ดู log kernel ล่าสุด"),
    (re.compile(r"เครื่องเปิดมานาน", re.I), "uptime", "ดูเวลาที่เครื่องเปิดอยู่"),
    (re.compile(r"ปิดเครื่อง(?!\s+\w)", re.I), "shutdown -h now", "ปิดเครื่อง"),
    (re.compile(r"รีสตาร์ทเครื่อง|reboot\s*เครื่อง", re.I), "sudo reboot", "รีสตาร์ทเครื่อง"),
]


def try_route(user_request: str) -> tuple[str, str] | None:
    """คืน (cmd, explain) หรือ None ถ้าไม่ match"""
    t = (user_request or "").strip()
    if not t:
        return None

    compact = re.sub(r"\s+", "", t.lower())
    if compact in ("ปิดollama", "หยุดollama"):
        return ("pkill -f ollama", "ปิด process ollama")

    for pat, cmd, explain in _ROUTES:
        if pat.search(t):
            return (cmd, explain)

    return None
