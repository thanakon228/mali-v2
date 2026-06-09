# -*- coding: utf-8 -*-
"""ทดสอบ config reload หลัง save_settings"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import harness.config as cfg


def _with_temp_config(fn):
    td = tempfile.mkdtemp()
    old_dir, old_file, old_resolved = cfg.CONFIG_DIR, cfg.SETTINGS_FILE, cfg._resolved
    try:
        cfg.CONFIG_DIR = td
        cfg.SETTINGS_FILE = os.path.join(td, "settings.json")
        cfg.invalidate_config()
        return fn()
    finally:
        cfg.CONFIG_DIR = old_dir
        cfg.SETTINGS_FILE = old_file
        cfg._resolved = old_resolved
        cfg.invalidate_config()


def test_get_config_reloads_after_save():
    def run():
        first = cfg.get_config()["ollama_host"]
        cfg.save_settings({"ollama_host": "http://127.0.0.1:19999"})
        second = cfg.get_config()["ollama_host"]
        if first == second or second != "http://127.0.0.1:19999":
            print(f"  ✗ FAIL reload: {first!r} -> {second!r}")
            return False
        print("  ✓ config reload หลัง save_settings")
        return True

    return _with_temp_config(run)


def test_history_log_default():
    def run():
        cfg.save_settings({})
        val = cfg.get_config().get("history_log")
        if val is not True:
            print(f"  ✗ FAIL history_log default: {val!r}")
            return False
        print("  ✓ history_log default = True")
        return True

    return _with_temp_config(run)


def run():
    tests = [test_get_config_reloads_after_save, test_history_log_default]
    passed = sum(1 for t in tests if t())
    failed = len(tests) - passed
    print(f"\n{'✓ ผ่านหมด' if not failed else '✗ มีพลาด'}: {passed}/{len(tests)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(run())
