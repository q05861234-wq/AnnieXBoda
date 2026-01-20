
اشطا يعم بس لو تزود برضو البلاي ليست عشان طبعا في ناس هتطلب بلاي ليست وشيل كلمة تايتان الخايبة دي الله يرضيك احنا مش صغيرين
# ==============================================================================
#  TITAN OS ULTIMATE EDITION - YOUTUBE CORE © 2025
#  Optimized for 16-Core vCPU | Zero-Latency | Aria2 Integration
#  Status: High-Performance Production Ready
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
#  SECTION 1: ENVIRONMENT & LOGGING SETUP
# ==============================================================================

try:
    from AnnieXMedia.utils.database import is_on_off
    from AnnieXMedia.utils.formatters import time_to_seconds
    from AnnieXMedia.utils.tuning import YTDLP_TIMEOUT, YOUTUBE_META_MAX, YOUTUBE_META_TTL
    from AnnieXMedia import LOGGER
except ImportError:
    # Fallback Environment for testing/standalone
    logging.basicConfig(level=logging.ERROR)
    def LOGGER(name): return logging.getLogger(name)
    async def is_on_off(x): return True
    def time_to_seconds(t): return 0
    YTDLP_TIMEOUT = 300
    YOUTUBE_META_MAX = 2000
    YOUTUBE_META_TTL = 3600

# Silence unnecessary logs for performance
logging.getLogger("yt_dlp").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.WARNING)

# ==============================================================================
#  SECTION 2: MEMORY CACHING SYSTEM (RAM Database)
# ==============================================================================

_meta_cache: Dict[str, Tuple[float, Dict]] = {}
_meta_lock = asyncio.Lock()

_format_cache: Dict[str, Tuple[float, List[Dict], str]] = {}
_format_lock = asyncio.Lock()

# Clean cache automatically if it gets too big
async def _clean_cache():
    async with _meta_lock:
        if len(_meta_cache) > YOUTUBE_META_MAX:
            # Remove oldest 50%
            keys = list(_meta_cache.keys())[:int(YOUTUBE_META_MAX/2)]
            for k in keys: del _meta_cache[k]

# ==============================================================================
#  SECTION 3: SYSTEM CONFIGURATION & HELPERS
# ==============================================================================

class TitanConfig:
    """System-Level Configuration for Maximum Throughput"""
    DOWNLOAD_PATH = os.path.abspath("downloads")
    # Smart Worker Calculation: 2 Threads per Core + 4 I/O Threads
    MAX_WORKERS = (os.cpu_count() or 4) * 2 + 4
    
    # Aria2 Turbo Settings (The Secret Sauce)
    ARIA2_ARGS = [
        "-c",                       # Resume capability
        "-x", "16",                 # 16 Connections per server
        "-s", "16",                 # 16 Splits per file
        "-j", "32",                 # 32 Parallel downloads
        "-k", "1M",                 # Min split size
        "--buffer-size=1024M",      # 1GB RAM Buffer (Speed!)
        "--file-allocation=none",   # Instant file creation
        "--console-log-level=error",
        "--summary-interval=0"
    ]
    
    # Anti-Fingerprinting Agents
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"
    ]

if not os.path.exists(TitanConfig.DOWNLOAD_PATH):
    os.makedirs(TitanConfig.DOWNLOAD_PATH)

def get_cookie_file() -> Optional[str]:
    """Intelligent Cookie Rotation Logic"""
    # Priority 1: Root file
    if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 0:
        return "cookies.txt"
    # Priority 2: Rotation Folder
    if os.path.exists("cookies"):
        try:
            files = [f for f in os.listdir("cookies") if f.endswith(".txt")]
            if files:
                selected = random.choice(files)
                return os.path.join("cookies", selected)
        except: pass
    return None

def get_random_agent():
    return random.choice(TitanConfig.USER_AGENTS)

async def _exec_shell(*args: str) -> Tuple[bytes, bytes]:
    """High-Performance Subprocess Wrapper"""
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        return await asyncio.wait_for(proc.communicate(), timeout=YTDLP_TIMEOUT)
    except asyncio.TimeoutError:
        with contextlib.suppress(Exception): proc.kill()
        return b"", b"timeout"

# ==============================================================================
#  SECTION 4: THE CORE ENGINE (YouTubeAPI)
# ==============================================================================

class YouTubeAPI:
    def __init__(self) -> None:
        self.base_url = "https://www.youtube.com/watch?v="
        self.playlist_url = "https://youtube.com/playlist?list="
        self._url_pattern = re.compile(r"(?:youtube\.com|youtu\.be)")
        self._id_regex = re.compile(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*")
        
        # Thread Pool for Blocking I/O
        self.pool = ThreadPoolExecutor(max_workers=TitanConfig.MAX_WORKERS)
        
        # Check Acceleration
        self.has_aria2 = shutil.which("aria2c") is not None
        if self.has_aria2:
            LOGGER("TitanOS").info("Aria2c Detected. Turbo Mode: ENABLED")
        else:
            LOGGER("TitanOS").warning("Aria2c Missing. Falling back to native (Slower).")

    def _sanitize_link(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        """Normalizes Links to Standard Format"""
        if isinstance(videoid, str) and videoid.strip():
            link = self.base_url + videoid.strip()
        link = link.strip()
        
        # Short Links
        if "youtu.be" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        # Live/Shorts
        elif "youtube.com/shorts/" in link or "youtube.com/live/" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
            
        return link.split("&")[0]

    # --------------------------------------------------------------------------
    # URL VALIDATION & PARSING
    # --------------------------------------------------------------------------
    async def exists(self, link: str, videoid: Union[str, bool, None] = None) -> bool:
        return bool(self._url_pattern.search(self._sanitize_link(link, videoid)))

    async def url(self, message: Message) -> Optional[str]:
        """Deep Scan for URLs in Messages"""
        msgs = [message] + ([message.reply_to_message] if message.reply_to_message else [])
        for msg in msgs:
            text = msg.text or msg.caption or ""
            
            # Check Entities first (Most Accurate)
            entities = (msg.entities or []) + (msg.caption_entities or [])
            for ent in entities:
                if ent.type == MessageEntityType.URL:
                    return text[ent.offset: ent.offset + ent.length].split("&si")[0]
                if ent.type == MessageEntityType.TEXT_LINK:
                    return ent.url.split("&si")[0]
            
            # Fallback Text Search
            if "http" in text:
                # Basic regex for raw text
                match = re.search(r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+", text)
                if match: return match.group(0)
        return None

    # --------------------------------------------------------------------------
    # METADATA FETCHING (WITH RAM CACHE)
    # --------------------------------------------------------------------------
    async def track(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[Dict, str]:
        prepared_link = self._sanitize_link(link, videoid)
        
        # 1. Fast Path: Cache
        async with _meta_lock:
            if prepared_link in _meta_cache:
                ts, val = _meta_cache[prepared_link]
                if time.time() - ts < YOUTUBE_META_TTL:
                    return val['details'], val['vidid']
                else:
                    del _meta_cache[prepared_link]

        # 2. Network Path
        try:
            search = VideosSearch(prepared_link, limit=1)
            res = await search.next()
            if not res or not res.get("result"):
                raise ValueError("No results found")
            
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
            vid_id = info.get("id", "")
            
            # 3. Store in Cache
            async with _meta_lock:
                _meta_cache[prepared_link] = (time.time(), {'details': details, 'vidid': vid_id})
            
            # Periodically clean cache
            if len(_meta_cache) % 100 == 0:
                asyncio.create_task(_clean_cache())
                
            return details, vid_id
        except Exception:
             return {"title": "Error", "link": prepared_link, "vidid": "error", "duration_min": "0:00", "thumb": ""}, "error"

    # Specific Helpers
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
    # TITAN DOWNLOADER (ARIA2 + NO-CONVERSION LOGIC)
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

        # Generate Reliable ID
        try:
            match = self._id_regex.search(link)
            vid_id = match.group(1) if match else str(int(time.time()))
        except:
             vid_id = str(int(time.time()))

        ext = 'mp4' if video else 'm4a'
        file_name = f"{vid_id}.{ext}"
        final_path = os.path.join(TitanConfig.DOWNLOAD_PATH, file_name)

        # Instant Hit (If exists)
        if os.path.exists(final_path):
            return final_path, True

        # === THE CORE LOGIC: Zero-Conversion ===
        # We instruct yt-dlp to download m4a directly. 
        # This bypasses ffmpeg conversion which kills CPU on long videos.
        
        opts = {
            "outtmpl": final_path,
            "cookiefile": get_cookie_file(),
            "geo_bypass": True,
            "nocheckcertificate": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "force_ipv4": True,
            "user_agent": get_random_agent(),
            "socket_timeout": 15,
            "retries": 3,
            
            # Critical Optimization for Long Videos
            "extractor_args": {
                'youtube': {
                    'skip': ['dash', 'hls'], # Avoid complex streams
                    'player_client': ['android', 'web'],
                }
            },
        }

        if video:
            opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        else:
            # PURE SPEED: Download raw M4A stream (No re-encoding)
            opts["format"] = "bestaudio[ext=m4a]/bestaudio"

        # === ARIA2 INJECTION ===
        if self.has_aria2:
            opts["external_downloader"] = "aria2c"
            opts["external_downloader_args"] = TitanConfig.ARIA2_ARGS
        else:
            # Fallback Tuning
            opts["concurrent_fragment_downloads"] = 10
            opts["buffersize"] = 1024 * 1024 * 16 # 16MB

        def _execute_download():
            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    ydl.download([link])
                except Exception as e:
                    LOGGER("TitanDL").error(f"DL Failed: {e}")
                    return None
            
            if os.path.exists(final_path):
                return final_path
            return None

        # Run in separate thread to keep bot responsive
        downloaded_file = await loop.run_in_executor(self.pool, _execute_download)
        
        if downloaded_file:
            return downloaded_file, True
        return None, None

    # --------------------------------------------------------------------------
    # MEDIA & PLAYLIST UTILITIES
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
        if videoid:
            link = self.playlist_url + str(videoid)
        link = self._sanitize_link(link).split("&")[0]

        # 1. Try Library (Fastest)
        try:
            plist = await Playlist.get(link)
            if plist and plist.get("videos"):
                 return [video["id"] for video in plist["videos"][:limit] if video.get("id")]
        except: pass

        # 2. Try Flat Dump (Reliable)
        cookie = get_cookie_file()
        cookies_arg = ["--cookies", cookie] if cookie else []
        
        stdout, _ = await _exec_shell(
            "yt-dlp",
            *cookies_arg,
            "-i", "--get-id", "--flat-playlist", "--playlist-end", str(limit), "--skip-download",
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

# Initialize
YouTube = YouTubeAPI()
