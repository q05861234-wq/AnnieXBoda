# ==============================================================================
#  TITANIUM ULTIMATE (MULTI-CLIENT ROTATION) © 2026
#  Clients: iPad -> Studio (Creator) -> Android -> TV
#  Strategy: Adaptive Formats + 2.6Gbps Aria2
# ==============================================================================

import asyncio
import os
import re
import random
import shutil
import logging
import time
from typing import Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor

import yt_dlp
from pyrogram.types import Message
from youtubesearchpython.aio import VideosSearch, Playlist

# ------------------------------------------------------------------------------
#  LOGGING & CONFIG
# ------------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logging.getLogger("yt_dlp").setLevel(logging.WARNING)

try:
    from AnnieXMedia.utils.formatters import time_to_seconds
    from AnnieXMedia import LOGGER as GLOBAL_LOGGER
    def LOGGER(name): return GLOBAL_LOGGER(name)
except ImportError:
    def time_to_seconds(t): return 0
    def LOGGER(name): return logging.getLogger(name)

class SystemConfig:
    DOWNLOAD_PATH = os.path.abspath("downloads")
    MAX_WORKERS = 16
    
    # إعدادات السرعة القصوى (Aria2)
    ARIA2_ARGS = [
        "-c", "-x", "16", "-s", "16", "-j", "64", "-k", "10M",
        "--min-split-size=10M", "--file-allocation=none", 
        "--buffer-size=64M", "--quiet=true"
    ]

if not os.path.exists(SystemConfig.DOWNLOAD_PATH):
    os.makedirs(SystemConfig.DOWNLOAD_PATH)

_meta_cache: Dict[str, Tuple[float, Dict]] = {}
_meta_lock = asyncio.Lock()
YOUTUBE_META_TTL = 3600

# ------------------------------------------------------------------------------
#  AUTH
# ------------------------------------------------------------------------------

def get_formatted_proxy() -> Optional[str]:
    if not os.path.exists("proxies.txt"): return None
    try:
        with open("proxies.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines: return None
        raw = random.choice(lines)
        if "@" in raw: return raw
        parts = raw.split(':')
        if len(parts) == 4: return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    except: pass
    return None

def get_cookie_file() -> Optional[str]:
    paths = ["cookies.txt", "AnnieXMedia/cookies.txt", "cookies/cookies.txt"]
    for path in paths:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            LOGGER("Auth").info(f"🍪 Secured: {path}")
            return os.path.abspath(path)
    return None

# ------------------------------------------------------------------------------
#  THE ENGINE
# ------------------------------------------------------------------------------

class YouTubeAPI:
    def __init__(self) -> None:
        self.base_url = "https://www.youtube.com/watch?v="
        self.pool = ThreadPoolExecutor(max_workers=SystemConfig.MAX_WORKERS)
        self.has_aria2 = shutil.which("aria2c") is not None
        self.cookie = get_cookie_file()
        self.proxy = get_formatted_proxy()
        
        LOGGER("Core").info(f"🚀 TITANIUM ULTIMATE: ACTIVE | Multi-Client Rotation")

    def _sanitize_link(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        if isinstance(videoid, str) and videoid.strip():
            return self.base_url + videoid.strip()
        return link.split("&")[0]

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
            match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", link)
            vid_id = match.group(1) if match else str(int(time.time()))
        except:
            vid_id = str(int(time.time()))

        # Check Cache
        for f in os.listdir(SystemConfig.DOWNLOAD_PATH):
            if f.startswith(vid_id):
                return os.path.join(SystemConfig.DOWNLOAD_PATH, f), True

        # ======================================================================
        #  GLOBAL CONFIGURATION
        # ======================================================================
        base_opts = {
            "outtmpl": os.path.join(SystemConfig.DOWNLOAD_PATH, f"{vid_id}.%(ext)s"),
            "cookiefile": self.cookie,
            "proxy": self.proxy,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "quiet": True,
            "ignoreerrors": True,
            # Aria2 Speed
            "external_downloader": "aria2c" if self.has_aria2 else None,
            "external_downloader_args": SystemConfig.ARIA2_ARGS if self.has_aria2 else None,
        }

        # ======================================================================
        #  SMART FORMATS (No Hard-coding)
        # ======================================================================
        if video:
            base_opts["format"] = "bestvideo+bestaudio/best"
            base_opts["merge_output_format"] = "mp4"
        else:
            # الأولوية: M4A > MP3 > أي حاجة تانية
            base_opts["format"] = "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best"
            base_opts["postprocessors"] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        def _execute_dl():
            # --- المحاولة 1: iPad Pro (السرعة) ---
            try:
                LOGGER("Titanium").info("⚡ Trying Client: iPad Pro...")
                opts = base_opts.copy()
                opts["extractor_args"] = {"youtube": {"player_client": ["ios", "web"]}}
                opts["user_agent"] = "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
                
                with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([link])
                if self._check_file(vid_id): return self._check_file(vid_id)
            except Exception: pass

            # --- المحاولة 2: Android Creator (الاستوديو) ---
            try:
                LOGGER("Titanium").info("🛡️ Trying Client: Studio (Creator)...")
                opts = base_opts.copy()
                opts["extractor_args"] = {"youtube": {"player_client": ["android_creator"]}}
                opts["user_agent"] = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36"
                
                with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([link])
                if self._check_file(vid_id): return self._check_file(vid_id)
            except Exception: pass

            # --- المحاولة 3: Android Standard (القياسي) ---
            try:
                LOGGER("Titanium").info("📱 Trying Client: Android Standard...")
                opts = base_opts.copy()
                opts["extractor_args"] = {"youtube": {"player_client": ["android"]}}
                
                with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([link])
                if self._check_file(vid_id): return self._check_file(vid_id)
            except Exception: pass

            # --- المحاولة 4: TV (الحل الأخير) ---
            try:
                LOGGER("Titanium").info("📺 Trying Client: TV Mode...")
                opts = base_opts.copy()
                opts["extractor_args"] = {"youtube": {"player_client": ["tv"]}}
                
                with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([link])
                if self._check_file(vid_id): return self._check_file(vid_id)
            except Exception: pass

            return None

        downloaded_file = await loop.run_in_executor(self.pool, _execute_dl)
        if downloaded_file: return downloaded_file, True
        return None, None

    def _check_file(self, vid_id):
        for f in os.listdir(SystemConfig.DOWNLOAD_PATH):
            if f.startswith(vid_id): return os.path.join(SystemConfig.DOWNLOAD_PATH, f)
        return None

    # --------------------------------------------------------------------------
    #  METADATA & EXTRAS
    # --------------------------------------------------------------------------
    async def track(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[Dict, str]:
        prepared_link = self._sanitize_link(link, videoid)
        async with _meta_lock:
            if prepared_link in _meta_cache:
                ts, val = _meta_cache[prepared_link]
                if time.time() - ts < YOUTUBE_META_TTL: return val['details'], val['vidid']
        try:
            search = VideosSearch(prepared_link, limit=1)
            res = await search.next()
            info = res["result"][0]
            details = {
                "title": info.get("title", "Unknown"), "link": prepared_link, "vidid": info.get("id", ""),
                "duration_min": info.get("duration", "0:00"), "thumb": info.get("thumbnails", [{}])[-1].get("url", "").split("?")[0],
                "channel": info.get("channel", {}).get("name", "Unknown")
            }
            async with _meta_lock: _meta_cache[prepared_link] = (time.time(), {'details': details, 'vidid': info.get("id", "")})
            return details, info.get("id", "")
        except: return {"title": "Error", "link": prepared_link, "vidid": "error", "duration_min": "0:00", "thumb": ""}, "error"

    async def playlist(self, link: str, limit: int, user_id, videoid: Union[str, bool, None] = None) -> List[str]:
        if videoid: link = f"https://youtube.com/playlist?list={videoid}"
        cmd = ["yt-dlp", "--flat-playlist", "--get-id", "--playlist-end", str(limit), "--ignore-errors", "--no-warnings", 
               # iPad User Agent for Playlist
               "--user-agent", "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
               link]
        if self.cookie: cmd.extend(["--cookies", self.cookie])
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        if stdout: return stdout.decode().splitlines()
        try:
            plist = await Playlist.get(link)
            if plist and plist.get("videos"): return [video["id"] for video in plist["videos"][:limit] if video.get("id")]
        except: pass
        return []

    async def formats(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[List[Dict], str]:
        link = self._sanitize_link(link, videoid)
        opts = {"quiet": True, "cookiefile": self.cookie}
        def _get():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(link, download=False).get("formats", [])
            except:
                return []
        loop = asyncio.get_running_loop()
        raw_formats = await loop.run_in_executor(self.pool, _get)
        out = []
        for fmt in raw_formats:
            if not fmt.get("filesize") and not fmt.get("filesize_approx"): continue
            out.append({"format": fmt.get("format"), "filesize": fmt.get("filesize") or fmt.get("filesize_approx"), "format_id": fmt.get("format_id"), "ext": fmt.get("ext"), "format_note": fmt.get("format_note", ""), "yturl": link})
        return out, link

    async def video(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[int, str]:
        link = self._sanitize_link(link, videoid)
        cmd = ["yt-dlp", "-g", "-f", "best[height<=?720]", link]
        if self.cookie: cmd.extend(["--cookies", self.cookie])
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stdout: return 1, stdout.decode().split("\n")[0]
        return 0, stderr.decode()

    async def details(self, link: str, videoid: Union[str, bool, None] = None):
        d, i = await self.track(link, videoid)
        return d["title"], d["duration_min"], time_to_seconds(d["duration_min"]), d["thumb"], i
    async def title(self, link: str, videoid: Union[str, bool, None] = None): return (await self.track(link, videoid))[0].get("title")
    async def duration(self, link: str, videoid: Union[str, bool, None] = None): return (await self.track(link, videoid))[0].get("duration_min")
    async def thumbnail(self, link: str, videoid: Union[str, bool, None] = None): return (await self.track(link, videoid))[0].get("thumb")
    async def slider(self, link: str, query_type: int, videoid: Union[str, bool, None] = None) -> Tuple[str, Optional[str], str, str]:
        try:
            res = (await VideosSearch(self._sanitize_link(link, videoid), limit=10).next())["result"][query_type]
            return res["title"], res["duration"], res["thumbnails"][0]["url"], res["id"]
        except: return "Error", "0", "", "error"
    async def url(self, message: Message) -> Optional[str]:
        if message.text and "http" in message.text:
            match = re.search(r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+", message.text)
            return match.group(0) if match else None
        return None
    async def exists(self, link: str, videoid: Union[str, bool, None] = None) -> bool: return True

YouTube = YouTubeAPI()
