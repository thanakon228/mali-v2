# Mali v2

Harness สำหรับผู้ช่วย terminal ภาษาไทย — ใช้โมเดล `thai-cli-3b-r2` ผ่าน Ollama

## เริ่มใช้เร็ว

```bash
cd /home/pixelbot/mali-v2
./install.sh
ollama serve                    # ถ้ายังไม่รัน
mali "เช็คพื้นที่ดิสก์"
```

## คู่มือใช้งาน

**[docs/USAGE.md](docs/USAGE.md)** — ติดตั้ง, คำสั่ง, REPL, ความปลอดภัย, ทดสอบ, แก้ปัญหา

## คำสั่งสำคัญ

```bash
mali                          # REPL
mali "คำขอภาษาไทย"            # one-shot
mali setup                    # ตั้งค่า
mali remember "..."           # จำความชอบ
python3 tests/run_all.py      # unit tests
python3 bench/run.py thai-cli-3b-r2   # benchmark
```

## โมเดล

- ชื่อ Ollama: `thai-cli-3b-r2`
- ติดตั้ง: `~/Desktop/thai-cli-train/dist/INSTALL.md`
- Config: `~/.config/mali-v2/settings.json`

## สถานะ

โปรเจกต์ครบทุก Phase (1–5) — พร้อมทดสอบด้วยตัวเอง ดู [`plan.md`](plan.md)
