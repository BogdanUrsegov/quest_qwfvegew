import asyncio
import logging
import os
# from bot.scheduler.scheduler import scheduler

from bot.database.session import init_db

from .create_bot import bot, ADMIN_ID, dp

# === Настройки ===
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")
HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
PORT = int(os.getenv("WEBHOOK_PORT", "8000"))
IS_POLLING = os.getenv("IS_POLLING", "1").strip().lower() in ("1", "true", "yes", "on")

# === Логгирование ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()


async def run_polling():
    await init_db()
    logger.info("✅ Database initialized")
    # scheduler.start()
    logger.info("✅ Scheduler started")
    await bot.send_message(ADMIN_ID, "✅ Bot started")
    await dp.start_polling(bot)

# === 5. Entry point ===
if __name__ == "__main__":
    try:
        asyncio.run(run_polling())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Shutdown signal received")