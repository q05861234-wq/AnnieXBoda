# Authored By Certified Coders © 2025
import asyncio
import sys
import os
import importlib

# ==========================================
# تــفــعــيــل مــحــرك UVLoop
# ==========================================
try:
    import uvloop
    uvloop.install()
    print("تــم تــفــعــيــل مــحــرك UVLoop بــنــجــاح... الــســرعــة الــقــصــوى")
except ImportError:
    print("مــحــرك UVLoop غــيــر مــثــبــت... جــاري الــعــمــل بــالــنــظــام الافــتــراضــي")

# ==========================================

sys.path.insert(0, os.getcwd())

from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from AnnieXMedia import LOGGER, app, userbot
from AnnieXMedia.core.call import StreamController
from AnnieXMedia.misc import sudo
from AnnieXMedia.plugins import ALL_MODULES
from AnnieXMedia.utils.database import get_banned_users, get_gbanned
from AnnieXMedia.utils.cookie_handler import fetch_and_store_cookies
from config import BANNED_USERS


async def init():
    # التحقق من الجلسات
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("خــطــأ: كــود جــلــســة الــمــســاعــد مــفــقــود... يــرجــى إضــافــة الــكــود")
        exit()

    # تحميل الكوكيز
    try:
        LOGGER("AnnieXMedia").info("جــاري جــلــب مــلــفــات الــكــوكــيــز مــن الــخــادم...")
        await fetch_and_store_cookies()
        LOGGER("AnnieXMedia").info("تــم تــحــمــيــل الــكــوكــيــز بــنــجــاح")
    except Exception as e:
        LOGGER("AnnieXMedia").warning(f"تــحــذيــر بــخــصــوص الــكــوكــيــز: {e}")


    await sudo()

    # تحميل المحظورين
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
        LOGGER("AnnieXMedia").info(f"تــم تــحــمــيــل {len(BANNED_USERS)} مــســتــخــدم فــي قــائــمــة الــحــظــر")
    except:
        pass

    # تشغيل البوت
    LOGGER("AnnieXMedia").info("جــاري بــدء تــشــغــيــل عــمــيــل الــبــوت...")
    await app.start()
    
    # تحميل الملحقات
    for all_module in ALL_MODULES:
        importlib.import_module("AnnieXMedia.plugins" + all_module)

    LOGGER("AnnieXMedia.plugins").info("تــم اســتــيــراد جــمــيــع مــلــفــات الــبــوت بــنــجــاح...")

    # تشغيل اليوزربوت والمكالمات
    LOGGER("AnnieXMedia").info("جــاري تــشــغــيــل الــحــســاب الــمــســاعــد...")
    await userbot.start()
    await StreamController.start()

    # فحص الكول
    try:
        await StreamController.stream_call("http://docs.evostream.com/sample_content/assets/sintel1m720p.mp4")
    except NoActiveGroupCall:
        LOGGER("AnnieXMedia").error(
            "الــمــحــادثــة الــصــوتــيــة مــغــلــقــة...\nيــرجــى فــتــح الــكــول فــي جــروب الــســجــل"
        )
        exit()
    except:
        pass

    await StreamController.decorators()
    
    # رسالة التشغيل النهائية
    LOGGER("AnnieXMedia").info(
        "تــم تــشــغــيــل ســورس آنــي مــيــوزك بــنــجــاح...\n"
        "الــنــظــام يــعــمــل الآن بــكــفــاءة عــالــيــة"
    )
    
    await idle()
    
    # الإغلاق
    await app.stop()
    await userbot.stop()
    LOGGER("AnnieXMedia").info("تــم إيــقــاف بــوت آنــي مــيــوزك بــنــجــاح...")


if __name__ == "__main__":
    # تشغيل الدالة باستخدام Loop مهيأ مسبقاً بـ uvloop
    asyncio.get_event_loop().run_until_complete(init())
