import asyncio
import logging
import os
import sys
import psutil

# ==========================================
# 1. تــهــيــئــة الــنــظــام والــ Loop
# ==========================================
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("تــم تــحــمــيــل UVLoop فــي الــمــشــغــل")
except ImportError:
    pass

# إنشاء اللوب وتثبيته
main_loop = asyncio.new_event_loop()
asyncio.set_event_loop(main_loop)

# (Monkey Patch) لمنع تضارب المكتبات
asyncio.get_event_loop = lambda: main_loop

# ==========================================
# 2. تــحــريــر الــمــوارد (16 Cores)
# ==========================================
def inject_power():
    try:
        os.environ["OMP_NUM_THREADS"] = "auto"
        p = psutil.Process(os.getpid())
        p.cpu_affinity(list(range(psutil.cpu_count())))
        try:
            p.nice(-10) # High Priority
        except:
            pass
        print(f"الــمــشــغــل يــعــمــل بــقــوة {psutil.cpu_count()} أنــويــة")
    except Exception as e:
        print(f"Error: {e}")

inject_power()

# ==========================================
# 3. استدعاء البوت
# ==========================================
from AnnieXMedia.__main__ import init
from AnnieXMedia import LOGGER

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)

# ==========================================
# 4. مــراقــب الــنــظــام (كــل 4 ســاعــات)
# ==========================================
async def server_status_monitor():
    while True:
        # الانتظار 4 ساعات (14400 ثانية)
        await asyncio.sleep(14400)
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            cores = psutil.cpu_count()
            
            LOGGER("SystemMonitor").info(
                f"\nتــقــريــر الــحــالــة الــدوري (4h):\n"
                f"___________________________\n"
                f"الــمــعــالــج : {cpu}% (Active Cores: {cores})\n"
                f"الــرامــات  : {ram}%\n"
                f"الــوضــع    : High Performance / UVLoop"
            )
        except:
            pass

# ==========================================
# الــتــشــغــيــل
# ==========================================
if __name__ == "__main__":
    try:
        # إضافة مهمة المراقبة للوب
        main_loop.create_task(server_status_monitor())
        
        # تشغيل البوت
        main_loop.run_until_complete(init())
        
        # ضمان استمرار العمل
        main_loop.run_forever()
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Critical Error: {e}")
