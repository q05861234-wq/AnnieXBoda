# ==============================================================================
#  TITANIUM EDITION ENGINE © 2026
#  Identity: iPhone 17 Pro Max (iOS 18) + 5G Ultra Wideband Mode
#  Features: Force Aria2 16x | Universal Format Support | Zero Latency
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

logging.getLogger("yt_dlp").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.WARNING)

# ==============================================================================
#  SECTION 2: 5G+ CONFIGURATION & IPHONE 17 IDENTITY
# ==============================================================================

class SystemConfig:
    DOWNLOAD_PATH = os.path.abspath("downloads")
    MAX_WORKERS = (os.cpu_count() or 4) * 8  # Extreme threading
    
    # === 5G+ TURBO ARIA2 ARGS (Global Force) ===
    ARIA2_ARGS = [
        "-c", "-x", "16", "-s", "16", "-j", "32", "-k", "1M",
        "--buffer-size=1024M", "--file-allocation=none", "--quiet=true",
        "--max-connection-per-server=16", "--min-split-size=1M"
    ]
    
    # === THE FUTURE IDENTITY (iPhone 17 Pro Max / iOS 18) ===
    # This tricks YouTube into thinking it's a next-gen device on a premium network
    NEXT_GEN_AGENTS = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
    ]

if not os.path.exists(SystemConfig.DOWNLOAD_PATH):
    os.makedirs(SystemConfig.DOWNLOAD_PATH)

# ==============================================================================
#  SECTION 3: CACHE SYSTEM
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
            LOGGER("Core").info("Titanium Engine: iPhone 17 Pro Max Mode (5G+) Active 🚀")

    def _sanitize_link(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        if isinstance(videoid, str) and videoid.strip():
            link = self.base_url + videoid.strip()
        link = link.strip()
        if "youtu.be" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        elif "youtube.com/shorts/" in link or "youtube.com/live/" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        return link.split("&")[0]

    # --- URL ---
    async def exists(self, link: str, videoid: Union[str, bool, None] = None) -> bool:
        return bool(self._url_regex.search(self._sanitize_link(link, videoid)))

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
            if "http" in text:
                match = re.search(r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+", text)
                if match: return match.group(0)
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
            if not res or not res.get("result"):
                raise ValueError("No results")
            
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

    # --- DOWNLOADER (TITANIUM MODE) ---
    async def download(
        self, link: str, mystic, *, video: Union[bool, str, None] = None, videoid: Union[str, bool, None] = None,
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

        if os.path.exists(final_path): return final_path, True

        # === THE CONFIGURATION (Global 5G+ Injection) ===
        opts = {
            "outtmpl": final_path,
            "cookiefile": get_cookie_file(),
            "geo_bypass": True, "nocheckcertificate": True,
            "quiet": True, "no_warnings": True, "ignoreerrors": True,
            "force_ipv4": True,
            "user_agent": random.choice(SystemConfig.NEXT_GEN_AGENTS), # iPhone 17 Identity
            "socket_timeout": 30,
            "retries": 10,
            "prefer_ffmpeg": True,
            # iOS-Like Client Spoofing
            "extractor_args": {
                'youtube': {
                    'skip': ['dash', 'hls'], 
                    'player_client': ['ios', 'web'] # Spoof iOS Client specifically
                }
            },
        }

        # === FORCE 5G+ IN ALL CASES ===
        if self.has_aria2:
            opts["external_downloader"] = "aria2c"
            opts["external_downloader_args"] = SystemConfig.ARIA2_ARGS

        # === FORMAT LOGIC (No Fail) ===
        if video:
            opts["format"] = "bestvideo[height<=1080]+bestaudio/bestvideo[height<=720]+bestaudio/best"
            opts["merge_output_format"] = "mp4"
        else:
            # 1. Best M4A (Native for iOS)
            # 2. Any Audio -> Convert to M4A (High Speed)
            opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "192",
            }]

        def _execute_dl():
            with yt_dlp.YoutubeDL(opts) as ydl:
                try: ydl.download([link])
                except Exception as e: LOGGER("DL").error(f"DL Error: {e}")
            
            # Final Safety Check
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
