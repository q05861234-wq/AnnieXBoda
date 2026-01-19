# Python 3.12 معتمدة على نسخة pytgcalls المحلية
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# تنظيف أي ملفات قديمة
RUN rm -rf /app/*

# تثبيت المتطلبات النظامية + deno
RUN apt-get update && \
    apt-get install -y --no-install-recommends git ffmpeg curl unzip build-essential && \
    rm -rf /var/lib/apt/lists/* && \
    curl -fsSL https://deno.land/install.sh | sh && \
    ln -s /root/.deno/bin/deno /usr/local/bin/deno

# نسخ مكتبة pytgcalls المحلية أولاً (عشان تضمن عدم التعارض)
COPY pytgcalls /app/pytgcalls

# نسخ requirements.txt مع حذف py-tgcalls منه عشان ميحملش من النت
COPY requirements.txt /app/requirements.txt
RUN if [ -f /app/requirements.txt ]; then \
      grep -v -i '^py-tgcalls' /app/requirements.txt > /app/filtered-requirements.txt || true; \
    fi

# تثبيت المكتبات (بما فيها psutil و uvloop لو موجودين في الملف)
RUN pip install --upgrade pip setuptools wheel && \
    if [ -f /app/filtered-requirements.txt ]; then pip install --no-cache-dir -r /app/filtered-requirements.txt; fi

# نسخ باقي ملفات البوت (بما فيها runner.py)
COPY . /app

# تأكيد ان Python بيستخدم النسخة المحلية
RUN python - <<'PY'
import pytgcalls, sys
print('PYTGCALLS_FROM=', getattr(pytgcalls,'__file__','<not found>'))
PY

# التشغيل عن طريق ملف الرونر الجديد
CMD ["python3", "runner.py"]
