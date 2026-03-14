# bot.py
import asyncio
import os
import shutil

import discord
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

if not TOKEN:
    print("Error: DISCORD_TOKEN not set. Create a .env file with DISCORD_TOKEN=your_bot_token")
    exit(1)

# Optional: Spotify for resolving track/playlist URLs to search queries
spotify = None
if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
    try:
        spotify = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
            )
        )
    except Exception:
        spotify = None

# Message content is a "privileged" intent. Enable it in the Developer Portal
# (Bot → Privileged Gateway Intents → Message Content Intent) for !hello to work.
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Per-guild voice state and queue: queue is list of (url, title)
voice_states = {}
queues = {}  # guild_id -> [(url, title), ...]
music_channels = {}  # guild_id -> TextChannel for "Now playing" / "Added to queue"


def _find_ffmpeg() -> str | None:
    """Return path to ffmpeg.exe, checking PATH then WinGet install location."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    # WinGet installs FFmpeg here without always adding to PATH
    localappdata = os.environ.get("LOCALAPPDATA", "")
    winget_packages = os.path.join(localappdata, "Microsoft", "WinGet", "Packages")
    if not os.path.isdir(winget_packages):
        return None
    for name in os.listdir(winget_packages):
        if "ffmpeg" not in name.lower():
            continue
        for root, _dirs, files in os.walk(os.path.join(winget_packages, name)):
            if "ffmpeg.exe" in files:
                return os.path.join(root, "ffmpeg.exe")
    return None


FFMPEG_PATH = _find_ffmpeg()
FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}
# yt-dlp expects js_runtimes as a dict: {runtime_name: {"path": path_to_executable}}
_node_path = shutil.which("node")
_deno_path = shutil.which("deno")
_js_runtimes = {}
if _node_path:
    _js_runtimes["node"] = {"path": _node_path}
if _deno_path:
    _js_runtimes["deno"] = {"path": _deno_path}
if not _js_runtimes:
    _js_runtimes["deno"] = {}  # default; install Node.js or Deno if extraction fails

YDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
    "extract_flat": False,
    "js_runtimes": _js_runtimes,
}


def _spotify_query(url: str) -> str | None:
    """Resolve a Spotify URL to a 'artist - track' search query. Returns None if not configured or invalid."""
    if not spotify:
        return None
    try:
        if "track/" in url:
            track = spotify.track(url)
            return f"{track['artists'][0]['name']} {track['name']}"
        if "playlist/" in url:
            tracks = spotify.playlist_tracks(url)
            if tracks["items"]:
                t = tracks["items"][0]["track"]
                if t:
                    return f"{t['artists'][0]['name']} {t['name']}"
        if "album/" in url:
            album = spotify.album_tracks(url)
            if album["items"]:
                t = album["items"][0]
                return f"{t['artists'][0]['name']} {t['name']}"
    except Exception:
        pass
    return None


def _get_audio_url(query: str) -> tuple[str | None, str]:
    """Get a direct audio URL from a YouTube search query or URL. Returns (url, title) or (None, error_msg)."""
    is_url = query.strip().startswith("http")
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        try:
            if is_url:
                info = ydl.extract_info(query, download=False)
            else:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                if info and "entries" in info and info["entries"]:
                    info = info["entries"][0]
            if not info:
                return None, "No result found."
            url = info.get("url") or (info.get("formats") and info["formats"][0].get("url"))
            title = info.get("title", "Unknown")
            if not url:
                return None, "Could not get audio stream."
            return url, title
        except Exception as e:
            return None, str(e) or "Failed to get audio."


async def _play_next(guild_id: int):
    """Play the next track in the queue for this guild, or do nothing if queue is empty."""
    queue = queues.get(guild_id, [])
    if not queue:
        return
    url, title = queue.pop(0)
    guild = client.get_guild(guild_id)
    if not guild or not guild.voice_client or not guild.voice_client.is_connected():
        return
    channel = music_channels.get(guild_id)
    try:
        source = discord.FFmpegPCMAudio(url, executable=FFMPEG_PATH, **FFMPEG_OPTS)
        def _after(err):
            if err is None:
                asyncio.run_coroutine_threadsafe(_play_next(guild_id), client.loop)

        guild.voice_client.play(source, after=_after)
        if channel:
            await channel.send(f"Now playing: **{title}**")
    except Exception:
        if channel:
            await channel.send(f"Failed to play **{title}**. Trying next in queue…")
        await _play_next(guild_id)


@client.event
async def on_ready():
    print(f"{client.user} is connected to the following guilds:")
    for guild in client.guilds:
        print(f"  - {guild.name} (id: {guild.id})")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.lower().startswith("!hello"):
        await message.channel.send(f"Hello, {message.author.mention}!")
    
    if message.content.lower().startswith("!help"):
        help_message = (
            "Here are the commands you can use:\n"
            "!hello - Greet the bot\n"
            "!help - Show this help message\n"
            "!birthday - Get a birthday message\n"
            "!play <Spotify link or song name> - Play a song (or add to queue)\n"
            "!skip - Skip the current song and play the next in queue\n"
            "!stop - Stop playback and leave the voice channel"
        )
        await message.channel.send(help_message)
        
    if message.content.lower().startswith("!birthday"):
        try:
            await message.channel.send(file=discord.File("BirthdayP.jpg"))
        except FileNotFoundError:
            pass  # No image file – just send the text below
        await message.channel.send("Happy Birthday! 🎉🎂")

    # ----- Music commands -----
    if message.content.lower().startswith("!play"):
        query = message.content[len("!play"):].strip()
        if not query:
            await message.channel.send("Usage: `!play <Spotify link or song name>`")
            return
        voice_channel = message.author.voice.channel if message.author.voice else None
        if not voice_channel:
            await message.channel.send("Join a voice channel first.")
            return
        if "spotify.com" in query or "open.spotify.com" in query:
            resolved = _spotify_query(query)
            if resolved:
                query = resolved
            elif spotify is None:
                await message.channel.send(
                    "Spotify links need SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env. "
                    "Using your message as a search query instead."
                )
        await message.channel.send("Finding the song…")
        loop = asyncio.get_event_loop()
        url, title = await loop.run_in_executor(None, lambda: _get_audio_url(query))
        if not url:
            await message.channel.send(
                f"**Song not found.** {title}\n"
                "Try a different search, check the link, or use a Spotify track URL."
            )
            return
        guild_id = message.guild.id
        voice_client = message.guild.voice_client
        if voice_client and voice_client.is_connected():
            if voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)
        else:
            voice_client = await voice_channel.connect()
        if not FFMPEG_PATH:
            await message.channel.send(
                "**FFmpeg is not installed.** Install it and add it to your PATH to play audio.\n"
                "Windows: `winget install FFmpeg` or download from https://ffmpeg.org/download.html"
            )
            return
        if queues.get(guild_id) is None:
            queues[guild_id] = []
        music_channels[guild_id] = message.channel
        queues[guild_id].append((url, title))
        voice_states[guild_id] = voice_client
        if voice_client.is_playing():
            pos = len(queues[guild_id])
            await message.channel.send(
                f"Added to queue: **{title}** (position {pos}). Use `!skip` to skip the current song."
            )
            return
        # Not playing – start with this track; _play_next will pop from queue
        await _play_next(guild_id)

    if message.content.lower().startswith("!skip"):
        voice_client = message.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await message.channel.send("I'm not in a voice channel.")
            return
        if not voice_client.is_playing():
            await message.channel.send("Nothing is playing. Use `!play` to add a song.")
            return
        voice_client.stop()
        if not queues.get(message.guild.id):
            await message.channel.send("Skipped. Queue is empty.")
        else:
            await message.channel.send("Skipped.")
            await _play_next(message.guild.id)

    if message.content.lower().startswith("!stop"):
        voice_client = message.guild.voice_client
        if voice_client and voice_client.is_connected():
            queues[message.guild.id] = []  # clear queue when stopping
            await voice_client.disconnect()
            await message.channel.send("Stopped and left the voice channel.")
        else:
            await message.channel.send("I'm not in a voice channel.")


client.run(TOKEN)
