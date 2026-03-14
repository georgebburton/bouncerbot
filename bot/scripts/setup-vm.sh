#!/bin/bash
# Run on a fresh Ubuntu/Debian VM to install deps, clone repo, and run the Discord bot as a systemd service.
# Usage:
#   ./setup-vm.sh                    # run from inside the repo (directory containing bot.py)
#   ./setup-vm.sh OWNER/REPO          # clone https://github.com/OWNER/REPO and setup there

set -e

GITHUB_REPO="${1:-}"

# --- Install system packages ---
echo "[1/6] Installing system packages (may ask for sudo)..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git ffmpeg nodejs >/dev/null

# --- Find or clone repo ---
if [ -n "$GITHUB_REPO" ]; then
    REPO_NAME="${GITHUB_REPO##*/}"
    CLONE_DIR="$HOME/$REPO_NAME"
    echo "[2/6] Cloning https://github.com/$GITHUB_REPO ..."
    if [ -d "$CLONE_DIR" ]; then
        (cd "$CLONE_DIR" && git pull --quiet 2>/dev/null || true)
    else
        git clone --depth 1 "https://github.com/$GITHUB_REPO.git" "$CLONE_DIR"
    fi
    BOT_ROOT="$CLONE_DIR"
    if [ -f "$CLONE_DIR/bot/bot.py" ]; then
        BOT_ROOT="$CLONE_DIR/bot"
    fi
else
    BOT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
    if [ ! -f "$BOT_ROOT/bot.py" ]; then
        echo "Error: bot.py not found in $BOT_ROOT. Run from repo root or pass GITHUB_REPO (e.g. owner/repo)."
        exit 1
    fi
    echo "[2/6] Using repo at $BOT_ROOT"
fi

# --- Python venv and pip ---
echo "[3/6] Setting up Python virtual environment..."
cd "$BOT_ROOT"
python3 -m venv venv
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt

# --- .env ---
if [ ! -f "$BOT_ROOT/.env" ]; then
    echo "[4/6] Creating .env from .env.example – please edit and add DISCORD_TOKEN."
    if [ -f "$BOT_ROOT/.env.example" ]; then
        cp "$BOT_ROOT/.env.example" "$BOT_ROOT/.env"
    else
        echo "DISCORD_TOKEN=your_bot_token_here" > "$BOT_ROOT/.env"
    fi
    echo "   Edit: nano $BOT_ROOT/.env"
else
    echo "[4/6] .env already exists."
fi

# --- systemd service ---
CURRENT_USER="${SUDO_USER:-$USER}"
if [ "$CURRENT_USER" = "root" ]; then
    CURRENT_USER="ubuntu"
fi
SERVICE_USER="$CURRENT_USER"
VENV_PYTHON="$BOT_ROOT/venv/bin/python"
SERVICE_FILE="/etc/systemd/system/discord-bot.service"

echo "[5/6] Installing systemd service..."
sudo tee "$SERVICE_FILE" >/dev/null << EOF
[Unit]
Description=Discord bot
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$BOT_ROOT
Environment=PATH=$BOT_ROOT/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$VENV_PYTHON -u bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable discord-bot

echo "[6/6] Starting bot..."
sudo systemctl start discord-bot
sleep 1
sudo systemctl status discord-bot --no-pager || true

echo ""
echo "Done. Bot should be running."
echo "  Logs:    journalctl -u discord-bot -f"
echo "  Restart: sudo systemctl restart discord-bot"
echo "  Stop:    sudo systemctl stop discord-bot"
echo "  Edit .env: nano $BOT_ROOT/.env  then  sudo systemctl restart discord-bot"
