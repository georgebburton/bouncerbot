# Run the bot on a Linux VM (Ubuntu/Debian)

Use this guide to run the bot 24/7 on a cloud VM (Oracle Free Tier, DigitalOcean, AWS, etc.) by cloning from GitHub.

**Before you start:** Push this project to a GitHub repo (e.g. `yourusername/discord-bot`) so the VM can clone it. If the bot code is in a subfolder (e.g. `bot/`), the script will detect it.

---

## 1. Create a VM

- **Oracle Cloud (free):** [cloud.oracle.com](https://cloud.oracle.com) → Create a VM (e.g. Ubuntu 22.04). Note the **public IP** and ensure port 22 (SSH) is open.
- **Other:** Any Ubuntu 22.04 (or 20.04) VM with SSH access is fine.

---

## 2. SSH into the VM

From your PC (PowerShell or terminal):

```bash
ssh ubuntu@YOUR_VM_IP
```

(Use `root@...` or the user your provider gives you if different.)

---

## 3. One-command setup (recommended)

**Option A – You already pushed this project to GitHub**

Replace `YOUR_USERNAME` and `YOUR_REPO` with your GitHub username and repo name, then run on the VM:

```bash
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/scripts/setup-vm.sh -o setup-vm.sh
chmod +x setup-vm.sh
./setup-vm.sh YOUR_USERNAME/YOUR_REPO
```

This clones the repo into `~/YOUR_REPO`, installs dependencies, creates `.env` from the example, and starts the bot as a systemd service.

**Option B – You cloned the repo yourself**

```bash
cd ~/YOUR_REPO
# If the bot lives in a "bot" subfolder:  cd bot
chmod +x scripts/setup-vm.sh
./scripts/setup-vm.sh
```

(With no argument, the script uses the current directory and expects `bot.py` and `requirements.txt` there.)

---

## 4. Manual setup (if you prefer)

### 4.1 Install dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git ffmpeg nodejs
```

### 4.2 Clone your repo

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
# If the bot is in a subfolder (e.g. "bot"), cd into it:
# cd bot
```

### 4.3 Python environment and dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4.4 Create `.env`

```bash
nano .env
```

Add (replace with your real token):

```
DISCORD_TOKEN=your_bot_token_here
SPOTIFY_CLIENT_ID=optional
SPOTIFY_CLIENT_SECRET=optional
COOKIES_FILE=./cookies.txt
```

Save (Ctrl+O, Enter, Ctrl+X). If you have a `cookies.txt` for YouTube, upload it to this folder (e.g. with `scp` from your PC).

### 4.5 Test run

```bash
source venv/bin/activate
python bot.py
```

Press Ctrl+C to stop. If it connects and shows guilds, continue.

### 4.6 Run as a service (keeps bot up after you disconnect and after reboot)

```bash
sudo nano /etc/systemd/system/discord-bot.service
```

Paste (adjust `User`, `WorkingDirectory`, and `ExecStart` path if your bot is in a subfolder):

```ini
[Unit]
Description=Discord bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/YOUR_REPO
Environment=PATH=/home/ubuntu/YOUR_REPO/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/ubuntu/YOUR_REPO/venv/bin/python -u bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Save, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable discord-bot
sudo systemctl start discord-bot
sudo systemctl status discord-bot
```

Use `journalctl -u discord-bot -f` to watch logs.

---

## 5. Upload cookies (optional)

From your **PC** (PowerShell), if you have `cookies.txt`:

```powershell
scp cookies.txt ubuntu@YOUR_VM_IP:~/YOUR_REPO/cookies.txt
```

Then on the VM ensure `.env` has `COOKIES_FILE=./cookies.txt` and restart: `sudo systemctl restart discord-bot`.

---

## 6. Useful commands

| Command | Description |
|--------|-------------|
| `sudo systemctl status discord-bot` | Check if bot is running |
| `sudo systemctl restart discord-bot` | Restart after code or .env changes |
| `sudo systemctl stop discord-bot` | Stop the bot |
| `journalctl -u discord-bot -f` | Follow logs |
