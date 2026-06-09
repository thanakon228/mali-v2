# -*- coding: utf-8 -*-
"""รัน unit tests ทั้งหมด"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = [
    "test_parse.py",
    "test_safety.py",
    "test_config.py",
    "test_tools.py",
    "test_cmd_fixup.py",
    "test_probe.py",
    "test_vague.py",
]


def main() -> int:
    failed = 0
    for name in TESTS:
        print(f"\n=== {name} ===")
        r = subprocess.run([sys.executable, str(ROOT / "tests" / name)], cwd=ROOT)
        failed += r.returncode
    print(f"\n{'✓ ผ่านหมด' if not failed else '✗ มีพลาด'} ({len(TESTS)} ชุด)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
