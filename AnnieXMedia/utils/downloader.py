# ==============================================================================
#  UNIVERSAL INFINITY DOWNLOADER © 2026
#  Engine: Pixel 10 Pro (Stable) | Network: 5G+ | Mode: RAW HYBRID
#  Supports: YouTube, SoundCloud, Spotify, Apple Music (No Conversion Speed)
# ==============================================================================

import asyncio
import contextlib
import glob
import os
import re
import shutil
import random
import logging
from typing import Dict, Optional

import aiofiles
import aiohttp
from aiohttp import TCPConnector
from yt_dlp import YoutubeDL

# Adjust these imports according to your bot structure
from AnnieXMedia.core.dir import CACHE_DIR, DOWNLOAD_DIR
from AnnieXMedia.utils.cookie_handler import COOKIE_PATH as _COOKIES_FILE
from AnnieXMedia.utils.tuning import CHUNK_SIZE, SEM
from config import API_KEY, API_URL, VIDEO_API_URL
from AnnieXMedia.logging import LOGGER

LOGGER = LOGGER(__name__)

# Silent Logs for Speed
logging.getLogger("yt_dlp").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

USE_AUDIO_API = bool(API_URL and API_KEY)
USE_VIDEO_API = bool(VIDEO_API_URL and API_KEY)
_inflight: Dict[str, asyncio.Future] = {}
_inflight_lock = asyncio.Lock()
_session: Optional[aiohttp.ClientSession] = None
_session_lock = asyncio.Lock()

# Generic ID Regex (Works for YT, SC, etc)
YOUTUBE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")
ARIA2_PATH = shutil.which("aria2c")

# ==============================================================================
#  SYSTEM CONFIGURATION (THE PIXEL 10 CORE)
# ==============================================================================

class SystemConfig:
    # 1. Aria2 God Mode (16 Threads)
    ARIA2_ARGS = [
        "-c", "-x", "16", "-s", "16", "-j", "32", "-k", "1M",
        "--min-split-size=1M", "--file-allocation=none",
        "--buffer-size=1024M", "--max-connection-per-server=16",
        "--quiet=true"
    ]

    # 2. Identity: Pixel 10 Pro (Stable Android 16)
    # This works wonders for SoundCloud and Spotify too
    NATIVE_AGENTS = [
        "Mozilla/5.0 (Linux; Android 16; Pixel 10 Pro Build/TP1A.251005.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.7200.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 16; Pixel 10 Pro Build/TP1A.250915.008) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.7150.12 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 16; Pixel 10 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36"
    ]

def log_download_source(title: str, source: str) -> None:
    LOGGER.info(f"⚡ Loaded: {title} | Source: {source}")

def extract_video_id(link: str) -> str:
    if not link: return ""
    s = link.strip()
    # Simple extraction logic
    if "youtu" in s:
        if YOUTUBE_ID_RE.match(s): return s
        if "v=" in s: return s.split("v=")[-1].split("&")[0]
        return s.split("/")[-1].split("?")[0]
    # For SoundCloud/Spotify, use hash of link as ID to prevent duplicates
    import hashlib
    return hashlib.md5(s.encode()).hexdigest()[:15]

def get_cookie_file() -> Optional[str]:
    # Priority rotation
    if _COOKIES_FILE and os.path.exists(_COOKIES_FILE): return _COOKIES_FILE
    if os.path.exists("cookies.txt"): return "cookies.txt"
    if os.path.exists("cookies"):
        try: return os.path.join("cookies", random.choice(os.listdir("cookies")))
        except: pass     
    return None

# ==============================================================================
#  CORE DOWNLOADER LOGIC
# ==============================================================================

def get_ytdlp_base_opts() -> Dict[str, object]:
    opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "overwrites": False, "continuedl": True, "noprogress": True,
        "socket_timeout": 30, "retries": 15,
        "cachedir": str(CACHE_DIR), "ignoreerrors": True,
        
        # NETWORK SPEED
        "geo_bypass": True, "nocheckcertificate": True, "source_address": "0.0.0.0",   

        # IDENTITY SPOOFING (Pixel 10 Pro)
        "user_agent": random.choice(SystemConfig.NATIVE_AGENTS),
        
        # RAW SPEED (Disable Conversion)
        "prefer_ffmpeg": False,
        
        # Spoofing Clients for YT
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
                "skip": ["dash", "hls"]
            }
        },
    }

    # Aria2 Injection
    if ARIA2_PATH:
        opts["external_downloader"] = ARIA2_PATH
        opts["external_downloader_args"] = SystemConfig.ARIA2_ARGS

    if cookiefile := get_cookie_file():
        opts["cookiefile"] = cookiefile
    return opts


def find_cached_file(video_id: str) -> Optional[str]:
    if not video_id: return None
    # Check ALL possible formats (Raw & Converted)
    for ext in ("opus", "webm", "m4a", "mp3", "mp4", "mkv", "aac"):
        path = f"{DOWNLOAD_DIR}/{video_id}.{ext}"
        if os.path.exists(path): return path
    return None


async def get_http_session() -> aiohttp.ClientSession:
    global _session
    if _session and not _session.closed: return _session
    async with _session_lock:
        if _session and not _session.closed: return _session
        # Optimized Timeout
        timeout = aiohttp.ClientTimeout(total=600, sock_connect=20, sock_read=60)
        connector = TCPConnector(limit=0, ttl_dns_cache=300, enable_cleanup_closed=True)
        _session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return _session


async def close_http_session() -> None:
    global _session
    async with _session_lock:
        if _session and not _session.closed: await _session.close()
        _session = None


async def download_file(url: str, out_path: str) -> Optional[str]:
    if not url: return None
    try:
        session = await get_http_session()
        async with session.get(url) as resp:
            if resp.status != 200: return None
            async with aiofiles.open(out_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                    if not chunk: break
                    await f.write(chunk)
        return out_path if os.path.exists(out_path) else None
    except: return None

# --- API FALLBACKS (Legacy Support) ---
async def api_download_audio(link: str) -> Optional[str]:
    if not USE_AUDIO_API: return None
    vid = extract_video_id(link)
    if not vid: return None
    poll_url = f"{API_URL}/song/{vid}?api={API_KEY}"
    try:
        session = await get_http_session()
        async with session.get(poll_url) as r:
            if r.status != 200: return None
            data = await r.json()
            if data.get("link"):
                out_path = f"{DOWNLOAD_DIR}/{vid}.mp3"
                return await download_file(data['link'], out_path)
    except: return None

async def api_download_video(link: str) -> Optional[str]:
    if not USE_VIDEO_API: return None
    vid = extract_video_id(link)
    if not vid: return None
    poll_url = f"{VIDEO_API_URL}/video/{vid}?api={API_KEY}"
    try:
        session = await get_http_session()
        async with session.get(poll_url) as r:
            if r.status != 200: return None
            data = await r.json()
            if data.get("link"):
                out_path = f"{DOWNLOAD_DIR}/{vid}.mp4"
                return await download_file(data['link'], out_path)
    except: return None


def get_final_path_from_info(info: Dict) -> Optional[str]:
    vid = info.get("id")
    if not vid: return None
    
    # 1. Check strict extension
    ext = info.get("ext")
    if ext:
        p = f"{DOWNLOAD_DIR}/{vid}.{ext}"
        if os.path.exists(p): return p
        
    # 2. Check any file with that ID (Smart Scan)
    matches = sorted(glob.glob(f"{DOWNLOAD_DIR}/{vid}.*"), key=os.path.getmtime, reverse=True)
    return matches[0] if matches else None


def download_with_ytdlp_sync(link: str, fmt: str) -> Optional[str]:
    try:
        opts = get_ytdlp_base_opts()
        opts["format"] = fmt
        with YoutubeDL(opts) as ydl:
            # Try getting info first to check cache
            info = ydl.extract_info(link, download=False)
            if path := get_final_path_from_info(info): return path
            
            # Download
            ydl.download([link])
            return get_final_path_from_info(info)
    except Exception as e:
        LOGGER.error(f"Universal DL Error: {e}")
        return None


async def run_with_semaphore(coro):
    async with SEM: return await coro


async def deduplicate_download(key: str, runner):
    async with _inflight_lock:
        if fut := _inflight.get(key): return await fut
        fut = asyncio.get_running_loop().create_future()
        _inflight[key] = fut
    try:
        result = await runner()
        fut.set_result(result)
        return result
    except Exception as e:
        fut.set_exception(e)
        return None
    finally:
        async with _inflight_lock: _inflight.pop(key, None)


async def race_ytdlp_and_api(yt_task, api_task, title: str):
    done, pending = await asyncio.wait({yt_task, api_task}, return_when=asyncio.FIRST_COMPLETED)
    for task in done:
        result = task.result()
        if result and os.path.exists(result):
            source = "Infinity Core" if task is yt_task else "Backup API"
            log_download_source(title, source)
            for p in pending: p.cancel()
            return result
    for task in pending:
        try:
            result = await task
            if result and os.path.exists(result): return result
        except: pass
    return None


# ==============================================================================
#  MAIN ENTRY POINT
# ==============================================================================

async def yt_dlp_download(link: str, type: str, title: str = "") -> Optional[str]:
    loop = asyncio.get_running_loop()
    vid = extract_video_id(link)
    
    # 1. Fast Cache Check
    if cached := find_cached_file(vid):
        if title: log_download_source(title, "Instant Cache")
        return cached

    if type == "audio":
        key = f"audio:{vid}"
        async def run():
            # STRATEGY: Get RAW Audio (WebM/Opus) -> No Conversion
            # This works for YT (Opus), SoundCloud (MP3/Opus), Spotify (AAC)
            ytdlp_task = asyncio.create_task(
                run_with_semaphore(
                    loop.run_in_executor(None, download_with_ytdlp_sync, link, "bestaudio/best")
                )
            )
            # Only use API if YTDLP fails (to save time) or race if critical
            api_task = asyncio.create_task(api_download_audio(link)) if USE_AUDIO_API else None
            
            if api_task:
                return await race_ytdlp_and_api(ytdlp_task, api_task, title or "Unknown")
            
            result = await ytdlp_task
            if result and title: log_download_source(title, "Infinity Core")
            return result
            
        return await deduplicate_download(key, run)

    elif type == "video":
        key = f"video:{vid}"
        async def run():
            # STRATEGY: Smart Video Merge
            ytdlp_task = asyncio.create_task(
                run_with_semaphore(
                    loop.run_in_executor(None, download_with_ytdlp_sync, link, "bestvideo[height<=1080]+bestaudio/best")
                )
            )
            api_task = asyncio.create_task(api_download_video(link)) if USE_VIDEO_API else None
            
            if api_task:
                return await race_ytdlp_and_api(ytdlp_task, api_task, title or "Unknown")
            
            result = await ytdlp_task
            if result and title: log_download_source(title, "Infinity Core")
            return result
            
        return await deduplicate_download(key, run)

    return None
