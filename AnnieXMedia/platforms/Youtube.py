# ==============================================================================
#  YOUTUBE STUDIO GOD MODE © 2026
#  Identity: Android Creator Studio (VIP Access) | Network: Proxy Shield
#  Status: TRUSTED UPLOADER | BYPASSING VERIFICATION | RAW STREAM
# ==============================================================================

import asyncio
import os
import re
import json
import time
import random
import shutil
import logging
import contextlib
from typing import Dict, List, Optional, Tuple, Union, Any
from concurrent.futures import ThreadPoolExecutor

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.aio import VideosSearch, Playlist

# ==============================================================================
#  SECTION 1: ENVIRONMENT & LOGGING
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

# MUTE ALL NOISE
logging.getLogger("yt_dlp").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.WARNING)

# ==============================================================================
#  SECTION 2: PROXY & COOKIE PARSERS
# ==============================================================================

def get_formatted_proxy() -> Optional[str]:
    """ Parses IP:PORT:USER:PASS to http://USER:PASS@IP:PORT """
    if not os.path.exists("proxies.txt"): return None
    try:
        with open("proxies.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines: return None
        
        raw = random.choice(lines)
        parts = raw.split(':')
        if len(parts) == 4:
            return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
        elif "@" in raw:
            return raw
    except: pass
    return None

def get_cookie_file() -> Optional[str]:
    possible_paths = ["cookies.txt", "cookies/cookies.txt", "AnnieXMedia/cookies.txt", "cookies"]
    for path in possible_paths:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return os.path.abspath(path)
    return None

# ==============================================================================
#  SECTION 3: STUDIO CONFIGURATION
# ==============================================================================

class SystemConfig:
    DOWNLOAD_PATH = os.path.abspath("downloads")
    MAX_WORKERS = (os.cpu_count() or 4) * 8
    
    # === ARIA2 ULTRA SETTINGS ===
    ARIA2_ARGS = [
        "-c", "-x", "16", "-s", "16", "-j", "32", "-k", "1M",
        "--buffer-size=1024M", "--file-allocation=none", "--quiet=true"
    ]
    
    # === IDENTITY: TRUSTED DESKTOP / STUDIO ===
    # These UAs look like a creator managing their channel from a PC
    STUDIO_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]

if not os.path.exists(SystemConfig.DOWNLOAD_PATH):
    os.makedirs(SystemConfig.DOWNLOAD_PATH)

# ==============================================================================
#  SECTION 4: CACHE & EXECUTION
# ==============================================================================

_meta_cache: Dict[str, Tuple[float, Dict]] = {}
_meta_lock = asyncio.Lock()

async def _clean_cache():
    async with _meta_lock:
        if len(_meta_cache) > YOUTUBE_META_MAX:
            keys = list(_meta_cache.keys())[:int(YOUTUBE_META_MAX * 0.3)]
            for k in keys: del _meta_cache[k]

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
#  SECTION 5: STUDIO ENGINE (THE VIP ACCESS)
# ==============================================================================

class YouTubeAPI:
    def __init__(self) -> None:
        self.base_url = "https://www.youtube.com/watch?v="
        self.playlist_url = "https://youtube.com/playlist?list="
        self._url_regex = re.compile(r"(?:youtube\.com|youtu\.be)")
        self._id_regex = re.compile(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*")
        
        self.pool = ThreadPoolExecutor(max_workers=SystemConfig.MAX_WORKERS)
        self.has_aria2 = shutil.which("aria2c") is not None
        
        self.proxy_status = get_formatted_proxy() is not None
        if self.has_aria2:
            LOGGER("Core").info(f"Studio Engine: CREATOR MODE 🟢 | Proxy: {'ACTIVE 🛡️' if self.proxy_status else 'OFF ⚠️'}")

    def _sanitize_link(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        if isinstance(videoid, str) and videoid.strip(): link = self.base_url + videoid.strip()
        link = link.strip()
        if "youtu.be" in link: link = self.base_url + link.split("/")[-1].split("?")[0]
        return link.split("&")[0]

    # --- URL & CHECK ---
    async def exists(self, link: str, videoid: Union[str, bool, None] = None) -> bool: return True 
    async def url(self, message: Message) -> Optional[str]:
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
                if time.time() - ts < YOUTUBE_META_TTL: return val['details'], val['vidid']

        try:
            search = VideosSearch(prepared_link, limit=1)
            res = await search.next()
            if not res or not res.get("result"): raise ValueError("No results")
            info = res["result"][0]
            thumb = (info.get("thumbnails", [{}])[-1].get("url", "")).split("?")[0]
            details = {
                "title": info.get("title", "Unknown"), "link": info.get("link", prepared_link),
                "vidid": info.get("id", ""), "duration_min": info.get("duration", "0:00"),
                "thumb": thumb, "channel": info.get("channel", {}).get("name", "Unknown")
            }
            vid_id = info.get("id", "")
            async with _meta_lock:
                _meta_cache[prepared_link] = (time.time(), {'details': details, 'vidid': vid_id})
            if len(_meta_cache) % 100 == 0: asyncio.create_task(_clean_cache())
            return details, vid_id
        except: return {"title": "Error", "link": prepared_link, "vidid": "error", "duration_min": "0:00", "thumb": ""}, "error"

    async def details(self, link: str, videoid: Union[str, bool, None] = None):
        d, i = await self.track(link, videoid)
        return d["title"], d["duration_min"], time_to_seconds(d["duration_min"]), d["thumb"], i
    async def title(self, link: str, videoid: Union[str, bool, None] = None):
        d, _ = await self.track(link, videoid)
        return d.get("title", "")
    async def duration(self, link: str, videoid: Union[str, bool, None] = None):
        d, _ = await self.track(link, videoid)
        return d.get("duration_min")
    async def thumbnail(self, link: str, videoid: Union[str, bool, None] = None):
        d, _ = await self.track(link, videoid)
        return d.get("thumb", "")

    # ==========================================================================
    #  DOWNLOADER (IDENTITY: STUDIO CREATOR)
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

        for ext in ['m4a', 'webm', 'mp4', 'opus', 'mp3', 'mkv']:
            final_path = os.path.join(SystemConfig.DOWNLOAD_PATH, f"{vid_id}.{ext}")
            if os.path.exists(final_path): return final_path, True

        # === THE GOD MODE CONFIGURATION ===
        opts = {
            "outtmpl": os.path.join(SystemConfig.DOWNLOAD_PATH, f"{vid_id}.%(ext)s"),
            "cookiefile": get_cookie_file(),
            "proxy": get_formatted_proxy(),
            
            # --- IDENTITY SPOOFING (STUDIO) ---
            "extractor_args": {
                "youtube": {
                    # THIS IS THE MAGIC: Android Creator + Web Creator
                    "player_client": ["android_creator", "web_creator"],
                    "skip": ["dash", "hls"]
                }
            },
            "http_headers": {
                "User-Agent": random.choice(SystemConfig.STUDIO_AGENTS),
                # Pretend we are coming from the Studio Dashboard
                "Referer": "https://studio.youtube.com/",
                "Origin": "https://studio.youtube.com",
            },
            
            "geo_bypass": True, "nocheckcertificate": True,
            "quiet": True, "no_warnings": True, "ignoreerrors": True,
            "force_ipv4": True, "socket_timeout": 30, "retries": 15,
            "prefer_ffmpeg": False,
        }

        if self.has_aria2:
            opts["external_downloader"] = "aria2c"
            opts["external_downloader_args"] = SystemConfig.ARIA2_ARGS

        if video:
            opts["format"] = "bestvideo+bestaudio/best"
            opts["merge_output_format"] = "mp4"
        else:
            opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"

        def _execute_dl():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([link])
            except Exception:
                # Emergency Fallback: If Proxy/Studio fails, try raw
                if opts.get("proxy"):
                    opts["proxy"] = None
                    try:
                        with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([link])
                    except: pass
            
            for f in os.listdir(SystemConfig.DOWNLOAD_PATH):
                if f.startswith(vid_id): return os.path.join(SystemConfig.DOWNLOAD_PATH, f)
            return None

        downloaded_file = await loop.run_in_executor(self.pool, _execute_dl)
        if downloaded_file: return downloaded_file, True
        return None, None

    # --- UTILS ---
    async def video_stream_url(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[int, str]:
        link = self._sanitize_link(link, videoid)
        args = ["yt-dlp", "--user-agent", SystemConfig.STUDIO_AGENTS[0], "-g", "-f", "best[height<=?1080]"]
        
        # Spoof Referer in headers for Stream too
        args.extend(["--add-header", "Referer:https://studio.youtube.com/"])
        
        cookie = get_cookie_file()
        if cookie: args.extend(["--cookies", cookie])
        proxy = get_formatted_proxy()
        if proxy: args.extend(["--proxy", proxy])
        args.append(link)
        
        stdout, stderr = await _exec_shell(*args)
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

        args = ["yt-dlp", "-i", "--get-id", "--flat-playlist", "--playlist-end", str(limit), "--skip-download", "--no-warnings"]
        args.extend(["--add-header", "Referer:https://studio.youtube.com/"])
        if get_cookie_file(): args.extend(["--cookies", get_cookie_file()])
        if get_formatted_proxy(): args.extend(["--proxy", get_formatted_proxy()])
        args.append(link)

        stdout, _ = await _exec_shell(*args)
        items = stdout.decode().strip().split("\n") if stdout else []
        return [i for i in items if i]

    async def formats(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[List[Dict], str]:
        link = self._sanitize_link(link, videoid)
        opts = {"quiet": True, "cookiefile": get_cookie_file(), "proxy": get_formatted_proxy()}
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
