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
# LOGGING CONFIGURATION
# =========================

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("UVLOOP-ENGINE")

# =========================
# CPU OPTIMIZATION
# =========================

CPU_CORES = os.cpu_count() or 4
MAX_THREADS = min(32, CPU_CORES * 4)
MAX_PROCESSES = max(2, CPU_CORES - 1)

logger.info(f"⚙️ CPU Cores Detected: {CPU_CORES}")
logger.info(f"🧵 Thread Pool Size: {MAX_THREADS}")
logger.info(f"⚡ Process Pool Size: {MAX_PROCESSES}")

thread_pool = ThreadPoolExecutor(max_workers=MAX_THREADS)
process_pool = ProcessPoolExecutor(max_workers=MAX_PROCESSES)

# =========================
# UVLOOP ACTIVATION
# =========================

def activate_uvloop():
    try:
        import uvloop
        uvloop.install()
        logger.info("🚀 UVLoop successfully activated")
    except Exception as e:
        logger.warning(f"⚠️ UVLoop activation failed: {e}")

activate_uvloop()

# =========================
# ASYNCIO OPTIMIZATIONS
# =========================

asyncio.get_event_loop_policy()

# =========================
# SYSTEM TUNING
# =========================

os.environ.setdefault("PYTHONASYNCIODEBUG", "0")
os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("OMP_NUM_THREADS", str(CPU_CORES))
os.environ.setdefault("MKL_NUM_THREADS", str(CPU_CORES))

# =========================
# PERFORMANCE MONITOR
# =========================

class PerformanceMonitor:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.start_time = datetime.now()
        self.tasks_processed = 0

    async def monitor(self):
        while True:
            await asyncio.sleep(10)
            uptime = (datetime.now() - self.start_time).seconds
            pending = len(asyncio.all_tasks(self.loop))

            logger.info(
                f"📊 Uptime: {uptime}s | Pending Tasks: {pending} | "
                f"Threads: {threading.active_count()} | "
                f"CPU Cores: {CPU_CORES}"
            )

monitor = PerformanceMonitor()

# =========================
# SAFE SHUTDOWN
# =========================

shutdown_event = asyncio.Event()

def handle_exit(sig, frame):
    logger.warning(f"🛑 Signal received: {sig}. Shutting down safely...")
    shutdown_event.set()

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# =========================
# BOT LOADER
# =========================

def load_bot():
    """
    Import bot ONLY after uvloop activation
    Prevents asyncio conflicts
    """
    try:
        from AnnieXMedia import app   # عدل المسار لو مختلف
        return app
    except Exception as e:
        logger.exception("❌ Failed to load bot")
        sys.exit(1)

# =========================
# ASYNC TASK WRAPPER
# =========================

async def run_blocking(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(thread_pool, func, *args)

async def run_cpu_bound(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(process_pool, func, *args)

# =========================
# MAIN ENGINE
# =========================

async def main():
    logger.info("🔥 High Performance Engine Starting...")

    app = load_bot()

    asyncio.create_task(monitor.monitor())

    await run_blocking(app.run)

    await shutdown_event.wait()

    logger.warning("🧹 Cleaning up resources...")

    thread_pool.shutdown(wait=False)
    process_pool.shutdown(wait=False)

# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("♥️  Boda")
