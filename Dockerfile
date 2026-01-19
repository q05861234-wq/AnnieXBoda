# Python 3.12 معتمدة على نسخة pytgcalls المحلية
FROM python:3.12

# تحسينات الأداء والبيئة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# 🔥 إعدادات السرعة القصوى تُفرض على النظام بالكامل 🔥
# ده بيخلي أي عملية تحميل تاخد 16 خط وتستخدم الرامات بدل الهارد
ENV ARIA2_OPTS="--max-connection-per-server=16 --split=16 --min-split-size=1M --disk-cache=256M"

WORKDIR /app

# تنظيف أي ملفات قديمة
RUN rm -rf /app/*

# -------------------------------------------------------------
# 1. تجهيز أدوات البناء وتجميع Aria2 من المصدر
# -------------------------------------------------------------
RUN apt-get update && \
    # ✅ إضافة autopoint و gettext لحل مشكلة البناء السابقة
    apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    curl \
    unzip \
    build-essential \
    autoconf \
    automake \
    libtool \
    pkg-config \
    gettext \
    autopoint \
    libxml2-dev \
    libcppunit-dev \
    libgcrypt-dev \
    lzip \
    zlib1g-dev \
    libc-ares-dev \
    libssh2-1-dev \
    libssl-dev && \
    \
    # ⬇️ بناء Aria2 من السورس كود (أحدث نسخة) ⬇️
    echo "Building latest Aria2 from Source..." && \
    git clone https://github.com/aria2/aria2.git && \
    cd aria2 && \
    autoreconf -i && \
    ./configure --without-gnutls --with-openssl && \
    make -j$(nproc) && \
    make install && \
    cd .. && \
    rm -rf aria2 && \
    \
    # ⚡ إنشاء ملف إعدادات "Turbo" دائم للنظام ⚡
    # الإعدادات دي بتشتغل أوتوماتيك مع أي تحميل
    mkdir -p /root/.aria2 && \
    echo "max-connection-per-server=16" > /root/.aria2/aria2.conf && \
    echo "split=16" >> /root/.aria2/aria2.conf && \
    echo "min-split-size=1M" >> /root/.aria2/aria2.conf && \
    echo "disk-cache=256M" >> /root/.aria2/aria2.conf && \
    echo "file-allocation=none" >> /root/.aria2/aria2.conf && \
    echo "continue=true" >> /root/.aria2/aria2.conf && \
    echo "optimize-concurrent-downloads=true" >> /root/.aria2/aria2.conf && \
    \
    # تثبيت Deno
    curl -fsSL https://deno.land/install.sh | sh && \
    ln -s /root/.deno/bin/deno /usr/local/bin/deno && \
    \
    # تنظيف
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# -------------------------------------------------------------
# 2. نسخ مكتبة pytgcalls المحلية وتثبيت المتطلبات
# -------------------------------------------------------------
COPY pytgcalls /app/pytgcalls

COPY requirements.txt /app/requirements.txt

# فلترة المتطلبات (حذف py-tgcalls عشان نستخدم المحلي)
RUN if [ -f /app/requirements.txt ]; then \
      grep -v -i '^py-tgcalls' /app/requirements.txt > /app/filtered-requirements.txt || true; \
    fi

# تثبيت المكتبات + uvloop للسرعة
RUN pip install --upgrade pip setuptools wheel && \
    pip install uvloop && \
    if [ -f /app/filtered-requirements.txt ]; then pip install --no-cache-dir -r /app/filtered-requirements.txt; fi

# -------------------------------------------------------------
# 3. نسخ باقي ملفات البوت
# -------------------------------------------------------------
COPY . /app

# اختبار النسخة المحلية
RUN python - <<'PY'
import pytgcalls, sys
print('PYTGCALLS_FROM=', getattr(pytgcalls,'__file__','<not found>'))
PY

# -------------------------------------------------------------
# 4. التشغيل
# -------------------------------------------------------------
CMD ["python3", "runner.py"]
