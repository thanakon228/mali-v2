# คู่มือใช้งาน Mali v2

ผู้ช่วย terminal ภาษาไทย — แปลงคำขอภาษาไทยเป็นคำสั่ง shell แล้วรันให้ (ผ่านด่านความปลอดภัย) ใช้โมเดล `thai-cli-3b-r2` ผ่าน Ollama

---

## สิ่งที่ต้องมีก่อนใช้

| รายการ | หมายเหตุ |
|--------|----------|
| Python 3.10+ | `python3 --version` |
| Ollama | รัน `ollama serve` ค้างไว้ |
| โมเดล `thai-cli-3b-r2` | ดูวิธีติดตั้งที่ `~/Desktop/thai-cli-train/dist/INSTALL.md` |

ตรวจว่าโมเดลพร้อม:

```bash
ollama list | grep thai-cli-3b-r2
ollama run thai-cli-3b-r2 "เช็คดิสก์"   # ทดสอบสั้น ๆ
```

---

## ติดตั้ง

```bash
cd /home/pixelbot/mali-v2
./install.sh
```

สคริปต์จะ:
1. ตรวจ Python และ Ollama
2. ตั้งโมเดลเริ่มต้น (default: `thai-cli-3b-r2`)
3. สร้าง symlink `~/.local/bin/mali`

ถ้า `mali` ยังไม่เจอ ให้เพิ่มใน `~/.bashrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

หรือรันตรงจาก repo:

```bash
python3 /home/pixelbot/mali-v2/mali "เช็คพื้นที่ดิสก์"
```

---

## คำสั่งหลัก

### One-shot (สั่งครั้งเดียว)

```bash
mali "เช็คพื้นที่ดิสก์"          # รัน df -h อัตโนมัติ (GREEN)
mali "แสดงไฟล์ในโฟลเดอร์นี้"     # ls -la
mali "ลบไฟล์ /tmp/test.txt"     # ถามยืนยันก่อน (YELLOW)
```

อ่านจาก pipe:

```bash
echo "ดู process ทั้งหมด" | mali
```

### REPL (คุยต่อเนื่อง)

```bash
mali
```

เข้าโหมดแชท — จำบทสนทนาก่อนหน้า ออกด้วย `exit` หรือ Ctrl+D (โมเดลจะถูก unload จาก RAM)

คำสั่งพิเศษใน REPL:

| คำสั่ง | ทำอะไร |
|--------|--------|
| `/help` | ช่วยเหลือ |
| `/setup` | เปิดเมนูตั้งค่า |
| `/remember ใช้ pnpm` | จำความชอบ |
| `/prefs` | ดูความชอบ |
| `/forget 0` | ลืมรายการที่ 0 |
| `/clear` | ล้างความจำบทสนทนา |
| `exit` | ออก + unload โมเดล |

### ตั้งค่า

```bash
mali setup
```

เมนูตั้งค่า: โมเดล, Ollama host, timeout, auto-yes, โหมดแนะนำเท่านั้น ฯลฯ

Config เก็บที่: `~/.config/mali-v2/settings.json`

### จำความชอบ (นอก REPL)

```bash
mali remember "ใช้ pnpm ไม่ใช่ npm"
mali prefs
mali forget 0
```

---

## ความปลอดภัย 3 ระดับ

Harness ตัดสินเองฝั่งโค้ด — **ไม่ไว้ใจโมเดล**

| ระดับ | ตัวอย่าง | พฤติกรรม |
|-------|---------|----------|
| **GREEN** | `ls`, `df -h`, `git status`, `pwd` | รันทันที |
| **YELLOW** | `rm`, `mv`, `sudo`, คำสั่งไม่รู้จัก | ถามยืนยัน `[1] รัน [2] ยกเลิก [3] อธิบาย` |
| **RED** | `rm -rf /`, `curl \| bash`, fork bomb | ยืนยัน 2 ชั้น — ต้องพิมพ์ `รัน` |

เมื่อปฏิเสธคำสั่ง (YELLOW/RED) ระบบถามเหตุผล:
- **[4] พิมพ์คำสั่งที่ถูกเอง** → บันทึกใน `~/.config/mali-v2/learned.jsonl` ใช้เป็น few-shot คราวหน้า

---

## ตัวแปรสภาพแวดล้อม

| ตัวแปร | ค่าเริ่มต้น | ความหมาย |
|--------|------------|----------|
| `MALI_MODEL` | `thai-cli-3b-r2` | ชื่อโมเดล Ollama |
| `MALI_OLLAMA` | `http://localhost:11434` | URL ของ Ollama |
| `MALI_YES` | `false` | ข้ามยืนยันเฉพาะ GREEN |
| `MALI_TIMEOUT` | `120` | timeout วินาที |
| `MALI_MAX_STEPS` | `8` | รอบสูงสุดต่อคำขอ |

ตัวอย่าง:

```bash
MALI_MODEL=thai-cli-3b-r2 mali "เช็คดิสก์"
MALI_YES=1 mali "ls -la"    # ข้ามยืนยัน green (yellow/red ยังถาม)
```

---

## ไฟล์ config ของผู้ใช้

```
~/.config/mali-v2/
├── settings.json      # ค่าตั้งหลัก
├── preferences.md     # ความชอบ (/remember)
├── learned.jsonl      # คำสั่งที่เรียนรู้จากการแก้
└── history.log        # ประวัติคำสั่งที่รัน (redact ข้อมูลลับ)
```

---

## ทดสอบระบบ

### Unit tests (ไม่ต้องมี Ollama)

```bash
cd /home/pixelbot/mali-v2
python3 tests/run_all.py
```

### ทดสอบด้วยมือ (ต้องมี Ollama + โมเดล)

```bash
# 1. เช็คสุขภาพ
mali --version
curl -s http://localhost:11434/api/tags | head

# 2. คำสั่งปลอดภัย — ควรรันทันที
mali "เช็คพื้นที่ดิสก์"

# 3. คำสั่งเสี่ยง — ควรถามยืนยัน
mali "ลบไฟล์ /tmp/test.txt"

# 4. Few-shot — ควรเสนอ find/du ที่สมเหตุสมผล
mali "หาไฟล์ใหญ่สุด 5 อัน"

# 5. REPL
mali
# พิมพ์: เช็คดิสก์
# พิมพ์: exit

# 6. ตั้งค่า
mali setup
```

### Benchmark (100 ข้อ, ใช้เวลานาน)

```bash
python3 bench/run.py thai-cli-3b-r2
# ผลบันทึกที่ bench/results.json
# เป้า: accuracy ≥ 90%, tool_rate ≥ 95%
```

---

## แก้ปัญหาที่พบบ่อย

### รันแล้วค้าง / ไม่มีอะไรขึ้น

**สาเหตุที่พบบ่อย:**

1. **มี `ollama run` ค้างอยู่** — ชนกับ `mali` ทำให้ API ช้ามากหรือไม่ตอบ
   ```bash
   ps aux | grep "ollama run"    # หา process
   kill <pid>                    # ปิด session ที่ค้าง
   ```

2. **โหลดโมเดลครั้งแรก** — ครั้งแรกหลังเปิด Ollama อาจใช้เวลา 5–15 วินาที (โหลดเข้า VRAM) รอ spinner `กำลังคิด…`

3. **Ollama ค้าง** — รีสตาร์ทแล้วลองใหม่:
   ```bash
   killall ollama; sleep 2; ollama serve &
   ```

4. **โหมด suggest_only เปิดอยู่** — แสดงคำสั่งแต่ไม่รัน (ดู `mali setup` เมนู 8 → ตั้งเป็น `off`)

**ห้าม** รัน `ollama run thai-cli-3b-r2` พร้อมกับ `mali` — ใช้อย่างใดอย่างหนึ่ง

### `ต่อ Ollama ไม่ได้`

```bash
ollama serve          # เปิด server
# หรือเช็คว่า service รันอยู่
curl http://localhost:11434/api/tags
```

### `ยังไม่มีโมเดล thai-cli-3b-r2`

ดู `~/Desktop/thai-cli-train/dist/INSTALL.md` — ต้อง import GGUF เข้า Ollama ก่อน

### โมเดลตอบแต่ไม่รันคำสั่ง

โมเดล 3B บางครั้งส่ง JSON ใน `content` แทน `tool_calls` — harness รองรับแล้วผ่าน `parse_tool_calls()` ถ้ายังไม่รัน ลอง:

```bash
mali setup   # เช็คว่าโมเดลถูกต้อง
python3 tests/test_parse.py   # ทดสอบ parser
```

### คำสั่งถูกบล็อก / ถามยืนยันบ่อย

ปกติสำหรับ YELLOW/RED — กด `[1]` เพื่อรัน หรือ `[3]` ให้อธิบายคำสั่งก่อน

### โมเดลกิน RAM ค้างหลังออก

ออกจาก REPL ด้วย `exit` — harness เรียก `keep_alive=0` อัตโนมัติ

---

## โครงสร้างโปรเจกต์ (สรุป)

```
mali-v2/
├── mali                 # entry point
├── install.sh
├── harness/             # โค้ดหลัก
├── data/examples.jsonl  # few-shot 100 ข้อ
├── bench/               # benchmark
├── tests/               # unit tests
└── docs/USAGE.md        # ไฟล์นี้
```

---

## ตัวอย่างการใช้งานจริง

```bash
# ดูระบบ
mali "เครื่องนี้เปิดมานานแค่ไหน"
mali "ดู process ที่กิน cpu มากสุด"

# ไฟล์
mali "หาไฟล์ .py ทั้งหมดในโฟลเดอร์นี้"
mali "นับบรรทัดในไฟล์ main.py"

# git
mali "ดูสถานะ git"
mali "ดู commit ล่าสุด 5 อัน"

# ติดตั้ง (จะถามยืนยัน)
mali "ติดตั้ง htop"
```

---

*Mali v2 · harness ภาษาไทย · โมเดล thai-cli-3b-r2*
