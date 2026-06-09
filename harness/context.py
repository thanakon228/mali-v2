"""รวบรวม context ของระบบเพื่อแนบไปกับ system prompt"""

import os
import platform
import shutil
import subprocess

_CHECK_TOOLS = (
    "rg", "fd", "tree", "jq", "bat", "exa", "eza", "docker",
    "podman", "git", "gh", "curl", "wget", "python3", "node", "go",
)
_PKG_MGRS = ("apt", "dnf", "yum", "pacman", "zypper", "apk", "brew")


def _env_facts(cwd: str) -> tuple[str, list[str], list[str]]:
    pkg = next((p for p in _PKG_MGRS if shutil.which(p)), "?")
    tools = [t for t in _CHECK_TOOLS if shutil.which(t)]
    proj = []
    has = lambda f: os.path.exists(os.path.join(cwd, f))
    if has("package.json"):
        proj.append("Node")
    if has("pyproject.toml") or has("requirements.txt") or has("setup.py"):
        proj.append("Python")
    if has("Cargo.toml"):
        proj.append("Rust")
    if has("go.mod"):
        proj.append("Go")
    if has("Makefile"):
        proj.append("Makefile")
    if has("Dockerfile") or has("docker-compose.yml") or has("compose.yaml"):
        proj.append("Docker")
    return pkg, tools, proj


def gather() -> str:
    cwd = os.getcwd()
    user = os.environ.get("USER", "?")
    shell = os.environ.get("SHELL", "?")
    osname = f"{platform.system()} {platform.release()}"

    try:
        entries = sorted(os.listdir(cwd))[:40]
        listing = "  ".join(entries) if entries else "(ว่าง)"
    except OSError:
        listing = "(อ่านไม่ได้)"

    git = _git_summary(cwd)
    pkg, tools, proj = _env_facts(cwd)

    lines = [
        f"ระบบปฏิบัติการ: {osname}",
        f"ผู้ใช้: {user}    shell: {shell}",
        f"package manager: {pkg}"
        + ("  ← ใช้ตัวนี้เท่านั้น (ห้ามเดา apt ถ้าไม่ใช่)" if pkg not in ("?", "apt") else ""),
        f"เครื่องมือที่ติดตั้ง: {', '.join(tools) if tools else '(พื้นฐานเท่านั้น)'}  — อย่าใช้เครื่องมือนอกรายการนี้",
        f"โฟลเดอร์ปัจจุบัน (cwd): {cwd}",
        f"ไฟล์ใน cwd: {listing}",
    ]
    if proj:
        lines.append(f"ชนิดโปรเจกต์ใน cwd: {', '.join(proj)}")
    if git:
        lines.append(f"git: {git}")
    return "\n".join(lines)


def _git_summary(cwd: str) -> str | None:
    try:
        branch = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if branch.returncode != 0:
            return None
        dirty = subprocess.run(
            ["git", "-C", cwd, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        n = len([line for line in dirty.stdout.splitlines() if line.strip()])
        state = f"{n} ไฟล์ยังไม่ commit" if n else "สะอาด"
        return f"branch {branch.stdout.strip()} ({state})"
    except (OSError, subprocess.SubprocessError):
        return None
