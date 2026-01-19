import asyncio
import logging
import os
import sys
import time

# ==========================================
# تــفــعــيــل UVLoop (أول خــطــوة حــصــريــاً)
# ==========================================
try:
    import uvloop
    uvloop.install()
    print("تــم تــفــعــيــل نــظــام UVLoop... الــوضــع الــســريــع")
except ImportError:
    print("نــظــام UVLoop غــيــر مــتــاح... الــعــمــل بــالــنــظــام الــعــادي")

# ==========================================
# اســتــدعــاء مــلــفــات الــبــوت
# ==========================================
# لازم الاستدعاء يحصل بعد تفعيل UVLoop عشان نتجنب التعارض
from AnnieXMedia.__main__ import init
from AnnieXMedia import LOGGER

# إعــداد الــمــراقــب
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)
monitor_logger = logging.getLogger("SystemMonitor")

# ==========================================
# وظــيــفــة مــراقــب الــســيــرفــر
# ==========================================
async def server_status_monitor():
    while True:
        # الانتظار 4 ساعات (14400 ثانية)
        await asyncio.sleep(14400)
        
        try:
            import psutil
            
            # جــلــب الــبــيــانــات
            cpu_usage = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # حــســاب وقــت الــتــشــغــيــل
            uptime_seconds = int(time.time() - psutil.boot_time())
            uptime_hours = uptime_seconds // 3600
            
            # تــنــســيــق الــرســالــة (مــطــول)
            status_msg = (
                f"تــقــريــر حــالــة الــســيــرفــر الــدوري :\n"
                f"___________________________________\n"
                f"اســتــهــلاك الــمــعــالــج : {cpu_usage}%\n"
                f"اســتــهــلاك الــرامــات : {ram.percent}%\n"
                f"الــمــســاحــة الــمــســتــخــدمــة : {disk.percent}%\n"
                f"عــدد ســاعــات الــعــمــل : {uptime_hours} ســاعــة\n"
                f"حــالــة الــنــظــام : مــســتــقــرة تــمــامــاً"
            )
            
            LOGGER("SystemMonitor").info(status_msg)
            
        except ImportError:
            LOGGER("SystemMonitor").warning("مــكــتــبــة psutil غــيــر مــثــبــتــة... لا يــمــكــن عــرض الــحــالــة")
        except Exception as e:
            LOGGER("SystemMonitor").error(f"خــطــأ فــي الــمــراقــب : {e}")

# ==========================================
# الــمــشــغــل الــرئــيــســي (Wrapper)
# ==========================================
async def main_runner():
    # 1. تــشــغــيــل الــمــراقــب فــي الــخــلــفــيــة
    asyncio.create_task(server_status_monitor())
    
    # 2. تــشــغــيــل الــبــوت (دالــة init مــن مــلــف الــمــايــن)
    # هــنــا هــيــشــتــغــل عــلــى نــفــس الــ Loop بــدون تــعــارض
    await init()

if __name__ == "__main__":
    try:
        # بــمــا إنــنــا فــعــلــنــا install فــوق... run هــتــســتــخــدم uvloop تــلــقــائــي
        asyncio.run(main_runner())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"حــدث خــطــأ جــســيــم : {e}")
