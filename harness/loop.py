"""Agent loop — โมเดลตัดสินใจ → safety gate → รันคำสั่ง → วนจนจบ"""

from . import context, prefs, retrieve, tools
from .config import get_config, is_suggest_only
from .model import ModelError, OllamaChat, parse_tool_calls
from .prompt import TOOLS, system_prompt
from .ui import Spinner

C_DIM = "\033[2m"
C_CYAN = "\033[96m"
C_OFF = "\033[0m"


def _coach(name: str, cmd: str, result: str, seen: set) -> str:
    """แปะคำแนะนำให้โมเดลจาก error ยอดฮิต / คำสั่งซ้ำ"""
    if name != "run_command" or not cmd:
        return ""
    hints = []
    if cmd in seen:
        hints.append("คำสั่งนี้รันซ้ำแล้วและได้ผลเดิม — อย่าทำซ้ำ ลองวิธีอื่นหรือสรุปว่าทำไม่ได้")
    low = result.lower()
    if "command not found" in low or ("not found" in low and "exit_code=127" in low):
        hints.append("คำสั่ง/โปรแกรมนี้ไม่มีในเครื่อง — ใช้เครื่องมือที่ติดตั้งแล้ว หรือบอกวิธีติดตั้ง")
    if "permission denied" in low:
        hints.append("สิทธิ์ไม่พอ — อาจต้องใช้ sudo นำหน้า")
    if "no such file or directory" in low:
        hints.append("ไม่พบไฟล์/โฟลเดอร์ตามที่ระบุ — ตรวจ path หรือ ls ดูก่อน")
    if "unrecognized option" in low or "invalid option" in low or "illegal option" in low:
        hints.append("ใช้ flag ผิด — ตรวจ --help ของคำสั่งนั้น หรือใช้ flag มาตรฐาน")
    return ("\n[harness] " + " · ".join(hints)) if hints else ""


class Session:
    """บทสนทนาหนึ่งครั้ง — จำ messages ข้ามเทิร์น"""

    def __init__(self, model: str | None = None):
        self.chat = OllamaChat(model=model or get_config()["model"])
        self.suggest_only = is_suggest_only(self.chat.model)
        tools.SUGGEST_ONLY = self.suggest_only
        self._notified = False
        self.messages = [
            {
                "role": "system",
                "content": system_prompt(context.gather(), prefs.prefs_block()),
            }
        ]

    @property
    def model(self) -> str:
        return self.chat.model

    def refresh_system(self):
        """อัปเดต system prompt โดยไม่ล้างบทสนทนา"""
        self.messages[0] = {
            "role": "system",
            "content": system_prompt(context.gather(), prefs.prefs_block()),
        }

    def ask(self, user_request: str) -> int:
        """ประมวลผล 1 คำขอ (อาจวนเรียก tool หลายรอบ) คืน exit code"""
        if self.suggest_only and not self._notified:
            self._notified = True
            print(
                f"{C_DIM}⚠ โมเดล {self.chat.model} เล็ก — โหมดแนะนำคำสั่งเท่านั้น "
                f"(แสดงคำสั่งให้ ไม่รันเอง){C_OFF}"
            )

        tools.CURRENT_REQUEST = user_request
        examples = retrieve.format_examples(user_request)
        parts = []
        if examples:
            parts.append(examples)
        parts.append(f"คำขอ: {user_request}")
        self.messages.append({"role": "user", "content": "\n\n".join(parts)})

        last_content = ""
        noop = 0
        seen_cmds: set[str] = set()

        for _ in range(get_config()["max_steps"]):
            try:
                with Spinner():
                    msg = self.chat.chat(self.messages, tools=TOOLS)
            except ModelError as e:
                print(f"\n❌ {e}")
                return 1

            self.messages.append(msg)
            content = (msg.get("content") or "").strip()
            if content:
                last_content = content

            tool_calls = parse_tool_calls(msg)
            if not tool_calls:
                if content:
                    print(f"\n{C_CYAN}{content}{C_OFF}")
                return 0

            if content and not content.startswith("{"):
                print(f"\n{C_CYAN}{content}{C_OFF}")

            for call in tool_calls:
                name = call["name"]
                args = dict(call.get("arguments") or {})
                if call.get("suggest_only"):
                    args["_suggest_only"] = True

                cmd = (args.get("cmd") or "").strip()
                noop = noop + 1 if (name == "run_command" and not cmd) else 0

                result = tools.call(name, args)
                result += _coach(name, cmd, result, seen_cmds)
                if cmd:
                    seen_cmds.add(cmd)
                self.messages.append({"role": "tool", "name": name, "content": result})

            if noop >= 2:
                print(f"\n{C_DIM}โมเดลส่งคำสั่งว่างซ้ำ ๆ — หยุดไว้ก่อน{C_OFF}")
                break

        if last_content:
            print(f"\n{C_CYAN}{last_content}{C_OFF}")
        print(
            f"\n{C_DIM}(ทำได้ไม่ครบใน {get_config()['max_steps']} ขั้น — "
            f"โมเดล {self.model} อาจเล็กไปสำหรับงานนี้){C_OFF}"
        )
        return 2


def run(user_request: str, model: str | None = None) -> int:
    """รัน 1 คำขอแบบ one-shot"""
    return Session(model).ask(user_request)
