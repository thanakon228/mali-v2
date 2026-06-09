# -*- coding: utf-8 -*-
"""ตรวจคำขอกำกวม — ถามกลับแทนเดาคำสั่ง"""

import re

_VAGUE_ONLY = re.compile(
    r"^(?:ขอ|ช่วย|อยาก|จะ|please\s*)*"
    r"(ทำยังไง|ช่วยหน่อย|แก้ให้หน่อย|รันให้หน่อย|มันไม่\s*work)\s*$",
    re.I,
)

_DANGEROUS_VAGUE = re.compile(
    r"^(?:ขอ|ช่วย|อยาก|จะ|please\s*)*"
    r"(ปิดทั้งหมด|ลบทิ้งให้หมด|พังหมดเลย)\s*$",
    re.I,
)


def clarify(user_request: str) -> str | None:
    """คืนข้อความถามกลับ หรือ None ถ้าคำขอชัดพอ"""
    t = (user_request or "").strip()
    if not t:
        return "ยังไม่มีคำขอ — ลองบอกสิ่งที่อยากทำ เช่น \"ดูพื้นที่ดิสก์\""

    if _VAGUE_ONLY.match(t):
        return (
            "คำขอยังกว้างเกินไป — ระบุชัด ๆ ว่าต้องการทำอะไร\n"
            "  เช่น \"ดูพื้นที่ดิสก์\"  \"ติดตั้ง git\"  \"ดู process ที่รันอยู่\""
        )

    if _DANGEROUS_VAGUE.match(t):
        return (
            "คำขอนี้กว้างและอาจอันตราย — ระบุเป้าหมายให้ชัด\n"
            "  เช่น \"ปิดโปรแกรม chrome\"  \"ลบไฟล์ temp ในโฟลเดอร์นี้\"  "
            "ไม่ใช่ปิด/ลบทั้งหมด"
        )

    return None
