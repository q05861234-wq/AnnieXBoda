# 1. إجبار النظام يستخدم x86_64 (القوي)
FROM --platform=linux/amd64 python:3.12-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app
RUN rm -rf /app/*

# 2. تحديث وتثبيت (Aria2 الرسمي)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git ffmpeg curl build-essential libffi-dev libssl-dev zlib1g-dev aria2 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 3. Deno
RUN curl -fsSL https://deno.land/install.sh | sh && \
    ln -s /root/.deno/bin/deno /usr/local/bin/deno

# 4. المكتبات
COPY pytgcalls /app/pytgcalls
COPY requirements.txt /app/requirements.txt
RUN if [ -f /app/requirements.txt ]; then grep -v -i '^py-tgcalls' /app/requirements.txt > /app/filtered-requirements.txt || true; fi

RUN pip install --upgrade pip setuptools wheel && \
    pip install uvloop==0.21.0 && \
    if [ -f /app/filtered-requirements.txt ]; then pip install --no-cache-dir -r /app/filtered-requirements.txt; fi

# 5. الكود والإصلاحات
COPY . /app

# إصلاح خطأ buffer-size
RUN find /app -name "*.py" -print0 | xargs -0 sed -i 's/buffer-size/disk-cache/g'

# طباعة للتأكد إننا شغالين x86_64
RUN echo "Checking Architecture:" && uname -m

CMD ["python3", "runner.py"]
