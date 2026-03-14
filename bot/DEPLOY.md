# Hosting Your Discord Bot 24/7

To keep the bot online without running it on your PC, use one of these options.

---

## Option 1: Railway (recommended, easy)

1. **Push your bot to GitHub** (create a repo and push the `bot` folder).
2. Go to [railway.app](https://railway.app) and sign in with GitHub.
3. **New Project** → **Deploy from GitHub** → select your repo (and set root directory to the folder that contains `bot.py` and `requirements.txt` if the repo root is higher).
4. In the project, open **Variables** and add:
   - `DISCORD_TOKEN` = your bot token
   - `SPOTIFY_CLIENT_ID` = (optional) your Spotify app client ID
   - `SPOTIFY_CLIENT_SECRET` = (optional) your Spotify app client secret
5. **Settings** → set **Start Command** to: `python bot.py`  
   (If Railway doesn’t detect a web server, it will run this as a worker.)
6. Deploy. Railway gives a small free credit; after that it’s pay-as-you-go (usually a few dollars/month for a bot).

**FFmpeg / Node on Railway:** Railway’s default image may not include FFmpeg or Node. If `!play` fails, use a **Dockerfile** (see Option 4) or a **Nixpacks** config so FFmpeg (and Node, if needed) are installed.

---

## Option 2: Render (free tier)

1. Push your bot to GitHub.
2. Go to [render.com](https://render.com) → **New** → **Background Worker**.
3. Connect the repo and set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
4. **Environment** → add `DISCORD_TOKEN` (and optional Spotify vars).
5. Deploy.

**Note:** Free Background Workers on Render **spin down after ~15 minutes** of no activity and can be slow to wake. For a bot that must stay up 24/7, use Railway or a VPS.

---

## Option 3: Free VPS (Oracle Cloud, etc.)

You get a small always-on Linux server for free.

1. Create an **Oracle Cloud** account and create a **Always Free** VM (e.g. Ubuntu).
2. SSH in and install dependencies:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip ffmpeg nodejs
   ```
3. Upload your bot (e.g. clone from GitHub or copy files):
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
   cd YOUR_REPO
   ```
4. Create `.env` with your tokens:
   ```bash
   nano .env
   # Add: DISCORD_TOKEN=..., SPOTIFY_CLIENT_ID=..., SPOTIFY_CLIENT_SECRET=...
   ```
5. Run in the background with **screen** or **tmux**:
   ```bash
   pip install -r requirements.txt
   screen -S bot
   python bot.py
   # Ctrl+A then D to detach; bot keeps running
   ```
   Or use **systemd** so it restarts on reboot (search “systemd service python script” for a template).

---

## Option 4: Docker (any VPS or cloud that runs Docker)

Use this if your host has Docker and you want FFmpeg + Node included.

1. Use the `Dockerfile` in this repo (see below).
2. Build and run:
   ```bash
   docker build -t discord-bot .
   docker run -d --env-file .env --name bot discord-bot
   ```

---

## YouTube "Sign in to confirm you're not a bot"

When the bot is hosted (Railway, Render, VPS), YouTube may block requests. Fix it with **cookies**:

1. **Export cookies** (on your PC, with a browser where you’re logged into YouTube):
   - **Option A:** Install a “Get cookies.txt” / “cookies.txt” extension (Chrome/Edge), go to youtube.com, export to `cookies.txt`.
   - **Option B:** From a terminal (with yt-dlp installed):  
     `yt-dlp --cookies-from-browser chrome --cookies cookies.txt "https://www.youtube.com"`  
     (Use `chrome`, `firefox`, or `edge` as needed.)
2. **Use the cookies on your host:**
   - **Railway:** Encode the file in base64 (e.g. on Windows PowerShell: `[Convert]::ToBase64String([IO.File]::ReadAllBytes("cookies.txt"))`), then in Railway **Variables** add `COOKIES_TXT` = that long string (paste the whole output). The bot will write it to a temp file at startup.
   - **VPS / Docker:** Put `cookies.txt` in your project directory. Set env: `COOKIES_FILE=./cookies.txt` (or the full path).
3. **Set the env var** on the host: `COOKIES_FILE=./cookies.txt` on VPS/Docker, or `COOKIES_TXT=<base64 string>` on Railway.
4. **Redeploy / restart** the bot. Cookies expire; re-export every few weeks if playback starts failing again.

**Do not commit `cookies.txt` to GitHub** — add it to `.gitignore`.

---

## Environment variables (all options)

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | Yes | Bot token from [Discord Developer Portal](https://discord.com/developers/applications) → your app → Bot |
| `SPOTIFY_CLIENT_ID` | No | For `!play` with Spotify links |
| `SPOTIFY_CLIENT_SECRET` | No | For `!play` with Spotify links |
| `COOKIES_FILE` or `YTDL_COOKIES_FILE` | No | Path to a Netscape-format cookies file (VPS/Docker). |
| `COOKIES_TXT` | No | Base64-encoded cookies file content (use on Railway when you can’t upload a file). |

Never commit `.env` or `cookies.txt` to GitHub.
