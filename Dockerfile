# استخدام Python 3.12 Slim (النسخة الاحترافية الخفيفة للأداء العالي)
# شلنا تحديد المعمارية عشان يختار الأقوى حسب السيرفر
FROM python:3.12-slim

# تحسينات الأداء للذاكرة والكاش
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# تنظيف شامل
RUN rm -rf /app/*

# -------------------------------------------------------------
# 1. تحديث النظام وتنزيل الوحوش (Aria2 & FFmpeg)
# -------------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    ffmpeg \
    aria2 \
    build-essential \
    libffi-dev \
    libssl-dev \
    zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------------------
# 2. حقن إعدادات Aria2 الصاروخية (Turbo Settings)
# -------------------------------------------------------------
# هنا بنجبر Aria2 يستخدم الرامات بدل الهارد عشان السرعة
RUN mkdir -p /root/.aria2 && \
    echo "max-connection-per-server=16" > /root/.aria2/aria2.conf && \
    echo "min-split-size=1M" >> /root/.aria2/aria2.conf && \
    echo "split=16" >> /root/.aria2/aria2.conf && \
    echo "max-concurrent-downloads=5" >> /root/.aria2/aria2.conf && \
    echo "check-certificate=false" >> /root/.aria2/aria2.conf && \
    echo "disk-cache=256M" >> /root/.aria2/aria2.conf

# -------------------------------------------------------------
# 3. تثبيت Deno (محرك اليوتيوب)
# -------------------------------------------------------------
RUN curl -fsSL https://deno.land/install.sh | sh && \
    ln -s /root/.deno/bin/deno /usr/local/bin/deno

# -------------------------------------------------------------
# 4. تثبيت مكتبات البايثون
# -------------------------------------------------------------
COPY pytgcalls /app/pytgcalls
COPY requirements.txt /app/requirements.txt

# فلترة المتطلبات لمنع التعارض
RUN if [ -f /app/requirements.txt ]; then \
      grep -v -i '^py-tgcalls' /app/requirements.txt > /app/filtered-requirements.txt || true; \
    fi

# تثبيت uvloop (مسرع البايثون) والمكتبات
RUN pip install --upgrade pip setuptools wheel && \
    pip install uvloop==0.21.0 && \
    if [ -f /app/filtered-requirements.txt ]; then pip install --no-cache-dir -r /app/filtered-requirements.txt; fi

# -------------------------------------------------------------
# 5. التشغيل والإصلاح الذاتي
# -------------------------------------------------------------
COPY . /app

# إصلاح مشكلة buffer-size أوتوماتيك في كل الملفات
RUN find /app -name "*.py" -print0 | xargs -0 sed -i 's/buffer-size/disk-cache/g'

# أمر التشغيل المباشر
CMD ["python3", "runner.py"]
