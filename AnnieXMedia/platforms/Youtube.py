# Authored By Certified Coders © 2025
# Integrated with TitanOS Hyper-Sonic Engine (Aria2 + Smart Spoofing)

import asyncio
import contextlib
import json
import os
import re
import shutil
import time
import random
from typing import Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.aio import VideosSearch, Playlist

# --- AnnieX Imports (Do Not Remove) ---
from AnnieXMedia.utils.cookie_handler import COOKIE_PATH
from AnnieXMedia.utils.database import is_on_off
from AnnieXMedia.utils.errors import capture_internal_err
from AnnieXMedia.utils.formatters import time_to_seconds
from AnnieXMedia.utils.tuning import YTDLP_TIMEOUT, YOUTUBE_META_MAX, YOUTUBE_META_TTL


# === Caches ===
_cache: Dict[str, Tuple[float, List[Dict]]] = {}
_cache_lock = asyncio.Lock()
_formats_cache: Dict[str, Tuple[float, List[Dict], str]] = {}
_formats_lock = asyncio.Lock()


# === Constants ===
YOUTUBE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")

# === HYPER CONFIGURATION ===
class UltraConfig:
    DOWNLOAD_PATH = os.path.abspath("downloads")
    
    # 16 Cores * 4 Threads = 64 Workers (Maximum Performance)
    MAX_WORKERS = 64
    
    # إعدادات Aria2 للسرعة الجنونية (2.6Gbps Optimized)
    ARIA2_ARGS = [
        "-c", 
        "-x", "16",           
        "-s", "16",           
        "-j", "64",           
        "-k", "2M",           
        "--min-split-size=1M", 
        "--file-allocation=none", 
        "--buffer-size=1024M", # 1GB RAM Buffer
        "--quiet=true",
        "--max-tries=3",
        "--connect-timeout=10"
    ]
    
    # التريكة السحرية لحل مشاكل التنسيق والحظر
    # بنقول لليوتيوب إننا "أندرويد" أو "iOS" عشان يفتح السرعة ويعدي الحظر
    EXTRACTOR_ARGS = {
        'youtube': {
            'skip': ['dash', 'hls'],
            'player_client': ['android', 'ios', 'web'], # الترتيب مهم
            'include_ssl_logs': [False] 
        }
    }

if not os.path.exists(UltraConfig.DOWNLOAD_PATH):
    os.makedirs(UltraConfig.DOWNLOAD_PATH)

# === Helpers ===
def _cookiefile_path() -> Optional[str]:
    # 1. Check AnnieX Path
    path = str(COOKIE_PATH)
    try:
        if path and os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    except Exception:
        pass
    
    # 2. Fallback Paths
    fallback_paths = ["cookies.txt", "cookies/cookies.txt"]
    for p in fallback_paths:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return os.path.abspath(p)
            
    return None

def _cookies_args() -> List[str]:
    path = _cookiefile_path()
    return ["--cookies", path] if path else []

async def _exec_proc(*args: str) -> Tuple[bytes, bytes]:
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

def get_user_agent():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    ]
    return random.choice(agents)


@capture_internal_err
async def cached_youtube_search(query: str) -> List[Dict]:
    key = f"q:{query}"
    now = time.time()

    async with _cache_lock:
        if key in _cache:
            ts, val = _cache[key]
            if now - ts < YOUTUBE_META_TTL:
                return val
            _cache.pop(key, None)
        if len(_cache) > YOUTUBE_META_MAX:
            _cache.clear()

    try:
        data = await VideosSearch(query, limit=1).next()
        result = data.get("result", [])
    except Exception:
        result = []

    if result:
        async with _cache_lock:
            _cache[key] = (now, result)

    return result


# === Main Class ===
class YouTubeAPI:
    def __init__(self) -> None:
        self.base_url = "https://www.youtube.com/watch?v="
        self.playlist_url = "https://youtube.com/playlist?list="
        self._url_pattern = re.compile(r"(?:youtube\.com|youtu\.be)")
        
        # Engine Core
        self.pool = ThreadPoolExecutor(max_workers=UltraConfig.MAX_WORKERS)
        self.has_aria2 = shutil.which("aria2c") is not None
        
        if self.has_aria2:
             print("🚀 TITANIUM ENGINE: ONLINE | Anti-Format-Error ACTIVE | 2.6Gbps Ready")

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
    @capture_internal_err
    async def exists(self, link: str, videoid: Union[str, bool, None] = None) -> bool:
        return bool(self._url_pattern.search(self._prepare_link(link, videoid)))

    @capture_internal_err
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
    @capture_internal_err
    async def _fetch_video_info(self, query: str, *, use_cache: bool = True) -> Optional[Dict]:
        q = self._prepare_link(query)
        if use_cache and not q.startswith("http"):
            res = await cached_youtube_search(q)
            return res[0] if res else None
        data = await VideosSearch(q, limit=1).next()
        result = data.get("result", [])
        return result[0] if result else None

    @capture_internal_err
    async def is_live(self, link: str) -> bool:
        prepared = self._prepare_link(link)
        stdout, _ = await _exec_proc("yt-dlp", *(_cookies_args()), "--dump-json", prepared)
        if not stdout:
            return False
        try:
            info = json.loads(stdout.decode())
            return bool(info.get("is_live"))
        except json.JSONDecodeError:
            return False

    @capture_internal_err
    async def details(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> Tuple[str, Optional[str], int, str, str]:
        prepared_link = self._prepare_link(link, videoid)

        try:
            info = await self._fetch_video_info(prepared_link)
            if not info:
                raise ValueError("No results")
        except Exception as search_err:
            raise ValueError("Video not found", {"cause": str(search_err)}) from search_err

        dt = info.get("duration")
        ds = int(time_to_seconds(dt)) if dt else 0
        thumb = (
            info.get("thumbnail")
            or info.get("thumbnails", [{}])[-1].get("url", "")
        ).split("?")[0]

        return info.get("title", ""), dt, ds, thumb, info.get("id", "")

    @capture_internal_err
    async def title(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        info = await self._fetch_video_info(self._prepare_link(link, videoid))
        return info.get("title", "") if info else ""

    @capture_internal_err
    async def duration(self, link: str, videoid: Union[str, bool, None] = None) -> Optional[str]:
        info = await self._fetch_video_info(self._prepare_link(link, videoid))
        return info.get("duration") if info else None

    @capture_internal_err
    async def thumbnail(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        info = await self._fetch_video_info(self._prepare_link(link, videoid))
        return (
            info.get("thumbnail")
            or info.get("thumbnails", [{}])[-1].get("url", "")
        ).split("?")[0] if info else ""

    @capture_internal_err
    async def track(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[Dict, str]:
        prepared_link = self._prepare_link(link, videoid)

        try:
            info = await self._fetch_video_info(prepared_link)
            if not info:
                raise ValueError(f"No results for: '{prepared_link}'")
        except Exception:
            # Fallback to yt-dlp metadata if search fails
            stdout, stderr = await _exec_proc(
                "yt-dlp", *(_cookies_args()), "--dump-json", "--no-warnings", prepared_link
            )
            if not stdout:
                raise ValueError("Both search and yt-dlp failed")
            info = json.loads(stdout.decode())

        thumb = (
            info.get("thumbnail")
            or info.get("thumbnails", [{}])[-1].get("url", "")
        ).split("?")[0]

        details = {
            "title": info.get("title", ""),
            "link": info.get("webpage_url", prepared_link),
            "vidid": info.get("id", ""),
            "duration_min": (info.get("duration") if isinstance(info.get("duration"), str) else None),
            "thumb": thumb,
        }
        return details, info.get("id", "")

    # === Media & Formats ===
    @capture_internal_err
    async def video(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[int, str]:
        link = self._prepare_link(link, videoid)
        stdout, stderr = await _exec_proc(
            "yt-dlp",
            *(_cookies_args()),
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]",
            link,
        )
        return (1, stdout.decode().split("\n")[0]) if stdout else (0, stderr.decode())

    # === TURBO PLAYLIST FETCHING (Hybrid) ===
    @capture_internal_err
    async def playlist(
        self, link: str, limit: int, user_id, videoid: Union[str, bool, None] = None
    ) -> List[str]:
        if videoid:
            link = self.playlist_url + str(videoid)
        link = self._prepare_link(link).split("&")[0]

        try:
            plist = await Playlist.get(link)
            items = [video.get("id") for video in plist.get("videos", [])[:limit] if video.get("id")]
            if items:
                return items
        except Exception:
            pass

        # Fast fetch via Shell Command
        def _get_pl():
            import subprocess
            cmd = [
                "yt-dlp",
                *(_cookies_args()),
                "-i",
                "--get-id",
                "--flat-playlist",
                "--playlist-end", str(limit),
                "--skip-download",
                "--compat-options", "no-youtube-unavailable-videos",
                link
            ]
            try:
                return subprocess.check_output(cmd).decode().strip().split("\n")
            except:
                return []

        items = await asyncio.get_running_loop().run_in_executor(self.pool, _get_pl)
        return [i for i in items if i]

    @capture_internal_err
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

        opts = {"quiet": True, "cookiefile": _cookiefile_path()}
        out: List[Dict] = []
        try:
            def _get_formats():
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(link, download=False)
            
            info = await asyncio.get_running_loop().run_in_executor(self.pool, _get_formats)
            
            for fmt in info.get("formats", []):
                if not any(k in fmt for k in ("filesize", "filesize_approx")): continue
                out.append({
                    "format": fmt.get("format"),
                    "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
                    "format_id": fmt.get("format_id"),
                    "ext": fmt.get("ext"),
                    "format_note": fmt.get("format_note"),
                    "yturl": link,
                })
        except Exception:
            pass

        async with _formats_lock:
            if len(_formats_cache) > YOUTUBE_META_MAX:
                _formats_cache.clear()
            _formats_cache[key] = (now, out, link)

        return out, link

    @capture_internal_err
    async def slider(
        self, link: str, query_type: int, videoid: Union[str, bool, None] = None
    ) -> Tuple[str, Optional[str], str, str]:
        data = await VideosSearch(self._prepare_link(link, videoid), limit=10).next()
        results = data.get("result", [])
        if not results or query_type >= len(results):
            raise IndexError("Query index out of range")
        r = results[query_type]
        return (
            r.get("title", ""),
            r.get("duration"),
            r.get("thumbnails", [{}])[-1].get("url", "").split("?")[0],
            r.get("id", ""),
        )

    # === TITAN DOWNLOADER (The Main Fix) ===
    @capture_internal_err
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

        # Handle Live Streams (Direct)
        if await self.is_live(link):
            status, stream_url = await self.video(link)
            if status == 1:
                return stream_url, None
            return None, None

        # Generate File Path
        try:
            match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", link)
            vid_id = match.group(1) if match else str(int(time.time()))
        except:
            vid_id = str(int(time.time()))

        ext = "mp4" if video else "m4a"
        final_path = os.path.join(UltraConfig.DOWNLOAD_PATH, f"{vid_id}.{ext}")

        # Instant Cache Hit
        if os.path.exists(final_path):
             return final_path, True

        # === THE CORE FIX ===
        def _execute_dl():
            # إعدادات خاصة لحل مشكلة التنسيقات
            opts = {
                "outtmpl": os.path.join(UltraConfig.DOWNLOAD_PATH, f"{vid_id}.%(ext)s"),
                "cookiefile": _cookiefile_path(),
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
                # Aria2 Integration
                "external_downloader": "aria2c" if self.has_aria2 else None,
                "external_downloader_args": UltraConfig.ARIA2_ARGS if self.has_aria2 else None,
                # Smart Format Selection (The Fix)
                # لو فيديو: هات أفضل جودة 720، لو مفيش هات أفضل فيديو بصوت، لو مفيش هات أفضل جودة وخلاص
                # لو صوت: هات أفضل صوت m4a، لو مفيش هات أفضل صوت، لو مفيش هات أفضل حاجة
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best" if video else "bestaudio[ext=m4a]/bestaudio/best",
                # Client Spoofing (Anti-Block)
                "extractor_args": UltraConfig.EXTRACTOR_ARGS,
                "user_agent": get_user_agent(),
                "writethumbnail": False
            }

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([link])
            except Exception as e:
                print(f"TitanDL Error: {e}")

        # Run Download in Background
        loop.run_in_executor(self.pool, _execute_dl)

        # Zero Latency Watcher
        start_time = time.time()
        found_file = None
        
        while time.time() - start_time < 40: # 40s Timeout
            for f_name in os.listdir(UltraConfig.DOWNLOAD_PATH):
                if f_name.startswith(vid_id):
                    f_path = os.path.join(UltraConfig.DOWNLOAD_PATH, f_name)
                    
                    if f_name.endswith(".aria2"):
                        real_file = f_path.replace(".aria2", "")
                        # 1MB Buffer is enough for your speed
                        if os.path.exists(real_file) and os.path.getsize(real_file) > 1024 * 1024: 
                            found_file = real_file
                            break
                    else:
                        try:
                            if os.path.getsize(f_path) > 1024 * 1024: 
                                found_file = f_path
                                break
                        except: pass
            
            if found_file:
                return found_file, True
            
            await asyncio.sleep(0.05) 

        return None, None
