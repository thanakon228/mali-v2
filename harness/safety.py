"""Safety gate — จัดระดับความเสี่ยงของคำสั่งฝั่งโค้ด (ไม่ไว้ใจโมเดล)"""

import re
import shlex
from enum import Enum


class Risk(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


GREEN_BINS = {
    "cd", "pushd", "popd", "dirs",
    "ls", "cat", "head", "tail", "less", "more", "pwd", "whoami", "id",
    "date", "cal", "uptime", "echo", "printf", "which", "type", "whereis",
    "file", "stat", "wc", "sort", "uniq", "cut", "tr", "column", "nl",
    "grep", "egrep", "fgrep", "rg", "ag", "find", "fd", "locate", "tree",
    "df", "du", "free", "ps", "top", "htop", "uname", "hostname", "env",
    "printenv", "history", "man", "tldr", "help", "true", "false", "seq",
    "basename", "dirname", "realpath", "readlink", "lsblk", "lscpu",
    "lsusb", "lspci", "ip", "ifconfig", "ping", "dig", "nslookup", "host",
    "curl", "wget",
    "jq", "yq", "xxd", "od", "md5sum", "sha256sum", "diff", "cmp",
}

GREEN_GIT = {
    "status", "log", "diff", "show", "branch", "remote", "blame",
    "stash", "tag", "describe", "rev-parse", "ls-files", "config",
}

RED_PATTERNS = [
    (r"\brm\b.*\s-[a-z]*r[a-z]*f|\brm\b.*\s-[a-z]*f[a-z]*r", "rm -rf"),
    (r"\brm\b.*\s-[a-z]*r\b.*\s-[a-z]*f\b|\brm\b.*\s-[a-z]*f\b.*\s-[a-z]*r\b", "rm -r -f (flag แยก)"),
    (r"\brm\b\s+(-[a-z]+\s+)*(/|/\*|~|\$HOME)(\s|$)", "ลบ root / home"),
    (r"\bmkfs\b", "ฟอร์แมตพาร์ทิชัน"),
    (r"\bdd\b.*\bof=/dev/", "เขียนทับ block device ด้วย dd"),
    (r">\s*/dev/(sd|nvme|hd|mmcblk|vd)", "เขียนทับดิสก์"),
    (r"\bof=/dev/(sd|nvme|hd|mmcblk|vd)", "เขียนทับดิสก์"),
    (r":\(\)\s*\{.*:\|:.*\}", "fork bomb"),
    (r"\bchmod\b\s+-R\s+(0?777|a\+rwx)\s+/", "chmod -R 777 ที่ root"),
    (r"\bchown\b\s+-R\b.*\s/(\s|$)", "chown -R ที่ root"),
    (r"\bshred\b", "shred (ลบกู้ไม่ได้)"),
    (r">\s*/etc/(passwd|shadow|fstab|sudoers)", "เขียนทับไฟล์ระบบสำคัญ"),
    (r"\bgit\b.*\breset\b.*--hard", "git reset --hard (ทิ้งงานที่ยังไม่ commit)"),
    (r"\bgit\b.*\bpush\b.*(-f\b|--force)", "git push --force"),
    (r"\bgit\b.*\bclean\b.*-[a-z]*f", "git clean -f (ลบไฟล์ที่ยังไม่ track)"),
    (r"\b(curl|wget|fetch)\b[^|]*\|\s*(sudo\s+)?(bash|sh|zsh|fish|python3?|perl|ruby|node)\b",
     "ดาวน์โหลดจากเน็ตแล้ว pipe เข้า shell/interpreter (อันตรายมาก)"),
    (r"\bfind\s+(/\S*|~\S*|\$HOME\S*)\s.*-delete\b", "find -delete บน path สำคัญ (root/absolute)"),
]

_FIND_DESTRUCTIVE = re.compile(r"-delete\b|-exec(dir)?\b|-ok(dir)?\b|-fprintf?\b", re.IGNORECASE)
_CURL_DANGEROUS = re.compile(
    r"(^|\s)(-d\b|--data|-X\b|--request|-o\b|-O\b|--output|-T\b|--upload-file|-F\b|--form)",
    re.IGNORECASE,
)

YELLOW_BINS = {
    "rm", "rmdir", "mv", "cp", "ln", "touch", "mkdir", "dd", "truncate",
    "chmod", "chown", "chgrp", "kill", "pkill", "killall", "pgrep",
    "systemctl", "service", "mount", "umount", "swapon", "swapoff",
    "apt", "apt-get", "dpkg", "pacman", "yum", "dnf", "snap", "flatpak",
    "pip", "pip3", "npm", "pnpm", "yarn", "cargo", "go", "make", "cmake",
    "docker", "podman", "kubectl", "systemd-run", "crontab", "at",
    "useradd", "userdel", "usermod", "passwd", "groupadd", "visudo",
    "iptables", "ufw", "firewall-cmd", "sysctl", "modprobe", "insmod",
    "git", "gh", "ssh", "scp", "rsync", "tar", "unzip", "zip", "gzip",
    "sed", "tee", "ln", "fdisk", "parted", "mkswap", "ip",
}

SHELLY = re.compile(r"[|&;><`$]|\$\(|\&\&|\|\|")


def classify(cmd: str) -> tuple[Risk, str]:
    """คืน (ระดับความเสี่ยง, เหตุผล) ของคำสั่ง"""
    text = cmd.strip()
    if not text:
        return Risk.GREEN, "คำสั่งว่าง"

    for pat, why in RED_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return Risk.RED, why

    if re.search(r"\bfind\b", text, re.IGNORECASE) and _FIND_DESTRUCTIVE.search(text):
        return Risk.YELLOW, "find มีคำสั่งลบ/รันคำสั่งกับไฟล์ที่เจอ"

    if re.search(r"\b(curl|wget)\b", text, re.IGNORECASE) and _CURL_DANGEROUS.search(text):
        return Risk.YELLOW, "curl/wget ส่งข้อมูลออก/เขียนไฟล์ (กันข้อมูลรั่ว)"

    bins = _binaries(text)
    elevated = "sudo" in bins or "doas" in bins
    bins = {b for b in bins if b not in ("sudo", "doas")}

    has_shelly = bool(SHELLY.search(text))
    writes_file = bool(re.search(r"-o\b|--output\b|>\s*\S", text))

    for b in bins:
        if b == "git":
            sub = _git_subcommand(text)
            if sub not in GREEN_GIT:
                return Risk.YELLOW, f"git {sub or '(แก้สถานะ repo)'}"
            continue
        if b in YELLOW_BINS:
            return Risk.YELLOW, f"คำสั่ง '{b}' แก้ไขสถานะระบบ"
        if b not in GREEN_BINS:
            return Risk.YELLOW, f"ไม่รู้จักคำสั่ง '{b}' — ขอยืนยันก่อน"

    if elevated:
        return Risk.YELLOW, "ใช้ sudo ยกสิทธิ์"
    if writes_file:
        return Risk.YELLOW, "คำสั่งเขียนไฟล์ออกมา"
    if has_shelly:
        return Risk.GREEN, "อ่านอย่างเดียว (มี pipe)"

    return Risk.GREEN, "อ่านอย่างเดียว"


def _binaries(text: str) -> set[str]:
    out: set[str] = set()
    for seg in re.split(r"\|\||&&|[|;&]", text):
        seg = seg.strip()
        if not seg:
            continue
        try:
            toks = shlex.split(seg)
        except ValueError:
            toks = seg.split()
        i = 0
        while i < len(toks) and re.match(r"^\w+=", toks[i]):
            i += 1
        if i < len(toks):
            out.add(toks[i].split("/")[-1])
    return out


def _git_subcommand(text: str) -> str | None:
    try:
        toks = shlex.split(text)
    except ValueError:
        toks = text.split()
    seen_git = False
    for t in toks:
        if t.split("/")[-1] == "git":
            seen_git = True
            continue
        if seen_git and not t.startswith("-"):
            return t
    return None
