# Authored By Certified Coders © 2025
import sys
import os
import importlib
import config
from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall
from AnnieXMedia import LOGGER, app, userbot
from AnnieXMedia.core.call import StreamController
from AnnieXMedia.misc import sudo
from AnnieXMedia.plugins import ALL_MODULES
from AnnieXMedia.utils.database import get_banned_users, get_gbanned
from AnnieXMedia.utils.cookie_handler import fetch_and_store_cookies
from config import BANNED_USERS

sys.path.insert(0, os.getcwd())

async def init():
    # 1. التحقق من الجلسات
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("خــطــأ: كــود جــلــســة الــمــســاعــد مــفــقــود")
        exit()

    # 2. الكوكيز
    try:
        LOGGER("AnnieXMedia").info("جــاري جــلــب الــكــوكــيــز...")
        await fetch_and_store_cookies()
    except Exception as e:
        LOGGER("AnnieXMedia").warning(f"Cookie Error: {e}")

    await sudo()

    # 3. المحظورين
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass

    # 4. تشغيل البوت
    LOGGER("AnnieXMedia").info("Start Client...")
    await app.start()
    
    # 5. الملحقات
    for all_module in ALL_MODULES:
        importlib.import_module("AnnieXMedia.plugins" + all_module)
    LOGGER("AnnieXMedia.plugins").info("Plugins Imported")

    # 6. المساعد والمكالمات
    await userbot.start()
    await StreamController.start()

    try:
        await StreamController.stream_call("http://docs.evostream.com/sample_content/assets/sintel1m720p.mp4")
    except NoActiveGroupCall:
        LOGGER("AnnieXMedia").error("Please start the Voice Chat..")
        exit()
    except:
        pass

    await StreamController.decorators()
    LOGGER("AnnieXMedia").info("Started Successfully")
    
    # الانتظار (Idle)
    await idle()
    
    # الإغلاق
    await app.stop()
    await userbot.stop()

# شيلنا الـ if __name__ == "__main__" من هنا خالص
# عشان نمنع التعارض مع runner.py
