import asyncio
import logging
import time
import sys

# ==========================================
# 1. تفعيل UVLoop (أول خطوة إجبارياً)
# ==========================================
# لازم ده يحصل قبل أي import للبوت عشان نمنع مشكلة "Different Loop"
try:
    import uvloop
    uvloop.install()
    LOOP_STATUS = "✅ UVLoop نشط"
except ImportError:
    LOOP_STATUS = "⚠️ Default Loop"

# ==========================================
# 2. استدعاء البوت (الآن آمن)
# ==========================================
from pyrogram import idle
# استدعاء البوت هنا بعد تفعيل الـ Loop عشان يشتغل عليه
from AnnieXMedia import app 

# ==========================================
# 3. إعدادات اللوجز
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SystemMonitor")

# ==========================================
# 4. مراقب السيرفر (كل 4 ساعات)
# ==========================================
async def server_status_worker():
    start_time = time.time()
    while True:
        try:
            # حساب الوقت
            uptime_seconds = int(time.time() - start_time)
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            
            # جلب المعلومات (لو متاحة)
            usage_info = ""
            try:
                import psutil
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory()
                usage_info = f"| 🖥️ CPU: {cpu}% | 💾 RAM: {ram.percent}%"
            except:
                pass

            # طباعة الحالة في سطر واحد نظيف
            logger.info(
                f"📊 الحالة: مستقر {usage_info} | ⏱️ العمل: {hours}س و {minutes}د | 🚀 {LOOP_STATUS}"
            )
            
            # النوم لمدة 4 ساعات
            await asyncio.sleep(14400)
            
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(60)

# ==========================================
# 5. التشغيل الرئيسي
# ==========================================
async def main():
    logger.info("🔥 بدء إقلاع النظام...")

    # تشغيل المراقب في الخلفية (Task منفصلة لا تعطل البوت)
    asyncio.create_task(server_status_worker())

    # تشغيل البوت فقط (بدون التدخل في المساعد)
    try:
        await app.start()
        logger.info(f"✅ تم الاتصال: {app.me.first_name} (@{app.me.username})")
    except Exception as e:
        logger.error(f"❌ فشل الاتصال: {e}")
        return

    # تثبيت التشغيل
    logger.info("⚡ النظام يعمل الآن. (Ctrl+C للإيقاف)")
    await idle()

    # الإغلاق
    try:
        await app.stop()
    except:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
