import os
import sys
import asyncio
import signal
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from datetime import datetime
from pyrogram import idle  # مهم جداً للتشغيل المستمر

# =========================
# إعدادات السجلات (LOGGING)
# =========================

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("UVLOOP-ENGINE")

# =========================
# تحسينات المعالج (CPU)
# =========================

CPU_CORES = os.cpu_count() or 4
MAX_THREADS = min(32, CPU_CORES * 4)
MAX_PROCESSES = max(2, CPU_CORES - 1)

logger.info(f"⚙️ عدد أنوية المعالج المكتشفة: {CPU_CORES}")
logger.info(f"🧵 حجم مجمع المسارات (Threads): {MAX_THREADS}")
logger.info(f"⚡ حجم مجمع العمليات (Processes): {MAX_PROCESSES}")

thread_pool = ThreadPoolExecutor(max_workers=MAX_THREADS)
process_pool = ProcessPoolExecutor(max_workers=MAX_PROCESSES)

# =========================
# تفعيل UVLOOP
# =========================

def activate_uvloop():
    try:
        import uvloop
        uvloop.install()
        logger.info("🚀 تم تفعيل UVLoop بنجاح")
    except Exception as e:
        logger.warning(f"⚠️ فشل تفعيل UVLoop: {e}")

activate_uvloop()

# =========================
# ضبط النظام (SYSTEM TUNING)
# =========================

os.environ.setdefault("PYTHONASYNCIODEBUG", "0")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

# =========================
# مراقب الأداء (PERFORMANCE MONITOR)
# =========================

class PerformanceMonitor:
    def __init__(self):
        self.start_time = datetime.now()

    async def monitor(self):
        while True:
            await asyncio.sleep(10)
            try:
                loop = asyncio.get_running_loop()
                uptime = (datetime.now() - self.start_time).seconds
                pending = len(asyncio.all_tasks(loop))

                logger.info(
                    f"📊 وقت التشغيل: {uptime}ث | المهام المعلقة: {pending} | "
                    f"المسارات النشطة: {threading.active_count()} | "
                    f"الأنوية: {CPU_CORES}"
                )
            except:
                pass

# =========================
# تحميل البوت (BOT LOADER)
# =========================

def load_bot():
    try:
        from AnnieXMedia import app
        return app
    except Exception as e:
        logger.exception("❌ فشل تحميل البوت")
        sys.exit(1)

# =========================
# المحرك الرئيسي (MAIN ENGINE)
# =========================

async def main():
    logger.info("🔥 بدء تشغيل المحرك عالي الأداء...")

    # تشغيل مراقب الأداء
    monitor = PerformanceMonitor()
    asyncio.create_task(monitor.monitor())

    # تحميل البوت
    app = load_bot()

    logger.info("🚀 جاري الاتصال بسيرفرات تليجرام...")

    # --- بداية التشغيل الصحيح ---
    try:
        # بنشغل البوت مباشرة هنا عشان يستفيد من سرعة UVLoop
        await app.start()
    except Exception as e:
        logger.error(f"⚠️ حدث خطأ أثناء الاتصال: {e}")
        # لو الخطأ بسيط كمل، لو كبير هيقفل لوحده

    # تفعيل وضع الخمول عشان البوت يفضل شغال وميقفلش
    await idle()
    
    # --- نهاية التشغيل ---

    logger.warning("🛑 جاري إغلاق البوت...")
    try:
        await app.stop()
    except:
        pass

    logger.warning("🧹 تنظيف الموارد...")
    thread_pool.shutdown(wait=False)
    process_pool.shutdown(wait=False)

# =========================
# نقطة الدخول (ENTRY POINT)
# =========================

if __name__ == "__main__":
    try:
        # تشغيل الـ Loop الرئيسي
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("♥️  تم الإغلاق بواسطة (Boda)")
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {e}")
