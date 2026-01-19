import asyncio
import logging
import time
import sys
import uvloop

# ==========================================
# 1. إجبار النظام على استخدام UVLoop يدوياً
# ==========================================
# بنعمل Loop جديد بـ uvloop
uvloop.install()
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ==========================================
# 2. استدعاء البوت (بعد تجهيز الـ Loop)
# ==========================================
# الترتيب هنا حياة أو موت: لازم الاستدعاء يتم بعد السطرين اللي فوق
from AnnieXMedia import app
from pyrogram import idle

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
async def server_monitor():
    while True:
        try:
            # انتظار 4 ساعات في البداية (عشان منزحمش اللوج أول ما يفتح)
            # 4 * 60 * 60 = 14400 ثانية
            await asyncio.sleep(14400)
            
            # تقرير بسيط جداً عشان ميعلقش
            report = f"📊 تقرير دوري: السيرفر يعمل باستقرار (UVLoop Active)"
            try:
                import psutil
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                report += f" | CPU: {cpu}% | RAM: {ram}%"
            except:
                pass
            
            logger.info(report)
            
        except asyncio.CancelledError:
            break
        except Exception:
            pass

# ==========================================
# 5. دالة التشغيل الرئيسية
# ==========================================
async def main():
    logger.info("🔥 بدء تشغيل النظام (Manual Loop Mode)...")
    
    # تشغيل المراقب كـ Task فرعية
    loop.create_task(server_monitor())

    # تشغيل البوت
    try:
        # هنا البوت هيشتغل على الـ Loop اللي احنا حددناه فوق
        await app.start()
        logger.info(f"✅ تم الاتصال: {app.me.first_name}")
    except Exception as e:
        logger.error(f"❌ خطأ: {e}")
        return

    # وضع الخمول
    logger.info("⚡ النظام يعمل الآن باستقرار تام.")
    await idle()

    # الإغلاق
    await app.stop()

# ==========================================
# 6. نقطة الدخول (بدون asyncio.run)
# ==========================================
if __name__ == "__main__":
    try:
        # بنشغل الـ Loop اللي كريتناه بنفسنا
        # دي الطريقة الوحيدة لمنع خطأ "Different Loop"
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal Error: {e}")
