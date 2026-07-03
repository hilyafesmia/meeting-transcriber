#!/usr/bin/env bash
# One-time setup for meeting-transcriber (SPEC.md section 8).
# Safe to re-run any time -- every step checks before it acts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Meeting Transcriber - Setup ==="
echo ""

# --- 1. Homebrew --------------------------------------------------------
if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew tidak ditemukan. Memasang Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "OK: Homebrew sudah terpasang."
fi

# --- 2. ffmpeg -----------------------------------------------------------
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Memasang ffmpeg..."
    brew install ffmpeg
else
    echo "OK: ffmpeg sudah terpasang."
fi

# --- 3. pyenv + Python virtualenv -----------------------------------------
if ! command -v pyenv >/dev/null 2>&1; then
    echo "pyenv tidak ditemukan. Memasang pyenv..."
    brew install pyenv pyenv-virtualenv
else
    echo "OK: pyenv sudah terpasang."
fi

eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init - 2>/dev/null || true)"

PYTHON_VERSION="3.13.6"
ENV_NAME="meeting-transcriber"

INSTALLED_VERSIONS="$(pyenv versions --bare)"
if ! grep -qx "$PYTHON_VERSION" <<< "$INSTALLED_VERSIONS"; then
    echo "Memasang Python $PYTHON_VERSION melalui pyenv (ini butuh beberapa menit)..."
    pyenv install "$PYTHON_VERSION"
fi

EXISTING_VIRTUALENVS="$(pyenv virtualenvs --bare)"
if ! grep -q "/envs/${ENV_NAME}$" <<< "$EXISTING_VIRTUALENVS"; then
    echo "Membuat virtualenv '$ENV_NAME'..."
    pyenv virtualenv "$PYTHON_VERSION" "$ENV_NAME"
else
    echo "OK: virtualenv '$ENV_NAME' sudah ada."
fi

pyenv local "$ENV_NAME"

# --- 4. Python dependencies ------------------------------------------------
echo "Memasang paket Python (bisa memakan waktu, mengunduh beberapa GB)..."
pip install --upgrade pip
pip install -e .

# --- 5. Hugging Face token ---------------------------------------------
HF_TOKEN_PATH="$HOME/.cache/huggingface/token"
if [ -f "$HF_TOKEN_PATH" ]; then
    echo "OK: token Hugging Face sudah ada di $HF_TOKEN_PATH."
else
    echo ""
    echo "=== Langkah token Hugging Face (sekali saja) ==="
    echo "Model pemisah suara pembicara membutuhkan akun gratis Hugging Face."
    echo ""
    echo "1. Buat akun gratis di: https://huggingface.co/join"
    echo "2. Buka halaman ini dan klik 'Agree and access repository':"
    echo "   https://huggingface.co/pyannote/speaker-diarization-3.1"
    echo "3. Buka halaman ini dan klik 'Agree and access repository' juga:"
    echo "   https://huggingface.co/pyannote/segmentation-3.0"
    echo "4. Buka halaman ini dan klik 'Agree and access repository' juga:"
    echo "   https://huggingface.co/pyannote/speaker-diarization-community-1"
    echo "5. Buat token di: https://huggingface.co/settings/tokens"
    echo "   (pilih tipe 'Read')"
    echo ""
    read -r -p "Tempelkan token Anda di sini, lalu tekan Enter: " HF_TOKEN
    mkdir -p "$HOME/.cache/huggingface"
    printf '%s' "$HF_TOKEN" > "$HF_TOKEN_PATH"
    echo "Token disimpan di $HF_TOKEN_PATH."
fi

# --- 6. Self-check --------------------------------------------------------
echo ""
echo "=== Memeriksa kesiapan sistem ==="
transcribe doctor || true

echo ""
echo "Setup selesai. Untuk memproses rekaman, jalankan:"
echo "    transcribe /path/ke/folder-rekaman-zoom"
