#!/usr/bin/env python3
"""Unit tests สำหรับ parse_tool_calls() — รองรับทุกรูปแบบ output ของโมเดล 3B"""

import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from harness.model import parse_tool_calls  # noqa: E402


class TestParseToolCalls(unittest.TestCase):
    def test_native_tool_calls(self):
        msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "run_command",
                        "arguments": {"cmd": "df -h", "explain": "ดูพื้นที่ดิสก์"},
                    }
                }
            ],
        }
        calls = parse_tool_calls(msg)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "run_command")
        self.assertEqual(calls[0]["arguments"]["cmd"], "df -h")
        self.assertEqual(calls[0]["arguments"]["explain"], "ดูพื้นที่ดิสก์")

    def test_native_tool_calls_json_string_args(self):
        msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "run_command",
                        "arguments": '{"cmd":"ls -la","explain":"ดูไฟล์"}',
                    }
                }
            ],
        }
        calls = parse_tool_calls(msg)
        self.assertEqual(calls[0]["arguments"]["cmd"], "ls -la")

    def test_json_in_content(self):
        msg = {
            "role": "assistant",
            "content": (
                '{"name":"run_command","arguments":{"cmd":"df -h","explain":"ดูพื้นที่ดิสก์"}}'
            ),
        }
        calls = parse_tool_calls(msg)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "run_command")
        self.assertEqual(calls[0]["arguments"]["cmd"], "df -h")

    def test_tool_call_tag(self):
        msg = {
            "role": "assistant",
            "content": (
                '<tool_call>{"name":"run_command","arguments":{"cmd":"uname -a",'
                '"explain":"ดูระบบ"}}</tool_call>'
            ),
        }
        calls = parse_tool_calls(msg)
        self.assertEqual(calls[0]["arguments"]["cmd"], "uname -a")

    def test_bash_code_block_suggest_only(self):
        msg = {
            "role": "assistant",
            "content": "ลองใช้คำสั่งนี้:\n```bash\ndf -h\n```",
        }
        calls = parse_tool_calls(msg)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "run_command")
        self.assertEqual(calls[0]["arguments"]["cmd"], "df -h")
        self.assertTrue(calls[0].get("suggest_only"))

    def test_explain_command_json(self):
        msg = {
            "role": "assistant",
            "content": '{"name":"explain_command","arguments":{"cmd":"grep -r foo ."}}',
        }
        calls = parse_tool_calls(msg)
        self.assertEqual(calls[0]["name"], "explain_command")
        self.assertEqual(calls[0]["arguments"]["cmd"], "grep -r foo .")

    def test_empty_message(self):
        self.assertEqual(parse_tool_calls({}), [])
        self.assertEqual(parse_tool_calls({"content": ""}), [])

    def test_plain_text_no_tool(self):
        msg = {"role": "assistant", "content": "สรุป: พื้นที่ดิสก์เหลือ 50GB"}
        self.assertEqual(parse_tool_calls(msg), [])

    def test_tool_calls_priority_over_content(self):
        msg = {
            "role": "assistant",
            "content": '{"name":"run_command","arguments":{"cmd":"wrong"}}',
            "tool_calls": [
                {"function": {"name": "run_command", "arguments": {"cmd": "right"}}}
            ],
        }
        calls = parse_tool_calls(msg)
        self.assertEqual(calls[0]["arguments"]["cmd"], "right")

    def test_embedded_json_with_garbage_prefix(self):
        msg = {
            "role": "assistant",
            "content": (
                ');\r\r\r\n\n{"name": "run_command", '
                '"arguments": {"cmd": "mkdir Desktop", "explain": "สร้างโฟลเดอร์"}}'
            ),
        }
        calls = parse_tool_calls(msg)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["arguments"]["cmd"], "mkdir Desktop")

    def test_embedded_json_nested_arguments(self):
        msg = {
            "role": "assistant",
            "content": '{"name": "run_command", "arguments": {"cmd": "git status"}}',
        }
        calls = parse_tool_calls(msg)
        self.assertEqual(calls[0]["arguments"]["cmd"], "git status")

    def test_multiple_native_tool_calls(self):
        msg = {
            "role": "assistant",
            "tool_calls": [
                {"function": {"name": "run_command", "arguments": {"cmd": "pwd"}}},
                {"function": {"name": "run_command", "arguments": {"cmd": "whoami"}}},
            ],
        }
        calls = parse_tool_calls(msg)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["arguments"]["cmd"], "pwd")
        self.assertEqual(calls[1]["arguments"]["cmd"], "whoami")


if __name__ == "__main__":
    unittest.main()
