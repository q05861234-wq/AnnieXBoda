import asyncio
import logging
import time
import sys
from pyrogram import idle
from AnnieXMedia import app

# =========================
# 1. تفعيل UVLoop (السرعة)
# =========================
try:
    import uvloop
    uvloop.install()
    UVLOOP_STATE = "✅ مفعل (Active)"
except ImportError:
    UVLOOP_STATE = "⚠️ غير مثبت (Not Installed)"

# =========================
# 2. إعدادات اللوجز
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ServerState")

# =========================
# 3. مراقب السيرفر (كل 4 ساعات)
# =========================
async def server_status_monitor():
    start_time = time.time()
    
    while True:
        try:
            # حساب وقت التشغيل بالساعات
            uptime_seconds = int(time.time() - start_time)
            uptime_hours = uptime_seconds // 3600
            uptime_minutes = (uptime_seconds % 3600) // 60
            
            # محاولة جلب معلومات الرام والمعالج
            status_report = f"⏱️ وقت التشغيل: {uptime_hours} ساعة و {uptime_minutes} دقيقة"
            
            try:
                import psutil
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory()
                ram_used = ram.used // (1024 * 1024)
                ram_total = ram.total // (1024 * 1024)
                
                status_report += f" | 🖥️ المعالج: {cpu}% | 💾 الرام: {ram_used}/{ram_total}MB ({ram.percent}%)"
            except ImportError:
                status_report += " | (psutil غير مثبت لعرض الموارد)"

            status_report += f" | 🚀 المحرك: {UVLOOP_STATE}"
            
            # طباعة الحالة
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(status_report)
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # الانتظار لمدة 4 ساعات (4 * 60 * 60 = 14400 ثانية)
            await asyncio.sleep(14400)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"⚠️ خطأ في المراقب: {e}")
            await asyncio.sleep(60)

# =========================
# 4. المحرك الرئيسي
# =========================
async def main():
    logger.info("🔥 بدء تشغيل النظام...")
    
    # تشغيل مراقب السيرفر في الخلفية
    monitor_task = asyncio.create_task(server_status_monitor())

    # تشغيل البوت
    try:
        await app.start()
        logger.info(f"✅ تم تشغيل البوت بنجاح: @{app.me.username}")
    except Exception as e:
        logger.error(f"❌ فشل تشغيل البوت: {e}")
        sys.exit(1)

    # تثبيت التشغيل
    logger.info("🟢 النظام يعمل باستقرار. سيتم تحديث الحالة كل 4 ساعات.")
    await idle()

    # الإغلاق
    logger.info("🛑 جاري إيقاف الخدمات...")
    monitor_task.cancel()
    await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
