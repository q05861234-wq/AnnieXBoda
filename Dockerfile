# استخدام النسخة الكاملة
FROM python:3.12

# تحسينات الأداء
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# إعدادات السرعة القصوى (تطبق تلقائياً)
ENV ARIA2_OPTS="--max-connection-per-server=128 --split=128 --min-split-size=1M --disk-cache=512M"

WORKDIR /app

# تنظيف
RUN rm -rf /app/*

# -------------------------------------------------------------
# 1. تثبيت النظام + Aria2 Static (بدون بناء)
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
    libssl-dev && \
    \
    # ⬇️ تنزيل نسخة Aria2 جاهزة (Static) ⬇️
    # دي أحدث نسخة مستقرة، بتدعم كل المميزات ومش محتاجة بناء
    wget -N https://github.com/q3aql/aria2-static-builds/releases/download/v1.36.0/aria2-1.36.0-linux-gnu-64bit-build1.tar.bz2 && \
    tar -xjvf aria2-1.36.0-linux-gnu-64bit-build1.tar.bz2 && \
    cp aria2-1.36.0-linux-gnu-64bit-build1/aria2c /usr/bin/aria2c && \
    chmod +x /usr/bin/aria2c && \
    rm -rf aria2-1.36.0-linux-gnu-64bit-build1* && \
    \
    # ⚡ حقن إعدادات السرعة (Turbo Config) ⚡
    mkdir -p /root/.aria2 && \
    echo "max-connection-per-server=128" > /root/.aria2/aria2.conf && \
    echo "split=128" >> /root/.aria2/aria2.conf && \
    echo "min-split-size=1M" >> /root/.aria2/aria2.conf && \
    echo "disk-cache=512M" >> /root/.aria2/aria2.conf && \
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
# 2. تجهيز مكتبات البايثون
# -------------------------------------------------------------
COPY pytgcalls /app/pytgcalls
COPY requirements.txt /app/requirements.txt

# فلترة المتطلبات لاستخدام pytgcalls المحلي
RUN if [ -f /app/requirements.txt ]; then \
      grep -v -i '^py-tgcalls' /app/requirements.txt > /app/filtered-requirements.txt || true; \
    fi

# تثبيت المكتبات + uvloop بالإصدار المحدد
RUN pip install --upgrade pip setuptools wheel && \
    # ✅ تثبيت النسخة المحددة
    pip install uvloop==0.21.0 && \
    if [ -f /app/filtered-requirements.txt ]; then pip install --no-cache-dir -r /app/filtered-requirements.txt; fi

# -------------------------------------------------------------
# 3. التشغيل
# -------------------------------------------------------------
COPY . /app

# اختبار سريع
RUN python - <<'PY'
import pytgcalls, sys
print('PYTGCALLS_FROM=', getattr(pytgcalls,'__file__','<not found>'))
PY

CMD ["python3", "runner.py"]
