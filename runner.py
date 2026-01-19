import asyncio
import logging
import os
import sys
import time

# ==========================================
# 1. إعــداد UVLoop وإنــشــاء الــ Loop يــدويــاً
# ==========================================
# الــخــطــوة دي ضــروريــة جــداً لــحــل مــشــكــلــة pytgcalls
try:
    import uvloop
    uvloop.install()
    print("تــم تــفــعــيــل نــظــام UVLoop... الــوضــع الــســريــع")
except ImportError:
    print("نــظــام UVLoop غــيــر مــتــاح... الــعــمــل بــالــنــظــام الــعــادي")

# نــقــوم بــإنــشــاء الــ Loop وتــعــيــيــنــه يــدويــاً قــبــل الاســتــدعــاء
# هــذا يــمــنــع خــطــأ Runtime Error: There is no current event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ==========================================
# 2. اســتــدعــاء مــلــفــات الــبــوت
# ==========================================
# تــم نــقــل الاســتــدعــاء هــنــا بــعــد تــهــيــئــة الــ Loop
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
        # الانتظار 4 ساعات
        await asyncio.sleep(14400)
        
        try:
            import psutil
            cpu_usage = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            uptime_seconds = int(time.time() - psutil.boot_time())
            uptime_hours = uptime_seconds // 3600
            
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
            pass
        except Exception:
            pass

# ==========================================
# الــمــشــغــل الــرئــيــســي
# ==========================================
if __name__ == "__main__":
    try:
        # تــشــغــيــل الــمــراقــب فــي الــخــلــفــيــة عــلــى نــفــس الــ Loop
        loop.create_task(server_status_monitor())
        
        # تــشــغــيــل الــبــوت
        loop.run_until_complete(init())
        
        # تــشــغــيــل الــ Loop إلــى مــا لا نــهــايــة
        loop.run_forever()
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"حــدث خــطــأ جــســيــم : {e}")
