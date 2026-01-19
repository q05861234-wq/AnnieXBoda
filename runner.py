import asyncio
import logging
import os
import sys
import psutil

# ==========================================
# 1. الــحــل الــنــهــائــي (Loop Initialization)
# ==========================================
# الخطوة دي لازم تحصل قبل أي import لأي مكتبة تانية
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("✅ تــم تــحــمــيــل UVLoop فــي الــمــشــغــل")
except ImportError:
    pass

# بنصنع اللوب يدوياً
main_loop = asyncio.new_event_loop()
asyncio.set_event_loop(main_loop)

# (Monkey Patch)
# بنجبر بايثون ومكتبة الاتصال يستخدموا اللوب ده غصب
# ده بيحل مشكلة RuntimeError: There is no current event loop
asyncio.get_event_loop = lambda: main_loop

# ==========================================
# 2. تــفــعــيــل الــ 16 كــور (Hardware Power)
# ==========================================
def inject_power():
    try:
        # السماح باستخدام كل الموارد
        os.environ["OMP_NUM_THREADS"] = "auto"
        
        # توزيع الحمل على جميع الأنوية
        p = psutil.Process(os.getpid())
        p.cpu_affinity(list(range(psutil.cpu_count())))
        
        # رفع الأولوية (High Priority)
        try:
            p.nice(-10)
        except:
            pass
            
        print(f"🚀 الــمــشــغــل يــعــمــل بــقــوة {psutil.cpu_count()} أنــويــة")
    except Exception as e:
        print(f"⚠️ {e}")

inject_power()

# ==========================================
# 3. بــدء الــبــوت
# ==========================================
# دلوقتي نقدر نستدعي ملفات البوت بأمان
from AnnieXMedia.__main__ import init
from AnnieXMedia import LOGGER

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)

if __name__ == "__main__":
    try:
        # بنستخدم اللوب اللي جهزناه فوق
        main_loop.run_until_complete(init())
        main_loop.run_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Critical Error: {e}")
