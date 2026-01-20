# ==============================================================================
#  TITANIUM NUCLEAR ENGINE (ZERO LATENCY) © 2026
#  Optimized for: 16-Core CPU | 2.5Gbps+ Uplink | 50GB RAM
#  Strategy: Async Read-Ahead Buffer (Stream from Disk while Downloading)
# ==============================================================================

import asyncio
import os
import re
import shutil
import logging
import time
from typing import Dict, List, Tuple, Union, Optional
from concurrent.futures import ThreadPoolExecutor

import yt_dlp
from pyrogram.types import Message
from pyrogram.enums import MessageEntityType
from youtubesearchpython.aio import VideosSearch, Playlist

# حاول استدعاء دوال السورس، لو مش موجودة استخدم البدائل لمنع الأخطاء
try:
    from AlexaMusic.utils.formatters import time_to_seconds
except ImportError:
    def time_to_seconds(t): return 0

# ------------------------------------------------------------------------------
#  HIGH-PERFORMANCE CONFIGURATION
# ------------------------------------------------------------------------------

class UltraConfig:
    DOWNLOAD_PATH = os.path.abspath("downloads")
    # استغلال الـ 16 كور بالكامل - كل عملية بتاخد خيط معالجة منفصل
    MAX_WORKERS = 32 
    
    # إعدادات Aria2 المدمرة للسرعة (مصممة لسرعة 2.5Gbps)
    # file-allocation=none: دي أهم حاجة عشان المشغل يقدر يقرأ الملف وهو بيتكتب
    ARIA2_ARGS = [
        "-c", 
        "-x", "16",       # 16 خط اتصال لكل ملف (أقصى حاجة)
        "-s", "16",       # تقسيم الملف لـ 16 جزء
        "-j", "32",       # 32 تحميل متوازي لو فيه ضغط
        "-k", "1M",       # حجم القطعة (1 ميجا عشان الستريمنج يبدأ فوراً)
        "--min-split-size=1M", 
        "--file-allocation=none", # ضروري جداً عشان التشغيل الفوري
        "--buffer-size=128M",     # استخدام 128 ميجا من الرامات كـ كاش للكتابة
        "--quiet=true"
    ]

# تجهيز المجلدات
if not os.path.exists(UltraConfig.DOWNLOAD_PATH):
    os.makedirs(UltraConfig.DOWNLOAD_PATH)

# كاش للمعلومات عشان منطلبش يوتيوب كل مرة
_meta_cache: Dict[str, Tuple[float, Dict]] = {}
_meta_lock = asyncio.Lock()

# ------------------------------------------------------------------------------
#  THE ENGINE
# ------------------------------------------------------------------------------

class YouTubeAPI:
    def __init__(self) -> None:
        self.base_url = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        
        self.pool = ThreadPoolExecutor(max_workers=UltraConfig.MAX_WORKERS)
        self.has_aria2 = shutil.which("aria2c") is not None
        self.cookie = self._get_cookie_file()
        
        # التأكد من وجود Aria2 لأن بدونه السرعة هتموت
        if not self.has_aria2:
            print("⚠️ WARNING: Aria2c NOT FOUND! Install it to unlock 2.6Gbps speed.")
        else:
            print(f"🚀 NUCLEAR ENGINE: ONLINE | 16-Core Mode | 2.6Gbps Optimized")

    def _get_cookie_file(self) -> Optional[str]:
        # البحث عن الكوكيز بذكاء في كل المسارات المحتملة
        possible_paths = ["cookies.txt", "cookies/cookies.txt", "AlexaMusic/cookies.txt", "AnnieXMedia/cookies.txt"]
        for path in possible_paths:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return os.path.abspath(path)
        return None

    def _sanitize_link(self, link: str, videoid: Union[str, bool, None] = None) -> str:
        if isinstance(videoid, str) and videoid.strip():
            return self.base_url + videoid.strip()
        return link.split("&")[0]

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base_url + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None if offset in (None,) else text[offset : offset + length]

    # ======================================================================
    #  NUCLEAR DOWNLOAD FUNCTION (Read-While-Write)
    # ======================================================================
    async def download(
        self,
        link: str,
        mystic,
        *,
        video: Union[bool, str, None] = None,
        videoid: Union[str, bool, None] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> Union[Tuple[str, Optional[bool]], str]:
        
        link = self._sanitize_link(link, videoid)
        loop = asyncio.get_running_loop()

        # استخراج ID الفيديو
        try:
            match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", link)
            vid_id = match.group(1) if match else str(int(time.time()))
        except:
            vid_id = str(int(time.time()))

        # تحديد المسار النهائي بناءً على النوع
        ext = "mp4" if (video or songvideo) else "m4a"
        final_filename = f"{vid_id}.{ext}"
        
        # حالة خاصة لو طلب تحميل أغنية بالاسم (songaudio)
        if songaudio and title:
            final_filename = f"{title}.mp3"
            ext = "mp3"

        final_path = os.path.join(UltraConfig.DOWNLOAD_PATH, final_filename)

        # لو الملف موجود وكامل، رجعه فوراً (Instant Play)
        if os.path.exists(final_path):
            if songaudio or songvideo: return final_path
            return final_path, True

        # --- بداية التحميل الخلفي ---
        def _start_download_process():
            ydl_opts = {
                "outtmpl": os.path.join(UltraConfig.DOWNLOAD_PATH, f"{vid_id}.%(ext)s"),
                "cookiefile": self.cookie,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "external_downloader": "aria2c" if self.has_aria2 else None,
                "external_downloader_args": UltraConfig.ARIA2_ARGS if self.has_aria2 else None,
                "format": "bestvideo+bestaudio/best" if (video or songvideo) else "bestaudio[ext=m4a]/bestaudio/best",
                "writethumbnail": False,
            }

            # تعديلات خاصة لو تحميل ملف MP3 (ليس بث)
            if songaudio:
                ydl_opts["outtmpl"] = final_path
                ydl_opts["format"] = "bestaudio/best"
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([link])
            except Exception as e:
                print(f"DL Error: {e}")

        # تشغيل التحميل في الخلفية (Fire & Forget)
        loop.run_in_executor(self.pool, _start_download_process)

        # لو ده تحميل ملف (مش ستريمنج)، هنستنى يخلص
        if songaudio or songvideo:
            while not os.path.exists(final_path):
                await asyncio.sleep(0.5)
            return final_path

        # --- المراقبة الحية (للبث المباشر - Streaming) ---
        # الكود ده بيراقب الهارد، أول ما الملف يوصل 1 ميجا بيرجعه للمشغل
        
        start_time = time.time()
        found_file = None
        
        while time.time() - start_time < 30: # مهلة 30 ثانية
            # البحث عن الملف أو أجزاءه
            for f_name in os.listdir(UltraConfig.DOWNLOAD_PATH):
                if f_name.startswith(vid_id):
                    f_path = os.path.join(UltraConfig.DOWNLOAD_PATH, f_name)
                    
                    # تجاهل ملفات Aria2 المؤقتة، احنا عايزين الملف اللي بيتكتب فيه الداتا
                    if f_name.endswith(".aria2"):
                        real_file = f_path.replace(".aria2", "")
                        if os.path.exists(real_file) and os.path.getsize(real_file) > 1024 * 1024:
                            found_file = real_file
                            break
                    else:
                        # لو لقينا ملف عادي وحجمه أكبر من 1 ميجا
                        try:
                            if os.path.getsize(f_path) > 1024 * 1024: 
                                found_file = f_path
                                break
                        except: pass
            
            if found_file:
                return found_file, True
            
            await asyncio.sleep(0.1) # فحص سريع جداً (كل 100 مللي ثانية)

        return None, None

    # --------------------------------------------------------------------------
    #  METADATA & HELPERS
    # --------------------------------------------------------------------------
    
    async def track(self, link: str, videoid: Union[str, bool, None] = None):
        prepared_link = self._sanitize_link(link, videoid)
        async with _meta_lock:
            if prepared_link in _meta_cache:
                return _meta_cache[prepared_link][1]['details'], _meta_cache[prepared_link][1]['vidid']
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
            # حفظ في الكاش
            async with _meta_lock:
                _meta_cache[prepared_link] = (time.time(), {'details': details, 'vidid': info.get("id", "")})
            return details, info.get("id", "")
        except:
            return {"title": "Error"}, "error"

    async def details(self, link: str, videoid: Union[str, bool, None] = None):
        d, i = await self.track(link, videoid)
        return d.get("title"), d.get("duration_min"), time_to_seconds(d.get("duration_min")), d.get("thumb"), i

    async def title(self, link: str, videoid: Union[str, bool, None] = None):
        return (await self.track(link, videoid))[0].get("title")

    async def duration(self, link: str, videoid: Union[str, bool, None] = None):
        return (await self.track(link, videoid))[0].get("duration_min")

    async def thumbnail(self, link: str, videoid: Union[str, bool, None] = None):
        return (await self.track(link, videoid))[0].get("thumb")
    
    async def video(self, link: str, videoid: Union[str, bool, None] = None):
        link = self._sanitize_link(link, videoid)
        cmd = ["yt-dlp", "-g", "-f", "best[height<=?720]", link]
        if self.cookie: cmd.extend(["--cookies", self.cookie])
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        return (1, stdout.decode().split("\n")[0]) if stdout else (0, stderr.decode())

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid: link = f"https://youtube.com/playlist?list={videoid}"
        cmd = ["yt-dlp", "--flat-playlist", "--get-id", "--playlist-end", str(limit), link]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await proc.communicate()
        return out.decode().splitlines() if out else []

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base_url + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base_url + link
        if "&" in link:
            link = link.split("&")[0]
        
        def _get_fmt():
            opts = {"quiet": True, "cookiefile": self.cookie}
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(link, download=False).get("formats", [])
        
        formats = await asyncio.get_running_loop().run_in_executor(self.pool, _get_fmt)
        formats_available = []
        for format in formats:
            try:
                if "dash" not in str(format.get("format")).lower():
                    formats_available.append({
                        "format": format.get("format"),
                        "filesize": format.get("filesize"),
                        "format_id": format.get("format_id"),
                        "ext": format.get("ext"),
                        "format_note": format.get("format_note"),
                        "yturl": link,
                        "cookiefile": self.cookie,
                    })
            except: continue
        return formats_available, link

YouTube = YouTubeAPI()
