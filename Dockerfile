# بنستخدم صورة Python 3.12 المبنية على Linux Debian Bookworm
# دي أكثر نسخة مستقرة لبيئة اللينكس
FROM python:3.12-bookworm

# ضبط إعدادات البيئة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV DEBIAN_FRONTEND=noninteractive

# 🔥 تفعيل وضع السرعة القصوى (Turbo Linux Mode) 🔥
ENV ARIA2_OPTS="--max-connection-per-server=128 --split=128 --min-split-size=1M --disk-cache=512M"

WORKDIR /app

# تنظيف الملفات المؤقتة
RUN rm -rf /app/*

# -------------------------------------------------------------
# 1. تحديث نظام اللينكس وتثبيت الأدوات الأساسية + Aria2
# -------------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    curl \
    wget \
    unzip \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    ca-certificates && \
    \
    # ⬇️ تنزيل نسخة Aria2 الخاصة باللينكس (Latest Linux Static Binary) ⬇️
    # دي النسخة الرسمية للينكس، سريعة ومستقرة جداً
    wget -N https://github.com/q3aql/aria2-static-builds/releases/download/v1.36.0/aria2-1.36.0-linux-gnu-64bit-build1.tar.bz2 && \
    tar -xjvf aria2-1.36.0-linux-gnu-64bit-build1.tar.bz2 && \
    cp aria2-1.36.0-linux-gnu-64bit-build1/aria2c /usr/bin/aria2c && \
    chmod +x /usr/bin/aria2c && \
    rm -rf aria2-1.36.0-linux-gnu-64bit-build1* && \
    \
    # ⚡ إعداد ملف الكونفيج للينكس (Linux Config Injection) ⚡
    mkdir -p /root/.aria2 && \
    echo "max-connection-per-server=128" > /root/.aria2/aria2.conf && \
    echo "split=128" >> /root/.aria2/aria2.conf && \
    echo "min-split-size=1M" >> /root/.aria2/aria2.conf && \
    echo "disk-cache=512M" >> /root/.aria2/aria2.conf && \
    echo "file-allocation=none" >> /root/.aria2/aria2.conf && \
    echo "continue=true" >> /root/.aria2/aria2.conf && \
    echo "optimize-concurrent-downloads=true" >> /root/.aria2/aria2.conf && \
    \
    # تثبيت Deno (لو محتاجه)
    curl -fsSL https://deno.land/install.sh | sh && \
    ln -s /root/.deno/bin/deno /usr/local/bin/deno && \
    \
    # تنظيف مخلفات اللينكس لتقليل الحجم
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# -------------------------------------------------------------
# 2. تجهيز البايثون والمكتبات
# -------------------------------------------------------------
COPY pytgcalls /app/pytgcalls
COPY requirements.txt /app/requirements.txt

# استخدام النسخة المحلية من pytgcalls
RUN if [ -f /app/requirements.txt ]; then \
      grep -v -i '^py-tgcalls' /app/requirements.txt > /app/filtered-requirements.txt || true; \
    fi

# تثبيت المكتبات وتحديد uvloop
RUN pip install --upgrade pip setuptools wheel && \
    # ✅ تثبيت uvloop 0.21.0 المخصص للينكس
    pip install uvloop==0.21.0 && \
    if [ -f /app/filtered-requirements.txt ]; then pip install --no-cache-dir -r /app/filtered-requirements.txt; fi

# -------------------------------------------------------------
# 3. نسخ ملفات البوت والتشغيل
# -------------------------------------------------------------
COPY . /app

# تأكيد التشغيل
RUN python - <<'PY'
import sys, platform
print(f"✅ Running on Linux: {platform.system()} {platform.release()}")
PY

CMD ["python3", "runner.py"]
