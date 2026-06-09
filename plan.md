# Mali v2 — Harness ใหม่ + โมเดล `thai-cli-3b-r2`

> **Workspace:** `/home/pixelbot/mali-v2`  
> **เป้าหมาย:** สร้าง CLI assistant ภาษาไทยใหม่ทั้งก้อน ใช้โมเดลที่เทรนแล้ว (`thai-cli-3b-r2`) ผ่าน Ollama  
> **ไม่ทำในแผนนี้:** เทรนโมเดลใหม่, Web UI, Rhino integration

---

## บริบทสำหรับ Cursor Agent

โปรเจกต์นี้ fork แนวคิดจาก `~/thai-cli-harness` แต่เขียนใหม่ให้สะอาด โดย:

- **เก็บ:** โมเดล `thai-cli-3b-r2` (~96% bench accuracy), dataset/bench อ้างอิงจาก `~/Desktop/thai-cli-train`
- **สร้างใหม่:** harness ทั้งหมดใน `mali-v2/harness/`
- **หัวใจพิเศษ:** `parse_tool_calls()` — โมเดล 3B มักส่ง JSON ใน `content` แทน structured `tool_calls`

### โมเดลที่ใช้

| รายการ | ค่า |
|--------|-----|
| ชื่อ Ollama | `thai-cli-3b-r2` |
| Base | Qwen2.5-Coder-3B-Instruct + QLoRA |
| GGUF | `thai-cli-3b-r2.q4_K_M.gguf` (~1.8GB) |
| Temperature | `0` (บังคับใน request) |
| Tool หลัก | `run_command` (field: `cmd`, `explain`) |

### Output ที่โมเดลอาจส่ง (ต้องรองรับทุกแบบ)

1. `message.tool_calls[].function.arguments` — ปกติ
2. `message.content` = `{"name":"run_command","arguments":{"cmd":"...","explain":"..."}}`
3. `message.content` = `<tool_call>{...}</tool_call>`
4. `message.content` = code block `` ```bash ... ``` `` — fallback suggest-only

---

## โครงสร้างไฟล์เป้าหมาย

```
mali-v2/
├── plan.md                 ← ไฟล์นี้
├── README.md
├── mali                      # entry → ~/.local/bin/mali
├── install.sh
├── pyproject.toml
├── harness/
│   ├── __init__.py           # __version__
│   ├── cli.py                # one-shot, REPL, subcommands
│   ├── loop.py               # agent loop
│   ├── model.py              # Ollama + parse_tool_calls()
│   ├── prompt.py             # system prompt + TOOLS
│   ├── tools.py              # run_command, explain_command
│   ├── safety.py             # GREEN / YELLOW / RED
│   ├── context.py            # cwd, OS, git, packages
│   ├── config.py             # ~/.config/mali-v2/settings.json
│   ├── session.py            # REPL state
│   ├── confirm.py            # กล่องยืนยัน [1][2][3]
│   ├── prefs.py              # remember / forget
│   ├── retrieve.py           # few-shot
│   ├── learned.py            # เรียนรู้จากการแก้
│   └── ui.py                 # banner, spinner, สี
├── bench/
│   ├── questions.py          # copy จาก thai-cli-harness
│   └── run.py
├── tests/
│   ├── test_parse.py         # ★ สำคัญ
│   ├── test_safety.py
│   ├── test_tools.py
│   ├── test_config.py
│   └── run_all.py
└── data/
    └── examples.jsonl        # few-shot
```

---

## หลักการเขียนโค้ด

1. **Python standard library เท่านั้น** — ไม่ใช้ pip dependency (เหมือน harness เดิม)
2. **Minimize scope** — ทำทีละ phase ตาม checklist ด้านล่าง
3. **Safety ฝั่งโค้ด** — อย่าไว้ใจโมเดลตัดสินความเสี่ยง
4. **Config แยก:** `~/.config/mali-v2/settings.json` (ไม่ชน `thai-cli-assistant` เดิม)
5. **Env prefix:** `MALI_*` (เช่น `MALI_MODEL`, `MALI_OLLAMA`)
6. **Default model:** `thai-cli-3b-r2`

---

## Phase 1 — โครงกระดูก + parse response

**เป้า:** one-shot รับคำขอไทย → กู้ tool call → แสดงคำสั่ง shell ได้

### งาน

- [x] `harness/config.py` — DEFAULTS, `get_config()`, `MALI_*` env override
- [x] `harness/prompt.py` — SYSTEM_TEMPLATE, TOOLS (`run_command`, `explain_command`)
- [x] `harness/model.py` — `OllamaChat`, `ModelError`, **`parse_tool_calls(msg) -> list[dict]`**
- [x] `harness/loop.py` — `Session.ask()`, `run()` one-shot (ยังไม่รัน shell)
- [x] `harness/cli.py` — `mali "คำขอ"`, `--help`, `--version`, health check Ollama
- [x] `mali` — entry script
- [x] `tests/test_parse.py` — unit test ทุกรูปแบบ output ของโมเดล 3B
- [x] `harness/__init__.py` — `__version__ = "0.1.0"`

### `parse_tool_calls()` spec

```python
def parse_tool_calls(msg: dict) -> list[dict]:
    """
    คืน list ของ {name, arguments} จาก message ของ Ollama
    ลำดับ: tool_calls → JSON ใน content → <tool_call> tag → None
    """
```

### Acceptance criteria

```bash
cd /home/pixelbot/mali-v2
python3 tests/test_parse.py          # ผ่านทุก case
MALI_MODEL=thai-cli-3b-r2 python3 mali "เช็คพื้นที่ดิสก์"
# → แสดงคำสั่ง df -h (หรือรันใน Phase 2)
```

---

## Phase 2 — Safety + รันคำสั่งจริง

**เป้า:** รัน shell ผ่านด่านความปลอดภัย 3 ชั้น

### งาน

- [x] `harness/safety.py` — `classify(cmd) -> green|yellow|red`, regex bypass protection
- [x] `harness/tools.py` — `run_command`, `explain_command`, ตัด output ตาม `max_output_chars`
- [x] `harness/confirm.py` — UI ยืนยัน, red ต้องพิมพ์ `รัน`, ปุ่ม [3] อธิบาย
- [x] `harness/loop.py` — ผ่าน safety ก่อนรัน, `_coach()` จาก error พื้นฐาน
- [x] `tests/test_safety.py` — copy/adapt จาก `~/thai-cli-harness/tests/test_safety.py`
- [x] `tests/test_tools.py`

### Safety rules

| ระดับ | ตัวอย่าง | พฤติกรรม |
|-------|---------|----------|
| GREEN | `ls`, `df`, `git status`, `find . -name` | รันทันที |
| YELLOW | `rm`, `mv`, `sudo`, คำสั่งไม่รู้จัก | ถามยืนยัน |
| RED | `rm -rf /`, `mkfs`, `curl \| bash`, fork bomb | ยืนยัน 2 ชั้น |

หลัก: **ไม่รู้จัก = YELLOW**

### Acceptance criteria

```bash
python3 tests/run_all.py
mali "เช็คพื้นที่ดิสก์"        # รัน df -h อัตโนมัติ
mali "ลบไฟล์ /tmp/test.txt"   # ถามยืนยันก่อน
```

---

## Phase 3 — REPL + Context + Install

**เป้า:** ใช้งานประจำวันได้สมบูรณ์

### งาน

- [x] `harness/session.py` — REPL loop, จำ messages, `refresh_system()`
- [x] `harness/context.py` — cwd, OS, RAM, git branch, package manager hint
- [x] `harness/ui.py` — banner, Spinner, สี ANSI
- [x] `harness/cli.py` — `mali` (ไม่มี args = REPL), `mali setup`
- [x] `harness/config.py` — `save_settings()`, setup menu
- [x] `install.sh` — ตรวจ python3/ollama, symlink `mali` → `~/.local/bin`
- [x] `README.md` — ติดตั้ง + ใช้งาน
- [x] `harness/prefs.py` — remember / forget (subcommands)
- [x] `harness/setup_menu.py` — เมนูตั้งค่า interactive
- [x] `pyproject.toml` — metadata เบา ๆ

### Subcommands ที่ต้องมี

```
mali                          REPL
mali "คำขอ"                   one-shot
mali setup                    ตั้งค่า
mali remember "..."           จำความชอบ
mali prefs | forget [n]       ดู/ลืม
mali --help | --version
```

### Acceptance criteria

```bash
./install.sh
mali                          # เข้า REPL, คุยต่อเนื่องได้
mali setup                    # เปลี่ยน model ได้
# ออก REPL แล้วโมเดล unload (keep_alive=0)
```

---

## Phase 4 — Few-shot + Learned + Retrieve

**เป้า:** ความแม่นสูงขึ้นโดยไม่เทรนโมเดลใหม่

### งาน

- [x] copy `~/thai-cli-harness/bench/questions.py` → `bench/questions.py`
- [x] export few-shot จาก `~/thai-cli-harness/assistant/examples.py` → `data/examples.jsonl`
- [x] `harness/retrieve.py` — ดึงตัวอย่างคล้าย ๆ ตามคำขอ
- [x] `harness/learned.py` — เก็บเมื่อ user แก้คำสั่ง
- [x] `harness/prefs.py` — `remember`, `forget`, แนบเข้า prompt
- [x] `harness/loop.py` — แทรก examples ก่อน user message

### Acceptance criteria

```bash
mali "หาไฟล์ใหญ่สุด 5 อัน"   # ใช้ few-shot ช่วย
# ปฏิเสธคำสั่งแล้วบอกที่ถูก → บันทึกใน ~/.config/mali-v2/learned.jsonl
```

---

## Phase 5 — Benchmark + CI

**เป้า:** วัดผล regression ทุกครั้งที่แก้ harness

### งาน

- [x] `bench/run.py` — accuracy, tool_rate, latency → `bench/results.json`
- [x] `tests/run_all.py` — รวมทุก test
- [x] `.github/workflows/test.yml` — CI บน push

### เป้า benchmark (`thai-cli-3b-r2`)

| เมตริก | เป้า |
|--------|------|
| accuracy | ≥ 90% |
| tool_rate (หลัง parse) | ≥ 95% |
| latency | ≤ 2s/ข้อ |
| safety bypass | 0 |

### Acceptance criteria

```bash
python3 bench/run.py thai-cli-3b-r2
# accuracy ≥ 90%, tool_rate ≥ 95%
```

---

## Model ↔ Harness Contract

### Request (ทุกครั้งที่คาดหวัง tool call)

```python
{
    "model": "thai-cli-3b-r2",
    "messages": [...],
    "tools": TOOLS,
    "stream": False,
    "think": False,
    "options": {"temperature": 0},
}
```

### Tool schema

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string"},
                    "explain": {"type": "string"},
                },
                "required": ["cmd"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_command",
            "parameters": {
                "type": "object",
                "properties": {"cmd": {"type": "string"}},
                "required": ["cmd"],
            },
        },
    },
]
```

---

## Config defaults

```json
{
  "model": "thai-cli-3b-r2",
  "ollama_host": "http://localhost:11434",
  "think": false,
  "max_steps": 8,
  "max_output_chars": 4000,
  "request_timeout": 120,
  "auto_yes": false,
  "suggest_only": "auto",
  "learn": true,
  "history_log": true
}
```

Path: `~/.config/mali-v2/settings.json`

---

## แหล่งอ้างอิงในเครื่อง

| Path | ใช้ทำอะไร |
|------|-----------|
| `~/thai-cli-harness/` | อ้างอิง architecture, safety tests, examples |
| `~/Desktop/thai-cli-train/` | โมเดล, Modelfile, bench log, บทเรียนเทรน |
| `~/Desktop/thai-cli-train/dist/INSTALL.md` | วิธี import `thai-cli-3b-r2` |
| `~/Desktop/thai-cli-train/dist/Modelfile.thai-cli-3b-r2` | Modelfile |

---

## สิ่งที่ยังไม่ทำ (out of scope)

- Web UI (`webui/`)
- `web_lookup` / cheat.sh
- Fine-tune / QLoRA รอบใหม่
- เปลี่ยนชื่อคำสั่งทับ `mali` เดิม (ใช้ config path แยกก่อน; ค่อย merge ทีหลัง)
- Claude API adapter (ทำหลัง Ollama stable)

---

## คำสั่งเริ่มต้นสำหรับ Cursor Agent

เมื่อเริ่ม session ใหม่ ให้ agent ทำตามลำดับนี้:

1. อ่าน `plan.md` (ไฟล์นี้)
2. เช็ค `ollama list | grep thai-cli-3b-r2`
3. ทำ Phase ถัดไปที่ยังมี `[ ]` ค้างอยู่
4. หลังแต่ละ phase — รัน acceptance criteria ให้ผ่านก่อนไป phase ถัดไป
5. อัปเดต `[ ]` → `[x]` ใน plan.md เมื่อเสร็จ

### ลำดับไฟล์แรกที่ควรสร้าง (Phase 1)

1. `harness/config.py`
2. `harness/prompt.py`
3. `harness/model.py` + `tests/test_parse.py`
4. `harness/loop.py`
5. `harness/cli.py` + `mali`

---

## Checklist ก่อนเริ่ม Phase 1

- [x] สร้าง workspace `/home/pixelbot/mali-v2` แล้ว
- [x] มี `plan.md` แล้ว
- [ ] `ollama list` มี `thai-cli-3b-r2` (ถ้าไม่มี → ดู `~/Desktop/thai-cli-train/dist/INSTALL.md`) — ทดสอบบนเครื่องผู้ใช้
- [ ] ทดสอบโมเดล: `ollama run thai-cli-3b-r2 "เช็คดิสก์"` ดู output format จริง — ทดสอบบนเครื่องผู้ใช้

---

*อัปเดตล่าสุด: 2026-06-09*
