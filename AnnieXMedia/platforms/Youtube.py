# ==============================================================================
#  TITANIUM FUSION (2.6 Gbps + BYPASS) © 2026
#  Strategy: 
#    1. Attack with iPad Pro (Max Speed/M4A).
#    2. If blocked -> Switch to PC Chrome (Bypass).
#  Engine: Aria2 Optimized for Datacenter
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
#  LOGGING
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
    
    # --- إعدادات الوحش (2.6 Gbps) ---
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
    LOGGER("Auth").warning("⚠️ No Cookies")
    return None

# ------------------------------------------------------------------------------
#  TITANIUM FUSION ENGINE
# ------------------------------------------------------------------------------

class YouTubeAPI:
    def __init__(self) -> None:
        self.base_url = "https://www.youtube.com/watch?v="
        self.pool = ThreadPoolExecutor(max_workers=SystemConfig.MAX_WORKERS)
        self.has_aria2 = shutil.which("aria2c") is not None
        self.cookie = get_cookie_file()
        self.proxy = get_formatted_proxy()
        
        LOGGER("Core").info(f"🚀 TITANIUM FUSION: READY | Target: 2.6 Gbps")

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
        #  STRATEGY A: THE iPad Pro (MAX SPEED)
        #  الأولوية الأولى: السرعة القصوى باستخدام هوية ايباد
        # ======================================================================
        ipad_opts = {
            "outtmpl": os.path.join(SystemConfig.DOWNLOAD_PATH, f"{vid_id}.%(ext)s"),
            "cookiefile": self.cookie,
            "proxy": self.proxy,
            
            # هوية iPad Pro الحقيقية (عشان يوتيوب ميعملش مشاكل User-Agent)
            "user_agent": "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "web"], # خلط بين ios والويب
                    "skip": ["dash", "hls"]
                }
            },
            
            # إعدادات السرعة (Aria2)
            "external_downloader": "aria2c" if self.has_aria2 else None,
            "external_downloader_args": SystemConfig.ARIA2_ARGS if self.has_aria2 else None,
            
            "prefer_ffmpeg": False,
            "keepvideo": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "quiet": True,
            "ignoreerrors": True,
            "retries": 5,
        }

        # ======================================================================
        #  STRATEGY B: THE PC BYPASS (SAFE MODE)
        #  البديل الفوري: لو الايباد اترفض، ادخل بوضع الكمبيوتر فوراً
        # ======================================================================
        pc_opts = ipad_opts.copy()
        # نغير الهوية لـ Windows Chrome
        pc_opts["user_agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        pc_opts["extractor_args"] = {"youtube": {"player_client": ["web"]}}
        # خلي Aria2 شغال برضه في وضع الكمبيوتر عشان السرعة متقعش
        
        if video:
            ipad_opts["format"] = pc_opts["format"] = "bestvideo+bestaudio/best"
            ipad_opts["merge_output_format"] = pc_opts["merge_output_format"] = "mp4"
        else:
            ipad_opts["format"] = pc_opts["format"] = "bestaudio/best"

        def _execute_fusion():
            # 1. محاولة السرعة (iPad)
            try:
                LOGGER("Fusion").info("🚀 Mode: iPad Pro (High Speed)")
                with yt_dlp.YoutubeDL(ipad_opts) as ydl:
                    ydl.download([link])
                
                # لو نجح، رجع الملف
                if self._check_file(vid_id): return self._check_file(vid_id)
            except Exception as e:
                LOGGER("Fusion").warning(f"⚠️ Speed Mode Blocked: {e}")

            # 2. محاولة الأمان (PC Bypass)
            # لو الكود وصل هنا، معناه محاولة الايباد فشلت (Sign in error)
            # نحول فوراً لوضع الكمبيوتر
            try:
                LOGGER("Fusion").info("🛡️ Mode: PC Bypass (Fallback)")
                
                # لو المشكلة كانت بروكسي، شيله في المحاولة دي
                if pc_opts.get("proxy"): pc_opts["proxy"] = None

                with yt_dlp.YoutubeDL(pc_opts) as ydl:
                    ydl.download([link])
                
                if self._check_file(vid_id): return self._check_file(vid_id)
            except Exception as e:
                LOGGER("Fusion").error(f"❌ All Modes Failed: {e}")

            return None

        downloaded_file = await loop.run_in_executor(self.pool, _execute_fusion)
        
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
                "title": info.get("title", "Unknown"),
                "link": prepared_link,
                "vidid": info.get("id", ""),
                "duration_min": info.get("duration", "0:00"),
                "thumb": info.get("thumbnails", [{}])[-1].get("url", "").split("?")[0],
                "channel": info.get("channel", {}).get("name", "Unknown")
            }
            async with _meta_lock:
                _meta_cache[prepared_link] = (time.time(), {'details': details, 'vidid': info.get("id", "")})
            return details, info.get("id", "")
        except: return {"title": "Error", "link": prepared_link, "vidid": "error", "duration_min": "0:00", "thumb": ""}, "error"

    async def playlist(self, link: str, limit: int, user_id, videoid: Union[str, bool, None] = None) -> List[str]:
        if videoid: link = f"https://youtube.com/playlist?list={videoid}"
        cmd = [
            "yt-dlp", "--flat-playlist", "--get-id", 
            "--playlist-end", str(limit), "--ignore-errors", 
            "--no-warnings", 
            # iPad User Agent for Playlist too
            "--user-agent", "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            link
        ]
        if self.cookie: cmd.extend(["--cookies", self.cookie])
        if self.proxy: cmd.extend(["--proxy", self.proxy])
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        ids = stdout.decode().splitlines()
        if ids: return ids
        try:
            plist = await Playlist.get(link)
            if plist and plist.get("videos"): return [video["id"] for video in plist["videos"][:limit] if video.get("id")]
        except: pass
        return []

    async def formats(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[List[Dict], str]:
        link = self._sanitize_link(link, videoid)
        opts = {"quiet": True, "cookiefile": self.cookie, "proxy": self.proxy}
        def _get():
            try: with yt_dlp.YoutubeDL(opts) as ydl: return ydl.extract_info(link, download=False).get("formats", [])
            except: return []
        loop = asyncio.get_running_loop()
        raw_formats = await loop.run_in_executor(self.pool, _get)
        out = []
        for fmt in raw_formats:
            if not fmt.get("filesize") and not fmt.get("filesize_approx"): continue
            out.append({
                "format": fmt.get("format"), "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
                "format_id": fmt.get("format_id"), "ext": fmt.get("ext"), "format_note": fmt.get("format_note", ""), "yturl": link
            })
        return out, link

    async def video(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[int, str]:
        link = self._sanitize_link(link, videoid)
        cmd = ["yt-dlp", "-g", "-f", "best[height<=?720]", link]
        if self.proxy: cmd.extend(["--proxy", self.proxy])
        if self.cookie: cmd.extend(["--cookies", self.cookie])
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stdout: return 1, stdout.decode().split("\n")[0]
        return 0, stderr.decode()

    # Wrappers
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
