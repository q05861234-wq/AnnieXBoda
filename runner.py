import asyncio
import logging
import os
import sys
import time
import psutil

# ==========================================
# 1. الإصــلاح الــجــذري للـ Loop (The Fix)
# ==========================================
# بـدلاً مـن install، سـنـقـوم بـفـرض الـسـيـاسـة يـدويـاً
# هـذا يـجـعـل بـايـثـون 3.12 يـعـتـرف بـالـ Loop فـوراً
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("✅ تــم فــرض ســيــاســة UVLoop بــنــجــاح")
except ImportError:
    print("⚠️ UVLoop غــيــر مــثــبــت")

# إنــشــاء الــ Loop وتــثــبــيــتــه "غــصــب" عــن الــنــظــام
# هـذا الـسـطـر هـو الـذي يـمـنـع خـطـأ RuntimeError
main_loop = asyncio.new_event_loop()
asyncio.set_event_loop(main_loop)

# ==========================================
# 2. تــفــعــيــل الــســرعــة الــقــصــوى (Full Speed)
# ==========================================
def set_max_priority():
    try:
        p = psutil.Process(os.getpid())
        # الـقـيـمـة -10 تـعـطـي أولـويـة أعـلـى مـن الـنـظـام الـعـادي
        p.nice(-10)
        print("🚀 تــم تــفــعــيــل وضــع الــأداء الــأقــصــى (High Priority)")
    except Exception as e:
        print(f"تــنــبــيــه: لــم نــتــمــكــن مــن رفــع الأولــويــة ({e})")

# تــنــفــيــذ الأولــويــة فــوراً
set_max_priority()

# ==========================================
# 3. اســتــدعــاء الــبــوت (بــعــد الــتــثــبــيــت)
# ==========================================
from AnnieXMedia.__main__ import init
from AnnieXMedia import LOGGER

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)

# ==========================================
# مــراقــب الــنــظــام الــســريــع
# ==========================================
async def server_status_monitor():
    while True:
        await asyncio.sleep(14400)
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            
            LOGGER("SystemMonitor").info(
                f"تــقــريــر الــســرعــة :\n"
                f"___________________\n"
                f"الــضــغــط عــلــى الــمــعــالــج : {cpu}%\n"
                f"اســتــهــلاك الــذاكــرة : {ram.percent}%\n"
                f"وضــع الــتــشــغــيــل : Full Speed / UVLoop Active"
            )
        except:
            pass

# ==========================================
# الــتــشــغــيــل الــنــهــائــي
# ==========================================
if __name__ == "__main__":
    try:
        # نــســتــخــدم الــ Loop الــذي أنــشــأنــاه بــالأعــلــى
        main_loop.create_task(server_status_monitor())
        main_loop.run_until_complete(init())
        main_loop.run_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"خــطــأ غــيــر مــتــوقــع : {e}")
