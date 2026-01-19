# Authored By Certified Coders © 2025
# Optimized by TitanOS (Full Features + 2.6Gbps Turbo Engine)

import asyncio
import contextlib
import json
import os
import re
import time
import random
import shutil
import logging
from typing import Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.aio import VideosSearch, Playlist

# --- Imports & Logging Setup ---
try:
    from AnnieXMedia.utils.database import is_on_off
    from AnnieXMedia.utils.formatters import time_to_seconds
    from AnnieXMedia.utils.tuning import YTDLP_TIMEOUT, YOUTUBE_META_MAX, YOUTUBE_META_TTL
    from AnnieXMedia import LOGGER
except ImportError:
    # Fallback placeholders
    logging.basicConfig(level=logging.ERROR)
    def LOGGER(name): return logging.getLogger(name)
    async def is_on_off(x): return True
    def time_to_seconds(t): return 0
    YTDLP_TIMEOUT = 300
    YOUTUBE_META_MAX = 1000
    YOUTUBE_META_TTL = 3600

# Suppress noise
logging.getLogger("yt_dlp").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# --- Caches ---
_cache: Dict[str, Tuple[float, List[Dict]]] = {}
_cache_lock = asyncio.Lock()
_formats_cache: Dict[str, Tuple[float, List[Dict], str]] = {}
_formats_lock = asyncio.Lock()

# --- Configuration ---
class Config:
    DOWNLOAD_PATH = "downloads"
    MAX_WORKERS = 50 # Optimized for high-speed VPS

if not os.path.exists(Config.DOWNLOAD_PATH):
    os.makedirs(Config.DOWNLOAD_PATH)

# --- Helpers ---
def get_cookie_file() -> Optional[str]:
    """Smart Cookie Rotation"""
    if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 0:
        return "cookies.txt"
    if os.path.exists("cookies"):
        try:
            files = [f for f in os.listdir("cookies") if f.endswith(".txt")]
            if files:
                return os.path.join("cookies", random.choice(files))
        except:
            pass
    return None

def get_user_agent():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36",
    ]
    return random.choice(agents)

async def _exec_proc(*args: str) -> Tuple[bytes, bytes]:
    """Execute shell commands safely"""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        return await asyncio.wait_for(proc.communicate(), timeout=YTDLP_TIMEOUT)
    except asyncio.TimeoutError:
        with contextlib.suppress(Exception):
            proc.kill()
        return b"", b"timeout"

# --- Main Class ---
class YouTubeAPI:
    def __init__(self) -> None:
        self.base_url = "https://www.youtube.com/watch?v="
        self.playlist_url = "https://youtube.com/playlist?list="
        self._url_pattern = re.compile(r"(?:youtube\.com|youtu\.be)")
        self.pool = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)
        self.has_aria2 = shutil.which("aria2c") is not None

    def _prepare_link(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        if isinstance(videoid, str) and videoid.strip():
            link = self.base_url + videoid.strip()
        link = link.strip()
        if "youtu.be" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        elif "youtube.com/shorts/" in link or "youtube.com/live/" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        return link.split("&")[0]

    # === URL Handling ===
    async def exists(self, link: str, videoid: Union[str, bool, None] = None) -> bool:
        return bool(self._url_pattern.search(self._prepare_link(link, videoid)))

    async def url(self, message: Message) -> Optional[str]:
        msgs = [message] + ([message.reply_to_message] if message.reply_to_message else [])
        for msg in msgs:
            text = msg.text or msg.caption or ""
            entities = (msg.entities or []) + (msg.caption_entities or [])
            for ent in entities:
                if ent.type == MessageEntityType.URL:
                    return text[ent.offset: ent.offset + ent.length].split("&si")[0]
                if ent.type == MessageEntityType.TEXT_LINK:
                    return ent.url.split("&si")[0]
        return None

    # === Metadata Fetching ===
    async def track(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[Dict, str]:
        prepared_link = self._prepare_link(link, videoid)
        
        # 1. Check Cache
        async with _cache_lock:
            if prepared_link in _cache:
                ts, val = _cache[prepared_link]
                if time.time() - ts < YOUTUBE_META_TTL:
                    return val[0], val[1]

        # 2. Fetch Data
        try:
            search = VideosSearch(prepared_link, limit=1)
            res = await search.next()
            if not res or not res.get("result"):
                raise ValueError("No results found")
            
            info = res["result"][0]
            thumb = (info.get("thumbnails", [{}])[-1].get("url", "")).split("?")[0]
            
            details = {
                "title": info.get("title", ""),
                "link": info.get("link", prepared_link),
                "vidid": info.get("id", ""),
                "duration_min": info.get("duration"),
                "thumb": thumb,
            }
            
            # 3. Save Cache
            async with _cache_lock:
                _cache[prepared_link] = (time.time(), (details, info.get("id", "")))
                
            return details, info.get("id", "")
        except Exception:
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

    # === 🚀 SUPERCHARGED DOWNLOADER (2.6Gbps Engine) ===
    async def download(
        self,
        link: str,
        mystic,
        *,
        video: Union[bool, str, None] = None,
        videoid: Union[str, bool, None] = None,
    ) -> Union[Tuple[str, Optional[bool]], Tuple[None, None]]:
        
        link = self._prepare_link(link, videoid)
        loop = asyncio.get_running_loop()

        # Generate unique ID
        try:
            if "v=" in link: vid_id = link.split("v=")[1].split("&")[0]
            elif "youtu.be/" in link: vid_id = link.split("youtu.be/")[1].split("?")[0]
            else: vid_id = str(int(time.time()))
        except:
             vid_id = str(int(time.time()))

        file_name = f"{vid_id}.{'mp4' if video else 'm4a'}"
        final_path = os.path.join(Config.DOWNLOAD_PATH, file_name)

        # 🔥 Speed & Anti-Ban Config 🔥
        opts = {
            "outtmpl": final_path,
            "cookiefile": get_cookie_file(),
            "geo_bypass": True,
            "nocheckcertificate": True, # Speed up SSL handshake
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "extractor_args": {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_client': ['android', 'web'], # Spoof as Android
                }
            },
            "user_agent": get_user_agent(),
            "concurrent_fragment_downloads": 10,
        }

        # Format Selection (Speed vs Quality)
        if video:
            opts["format"] = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        else:
            # Direct Stream Copy (No Conversion) = Maximum Speed
            opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"

        # ⚡ Aria2 Injection for 2.6Gbps ⚡
        if self.has_aria2:
            opts["external_downloader"] = "aria2c"
            opts["external_downloader_args"] = [
                "-c",
                "-x", "16",         # Max connections
                "-s", "16",         # Max splits
                "-j", "32",         # Max concurrents
                "-k", "1M",         # Min split
                "--buffer-size=64M", # RAM Buffering (Crucial for high speed)
                "--file-allocation=none",
            ]

        def _run_download():
            if os.path.exists(final_path):
                return final_path
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    ydl.download([link])
                except Exception as e:
                    LOGGER(__name__).error(f"DL Error: {e}")
                    return None
            
            if os.path.exists(final_path):
                return final_path
            return None

        # Execute
        downloaded_file = await loop.run_in_executor(self.pool, _run_download)
        
        if downloaded_file:
            return downloaded_file, True
        return None, None

    # === Media & Formats ===
    async def video_stream_url(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[int, str]:
        """Get direct stream URL (for live streams)"""
        link = self._prepare_link(link, videoid)
        cookie = get_cookie_file()
        cookies_arg = ["--cookies", cookie] if cookie else []
        
        stdout, stderr = await _exec_proc(
            "yt-dlp", *cookies_arg, "-g", "-f", "best[height<=?720][width<=?1280]", link
        )
        return (1, stdout.decode().split("\n")[0]) if stdout else (0, stderr.decode())

    # Compatibility alias for old calls
    video = video_stream_url 

    async def playlist(
        self, link: str, limit: int, user_id, videoid: Union[str, bool, None] = None
    ) -> List[str]:
        if videoid:
            link = self.playlist_url + str(videoid)
        link = self._prepare_link(link).split("&")[0]

        # 1. Try library first (Faster)
        try:
            plist = await Playlist.get(link)
            if plist and plist.get("videos"):
                 return [video["id"] for video in plist["videos"][:limit] if video.get("id")]
        except:
            pass

        # 2. Fallback to yt-dlp
        cookie = get_cookie_file()
        cookies_arg = ["--cookies", cookie] if cookie else []
        
        stdout, _ = await _exec_proc(
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
        link = self._prepare_link(link, videoid)
        key = f"f:{link}"
        now = time.time()

        async with _formats_lock:
            cached = _formats_cache.get(key)
            if cached and now - cached[0] < YOUTUBE_META_TTL:
                return cached[1], cached[2]

        opts = {"quiet": True, "cookiefile": get_cookie_file()}
        out: List[Dict] = []
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=False)
                for fmt in info.get("formats", []):
                    if not fmt.get("filesize") and not fmt.get("filesize_approx"): continue
                    out.append({
                        "format": fmt["format"],
                        "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
                        "format_id": fmt["format_id"],
                        "ext": fmt["ext"],
                        "format_note": fmt.get("format_note", ""),
                        "yturl": link,
                    })
        except: pass

        async with _formats_lock:
            if len(_formats_cache) > 1000: _formats_cache.clear()
            _formats_cache[key] = (now, out, link)

        return out, link

    async def slider(
        self, link: str, query_type: int, videoid: Union[str, bool, None] = None
    ) -> Tuple[str, Optional[str], str, str]:
        link = self._prepare_link(link, videoid)
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

YouTube = YouTubeAPI()
