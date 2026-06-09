# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.cmd_fixup import normalize_cmd
from harness.quick_route import try_route


def test_fixup_ollama_split():
    fixed, note = normalize_cmd("pkill -f ol llama")
    assert fixed == "pkill -f ollama", fixed
    assert note
    print("  ✓ แก้ pkill -f ol llama → pkill -f ollama")
    return True


def test_fixup_unchanged():
    fixed, note = normalize_cmd("pkill -9 chrome")
    assert fixed == "pkill -9 chrome"
    assert note is None
    print("  ✓ ไม่แก้คำสั่งที่ถูกอยู่แล้ว")
    return True


def test_fixup_windows_taskmgr():
    fixed, note = normalize_cmd("taskmgr")
    assert fixed == "htop", fixed
    assert note
    print("  ✓ แทน taskmgr → htop")
    return True


def test_fixup_windows_notepad():
    fixed, _ = normalize_cmd("notepad file.txt")
    assert fixed.startswith("nano"), fixed
    print("  ✓ แทน notepad → nano")
    return True


def test_quick_route_ollama():
    r = try_route("ปิดollama")
    assert r == ("pkill -f ollama", "ปิด process ollama"), r
    print("  ✓ quick_route ปิดollama")
    return True


def run():
    tests = [
        test_fixup_ollama_split,
        test_fixup_unchanged,
        test_fixup_windows_taskmgr,
        test_fixup_windows_notepad,
        test_quick_route_ollama,
    ]
    passed = sum(1 for t in tests if t())
    failed = len(tests) - passed
    print(f"\n{'✓ ผ่านหมด' if not failed else '✗ มีพลาด'}: {passed}/{len(tests)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(run())
