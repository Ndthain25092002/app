import logging
import sys
import os
import asyncio

# --- IMPORT LOGIC CHẠY BOT ---
try:
    from telegram_openai_bot import main as run_telegram_bot
except ImportError:
    print("❌ LỖI: Không tìm thấy file 'telegram_openai_bot.py'.")
    sys.exit(1)

# --- IMPORT ĐỂ TỰ ĐỘNG BUILD VECTORSTORE ---
from agents.qdrant_agent import build_qdrant_index as build_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")

def check_and_build_index():
    """Ensure vectorstore is ready (Qdrant)."""
    try:
        build_index()
        print("\n✅ Qdrant collection ready. Sẵn sàng khởi động Bot.\n")
    except Exception as e:
        logger.error(f"❌ Lỗi khi tạo/kiểm tra Qdrant index: {e}")
        sys.exit(1)

def main():
    print("\n" + "█"*60)
    print("   🚀 HỆ THỐNG AI AGENT (SERVER MODE)")
    print("█"*60 + "\n")

    # 1. Kiểm tra và Build dữ liệu trước khi chạy Bot
    check_and_build_index()

    # 2. Chạy Bot
    print("🤖 Đang khởi động Telegram Bot...")
    try:
        run_telegram_bot()
    except KeyboardInterrupt:
        logger.info("👋 Đã nhận lệnh dừng (Ctrl+C).")
    except Exception as e:
        logger.exception(f"❌ Lỗi nghiêm trọng: {e}")

if __name__ == "__main__":
    main()  