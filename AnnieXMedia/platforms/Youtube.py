# Copyright (C) 2026 by Alexa_Help & AnnieXMedia @ Github
# Optimized for High-End Servers (16-Core / 50GB RAM / 2.5Gbps Uplink)
# Nuclear Engine Strategy: Read-While-Write Buffer

import asyncio
import os
import re
import json
import shutil
import time
import logging
from typing import Union, Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

from yt_dlp import YoutubeDL
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch
from youtubesearchpython import Playlist

import config
from AlexaMusic.utils.database import is_on_off
from AlexaMusic.utils.formatters import time_to_seconds

# ==============================================================================
#  SERVER CONFIGURATION (NUCLEAR MODE)
# ==============================================================================

class SystemConfig:
    DOWNLOAD_PATH = os.path.abspath("downloads")
    # استغلال كامل لقوة المعالج 16 كور
    MAX_WORKERS = 32 
    
    # إعدادات Aria2c المخصصة للسرعات الفائقة (2.5Gbps+)
    ARIA2_ARGS = [
        "-c", 
        "-x", "16",       # 16 خط اتصال لكل ملف
        "-s", "16",       # تقسيم السيرفرات
        "-j", "64",       # 64 تحميل متوازي
        "-k", "1M",       # حجم القطعة لسرعة التجميع
        "--min-split-size=1M", 
        "--file-allocation=none", # ضروري جداً للتشغيل الفوري
        "--buffer-size=128M",     # استخدام الرامات كـ كاش
        "--quiet=true"
    ]

# إنشاء مجلد التحميلات لو مش موجود
if not os.path.exists(SystemConfig.DOWNLOAD_PATH):
    os.makedirs(SystemConfig.DOWNLOAD_PATH)

# ==============================================================================
#  HELPER FUNCTIONS
# ==============================================================================

def cookiefile():
    """البحث الذكي عن ملف الكوكيز لضمان عدم الحظر"""
    possible_paths = ["cookies", "cookies.txt", "AnnieXMedia/cookies.txt"]
    
    # البحث داخل مجلد cookies
    if os.path.exists("cookies") and os.path.isdir("cookies"):
        cookies_files = [f for f in os.listdir("cookies") if f.endswith(".txt")]
        if cookies_files:
            return os.path.join("cookies", cookies_files[0])
            
    # البحث عن ملفات فردية
    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(path):
            return path
            
    return None

async def shell_cmd(cmd):
    """تنفيذ أوامر الشل الخارجية للأوامر المعقدة"""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")

# ==============================================================================
#  CORE ENGINE (YOUTUBE API)
# ==============================================================================

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        
        # إعداد الـ ThreadPool للمعالج 16 كور
        self.pool = ThreadPoolExecutor(max_workers=SystemConfig.MAX_WORKERS)
        self.has_aria2 = shutil.which("aria2c") is not None
        
        if self.has_aria2:
            print("✅ Nuclear Engine: Aria2c Detected & Linked to 16-Cores.")
        else:
            print("⚠️ Warning: Aria2c not found. Speed will be limited.")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
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

    # --------------------------------------------------------------------------
    #  METADATA FETCHERS (Optimized)
    # --------------------------------------------------------------------------

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            if str(duration_min) == "None":
                duration_sec = 0
            else:
                duration_sec = int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
        return title

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            duration = result["duration"]
        return duration

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return thumbnail

    # --------------------------------------------------------------------------
    #  ADVANCED FETCHERS
    # --------------------------------------------------------------------------

    async def video(self, link: str, videoid: Union[bool, str] = None):
        """جلب رابط مباشر (Direct Link) للبث السريع جداً"""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        # استخدام yt-dlp لاستخراج الرابط المباشر
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--cookies", cookiefile() if cookiefile() else "",
            "-g",
            "-f", "best[height<=?720][width<=?1280]",
            f"{link}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return (1, stdout.decode().split("\n")[0]) if stdout else (0, stderr.decode())

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        
        # استخدام Shell command للأداء الأفضل مع قوائم التشغيل الضخمة
        cmd = (
            f"yt-dlp -i --compat-options no-youtube-unavailable-videos "
            f"--get-id --flat-playlist --playlist-end {limit} --skip-download '{link}' "
            f"2>/dev/null"
        )
        playlist = await shell_cmd(cmd)
        try:
            result = [key for key in playlist.split("\n") if key]
        except Exception:
            result = []
        return result

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
            "cookiefile": cookiefile(),
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ytdl_opts = {"quiet": True, "cookiefile": cookiefile()}
        ydl = YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    str(format["format"])
                except Exception:
                    continue
                if "dash" not in str(format["format"]).lower():
                    try:
                        format["format"]
                        format["filesize"]
                        format["format_id"]
                        format["ext"]
                        format["format_note"]
                    except Exception:
                        continue
                    formats_available.append(
                        {
                            "format": format["format"],
                            "filesize": format["filesize"],
                            "format_id": format["format_id"],
                            "ext": format["ext"],
                            "format_note": format["format_note"],
                            "yturl": link,
                            "cookiefile": cookiefile(),
                        }
                    )
        return formats_available, link

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    # ==========================================================================
    #  NUCLEAR DOWNLOAD LOGIC (READ-WHILE-WRITE)
    # ==========================================================================
    
    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        
        if videoid:
            link = self.base + link
        loop = asyncio.get_running_loop()

        # استخراج الـ ID لضبط المسار
        try:
            match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", link)
            vid_id = match.group(1) if match else str(int(time.time()))
        except:
            vid_id = str(int(time.time()))

        # تكوين المسار المتوقع للملف
        # ملاحظة: yt-dlp ممكن يضيف الامتداد تلقائياً، هنستخدم wildcard للبحث
        
        def get_download_options(is_video=False, specific_format=None):
            """تكوين إعدادات التحميل بناءً على نوع الطلب"""
            opts = {
                "cookiefile": cookiefile(),
                "outtmpl": f"downloads/{vid_id}.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                # تفعيل المحرك النووي (Aria2)
                "external_downloader": "aria2c" if self.has_aria2 else None,
                "external_downloader_args": SystemConfig.ARIA2_ARGS if self.has_aria2 else None,
            }
            
            if specific_format:
                 opts["format"] = specific_format
            elif is_video:
                 opts["format"] = "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]"
            else:
                 opts["format"] = "bestaudio[ext=m4a]/bestaudio/best" # m4a أسرع في الستريمنج
            
            return opts

        # دالة التنفيذ في الخلفية (عشان منوقفش البوت)
        def execute_dl_background(opts):
            with YoutubeDL(opts) as ydl:
                try:
                    ydl.download([link])
                except Exception as e:
                    pass # تجاهل الأخطاء هنا لأننا بنراقب الملف

        # ----------------------------------------------------------------------
        #  SCENARIO 1: SONG VIDEO (SPECIFIC FORMAT)
        # ----------------------------------------------------------------------
        if songvideo:
            # هنا بنحمل كامل لأن اليوزر طالب ملف فيديو محدد
            await loop.run_in_executor(None, lambda: YoutubeDL({
                "format": f"{format_id}+140",
                "outtmpl": f"downloads/{title}",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True, 
                "cookiefile": cookiefile(),
                "merge_output_format": "mp4",
                "external_downloader": "aria2c" if self.has_aria2 else None,
                "external_downloader_args": SystemConfig.ARIA2_ARGS if self.has_aria2 else None,
            }).download([link]))
            return f"downloads/{title}.mp4"

        # ----------------------------------------------------------------------
        #  SCENARIO 2: SONG AUDIO (SPECIFIC FORMAT)
        # ----------------------------------------------------------------------
        elif songaudio:
            await loop.run_in_executor(None, lambda: YoutubeDL({
                "format": format_id,
                "outtmpl": f"downloads/{title}.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "cookiefile": cookiefile(),
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
            }).download([link]))
            return f"downloads/{title}.mp3"

        # ----------------------------------------------------------------------
        #  SCENARIO 3: PLAY / VPLAY (STREAMING + DOWNLOAD) - THE NUCLEAR PART
        # ----------------------------------------------------------------------
        else:
            is_vid_req = bool(video)
            # 1. التحقق من وجود الملف مسبقاً (Cache Hit)
            for f in os.listdir("downloads"):
                if f.startswith(vid_id):
                     return os.path.join("downloads", f), True

            # 2. بدء التحميل في الخلفية (بدون انتظار الانتهاء)
            dl_opts = get_download_options(is_video=is_vid_req)
            loop.run_in_executor(self.pool, execute_dl_background, dl_opts)

            # 3. حلقة المراقبة (Watchdog Loop)
            # الهدف: العثور على الملف بمجرد وصوله لحجم آمن (مثلاً 5 ميجا)
            start_time = time.time()
            found_file = None
            
            while time.time() - start_time < 30: # انتظار أقصى 30 ثانية
                files = [f for f in os.listdir("downloads") if f.startswith(vid_id) and not f.endswith(".aria2")]
                
                if files:
                    current_file = os.path.join("downloads", files[0])
                    try:
                        # الشرط السحري: هل حجم الملف > 2 ميجا؟
                        # لسرعتك (2.6 جيجا) ده هيحصل في جزء من الثانية
                        if os.path.getsize(current_file) > (2 * 1024 * 1024):
                            found_file = current_file
                            break
                    except OSError:
                        pass # الملف لسه محجوز
                
                await asyncio.sleep(0.5) # ريح المعالج نص ثانية

            # 4. النتيجة
            if found_file:
                # بنرجع True في المتغير التاني عشان نقول للبوت إن ده ملف محلي مش رابط مباشر
                return found_file, True 
            else:
                # لو فشل التحميل السريع، نرجع Fallback (رابط مباشر)
                # ده نظام أمان عشان البث ميقفش
                direct_link = await self.video(link)
                if direct_link[0] == 1:
                    return direct_link[1], False
                return None, None
