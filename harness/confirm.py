"""UI ยืนยันก่อนรันคำสั่ง — [1] รัน [2] ยกเลิก [3] อธิบาย"""

from .config import get_config
from .safety import Risk

C_RED = "\033[91m"
C_YEL = "\033[93m"
C_GRN = "\033[92m"
C_CYAN = "\033[96m"
C_DIM = "\033[2m"
C_BOLD = "\033[1m"
C_OFF = "\033[0m"

_BADGE = {
    Risk.GREEN: f"{C_GRN}● ปลอดภัย{C_OFF}",
    Risk.YELLOW: f"{C_YEL}● ต้องยืนยัน{C_OFF}",
    Risk.RED: f"{C_RED}● อันตราย{C_OFF}",
}


def ask(prompt: str) -> str:
    """อ่าน input จากผู้ใช้ — เปิด /dev/tty เผื่อ stdin ถูก pipe"""
    try:
        with open("/dev/tty", "r+") as tty:
            tty.write(prompt)
            tty.flush()
            return tty.readline().strip()
    except OSError:
        return input(prompt)


def explain_more(cmd: str) -> str:
    """ให้โมเดลขยายความคำสั่งทีละส่วนเป็นภาษาไทย"""
    from .model import ModelError, OllamaChat

    try:
        msg = OllamaChat().chat(
            [
                {
                    "role": "system",
                    "content": (
                        "อธิบายคำสั่ง shell เป็นภาษาไทยสั้นมาก ไม่เกิน 3 บรรทัด "
                        "บอกแค่ว่าทำอะไรและ flag สำคัญ ห้ามเกริ่น ห้ามใส่หัวข้อ"
                    ),
                },
                {"role": "user", "content": f"อธิบายคำสั่งนี้สั้น ๆ:\n{cmd}"},
            ],
            options={"num_predict": 160, "temperature": 0.1},
        )
        text = (msg.get("content") or "").strip()
        for junk in ("/no_think", "/think", "", ""):
            text = text.replace(junk, "")
        return text.strip() or "(โมเดลไม่ตอบ)"
    except ModelError as e:
        return f"(อธิบายไม่ได้: {e})"


def confirm(cmd: str, risk: Risk, why: str, explain: str = "") -> bool:
    """ถามยืนยันก่อนรัน — red ต้องพิมพ์ 'รัน' อีกชั้น"""
    print()
    if explain:
        print(f"  {C_CYAN}คุณกำลังจะ: {explain}{C_OFF}")
    print(f"  {_BADGE[risk]}  {C_DIM}({why}){C_OFF}")
    print(f"  {C_BOLD}$ {cmd}{C_OFF}")

    if get_config()["auto_yes"] and risk is Risk.GREEN:
        print(f"  {C_DIM}(auto-yes — คำสั่งปลอดภัย){C_OFF}")
        return True

    if risk is Risk.RED:
        print(f"  {C_RED}⚠ คำสั่งนี้ทำลายข้อมูลได้ ระวังให้ดี{C_OFF}")

    while True:
        print(
            f"  {C_BOLD}[1]{C_OFF} ใช่ รันเลย    "
            f"{C_BOLD}[2]{C_OFF} ยกเลิก    "
            f"{C_BOLD}[3]{C_OFF} อธิบายคำสั่งนี้ให้ละเอียด"
        )
        ans = ask("  เลือก › ").strip().lower()

        if ans in ("3", "d", "อธิบาย"):
            print(f"\n{C_DIM}{explain_more(cmd)}{C_OFF}\n")
            continue
        if ans in ("2", "n", "no", "ไม่", "ยกเลิก"):
            return False
        if ans in ("1", "y", "yes", "ใช่", "ย"):
            if risk is Risk.RED:
                t = ask(f"  ยืนยันอีกครั้ง — พิมพ์ {C_BOLD}รัน{C_OFF}: ").strip()
                return t in ("รัน", "run")
            return True
