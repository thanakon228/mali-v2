#!/usr/bin/env bash
# ติดตั้ง Mali v2 — ตรวจ dependency, ผูก mali เข้า PATH
set -euo pipefail

GRN='\033[92m'; YEL='\033[93m'; RED='\033[91m'; CYN='\033[96m'; DIM='\033[2m'; OFF='\033[0m'
ok()   { echo -e "${GRN}✓${OFF} $1"; }
warn() { echo -e "${YEL}!${OFF} $1"; }
err()  { echo -e "${RED}✗${OFF} $1"; }
info() { echo -e "${CYN}›${OFF} $1"; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
DEFAULT_MODEL="thai-cli-3b-r2"

echo -e "${CYN}❀ ติดตั้ง Mali v2${OFF}\n"

if command -v python3 >/dev/null 2>&1; then
  ok "พบ Python: $(python3 --version)"
else
  err "ไม่พบ python3 — ติดตั้งก่อน (เช่น: sudo apt install python3)"
  exit 1
fi

if command -v ollama >/dev/null 2>&1; then
  ok "พบ Ollama: $(ollama --version 2>/dev/null | head -1)"
else
  warn "ไม่พบ Ollama"
  read -rp "  ติดตั้ง Ollama อัตโนมัติเลยไหม? (curl จาก ollama.com) [y/N] " a
  if [[ "${a,,}" == y* ]]; then
    curl -fsSL https://ollama.com/install.sh | sh
    ok "ติดตั้ง Ollama แล้ว"
  else
    err "ติดตั้ง Ollama ก่อนแล้วรันสคริปต์นี้ใหม่ — https://ollama.com/download"
    exit 1
  fi
fi

if ! curl -fsS -m 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
  warn "Ollama ยังไม่รัน — กำลังสตาร์ท 'ollama serve' เบื้องหลัง"
  (ollama serve >/dev/null 2>&1 &) || true
  sleep 2
fi

info "โมเดลเริ่มต้น: ${DEFAULT_MODEL}"
read -rp "  โมเดลที่จะใช้ [${DEFAULT_MODEL}]: " MODEL
MODEL="${MODEL:-$DEFAULT_MODEL}"

if ollama list 2>/dev/null | awk '{print $1}' | grep -qE "^${MODEL}(:|$)"; then
  ok "มีโมเดล ${MODEL} อยู่แล้ว"
else
  if [[ "${MODEL}" == "thai-cli-3b-r2" ]]; then
    warn "ยังไม่มี ${MODEL} — ดูวิธี import ที่ ~/Desktop/thai-cli-train/dist/INSTALL.md"
    warn "ข้ามการโหลดโมเดล (ตั้งค่าใน settings ไว้แล้ว)"
  else
    info "กำลังโหลด ${MODEL} ..."
    ollama pull "${MODEL}"
  fi
fi

python3 -c "import sys; sys.path.insert(0, '${HERE}'); from harness.config import save_model; save_model('${MODEL}')"
ok "ตั้ง ${MODEL} เป็นโมเดลหลัก (ปรับเพิ่มได้ด้วย 'mali setup')"

mkdir -p "${BIN_DIR}"
chmod +x "${HERE}/mali"
ln -sf "${HERE}/mali" "${BIN_DIR}/mali"
ok "ลิงก์ ${BIN_DIR}/mali → ${HERE}/mali"

if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
  warn "${BIN_DIR} ยังไม่อยู่ใน PATH — เพิ่มบรรทัดนี้ใน ~/.bashrc หรือ ~/.zshrc:"
  echo -e "    ${DIM}export PATH=\"\$HOME/.local/bin:\$PATH\"${OFF}"
fi

echo -e "\n${GRN}เสร็จ!${OFF} ลองใช้:"
echo -e "    ${DIM}mali${OFF}                       # เข้าโหมด REPL"
echo -e "    ${DIM}mali \"เช็คพื้นที่ดิสก์\"${OFF}   # สั่งงานครั้งเดียว"
echo -e "    ${DIM}mali setup${OFF}                 # ตั้งค่า"
