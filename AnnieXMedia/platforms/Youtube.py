# Authored By Certified Coders © 2025 (Hyper-Sonic Edition for 50GB/16Core)
import asyncio
import contextlib
import json
import os
import re
import shutil
import time
from typing import Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.aio import VideosSearch, Playlist

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

# === HYPER CONFIGURATION (Optimized for your Server) ===
class UltraConfig:
    DOWNLOAD_PATH = os.path.abspath("downloads")
    
    # 16 Cores * 4 Threads = 64 Workers (Maximum Efficiency)
    MAX_WORKERS = 64
    
    # إعدادات مخصصة لسرعة 2.6Gbps ورام 50GB
    ARIA2_ARGS = [
        "-c", 
        "-x", "16",           # Max connection per server
        "-s", "16",           # Split to 16 parts
        "-j", "64",           # Max concurrent downloads (Higher because you have CPU)
        "-k", "2M",           # Chunk size 2MB (Better for high speed)
        "--min-split-size=1M", 
        "--file-allocation=none", 
        "--buffer-size=1024M", # 1GB RAM Buffer (استغلال الرامات الجبارة لتقليل الضغط على الهارد)
        "--quiet=true",
        "--max-tries=3",      # Retry fast
        "--connect-timeout=10"
    ]
    
    # Anti-SABR (خداع يوتيوب)
    EXTRACTOR_ARGS = {
        'youtube': {
            'player_client': ['android', 'ios'],
            'player_skip': ['web', 'tv'],
            'include_ssl_logs': [False] 
        }
    }

if not os.path.exists(UltraConfig.DOWNLOAD_PATH):
    os.makedirs(UltraConfig.DOWNLOAD_PATH)

# === Helpers ===
def _cookiefile_path() -> Optional[str]:
    path = str(COOKIE_PATH)
    try:
        if path and os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    except Exception:
        pass
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
        
        # تشغيل المحرك بقوة 64 خيط معالجة
        self.pool = ThreadPoolExecutor(max_workers=UltraConfig.MAX_WORKERS)
        self.has_aria2 = shutil.which("aria2c") is not None
        
        if self.has_aria2:
             print("🚀 HYPER-SONIC ENGINE: ONLINE | 50GB RAM Optimized | 2.6Gbps Uplink")

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

    async def _ensure_watch_url(self, maybe_query_or_url: str) -> Optional[str]:
        prepared = self._prepare_link(maybe_query_or_url)
        if prepared.startswith("http"):
            return prepared
        data = await cached_youtube_search(prepared)
        if not data:
            return None
        vid = data[0].get("id")
        return self.base_url + vid if vid else None

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
                raise ValueError("No results from youtubesearchpython (VideosSearch)")
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
                raise ValueError(
                    f"No results from youtubesearchpython (VideosSearch) "
                    f"for query/URL: '{prepared_link}'"
                )
        except Exception as search_err:
            stdout, stderr = await _exec_proc(
                "yt-dlp", *(_cookies_args()), "--dump-json", "--no-warnings", prepared_link
            )

            def _both_failed(details: str) -> ValueError:
                return ValueError(
                    f"Both methods failed for '{prepared_link}':\n"
                    f"  1. youtubesearchpython error: {search_err}\n"
                    f"{details}"
                )

            if not stdout:
                stderr_msg = stderr.decode().strip() if stderr else "Empty response"
                raise _both_failed(f"  2. yt-dlp error: {stderr_msg}")

            try:
                info = json.loads(stdout.decode())
            except json.JSONDecodeError as json_err:
                raw = stdout.decode()[:400]
                raise _both_failed(
                    f"  2. yt-dlp JSON error: {json_err}\n"
                    f"     Raw: {raw}..."
                ) from json_err

        thumb = (
            info.get("thumbnail")
            or info.get("thumbnails", [{}])[-1].get("url", "")
        ).split("?")[0]

        details = {
            "title": info.get("title", ""),
            "link": info.get("webpage_url", prepared_link),
            "vidid": info.get("id", ""),
            "duration_min": (
                info.get("duration")
                if isinstance(info.get("duration"), str)
                else None
            ),
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

    # === TURBO PLAYLIST FETCHING ===
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

        # استخدام Threads في البحث كمان عشان السرعة
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
            return subprocess.check_output(cmd).decode().strip().split("\n")

        try:
            items = await asyncio.get_running_loop().run_in_executor(self.pool, _get_pl)
            return [i for i in items if i]
        except:
            return []

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

        opts = {"quiet": True}
        if cf := _cookiefile_path():
            opts["cookiefile"] = cf

        out: List[Dict] = []
        try:
            def _get_formats():
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(link, download=False)
            
            info = await asyncio.get_running_loop().run_in_executor(self.pool, _get_formats)
            
            for fmt in info.get("formats", []):
                if "dash" in str(fmt.get("format", "")).lower():
                    continue
                if not any(k in fmt for k in ("filesize", "filesize_approx")):
                    continue
                if not all(k in fmt for k in ("format", "format_id", "ext", "format_note")):
                    continue
                size = fmt.get("filesize") or fmt.get("filesize_approx")
                if not size:
                    continue
                out.append(
                    {
                        "format": fmt["format"],
                        "filesize": size,
                        "format_id": fmt["format_id"],
                        "ext": fmt["ext"],
                        "format_note": fmt["format_note"],
                        "yturl": link,
                    }
                )
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
            raise IndexError(
                f"Query type index {query_type} out of range (found {len(results)} results)"
            )
        r = results[query_type]
        return (
            r.get("title", ""),
            r.get("duration"),
            r.get("thumbnails", [{}])[-1].get("url", "").split("?")[0],
            r.get("id", ""),
        )

    # === HYPER DOWNLOAD (The Beast) ===
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

        # Live Stream Handling
        if await self.is_live(link):
            status, stream_url = await self.video(link)
            if status == 1:
                return stream_url, None
            return None, None

        # Generate ID
        try:
            match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", link)
            vid_id = match.group(1) if match else str(int(time.time()))
        except:
            vid_id = str(int(time.time()))

        ext = "mp4" if video else "m4a"
        final_path = os.path.join(UltraConfig.DOWNLOAD_PATH, f"{vid_id}.{ext}")

        # Check Cache
        if os.path.exists(final_path):
             return final_path, True

        # Background Downloader
        def _execute_dl():
            opts = {
                "outtmpl": os.path.join(UltraConfig.DOWNLOAD_PATH, f"{vid_id}.%(ext)s"),
                "cookiefile": _cookiefile_path(),
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "external_downloader": "aria2c" if self.has_aria2 else None,
                "external_downloader_args": UltraConfig.ARIA2_ARGS if self.has_aria2 else None,
                "format": "bestvideo+bestaudio/best" if video else "bestaudio[ext=m4a]/bestaudio/best",
                "extractor_args": UltraConfig.EXTRACTOR_ARGS,
                "writethumbnail": False
            }

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([link])
            except Exception as e:
                print(f"DL Error: {e}")

        # Start Download in Thread Pool
        loop.run_in_executor(self.pool, _execute_dl)

        # Streaming Watcher (Zero Latency)
        start_time = time.time()
        found_file = None
        
        # Reduced timeout logic because your internet is fast
        while time.time() - start_time < 30: 
            for f_name in os.listdir(UltraConfig.DOWNLOAD_PATH):
                if f_name.startswith(vid_id):
                    f_path = os.path.join(UltraConfig.DOWNLOAD_PATH, f_name)
                    
                    if f_name.endswith(".aria2"):
                        real_file = f_path.replace(".aria2", "")
                        # 1MB buffer is nothing for your speed, streaming starts instantly
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
            
            await asyncio.sleep(0.05) # Check every 50ms (Super Fast)

        return None, None
