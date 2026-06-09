# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.quick_route import try_route
from harness.vague import clarify


def test_vague_blocks():
    assert clarify("ช่วยหน่อย")
    assert clarify("ปิดทั้งหมด")
    assert clarify("ลบทิ้งให้หมด")
    print("  ✓ vague จับคำขอกว้าง")
    return True


def test_vague_allows_specific():
    assert clarify("ดูพื้นที่ดิสก์") is None
    assert clarify("ติดตั้ง git") is None
    print("  ✓ vague ปล่อยคำขอชัด")
    return True


def test_quick_route_task_manager():
    r = try_route("เปิด Task Manager ดูโปรแกรมค้าง")
    assert r and r[0] == "htop", r
    print("  ✓ quick_route Task Manager")
    return True


def test_quick_route_trash():
    r = try_route("ถังขยะอยู่ไหน")
    assert r and "Trash" in r[0], r
    print("  ✓ quick_route ถังขยะ")
    return True


def run():
    tests = [
        test_vague_blocks,
        test_vague_allows_specific,
        test_quick_route_task_manager,
        test_quick_route_trash,
    ]
    passed = sum(1 for t in tests if t())
    failed = len(tests) - passed
    print(f"\n{'✓ ผ่านหมด' if not failed else '✗ มีพลาด'}: {passed}/{len(tests)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(run())
