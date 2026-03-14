# Discord bot with FFmpeg and Node (for yt-dlp) for 24/7 hosting
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .

# Run the bot (pass DISCORD_TOKEN etc. via env or --env-file)
CMD ["python", "-u", "bot.py"]
