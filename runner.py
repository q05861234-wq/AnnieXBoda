import asyncio
import logging
import os
import sys
import psutil

# ==========================================
# 1. الــكــشــف الــتــلــقــائــي عــن الــمــوارد
# ==========================================
# هنا بنخلي الكود يعد الكورات الحقيقية للسيرفر الحالي
# لو فشل في العد لأي سبب، بيفترض وجود كور واحد كحد أدنى
real_cpu_count = psutil.cpu_count(logical=True) or 1
cpu_count_str = str(real_cpu_count)

# بنطبق الرقم اللي طلعناه على إعدادات النظام
# كده تخلصنا من كلمة 'auto' اللي بتعمل مشاكل
os.environ["OMP_NUM_THREADS"] = cpu_count_str
os.environ["MKL_NUM_THREADS"] = cpu_count_str
os.environ["OPENBLAS_NUM_THREADS"] = cpu_count_str

# ==========================================
# 2. تــهــيــئــة الــ Loop
# ==========================================
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("تــم تــحــمــيــل UVLoop فــي الــمــشــغــل")
except ImportError:
    pass

main_loop = asyncio.new_event_loop()
asyncio.set_event_loop(main_loop)
asyncio.get_event_loop = lambda: main_loop

# ==========================================
# 3. تــحــريــر الــمــوارد (Dynamic)
# ==========================================
def inject_power():
    try:
        p = psutil.Process(os.getpid())
        
        # توزيع الحمل ديناميكياً بناءً على العدد اللي كشفناه فوق
        available_cores = list(range(real_cpu_count))
        p.cpu_affinity(available_cores)
        
        try:
            p.nice(-10) # High Priority
        except:
            pass
            
        print(f"الــمــشــغــل يــعــمــل بــقــوة {real_cpu_count} أنــويــة (Dynamic Mode)")
    except Exception as e:
        print(f"Error: {e}")

inject_power()

# ==========================================
# 4. استدعاء البوت
# ==========================================
from AnnieXMedia.__main__ import init
from AnnieXMedia import LOGGER

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)

# ==========================================
# 5. مــراقــب الــنــظــام (كــل 4 ســاعــات)
# ==========================================
async def server_status_monitor():
    while True:
        await asyncio.sleep(14400)
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            
            LOGGER("SystemMonitor").info(
                f"\nتــقــريــر الــحــالــة الــدوري (4h):\n"
                f"___________________________\n"
                f"الــمــعــالــج : {cpu}% (Active Cores: {real_cpu_count})\n"
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
        # منع كراش التليجرام سيرفر ايرور
        main_loop.set_exception_handler(lambda loop, context: None)

        main_loop.create_task(server_status_monitor())
        main_loop.run_until_complete(init())
        main_loop.run_forever()
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Critical Error: {e}")
