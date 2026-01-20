# ==============================================================================
#  INFINITY-TITANIUM HYBRID ENGINE © 2026
#  Identity: Google Pixel 10 Pro (Stable Android 16)
#  Network: 5G+ Priority | Mode: RAW DIRECT STREAM (Zero Latency)
#  Merged Features: Force Aria2 16x | Smart Format Detection
# ==============================================================================

import asyncio
import os
import re
import json
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
#  SECTION 1: ENVIRONMENT & PERFORMANCE
# ==============================================================================

logging.basicConfig(level=logging.ERROR)
def LOGGER(name): return logging.getLogger(name)

try:
    from AnnieXMedia.utils.database import is_on_off
    from AnnieXMedia.utils.formatters import time_to_seconds
    from AnnieXMedia.utils.tuning import YTDLP_TIMEOUT, YOUTUBE_META_MAX, YOUTUBE_META_TTL
    from AnnieXMedia import LOGGER as GLOBAL_LOGGER
    def LOGGER(name): return GLOBAL_LOGGER(name)
except ImportError:
    async def is_on_off(x): return True
    def time_to_seconds(t): return 0
    YTDLP_TIMEOUT = 300
    YOUTUBE_META_MAX = 5000
    YOUTUBE_META_TTL = 3600

# MUTE LOGS FOR EXTREME SPEED
logging.getLogger("yt_dlp").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.WARNING)

# ==============================================================================
#  SECTION 2: PIXEL 10 PRO IDENTITY & 5G+ CONFIG
# ==============================================================================

class SystemConfig:
    DOWNLOAD_PATH = os.path.abspath("downloads")
    MAX_WORKERS = (os.cpu_count() or 4) * 16  # Max Parallel Threads
    
    # === 5G+ GOD MODE ARIA2 ===
    ARIA2_ARGS = [
        "-c", "-x", "16", "-s", "16", "-j", "32", "-k", "1M",
        "--buffer-size=1024M", "--file-allocation=none", "--quiet=true",
        "--max-connection-per-server=16", "--min-split-size=1M"
    ]
    
    # === IDENTITY: PIXEL 10 PRO (STABLE RELEASE) ===
    # Triggers "Android Priority" -> Returns light & fast Opus/WebM streams
    NATIVE_AGENTS = [
        "Mozilla/5.0 (Linux; Android 16; Pixel 10 Pro Build/TP1A.251005.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.7200.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 16; Pixel 10 Pro Build/TP1A.250915.008) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.7150.12 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 16; Pixel 10 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36"
    ]

if not os.path.exists(SystemConfig.DOWNLOAD_PATH):
    os.makedirs(SystemConfig.DOWNLOAD_PATH)

# ==============================================================================
#  SECTION 3: INSTANT CACHE SYSTEM
# ==============================================================================

_meta_cache: Dict[str, Tuple[float, Dict]] = {}
_meta_lock = asyncio.Lock()

async def _clean_cache():
    async with _meta_lock:
        if len(_meta_cache) > YOUTUBE_META_MAX:
            keys = list(_meta_cache.keys())[:int(YOUTUBE_META_MAX * 0.3)]
            for k in keys: del _meta_cache[k]

def get_cookie_file() -> Optional[str]:
    if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 0: return "cookies.txt"
    if os.path.exists("cookies"):
        try:
            files = [f for f in os.listdir("cookies") if f.endswith(".txt")]
            if files: return os.path.join("cookies", random.choice(files))
        except: pass
    return None

async def _exec_shell(*args: str) -> Tuple[bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        return await asyncio.wait_for(proc.communicate(), timeout=YTDLP_TIMEOUT)
    except asyncio.TimeoutError:
        with contextlib.suppress(Exception): proc.kill()
        return b"", b"timeout"

# ==============================================================================
#  SECTION 4: CORE ENGINE (MERGED LOGIC)
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
            LOGGER("Core").info("Hybrid Engine: Pixel 10 Pro + Aria2 16x (Ready) 🚀")

    def _sanitize_link(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        if isinstance(videoid, str) and videoid.strip():
            link = self.base_url + videoid.strip()
        link = link.strip()
        if "youtu.be" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        elif "youtube.com/shorts/" in link or "youtube.com/live/" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        return link.split("&")[0]

    # --- URL & CHECK ---
    async def exists(self, link: str, videoid: Union[str, bool, None] = None) -> bool:
        return True # Bypass regex check for speed

    async def url(self, message: Message) -> Optional[str]:
        # Fast extraction logic
        if message.text and "http" in message.text:
            match = re.search(r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+", message.text)
            return match.group(0) if match else None
        return None

    # --- METADATA ---
    async def track(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[Dict, str]:
        prepared_link = self._sanitize_link(link, videoid)
        
        async with _meta_lock:
            if prepared_link in _meta_cache:
                ts, val = _meta_cache[prepared_link]
                if time.time() - ts < YOUTUBE_META_TTL:
                    return val['details'], val['vidid']
                else:
                    del _meta_cache[prepared_link]

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
            vid_id = info.get("id", "")
            
            async with _meta_lock:
                _meta_cache[prepared_link] = (time.time(), {'details': details, 'vidid': vid_id})
            
            if len(_meta_cache) % 100 == 0: asyncio.create_task(_clean_cache())
            return details, vid_id
        except:
             return {"title": "Error", "link": prepared_link, "vidid": "error", "duration_min": "0:00", "thumb": ""}, "error"

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

    # ==========================================================================
    #  THE HYBRID DOWNLOADER (RAW SPEED + SMART FORMATS)
    # ==========================================================================
    async def download(
        self, link: str, mystic, *, video: Union[bool, str, None] = None, videoid: Union[str, bool, None] = None,
    ) -> Union[Tuple[str, Optional[bool]], Tuple[None, None]]:
        
        link = self._sanitize_link(link, videoid)
        loop = asyncio.get_running_loop()

        try:
            match = self._id_regex.search(link)
            vid_id = match.group(1) if match else str(int(time.time()))
        except: vid_id = str(int(time.time()))

        # 1. SMART SCANNER: Check if ANY format exists (No Redownload)
        # This checks for WebM (Pixel default), M4A (iPhone default), or MP3/MP4
        for ext in ['webm', 'm4a', 'opus', 'mp4', 'mp3', 'mkv']:
            final_path = os.path.join(SystemConfig.DOWNLOAD_PATH, f"{vid_id}.{ext}")
            if os.path.exists(final_path): return final_path, True

        # 2. RAW CONFIGURATION (Maximum Speed)
        opts = {
            # Save as ID.extension (Let YouTube decide the best extension)
            "outtmpl": os.path.join(SystemConfig.DOWNLOAD_PATH, f"{vid_id}.%(ext)s"),
            "cookiefile": get_cookie_file(),
            "geo_bypass": True, "nocheckcertificate": True,
            "quiet": True, "no_warnings": True, "ignoreerrors": True,
            "force_ipv4": True,
            
            # IDENTITY: PIXEL 10 PRO STABLE (Best Priority)
            "user_agent": random.choice(SystemConfig.NATIVE_AGENTS),
            
            "socket_timeout": 30,
            "retries": 15,
            
            # CRITICAL FOR SPEED: Disable FFmpeg Conversion
            # We will play the raw file (WebM/Opus) directly
            "prefer_ffmpeg": False,
        }

        # 3. FORCE 5G+ ARIA2
        if self.has_aria2:
            opts["external_downloader"] = "aria2c"
            opts["external_downloader_args"] = SystemConfig.ARIA2_ARGS

        # 4. UNIVERSAL FORMAT LOGIC
        if video:
            opts["format"] = "bestvideo+bestaudio/best"
            opts["merge_output_format"] = "mp4" # Merge only if video requested
        else:
            # "bestaudio" with Pixel Agent = Opus/WebM (Fastest Stream available)
            # We DO NOT force m4a here to avoid conversion lag.
            opts["format"] = "bestaudio/best"

        def _execute_dl():
            with yt_dlp.YoutubeDL(opts) as ydl:
                try: ydl.download([link])
                except Exception as e: LOGGER("DL").error(f"DL Error: {e}")
            
            # 5. SMART DISCOVERY: Find whatever file landed
            for f in os.listdir(SystemConfig.DOWNLOAD_PATH):
                if f.startswith(vid_id):
                    return os.path.join(SystemConfig.DOWNLOAD_PATH, f)
            return None

        downloaded_file = await loop.run_in_executor(self.pool, _execute_dl)
        if downloaded_file: return downloaded_file, True
        return None, None

    # --- UTILS ---
    async def video_stream_url(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[int, str]:
        link = self._sanitize_link(link, videoid)
        cookie = get_cookie_file()
        cookies_arg = ["--cookies", cookie] if cookie else []
        stdout, stderr = await _exec_shell("yt-dlp", *cookies_arg, "-g", "-f", "best[height<=?1080]", link)
        return (1, stdout.decode().split("\n")[0]) if stdout else (0, stderr.decode())
    video = video_stream_url 

    async def playlist(self, link: str, limit: int, user_id, videoid: Union[str, bool, None] = None) -> List[str]:
        if videoid: link = self.playlist_url + str(videoid)
        link = self._sanitize_link(link).split("&")[0]

        try:
            plist = await Playlist.get(link)
            if plist and plist.get("videos"):
                 return [video["id"] for video in plist["videos"][:limit] if video.get("id")]
        except: pass

        cookie = get_cookie_file()
        cookies_arg = ["--cookies", cookie] if cookie else []
        stdout, _ = await _exec_shell(
            "yt-dlp", *cookies_arg, "-i", "--get-id", "--flat-playlist", 
            "--playlist-end", str(limit), "--skip-download", "--no-warnings", link
        )
        items = stdout.decode().strip().split("\n") if stdout else []
        return [i for i in items if i]

    async def formats(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[List[Dict], str]:
        link = self._sanitize_link(link, videoid)
        opts = {"quiet": True, "cookiefile": get_cookie_file()}
        def _get_formats():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl: return ydl.extract_info(link, download=False).get("formats", [])
            except: return []
        loop = asyncio.get_running_loop()
        formats = await loop.run_in_executor(self.pool, _get_formats)
        out = []
        for fmt in formats:
            if not fmt.get("filesize") and not fmt.get("filesize_approx"): continue
            out.append({
                "format": fmt.get("format"), "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
                "format_id": fmt.get("format_id"), "ext": fmt.get("ext"), "format_note": fmt.get("format_note", ""), "yturl": link
            })
        return out, link

    async def slider(self, link: str, query_type: int, videoid: Union[str, bool, None] = None) -> Tuple[str, Optional[str], str, str]:
        link = self._sanitize_link(link, videoid)
        try:
            data = await VideosSearch(link, limit=10).next()
            results = data.get("result", [])
            if not results or query_type >= len(results): raise IndexError
            r = results[query_type]
            return (r.get("title", ""), r.get("duration"), r.get("thumbnails", [{}])[-1].get("url", "").split("?")[0], r.get("id", ""))
        except: return "Error", "0:00", "", "error"

YouTube = YouTubeAPI()
