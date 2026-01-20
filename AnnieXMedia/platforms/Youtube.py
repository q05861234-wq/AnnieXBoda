# ==============================================================================
#  TITANIUM ULTIMATE (FULL EXPANDED) © 2026
#  Features:
#  1. Aria2 High Speed (16x)
#  2. Authentication (Cookies + Proxy)
#  3. Smart Cache System
#  4. Zero Latency (Direct Stream / No Conversion)
#  5. Full Playlist Support (Private & Public)
#  6. Error Resilience (Auto Retry)
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
#  SECTION 1: SYSTEM CONFIGURATION & LOGGING
# ------------------------------------------------------------------------------

# ضبط مستوى السجلات عشان الكونسول يكون نضيف
logging.basicConfig(level=logging.ERROR)
logging.getLogger("yt_dlp").setLevel(logging.CRITICAL)

# محاولة استيراد دوال البوت، لو مش موجودة نستخدم البدائل
try:
    from AnnieXMedia.utils.formatters import time_to_seconds
    from AnnieXMedia import LOGGER as GLOBAL_LOGGER
    def LOGGER(name):
        return GLOBAL_LOGGER(name)
except ImportError:
    def time_to_seconds(t):
        return 0
    def LOGGER(name):
        return logging.getLogger(name)

class SystemConfig:
    DOWNLOAD_PATH = os.path.abspath("downloads")
    MAX_WORKERS = 12
    # إعدادات Aria2 للتحميل الصاروخي
    ARIA2_ARGS = [
        "-c",
        "-x", "16",
        "-s", "16",
        "-j", "32",
        "-k", "1M",
        "--min-split-size=1M",
        "--file-allocation=none",
        "--quiet=true"
    ]

# إنشاء مجلد التحميلات لو مش موجود
if not os.path.exists(SystemConfig.DOWNLOAD_PATH):
    os.makedirs(SystemConfig.DOWNLOAD_PATH)

# نظام الكاش لتخزين معلومات الفيديو وتوفير البحث
_meta_cache: Dict[str, Tuple[float, Dict]] = {}
_meta_lock = asyncio.Lock()
YOUTUBE_META_TTL = 3600  # مدة بقاء المعلومات في الذاكرة (ساعة)

# ------------------------------------------------------------------------------
#  SECTION 2: AUTHENTICATION (Cookies & Proxy)
# ------------------------------------------------------------------------------

def get_formatted_proxy() -> Optional[str]:
    """
    جلب بروكسي عشوائي من ملف proxies.txt لتجاوز حظر الـ IP
    """
    if not os.path.exists("proxies.txt"):
        return None
    try:
        with open("proxies.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines:
            return None
        raw = random.choice(lines)
        if "@" in raw:
            return raw
        parts = raw.split(':')
        if len(parts) == 4:
            return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    except Exception:
        pass
    return None

def get_cookie_file() -> Optional[str]:
    """
    البحث عن ملف الكوكيز لتفعيل ميزات الحساب (Premium/Age-Gate)
    """
    paths = ["cookies.txt", "AnnieXMedia/cookies.txt", "cookies/cookies.txt"]
    for path in paths:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return os.path.abspath(path)
    return None

# ------------------------------------------------------------------------------
#  SECTION 3: THE ENGINE (Main Class)
# ------------------------------------------------------------------------------

class YouTubeAPI:
    def __init__(self) -> None:
        self.base_url = "https://www.youtube.com/watch?v="
        self.pool = ThreadPoolExecutor(max_workers=SystemConfig.MAX_WORKERS)
        self.has_aria2 = shutil.which("aria2c") is not None
        self.cookie = get_cookie_file()
        self.proxy = get_formatted_proxy()
        
        # رسالة ترحيبية في اللوج
        LOGGER("Core").info(f"Titanium Engine: FULL LOADED | Aria2: {self.has_aria2} | Auth: {bool(self.cookie)}")

    def _sanitize_link(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        if isinstance(videoid, str) and videoid.strip():
            return self.base_url + videoid.strip()
        return link.split("&")[0]

    # ==========================================================================
    #  METHOD 1: DOWNLOADER (The Beast)
    # ==========================================================================
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

        # استخراج الـ ID لعمل اسم الملف
        try:
            match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", link)
            vid_id = match.group(1) if match else str(int(time.time()))
        except:
            vid_id = str(int(time.time()))

        # فحص الملفات الموجودة مسبقاً (Smart Check)
        for f in os.listdir(SystemConfig.DOWNLOAD_PATH):
            if f.startswith(vid_id):
                return os.path.join(SystemConfig.DOWNLOAD_PATH, f), True

        # إعدادات التحميل (موسعة وواضحة)
        opts = {
            "outtmpl": os.path.join(SystemConfig.DOWNLOAD_PATH, f"{vid_id}.%(ext)s"),
            "cookiefile": self.cookie,
            "proxy": self.proxy,
            
            # --- إعدادات عدم التحويل (السرعة القصوى) ---
            "prefer_ffmpeg": False,  # لا تستخدم FFMPEG للتحويل
            "keepvideo": True,       # احتفظ بالملف الأصلي
            
            # --- إعدادات الهوية ---
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "android_creator", "web"],
                    "skip": ["dash", "hls"]
                }
            },
            
            # --- إعدادات الشبكة والأمان ---
            "geo_bypass": True,
            "nocheckcertificate": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "force_ipv4": True,
            "socket_timeout": 30,
            "retries": 10,
        }

        # تفعيل Aria2 لو موجود
        if self.has_aria2:
            opts["external_downloader"] = "aria2c"
            opts["external_downloader_args"] = SystemConfig.ARIA2_ARGS

        # اختيار الجودة (صوت أو فيديو)
        if video:
            opts["format"] = "bestvideo+bestaudio/best"
            opts["merge_output_format"] = "mp4"
        else:
            # هنا بنقوله هات أحسن صوت (opus أو m4a) ومتحولش حاجة
            opts["format"] = "bestaudio/best"

        # دالة التنفيذ (مفكوكة لتجنب Syntax Error)
        def _execute_dl():
            # المحاولة الأولى: باستخدام البروكسي والكوكيز
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([link])
            except Exception as e:
                # لو فشل، والمشكلة ممكن تكون في البروكسي، نجرب من غيره
                if opts.get("proxy"):
                    opts["proxy"] = None
                    try:
                        with yt_dlp.YoutubeDL(opts) as ydl:
                            ydl.download([link])
                    except Exception:
                        pass
            
            # البحث عن الملف اللي نزل
            for f in os.listdir(SystemConfig.DOWNLOAD_PATH):
                if f.startswith(vid_id):
                    return os.path.join(SystemConfig.DOWNLOAD_PATH, f)
            return None

        # تشغيل الدالة في Thread منفصل عشان ميعطلش البوت
        downloaded_file = await loop.run_in_executor(self.pool, _execute_dl)
        
        if downloaded_file:
            return downloaded_file, True
        return None, None

    # ==========================================================================
    #  METHOD 2: METADATA & SEARCH (Cached)
    # ==========================================================================
    async def track(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[Dict, str]:
        prepared_link = self._sanitize_link(link, videoid)
        
        # 1. البحث في الكاش (الذاكرة العشوائية)
        async with _meta_lock:
            if prepared_link in _meta_cache:
                ts, val = _meta_cache[prepared_link]
                if time.time() - ts < YOUTUBE_META_TTL:
                    return val['details'], val['vidid']

        # 2. البحث الفعلي (Network Request)
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
            vid_id = info.get("id", "")
            
            # 3. الحفظ في الكاش للمرة الجاية
            async with _meta_lock:
                _meta_cache[prepared_link] = (time.time(), {'details': details, 'vidid': vid_id})
                
            return details, vid_id
        except Exception:
             return {"title": "Error", "link": prepared_link, "vidid": "error", "duration_min": "0:00", "thumb": ""}, "error"

    # ==========================================================================
    #  METHOD 3: PLAYLISTS (Private & Public)
    # ==========================================================================
    async def playlist(self, link: str, limit: int, user_id, videoid: Union[str, bool, None] = None) -> List[str]:
        if videoid:
            link = f"https://youtube.com/playlist?list={videoid}"
        
        # الطريقة الأولى: yt-dlp (الأقوى والأدق مع الكوكيز)
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--get-id",
            "--playlist-end", str(limit),
            "--ignore-errors",
            "--no-warnings",
            link
        ]
        
        # إضافة الكوكيز والبروكسي للأمر
        if self.cookie:
            cmd.extend(["--cookies", self.cookie])
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
            
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        ids = stdout.decode().splitlines()
        
        if ids:
            return ids

        # الطريقة الثانية: مكتبة Playlist (كخطة بديلة)
        try:
            plist = await Playlist.get(link)
            if plist and plist.get("videos"):
                 return [video["id"] for video in plist["videos"][:limit] if video.get("id")]
        except Exception:
            pass
        
        return []

    # ==========================================================================
    #  METHOD 4: FORMATS & UTILS
    # ==========================================================================
    async def formats(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[List[Dict], str]:
        link = self._sanitize_link(link, videoid)
        opts = {
            "quiet": True,
            "cookiefile": self.cookie,
            "proxy": self.proxy
        }
        
        def _get_formats():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(link, download=False).get("formats", [])
            except Exception:
                return []
                
        loop = asyncio.get_running_loop()
        raw_formats = await loop.run_in_executor(self.pool, _get_formats)
        
        out = []
        for fmt in raw_formats:
            # استبعاد الصيغ الوهمية (بدون حجم)
            if not fmt.get("filesize") and not fmt.get("filesize_approx"):
                continue
                
            out.append({
                "format": fmt.get("format"),
                "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
                "format_id": fmt.get("format_id"),
                "ext": fmt.get("ext"),
                "format_note": fmt.get("format_note", ""),
                "yturl": link
            })
        return out, link

    async def video(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[int, str]:
        # لجلب رابط البث المباشر (Direct URL)
        link = self._sanitize_link(link, videoid)
        cmd = ["yt-dlp", "-g", "-f", "best[height<=?720]", link]
        
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
        if self.cookie:
            cmd.extend(["--cookies", self.cookie])
            
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        return 0, stderr.decode()

    # دوال مساعدة لجلب البيانات بسرعة
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

    async def slider(self, link: str, query_type: int, videoid: Union[str, bool, None] = None) -> Tuple[str, Optional[str], str, str]:
        # البحث في يوتيوب (يستخدم للتنقل بين النتائج)
        link = self._sanitize_link(link, videoid)
        try:
            search = VideosSearch(link, limit=10)
            res = await search.next()
            results = res.get("result", [])
            
            if not results or query_type >= len(results):
                return "Error", "0:00", "", "error"
                
            info = results[query_type]
            return (
                info.get("title", "Unknown"),
                info.get("duration", "0:00"),
                (info.get("thumbnails", [{}])[-1].get("url", "")).split("?")[0],
                info.get("id", "")
            )
        except Exception:
            return "Error", "0:00", "", "error"

    async def url(self, message: Message) -> Optional[str]:
        # استخراج الرابط من الرسالة
        if message.text and "http" in message.text:
            match = re.search(r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+", message.text)
            return match.group(0) if match else None
        return None
        
    async def exists(self, link: str, videoid: Union[str, bool, None] = None) -> bool:
        return True

# إنشاء الكائن لاستخدامه في البوت
YouTube = YouTubeAPI()
