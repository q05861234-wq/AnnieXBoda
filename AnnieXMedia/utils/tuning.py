# Authored By Certified Coders © 2025
import asyncio
import os

# استخدام كل الكورات المتاحة
CPU = os.cpu_count() or 4

# زيادة عدد التحميلات المتزامنة
MAX_CONCURRENT = min(64, CPU * 8)

# تكبير حجم الكاش لـ 1 ميجا (كان 128 كيلو بس)
# ده بيقلل الضغط على الهارد ويسرع التحميل
CHUNK_SIZE = 1024 * 1024 

YTDLP_TIMEOUT = 300
YOUTUBE_META_TTL = 600
YOUTUBE_META_MAX = 2048
SEM = asyncio.Semaphore(MAX_CONCURRENT)
