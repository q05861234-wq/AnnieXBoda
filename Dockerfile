# Python 3.12 معتمدة على نسخة pytgcalls المحلية
FROM python:3.12-slim

# تحسينات الأداء والبيئة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
# السماح لـ Aria2 باستخدام التوصيلات المتعددة افتراضياً لو تم استدعاؤه بدون كونفيج
ENV ARIA2_OPTS="--max-connection-per-server=16 --split=16 --min-split-size=1M"

WORKDIR /app

# تنظيف أي ملفات قديمة
RUN rm -rf /app/*

# -------------------------------------------------------------
# 1. تثبيت المتطلبات النظامية + Aria2 + Deno
# تم إضافة aria2 هنا عشان يشتغل مع yt-dlp
# -------------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    aria2 \
    curl \
    unzip \
    build-essential && \
    rm -rf /var/lib/apt/lists/* && \
    # تثبيت Deno (لو البوت بيستخدمه في حاجة جانبية)
    curl -fsSL https://deno.land/install.sh | sh && \
    ln -s /root/.deno/bin/deno /usr/local/bin/deno

# -------------------------------------------------------------
# 2. نسخ مكتبة pytgcalls المحلية وتثبيت المتطلبات
# -------------------------------------------------------------
COPY pytgcalls /app/pytgcalls

COPY requirements.txt /app/requirements.txt

# حذف py-tgcalls من الملف عشان نستخدم النسخة المحلية + تثبيت المكتبات
RUN if [ -f /app/requirements.txt ]; then \
      grep -v -i '^py-tgcalls' /app/requirements.txt > /app/filtered-requirements.txt || true; \
    fi

# تثبيت uvloop يدوياً لو مش موجود (عشان السرعة القصوى)
RUN pip install --upgrade pip setuptools wheel && \
    pip install uvloop && \
    if [ -f /app/filtered-requirements.txt ]; then pip install --no-cache-dir -r /app/filtered-requirements.txt; fi

# -------------------------------------------------------------
# 3. نسخ باقي ملفات البوت وتشغيل الاختبار
# -------------------------------------------------------------
COPY . /app

# تأكيد ان Python بيستخدم النسخة المحلية
RUN python - <<'PY'
import pytgcalls, sys
print('PYTGCALLS_FROM=', getattr(pytgcalls,'__file__','<not found>'))
PY

# -------------------------------------------------------------
# 4. التشغيل: استخدام runner.py لسحب سرعة المعالج بالكامل
# -------------------------------------------------------------
CMD ["python3", "runner.py"]
