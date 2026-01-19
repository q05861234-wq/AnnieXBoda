import os
import sys
import asyncio
import signal
import logging
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from datetime import datetime

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
# تحسينات ASYNCIO
# =========================

# تم إزالة الاستدعاء المباشر هنا لتجنب الأخطاء في إصدارات بايثون الحديثة
# asyncio.get_event_loop_policy() 

# =========================
# ضبط النظام (SYSTEM TUNING)
# =========================

os.environ.setdefault("PYTHONASYNCIODEBUG", "0")
os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("OMP_NUM_THREADS", str(CPU_CORES))
os.environ.setdefault("MKL_NUM_THREADS", str(CPU_CORES))

# =========================
# مراقب الأداء (PERFORMANCE MONITOR)
# =========================

class PerformanceMonitor:
    def __init__(self):
        # تم إزالة get_event_loop من هنا لأنها تسبب المشكلة
        self.start_time = datetime.now()

    async def monitor(self):
        while True:
            await asyncio.sleep(10)
            loop = asyncio.get_running_loop() # الحصول على الـ Loop الحالي بأمان
            uptime = (datetime.now() - self.start_time).seconds
            pending = len(asyncio.all_tasks(loop))

            logger.info(
                f"📊 وقت التشغيل: {uptime}ث | المهام المعلقة: {pending} | "
                f"المسارات النشطة: {threading.active_count()} | "
                f"الأنوية: {CPU_CORES}"
            )

# =========================
# الإغلاق الآمن (SAFE SHUTDOWN)
# =========================

shutdown_event = asyncio.Event()

def handle_exit(sig, frame):
    logger.warning(f"🛑 تم استلام إشارة: {sig}. جاري إغلاق النظام بأمان...")
    shutdown_event.set()

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# =========================
# تحميل البوت (BOT LOADER)
# =========================

def load_bot():
    """
    استيراد البوت فقط بعد تفعيل uvloop
    لمنع تضارب asyncio
    """
    try:
        from AnnieXMedia import app   # تأكد أن المسار صحيح
        return app
    except Exception as e:
        logger.exception("❌ فشل تحميل البوت")
        sys.exit(1)

# =========================
# مغلف المهام غير المتزامنة
# =========================

async def run_blocking(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(thread_pool, func, *args)

async def run_cpu_bound(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(process_pool, func, *args)

# =========================
# المحرك الرئيسي (MAIN ENGINE)
# =========================

async def main():
    logger.info("🔥 بدء تشغيل المحرك عالي الأداء...")

    # تهيئة المراقب هنا داخل الـ Loop
    monitor = PerformanceMonitor()
    asyncio.create_task(monitor.monitor())

    app = load_bot()

    # تشغيل البوت
    await run_blocking(app.run)

    await shutdown_event.wait()

    logger.warning("🧹 تنظيف الموارد...")

    thread_pool.shutdown(wait=False)
    process_pool.shutdown(wait=False)

# =========================
# نقطة الدخول (ENTRY POINT)
# =========================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("♥️  تم الإغلاق بواسطة (Boda)")
