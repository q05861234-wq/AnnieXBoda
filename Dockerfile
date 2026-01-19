# استخدام Python 3.12 على Debian Bookworm (المستقر)
FROM python:3.12-bookworm

# إعدادات البيئة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# تنظيف أي ملفات قديمة
RUN rm -rf /app/*

# -------------------------------------------------------------
# 1. تثبيت النظام والأدوات (بما فيهم aria2 الرسمي)
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
    # 👇 هنا الخلاصة: بنقول للنظام نزل أنت aria2 بمعرفتك
    aria2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------------------
# 2. تثبيت Deno (ضروري لتشغيل يوتيوب)
# -------------------------------------------------------------
RUN curl -fsSL https://deno.land/install.sh | sh && \
    ln -s /root/.deno/bin/deno /usr/local/bin/deno

# -------------------------------------------------------------
# 3. تثبيت المكتبات
# -------------------------------------------------------------
COPY pytgcalls /app/pytgcalls
COPY requirements.txt /app/requirements.txt

# منع تعارض pytgcalls
RUN if [ -f /app/requirements.txt ]; then \
      grep -v -i '^py-tgcalls' /app/requirements.txt > /app/filtered-requirements.txt || true; \
    fi

# التثبيت
RUN pip install --upgrade pip setuptools wheel && \
    pip install uvloop==0.21.0 && \
    if [ -f /app/filtered-requirements.txt ]; then pip install --no-cache-dir -r /app/filtered-requirements.txt; fi

# -------------------------------------------------------------
# 4. التشغيل
# -------------------------------------------------------------
COPY . /app

CMD ["python3", "runner.py"]
