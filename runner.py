import asyncio

try:
    import uvloop
    uvloop.install()
    print("🚀 uvloop activated successfully")
except Exception as e:
    print("⚠️ uvloop not available:", e)

# بعد تفعيل uvloop استورد باقي المشروع
from AnnieXMedia import app   # عدل المسار حسب اسم مشروعك

if __name__ == "__main__":
    app.run()
