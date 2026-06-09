# -*- coding: utf-8 -*-
"""สร้างชุด ~1000 คำถาม — มือใหม่ Linux / ย้ายมาจาก Windows"""

import json
import os
import random

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_ROOT, "data", "beginner_1000.jsonl")

# คำถามแม่แบบ — ใส่ {placeholders}
_TEMPLATES: list[tuple[str, str, list[str]]] = [
    # (category, template, expected_cmd_hints — regex fragments สำหรับวิเคราะห์)
    ("win_file", "จะคัดลอกไฟล์ {f} ไปโฟลเดอร์ {d} ทำยังไง", ["cp|rsync"]),
    ("win_file", "อยาก copy ไฟล์ {f} เหมือนใน Windows", ["cp"]),
    ("win_file", "ย้ายไฟล์ {f} ไป {d}", ["mv"]),
    ("win_file", "ลบไฟล์ {f} ทิ้ง", ["rm"]),
    ("win_file", "ถังขยะอยู่ไหน อยากกู้ไฟล์ที่ลบ", ["trash|restore|~/.local/share/Trash"]),
    ("win_file", "เปิดโฟลเดอร์ {d} ใน file explorer", ["xdg-open|nautilus|thunar|dolphin"]),
    ("win_file", "หาไฟล์ชื่อ {f} ในเครื่อง", ["find|locate|fd"]),
    ("win_file", "แสดงไฟล์ที่ซ่อนอยู่ในโฟลเดอร์นี้", ["ls.*-a|ls -la"]),
    ("win_file", "เปลี่ยนชื่อไฟล์ {f} เป็น {f2}", ["mv"]),
    ("win_file", "สร้างโฟลเดอร์ใหม่ชื่อ {d}", ["mkdir"]),
    ("win_disk", "ไดรฟ์ C อยู่ไหนใน Linux", ["df|lsblk|mount|/"]),
    ("win_disk", "เช็คพื้นที่ดิสก์เหลือเท่าไหร่", ["df"]),
    ("win_disk", "ดูว่า SSD หรือ HDD", ["lsblk|smartctl|rotational"]),
    ("win_disk", "ทำความสะอาดดิสก์เหมือน Disk Cleanup", ["apt.*autoclean|journalctl.*vacuum|du|ncdu"]),
    ("win_disk", "ดูไฟล์ไหนกินพื้นที่เยอะสุด", ["du|ncdu"]),
    ("win_proc", "เปิด Task Manager ดูโปรแกรมค้าง", ["htop|top|ps"]),
    ("win_proc", "ดูว่าโปรแกรมไหนกิน CPU เยอะ", ["top|htop|ps.*cpu"]),
    ("win_proc", "ปิดโปรแกรม {p} ที่ค้าง", ["kill|pkill"]),
    ("win_proc", "ดู process ทั้งหมดที่รันอยู่", ["ps aux|ps -ef"]),
    ("win_proc", "รีสตาร์ทเครื่อง", ["reboot|shutdown -r"]),
    ("win_proc", "ปิดเครื่อง", ["shutdown|poweroff"]),
    ("win_proc", "เครื่องค้าง จะ force quit ยังไง", ["kill|xkill|pkill"]),
    ("win_net", "เช็คว่าต่อ wifi ได้ไหม", ["nmcli|iwconfig|ip"]),
    ("win_net", "ดู IP เครื่องนี้", ["ip a|hostname -I|ifconfig"]),
    ("win_net", "ping ทดสอบเน็ต", ["ping"]),
    ("win_net", "ดูว่า port {port} เปิดอยู่ไหม", ["ss|netstat|lsof"]),
    ("win_pkg", "ติดตั้งโปรแกรม {p} เหมือน install ใน Windows", ["apt install|snap install|flatpak"]),
    ("win_pkg", "ถอนโปรแกรม {p} ออก", ["apt remove|snap remove|dpkg -r"]),
    ("win_pkg", "ดูว่าติดตั้งอะไรไว้บ้าง", ["apt list|dpkg -l|snap list"]),
    ("win_pkg", "อัปเดต Windows update แบบนี้ทำยังไง", ["apt update|apt upgrade"]),
    ("win_perm", "รันแบบ Run as administrator", ["sudo"]),
    ("win_perm", "ไม่มีสิทธิ์ permission denied แก้ยังไง", ["sudo|chmod|chown"]),
    ("win_perm", "เปลี่ยนสิทธิ์ไฟล์ {f} ให้ทุกคนอ่านได้", ["chmod"]),
    ("win_perm", "ไฟล์รันไม่ได้ permission denied", ["chmod \\+x|chmod 755"]),
    ("win_env", "ตั้งค่า PATH เหมือนใน Windows", ["export PATH|echo \\$PATH"]),
    ("win_env", "ดูตัวแปร environment ทั้งหมด", ["env|printenv"]),
    ("win_env", "ตั้งค่า {var}={val} ชั่วคราว", ["export"]),
    ("win_text", "เปิดไฟล์ {f} ด้วย notepad", ["nano|vim|gedit|xdg-open|cat"]),
    ("win_text", "แก้ไขไฟล์ {f} ใน terminal", ["nano|vim|sed"]),
    ("win_text", "ดูเนื้อหาไฟล์ {f}", ["cat|less|head"]),
    ("win_zip", "บีบอัดไฟล์เป็น zip", ["zip"]),
    ("win_zip", "แตกไฟล์ zip", ["unzip"]),
    ("win_zip", "แตกไฟล์ tar.gz", ["tar"]),
    ("win_user", "เปลี่ยนรหัสผ่าน", ["passwd"]),
    ("win_user", "ดูว่า login เป็น user ไหน", ["whoami|id"]),
    ("win_user", "สลับ user", ["su |sudo -u"]),
    ("win_git", "โหลดโปรเจกต์จาก github", ["git clone"]),
    ("win_git", "ดูสถานะ git", ["git status"]),
    ("win_misc", "เครื่องเปิดมานานแค่ไหนแล้ว", ["uptime"]),
    ("win_misc", "ดูเวอร์ชัน Linux", ["uname|lsb_release"]),
    ("win_misc", "เปิด terminal ยังไง", ["ctrl|gnome-terminal|konsole"]),  # meta — อาจไม่มี cmd
    ("win_misc", "คำสั่ง help ดูว่ามีคำสั่งอะไร", ["man |--help|help"]),
    ("win_misc", "จอค้าง กดอะไร", ["tty|chvt|reboot"]),  # vague
    ("win_misc", "Blue Screen ใน Linux เรียกอะไร", ["journalctl|dmesg|kernel panic"]),
    ("win_misc", "Registry อยู่ไหน", ["/etc|dconf|gsettings"]),
    ("win_misc", "Control Panel อยู่ไหน", ["settings|gnome-control|systemsettings"]),
    ("win_misc", "Device Manager ดูยังไง", ["lspci|lsusb|lshw"]),
    ("win_misc", "Print Screen จับภาพหน้าจอ", ["scrot|gnome-screenshot|import"]),
    ("win_misc", "เปิด Calculator", ["gnome-calculator|bc|python3"]),
    ("win_misc", "เช็คแบตเหลือเท่าไหร่", ["upower|acpi"]),
    ("win_misc", "Bluetooth เปิดยังไง", ["bluetoothctl|rfkill"]),
    ("win_misc", "ต่อ printer", ["lpstat|cups"]),
    ("win_thai", "จะลงโปรแกรม {p} ยังไง", ["apt|install|snap"]),
    ("win_thai", "ขอดูไฟล์ในโฟลเดอร์ปัจจุบัน", ["ls"]),
    ("win_thai", "ไปที่โฟลเดอร์ {d}", ["cd"]),
    ("win_thai", "อยู่โฟลเดอร์ไหนอยู่", ["pwd"]),
    ("win_thai", "ค้นหาคำว่า {word} ในไฟล์", ["grep|rg"]),
    ("win_thai", "ดาวน์โหลดไฟล์จากเน็ต", ["wget|curl"]),
    ("win_thai", "เช็คว่าเครื่องร้อนไหม", ["sensors|acpi|htop"]),
    ("win_thai", "ลบทุกอย่างในโฟลเดอร์ {d}", ["rm"]),
    ("win_thai", "สำเนาโฟลเดอร์ {d} ทั้งก้อน", ["cp -r|rsync"]),
    ("win_thai", "เปิดเว็บ {url} ใน browser", ["xdg-open|firefox|chromium"]),
    ("win_thai", "ดู log error ระบบ", ["journalctl|dmesg|/var/log"]),
    ("win_thai", "เช็คว่า {p} ติดตั้งแล้วหรือยัง", ["which|dpkg -l|command -v"]),
    ("win_thai", "รันสคริปต์ {f}.sh", ["bash|chmod|./"]),
    ("win_thai", "ทำไมคำสั่ง {p} ไม่เจอ command not found", ["which|apt install|command -v"]),
    ("win_thai", "จะใช้ sudo ทุกครั้งไม่ได้ ทำยังไง", ["sudoers|usermod"]),
    ("win_thai", "Desktop อยู่ path ไหน", ["~/Desktop|xdg-user-dir"]),
    ("win_thai", "Downloads อยู่ไหน", ["~/Downloads|xdg-user-dir"]),
    ("win_thai", "Documents โฟลเดอร์เอกสารอยู่ไหน", ["xdg-user-dir|~/Documents"]),
    ("win_vague", "ทำยังไง", []),
    ("win_vague", "ช่วยหน่อย", []),
    ("win_vague", "มันไม่ work", []),
    ("win_vague", "พังหมดเลย", []),
    ("win_vague", "ปิดทั้งหมด", ["pkill|killall"]),
    ("win_vague", "ลบทิ้งให้หมด", ["rm"]),
    ("win_vague", "แก้ให้หน่อย", []),
    ("win_vague", "รันให้หน่อย", []),
]

_FILES = [
    "report.pdf", "photo.jpg", "data.txt", "script.sh", "config.json",
    "resume.docx", "music.mp3", "backup.zip", "notes.md", "app.deb",
]
_DIRS = [
    "Desktop", "Documents", "Downloads", "Pictures", "project",
    "backup", "temp", "src", "home", "work",
]
_PROCS = [
    "chrome", "firefox", "node", "python", "nginx",
    "docker", "code", "spotify", "java", "ollama",
]
_PKGS = [
    "htop", "git", "curl", "vim", "nodejs",
    "python3", "docker", "ffmpeg", "zip", "tree",
]
_VARS = [("API_KEY", "abc123"), ("EDITOR", "nano"), ("LANG", "th_TH.UTF-8")]
_WORDS = ["error", "TODO", "password", "import", "function"]
_URLS = ["google.com", "github.com", "example.com"]


def _expand(template: str) -> str:
    f = random.choice(_FILES)
    f2 = random.choice([x for x in _FILES if x != f])
    d = random.choice(_DIRS)
    p = random.choice(_PROCS)
    pkg = random.choice(_PKGS)
    var, val = random.choice(_VARS)
    word = random.choice(_WORDS)
    url = random.choice(_URLS)
    port = random.choice(["80", "443", "3000", "8080", "22"])
    return (
        template.format(f=f, f2=f2, d=d, p=p, pkg=pkg, var=var, val=val, word=word, url=url, port=port)
        .replace("  ", " ")
        .strip()
    )


def generate(n: int = 1000, seed: int = 42) -> list[dict]:
    random.seed(seed)
    seen: set[str] = set()
    out: list[dict] = []
    prefixes = [
        "",
        "ขอ",
        "ช่วย",
        "อยาก",
        "จะ",
        "ยังไง",
        "ทำไม",
        "please ",
        "ใน linux ",
        "บน ubuntu ",
        "ผมใช้ windows มาก่อน ",
    ]

    # สร้างแบบ deterministic: template × prefix × หลาย seed ย่อย
    attempt = 0
    while len(out) < n and attempt < n * 30:
        attempt += 1
        random.seed(seed + attempt)
        cat, tmpl, hints = _TEMPLATES[attempt % len(_TEMPLATES)]
        pref = prefixes[(attempt // len(_TEMPLATES)) % len(prefixes)]
        q = (pref + _expand(tmpl)).strip()
        if q in seen:
            continue
        seen.add(q)
        out.append({"id": len(out) + 1, "cat": cat, "q": q, "hints": hints})

    # fallback: ใส่เลขท้ายถ้ายังไม่ครบ (ไม่ควรเกิด)
    base = len(out)
    while len(out) < n:
        i = len(out) - base
        cat, tmpl, hints = _TEMPLATES[i % len(_TEMPLATES)]
        q = f"{_expand(tmpl)} (#{len(out)})"
        out.append({"id": len(out) + 1, "cat": cat, "q": q, "hints": hints})

    return out[:n]


def save(path: str = OUT) -> str:
    qs = generate(1000)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in qs:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def load(path: str = OUT) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
    return out


if __name__ == "__main__":
    p = save()
    print(f"✓ สร้าง {len(load(p))} คำถาม → {p}")
