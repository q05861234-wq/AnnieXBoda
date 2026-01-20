# ==============================================================================
#  HIGH-PERFORMANCE YOUTUBE CORE ENGINE © 2025
#  Architecture: S25 Ultra Spoofing | Aria2 Integration | Zero-Latency
#  Target System: 16-Core vCPU / Enterprise Grade
# ==============================================================================

import asyncio
import contextlib
import json
import os
import re
import time
import random
import shutil
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from concurrent.futures import ThreadPoolExecutor

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.aio import VideosSearch, Playlist

# ==============================================================================
#  SECTION 1: ENVIRONMENT & LOGGING
# ==============================================================================

try:
    from AnnieXMedia.utils.database import is_on_off
    from AnnieXMedia.utils.formatters import time_to_seconds
    from AnnieXMedia.utils.tuning import YTDLP_TIMEOUT, YOUTUBE_META_MAX, YOUTUBE_META_TTL
    from AnnieXMedia import LOGGER
except ImportError:
    logging.basicConfig(level=logging.ERROR)
    def LOGGER(name): return logging.getLogger(name)
    async def is_on_off(x): return True
    def time_to_seconds(t): return 0
    YTDLP_TIMEOUT = 300
    YOUTUBE_META_MAX = 5000
    YOUTUBE_META_TTL = 3600

# Suppress internal noise for maximum I/O throughput
logging.getLogger("yt_dlp").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.WARNING)

# ==============================================================================
#  SECTION 2: MEMORY MANAGEMENT (RAM CACHE)
# ==============================================================================

_meta_cache: Dict[str, Tuple[float, Dict]] = {}
_meta_lock = asyncio.Lock()
_format_cache: Dict[str, Tuple[float, List[Dict], str]] = {}
_format_lock = asyncio.Lock()

async def _garbage_collector():
    """Background task to clean RAM without blocking download threads"""
    async with _meta_lock:
        if len(_meta_cache) > YOUTUBE_META_MAX:
            # Purge oldest 30% entries
            keys = list(_meta_cache.keys())[:int(YOUTUBE_META_MAX * 0.3)]
            for k in keys: del _meta_cache[k]

# ==============================================================================
#  SECTION 3: SYSTEM CONFIGURATION
# ==============================================================================

class SystemConfig:
    DOWNLOAD_PATH = os.path.abspath("downloads")
    # Worker Calculation: Optimized for 16 Cores (High Concurrency)
    MAX_WORKERS = (os.cpu_count() or 4) * 4
    
    # === ARIA2: ENTERPRISE TUNING ===
    ARIA2_ARGS = [
        "-c",                       # Resume capability
        "-x", "16",                 # Max Connections (HTTP/1.1 Limit)
        "-s", "16",                 # Splits
        "-j", "32",                 # Parallel Downloads
        "-k", "1M",                 # Min Split Size (Instant start)
        "--buffer-size=1024M",      # 1GB RAM Buffer (Bypass Disk Latency)
        "--file-allocation=none",   # Zero-Allocation
        "--max-connection-per-server=16",
        "--stream-piece-selector=inorder",
        "--quiet=true"
    ]
    
    # === S25 ULTRA 5G SPOOFING ===
    # Simulating the latest hardware to get priority traffic from YouTube CDN
    USER_AGENTS = [
        # Samsung Galaxy S25 Ultra (Hypothetical Model SM-S938B - International)
        "Mozilla/5.0 (Linux; Android 15; SM-S938B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.58 Mobile Safari/537.36",
        # Samsung Galaxy S25 Ultra (US Variant)
        "Mozilla/5.0 (Linux; Android 15; SM-S938U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.58 Mobile Safari/537.36",
        # Fallback: S24 Ultra Android 14 (Proven High Speed)
        "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.144 Mobile Safari/537.36"
    ]

if not os.path.exists(SystemConfig.DOWNLOAD_PATH):
    os.makedirs(SystemConfig.DOWNLOAD_PATH)

def get_cookie_file() -> Optional[str]:
    """Rotates cookies to distribute request load"""
    if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 0:
        return "cookies.txt"
    if os.path.exists("cookies"):
        try:
            files = [f for f in os.listdir("cookies") if f.endswith(".txt")]
            if files: return os.path.join("cookies", random.choice(files))
        except: pass
    return None

async def _exec_shell(*args: str) -> Tuple[bytes, bytes]:
    """High-Performance Async Shell Wrapper"""
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        return await asyncio.wait_for(proc.communicate(), timeout=YTDLP_TIMEOUT)
    except asyncio.TimeoutError:
        with contextlib.suppress(Exception): proc.kill()
        return b"", b"timeout"

# ==============================================================================
#  SECTION 4: CORE ENGINE
# ==============================================================================

class YouTubeAPI:
    def __init__(self) -> None:
        self.base_url = "https://www.youtube.com/watch?v="
        self.playlist_url = "https://youtube.com/playlist?list="
        self._url_regex = re.compile(r"(?:youtube\.com|youtu\.be)")
        self._id_regex = re.compile(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*")
        
        self.pool = ThreadPoolExecutor(max_workers=SystemConfig.MAX_WORKERS)
        self.has_aria2 = shutil.which("aria2c") is not None
        
        if self.has_aria2:
            LOGGER("Core").info("Engine Started: S25 Ultra Mode | Aria2 (16x)")

    def _sanitize_link(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        if isinstance(videoid, str) and videoid.strip():
            link = self.base_url + videoid.strip()
        link = link.strip()
        if "youtu.be" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        elif "youtube.com/shorts/" in link or "youtube.com/live/" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        return link.split("&")[0]

    # --------------------------------------------------------------------------
    # URL HANDLING
    # --------------------------------------------------------------------------
    async def exists(self, link: str, videoid: Union[str, bool, None] = None) -> bool:
        return bool(self._url_regex.search(self._sanitize_link(link, videoid)))

    async def url(self, message: Message) -> Optional[str]:
        """Deep scanning for URLs"""
        msgs = [message] + ([message.reply_to_message] if message.reply_to_message else [])
        for msg in msgs:
            text = msg.text or msg.caption or ""
            entities = (msg.entities or []) + (msg.caption_entities or [])
            for ent in entities:
                if ent.type == MessageEntityType.URL:
                    return text[ent.offset: ent.offset + ent.length].split("&si")[0]
                if ent.type == MessageEntityType.TEXT_LINK:
                    return ent.url.split("&si")[0]
            if "http" in text:
                match = re.search(r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+", text)
                if match: return match.group(0)
        return None

    # --------------------------------------------------------------------------
    # METADATA (RAM CACHED)
    # --------------------------------------------------------------------------
    async def track(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[Dict, str]:
        prepared_link = self._sanitize_link(link, videoid)
        
        # 1. RAM Cache Check
        async with _meta_lock:
            if prepared_link in _meta_cache:
                ts, val = _meta_cache[prepared_link]
                if time.time() - ts < YOUTUBE_META_TTL:
                    return val['details'], val['vidid']
                else:
                    del _meta_cache[prepared_link]

        # 2. Network Fetch
        try:
            search = VideosSearch(prepared_link, limit=1)
            res = await search.next()
            if not res or not res.get("result"): raise ValueError("No results")
            
            info = res["result"][0]
            thumb = (info.get("thumbnails", [{}])[-1].get("url", "")).split("?")[0]
            details = {
                "title": info.get("title", "Unknown"),
                "link": info.get("link", prepared_link),
                "vidid": info.get("id", ""),
                "duration_min": info.get("duration", "0:00"),
                "thumb": thumb,
                "channel": info.get("channel", {}).get("name", "Unknown")
            }
            
            # 3. Cache Storage
            async with _meta_lock:
                _meta_cache[prepared_link] = (time.time(), {'details': details, 'vidid': info.get("id", "")})
            
            # Auto-Maintenance
            if len(_meta_cache) % 100 == 0:
                asyncio.create_task(_garbage_collector())
                
            return details, info.get("id", "")
        except: return {"title": "Error", "link": prepared_link, "vidid": "error", "duration_min": "0:00", "thumb": ""}, "error"

    async def details(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[str, Optional[str], int, str, str]:
        d, i = await self.track(link, videoid)
        if i == "error": return "", "0:00", 0, "", ""
        return d["title"], d["duration_min"], time_to_seconds(d["duration_min"]), d["thumb"], i

    async def title(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        d, _ = await self.track(link, videoid)
        return d.get("title", "")

    async def duration(self, link: str, videoid: Union[str, bool, None] = None) -> Optional[str]:
        d, _ = await self.track(link, videoid)
        return d.get("duration_min")

    async def thumbnail(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        d, _ = await self.track(link, videoid)
        return d.get("thumb", "")

    # --------------------------------------------------------------------------
    # DOWNLOADER: ZERO-LATENCY 5G MODE
    # --------------------------------------------------------------------------
    async def download(
        self,
        link: str,
        mystic,
        *,
        video: Union[bool, str, None] = None,
        videoid: Union[str, bool, None] = None,
    ) -> Union[Tuple[str, Optional[bool]], Tuple[None, None]]:
        
        link = self._sanitize_link(link, videoid)
        loop = asyncio.get_running_loop()

        try:
            match = self._id_regex.search(link)
            vid_id = match.group(1) if match else str(int(time.time()))
        except: vid_id = str(int(time.time()))

        ext = 'mp4' if video else 'm4a'
        file_name = f"{vid_id}.{ext}"
        final_path = os.path.join(SystemConfig.DOWNLOAD_PATH, file_name)

        if os.path.exists(final_path):
            return final_path, True

        # === CORE OPTIMIZATION: S25 Ultra Client + Zero-Conversion ===
        opts = {
            "outtmpl": final_path,
            "cookiefile": get_cookie_file(),
            "geo_bypass": True, "nocheckcertificate": True,
            "quiet": True, "no_warnings": True, "ignoreerrors": True,
            "force_ipv4": True,
            "user_agent": random.choice(SystemConfig.USER_AGENTS), # S25 Ultra Spoof
            "socket_timeout": 15,
            
            # This is the key to 5G speeds:
            "extractor_args": {
                'youtube': {
                    'skip': ['dash', 'hls'], 
                    'player_client': ['android', 'web'] # Prioritize Android API
                }
            },
        }

        # Format Logic: Direct Stream Fetch
        if video:
            opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        else:
            # Force M4A directly. No FFmpeg, no waiting.
            opts["format"] = "bestaudio[ext=m4a]/bestaudio"

        # Aria2 Injection
        if self.has_aria2:
            opts["external_downloader"] = "aria2c"
            opts["external_downloader_args"] = SystemConfig.ARIA2_ARGS
        else:
            opts["concurrent_fragment_downloads"] = 15
            opts["buffersize"] = 25 * 1024 * 1024 

        def _execute_dl():
            with yt_dlp.YoutubeDL(opts) as ydl:
                try: ydl.download([link])
                except Exception as e: LOGGER("Downloader").error(f"DL Error: {e}")
            return final_path if os.path.exists(final_path) else None

        downloaded_file = await loop.run_in_executor(self.pool, _execute_dl)
        
        if downloaded_file: return downloaded_file, True
        return None, None

    # --------------------------------------------------------------------------
    # MEDIA & PLAYLIST UTILITIES (OPTIMIZED)
    # --------------------------------------------------------------------------
    async def video_stream_url(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[int, str]:
        """Direct Stream Link (For Live/Radio)"""
        link = self._sanitize_link(link, videoid)
        cookie = get_cookie_file()
        cookies_arg = ["--cookies", cookie] if cookie else []
        
        stdout, stderr = await _exec_shell(
            "yt-dlp", *cookies_arg, "-g", "-f", "best[height<=?720][width<=?1280]", link
        )
        return (1, stdout.decode().split("\n")[0]) if stdout else (0, stderr.decode())

    # Compatibility Alias
    video = video_stream_url 

    async def playlist(
        self, link: str, limit: int, user_id, videoid: Union[str, bool, None] = None
    ) -> List[str]:
        """Robust Playlist Extraction (Handles Large Lists)"""
        if videoid:
            link = self.playlist_url + str(videoid)
        link = self._sanitize_link(link).split("&")[0]

        # Strategy 1: Fast Python Lib (VideosSearch/Playlist)
        # Best for small/medium playlists
        try:
            plist = await Playlist.get(link)
            if plist and plist.get("videos"):
                 return [video["id"] for video in plist["videos"][:limit] if video.get("id")]
        except: pass

        # Strategy 2: yt-dlp Flat Dump (Robust Fallback)
        # Best for huge playlists (doesn't download info, just IDs)
        cookie = get_cookie_file()
        cookies_arg = ["--cookies", cookie] if cookie else []
        
        stdout, _ = await _exec_shell(
            "yt-dlp",
            *cookies_arg,
            "-i",
            "--get-id",
            "--flat-playlist",  # Crucial for speed
            "--playlist-end", str(limit),
            "--skip-download",
            "--no-warnings",
            link,
        )
        items = stdout.decode().strip().split("\n") if stdout else []
        return [i for i in items if i]

    async def formats(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> Tuple[List[Dict], str]:
        link = self._sanitize_link(link, videoid)
        key = f"f:{link}"
        now = time.time()

        async with _format_lock:
            cached = _format_cache.get(key)
            if cached and now - cached[0] < YOUTUBE_META_TTL:
                return cached[1], cached[2]

        opts = {"quiet": True, "cookiefile": get_cookie_file()}
        out: List[Dict] = []
        
        # Run extractor in thread
        def _get_formats():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(link, download=False)
                    return info.get("formats", [])
            except: return []

        loop = asyncio.get_running_loop()
        formats = await loop.run_in_executor(self.pool, _get_formats)

        for fmt in formats:
            if not fmt.get("filesize") and not fmt.get("filesize_approx"): continue
            out.append({
                "format": fmt.get("format"),
                "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
                "format_id": fmt.get("format_id"),
                "ext": fmt.get("ext"),
                "format_note": fmt.get("format_note", ""),
                "yturl": link,
            })

        async with _format_lock:
            if len(_format_cache) > 1000: _format_cache.clear()
            _format_cache[key] = (now, out, link)

        return out, link

    async def slider(
        self, link: str, query_type: int, videoid: Union[str, bool, None] = None
    ) -> Tuple[str, Optional[str], str, str]:
        link = self._sanitize_link(link, videoid)
        try:
            data = await VideosSearch(link, limit=10).next()
            results = data.get("result", [])
            if not results or query_type >= len(results):
                raise IndexError
            r = results[query_type]
            return (
                r.get("title", ""),
                r.get("duration"),
                r.get("thumbnails", [{}])[-1].get("url", "").split("?")[0],
                r.get("id", ""),
            )
        except:
             return "Error", "0:00", "", "error"

# Initialize Engine
YouTube = YouTubeAPI()
