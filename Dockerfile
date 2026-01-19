# استخدام Python 3.12 على Debian Bookworm (المستقر وقوي جداً)
FROM python:3.12-bookworm

# إعدادات البيئة لتحسين الأداء
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# تنظيف أي ملفات قديمة لضمان بداية نظيفة
RUN rm -rf /app/*

# -------------------------------------------------------------
# 1. تحديث النظام وتثبيت الأدوات (بما فيهم aria2 الرسمي)
# -------------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    curl \
    build-essential \
    libffi-dev \
    libssl-dev \
    zlib1g-dev \
    # 👇 تثبيت aria2 الرسمي من مخازن ديبيان (أضمن وأسرع)
    aria2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------------------
# 2. تثبيت Deno (ضروري لتشغيل يوتيوب بسرعة عالية)
# -------------------------------------------------------------
RUN curl -fsSL https://deno.land/install.sh | sh && \
    ln -s /root/.deno/bin/deno /usr/local/bin/deno

# -------------------------------------------------------------
# 3. تجهيز المكتبات
# -------------------------------------------------------------
COPY pytgcalls /app/pytgcalls
COPY requirements.txt /app/requirements.txt

# تنظيف requirements لمنع تعارض pytgcalls
RUN if [ -f /app/requirements.txt ]; then \
      grep -v -i '^py-tgcalls' /app/requirements.txt > /app/filtered-requirements.txt || true; \
    fi

# التثبيت (تفعيل Turbo Mode للبايثون باستخدام uvloop)
RUN pip install --upgrade pip setuptools wheel && \
    pip install uvloop==0.21.0 && \
    if [ -f /app/filtered-requirements.txt ]; then pip install --no-cache-dir -r /app/filtered-requirements.txt; fi

# -------------------------------------------------------------
# 4. نسخ ملفات البوت + 🛠️ إصلاح خطأ ARIA2 🛠️
# -------------------------------------------------------------
COPY . /app

# 👇👇 ده السطر السحري الجديد 👇👇
# بيبحث في كل ملفات البايثون ويصلح الأمر الغلط (buffer-size) ويخليه (disk-cache)
RUN find /app -name "*.py" -print0 | xargs -0 sed -i 's/buffer-size/disk-cache/g'

# التشغيل
CMD ["python3", "runner.py"]
