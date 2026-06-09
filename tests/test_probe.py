# -*- coding: utf-8 -*-
"""
Bug probe — unit tests ที่ออกแบบเพื่อค้นหาบัคที่ชุด test ปกติไม่ครอบคลุม

รัน: python3 tests/test_probe.py
"""

import os
import re
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench.questions import QUESTIONS
from harness.cmd_fixup import normalize_cmd
from harness.config import is_small_model, is_suggest_only, normalize_host
from harness.loop import Session, _coach
from harness.quick_route import try_route
from harness.retrieve import format_examples
from harness.shell_input import extract_shell_command

# บัคที่ยืนยันแล้ว — test จะ fail จนกว่าจะแก้
KNOWN_BUGS: list[str] = []


def _bug(msg: str):
    KNOWN_BUGS.append(msg)
    print(f"  ✗ BUG: {msg}")
    return False


def test_cmd_fixup_ollama_split():
    fixed, _ = normalize_cmd("pkill -f ol llama")
    if fixed != "pkill -f ollama":
        return _bug(f"cmd_fixup ollama: got {fixed!r}")
    print("  ✓ cmd_fixup แก้ ol llama")
    return True


def test_cmd_fixup_no_merge_two_processes():
    """pkill chrome firefox ไม่ควรถูกรวมเป็น chromefirefox"""
    fixed, note = normalize_cmd("pkill chrome firefox")
    if fixed in ("pkill -f chromefirefox", "pkill chromefirefox"):
        return _bug(f"cmd_fixup รวม 2 process ผิด: {fixed!r} (note={note})")
    if fixed != "pkill chrome firefox":
        return _bug(f"cmd_fixup เปลี่ยนคำสั่งที่ถูกอยู่แล้ว: {fixed!r}")
    print("  ✓ cmd_fixup ไม่รวม chrome + firefox")
    return True


def test_cmd_fixup_no_merge_chrome_firefox_with_f():
    fixed, _ = normalize_cmd("pkill -f chrome firefox")
    if fixed == "pkill -f chromefirefox":
        return _bug(f"cmd_fixup รวม -f chrome firefox ผิด: {fixed!r}")
    print("  ✓ cmd_fixup ไม่รวม -f chrome firefox")
    return True


def test_quick_route_ollama():
    if try_route("ปิดollama") != ("pkill -f ollama", "ปิด process ollama"):
        return _bug("quick_route ไม่ match ปิดollama")
    if try_route("ปิดทั้งหมด") is not None:
        return _bug(f"quick_route false positive ปิดทั้งหมด: {try_route('ปิดทั้งหมด')}")
    print("  ✓ quick_route ollama / ไม่ match ปิดทั้งหมด")
    return True


def test_shell_input():
    cases = [
        ("pgrep -a ollama", True),
        ("chmod a+rw f", True),
        ("ปิดollama", False),
        ("echo hi", True),
    ]
    for text, want in cases:
        got = extract_shell_command(text) is not None
        if got != want:
            return _bug(f"shell_input {text!r}: want={want} got={got}")
    print("  ✓ shell_input direct vs ไทย")
    return True


def test_examples_must_patterns():
    for q in QUESTIONS:
        for pat in q.get("must", []):
            if not re.search(pat, q["ex"], re.I):
                return _bug(f"example #{q['id']} must ไม่ match: {pat!r} vs {q['ex']!r}")
    print(f"  ✓ examples must regex ครบ {len(QUESTIONS)} ข้อ")
    return True


def test_config_trained_model():
    if is_suggest_only("thai-cli-3b-r2"):
        return _bug("thai-cli-3b-r2 ไม่ควรเป็น suggest_only")
    if is_small_model("thai-cli-3b-r2"):
        return _bug("thai-cli-3b-r2 ไม่ควรถูกจัดเป็น small model")
    print("  ✓ config thai-cli-3b-r2 ไม่ suggest_only")
    return True


def test_normalize_host():
    if normalize_host("11434") != "http://localhost:11434":
        return _bug(f"normalize_host port: {normalize_host('11434')!r}")
    print("  ✓ normalize_host")
    return True


def test_coach_pkill_and_permission():
    r1 = _coach("run_command", "x", "only one pattern can be provided", set())
    if "pattern" not in r1.lower():
        return _bug("_coach ไม่มี hint pkill pattern")
    r2 = _coach("run_command", "x", "killing pid 1 failed: Operation not permitted", set())
    if "pgrep" not in r2:
        return _bug("_coach ไม่มี hint operation not permitted")
    print("  ✓ _coach hints")
    return True


def test_retrieve_ปิด_ollama():
    block = format_examples("ปิด ollama")
    if "ollama" not in block.lower():
        return _bug(f"retrieve ไม่ดึงตัวอย่าง ollama: {block!r}")
    print("  ✓ retrieve ปิด ollama")
    return True


def test_loop_quick_route_exit_code_on_failure():
    """loop.ask ควรคืน exit != 0 เมื่อคำสั่ง routed ล้มเหลว"""
    with patch("harness.tools.run_command", return_value="exit_code=2\nfailed"):
        with patch("harness.loop.try_route", return_value=("pkill -f ollama", "ปิด")):
            code = Session().ask("ปิดollama")
    if code == 0:
        return _bug("loop.ask quick_route คืน 0 แม้ run_command ล้มเหลว")
    print("  ✓ loop exit code เมื่อ quick_route ล้มเหลว")
    return True


def test_loop_direct_shell_exit_code_on_failure():
    with patch("harness.tools.run_direct_command", return_value="exit_code=1\nfail"):
        with patch("harness.loop.extract_shell_command", return_value="false"):
            code = Session().ask("false")
    if code == 0:
        return _bug("loop.ask direct shell คืน 0 แม้คำสั่งล้มเหลว")
    print("  ✓ loop exit code เมื่อ direct shell ล้มเหลว")
    return True


def test_parse_garbage_prefix():
    from harness.model import parse_tool_calls

    msg = {
        "content": ');\n{"name": "run_command", "arguments": {"cmd": "ls"}}',
    }
    calls = parse_tool_calls(msg)
    if not calls or calls[0]["arguments"]["cmd"] != "ls":
        return _bug(f"parse garbage prefix ล้มเหลว: {calls}")
    print("  ✓ parse JSON หลัง garbage prefix")
    return True


def run():
    tests = [
        test_cmd_fixup_ollama_split,
        test_cmd_fixup_no_merge_two_processes,
        test_cmd_fixup_no_merge_chrome_firefox_with_f,
        test_quick_route_ollama,
        test_shell_input,
        test_examples_must_patterns,
        test_config_trained_model,
        test_normalize_host,
        test_coach_pkill_and_permission,
        test_retrieve_ปิด_ollama,
        test_loop_quick_route_exit_code_on_failure,
        test_loop_direct_shell_exit_code_on_failure,
        test_parse_garbage_prefix,
    ]
    passed = sum(1 for t in tests if t())
    failed = len(tests) - passed
    print()
    if KNOWN_BUGS:
        print("=== สรุปบัคที่พบ ===")
        for i, b in enumerate(KNOWN_BUGS, 1):
            print(f"  {i}. {b}")
    print(f"\n{'✓ ไม่พบบัค' if not failed else '✗ พบบัค'}: {passed}/{len(tests)} ผ่าน, {failed} ล้ม")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
