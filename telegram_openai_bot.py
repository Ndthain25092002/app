import telegram
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import os
import uuid
import logging 
import sys
import time
import sqlite3
import asyncio
from dotenv import load_dotenv

# Import Scheduler
from scheduler.scheduler_agent import AgentScheduler

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    print("❌ LỖI: Thiếu TELEGRAM_BOT_TOKEN trong .env")
    sys.exit(1)

# Cấu hình Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- KHỞI TẠO SCHEDULER ---
print("🔄 Đang khởi động Agent Scheduler...")
agent_scheduler = AgentScheduler()
print("✅ Agent Scheduler đã sẵn sàng!")

# --- TẠO FOLDER LƯU FILE ---
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# ======================================================
# 1. DATABASE SQLITE (LƯU LỊCH SỬ CHAT)
# ======================================================
conn = sqlite3.connect("conversation.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    role TEXT,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

def save_message(chat_id, role, content):
    """Lưu tin nhắn vào DB"""
    try:
        cursor.execute("INSERT INTO history (chat_id, role, content) VALUES (?, ?, ?)",
                       (chat_id, role, content))
        conn.commit()
    except Exception as e:
        logging.error(f"Lỗi lưu DB: {e}")

def get_chat_history_string(chat_id, limit=6):
    """
    Lấy lịch sử gần nhất và format thành chuỗi text để đưa vào Prompt.
    Format:
    User: ...
    AI: ...
    """
    try:
        cursor.execute("""
            SELECT role, content FROM history 
            WHERE chat_id=? 
            ORDER BY id DESC 
            LIMIT ?
        """, (chat_id, limit))
        
        rows = cursor.fetchall()[::-1] # Đảo ngược lại để đúng thứ tự thời gian
        
        history_str = ""
        for role, content in rows:
            role_name = "User" if role == "user" else "AI"
            history_str += f"{role_name}: {content}\n"
            
        return history_str
    except Exception as e:
        logging.error(f"Lỗi lấy lịch sử: {e}")
        return ""

# ======================================================
# 2. XỬ LÝ TIN NHẮN (HANDLER)
# ======================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    user_msg = ""
    file_path_info = "" # Chuỗi thông tin file để nhét vào prompt

    # --- A. XỬ LÝ FILE (DOCUMENT) ---
    if update.message.document:
        doc = update.message.document
        original_name = doc.file_name
        
        # Chỉ nhận PDF/Excel
        if original_name.lower().endswith(('.pdf', '.xlsx', '.xls', '.csv')):
            waiting_msg = await update.message.reply_text("📥 Đang tải tài liệu về server...")
            
            try:
                new_file = await doc.get_file()
                
                # Tạo tên file duy nhất tránh trùng lặp
                unique_name = f"{uuid.uuid4()}_{original_name}"
                save_path = os.path.join(DOWNLOAD_DIR, unique_name)
                
                # Tải về ổ cứng
                await new_file.download_to_drive(save_path)
                
                # Quan trọng: Tạo chuỗi thông tin hệ thống để báo cho AI biết file ở đâu
                # Đường dẫn này cần được chuẩn hóa (dùng / thay vì \) để Python dễ đọc
                clean_path = save_path.replace("\\", "/")
                file_path_info = f"\n\n[SYSTEM INFO]: Người dùng đã upload file. Đường dẫn cục bộ: {clean_path}"
                
                await context.bot.delete_message(chat_id=chat_id, message_id=waiting_msg.message_id)
                print(f"✅ Đã lưu file: {clean_path}")
                
            except Exception as e:
                await update.message.reply_text(f"❌ Lỗi tải file: {e}")
                return
        
        # Lấy caption làm nội dung câu hỏi
        user_msg = update.message.caption if update.message.caption else "Hãy phân tích file tài liệu này."

    # --- B. XỬ LÝ TEXT THƯỜNG ---
    elif update.message.text:
        user_msg = update.message.text

    if not user_msg: return

    # Check mention trong Group
    bot = await context.bot.get_me()
    if update.message.chat.type in ['group', 'supergroup']:
        if update.message.text and f"@{bot.username}" not in update.message.text:
             if not update.message.document: return
        user_msg = user_msg.replace(f"@{bot.username}", "").strip()

    print(f"📩 ChatID {chat_id}: {user_msg}")
    status_msg = await update.message.reply_text("🕵️‍♂️ _Agent đang khởi động..._", parse_mode='Markdown')

    # --- HÀM CALLBACK CẬP NHẬT TRẠNG THÁI ---  
    async def status_callback(step_name: str, details: str = ""):
        try:
            # 1. Escape các ký tự đặc biệt của Markdown để tránh lỗi
            # (Thay thế _ thành \_, * thành \*)
            safe_step = step_name.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
            safe_details = details.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
            
            new_text = f"🕵️‍♂️ **TRẠNG THÁI XỬ LÝ:**\n\n✅ {safe_step}\n_{safe_details}_"
            
            if status_msg.text != new_text:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=new_text,
                    parse_mode='Markdown' # Vẫn giữ Markdown để in đậm tiêu đề
                )
        except Exception as e:
            print(f"⚠️ Lỗi update status (Bỏ qua): {e}")

    # Gửi Typing...
    await context.bot.send_chat_action(chat_id=chat_id, action=telegram.constants.ChatAction.TYPING)
    
    # --- C. GỌI AGENT VỚI LỊCH SỬ ---
    start_time = time.time()
    
    try:
        # 1. Lấy lịch sử cũ từ DB
        history_str = get_chat_history_string(chat_id, limit=6)

        # 2. Ghép thông tin file (nếu có) vào câu hỏi hiện tại
        # Đây là bước quyết định: AI sẽ nhìn thấy đường dẫn file trong user_input
        full_input_context = user_msg + file_path_info

        # 3. Gọi Agent Scheduler
        # --- TRUYỀN CALLBACK VÀO SCHEDULER ---
        response_text = await agent_scheduler.process_request(
            user_query=full_input_context, 
            chat_history=history_str,
            status_callback=status_callback # <--- THAM SỐ MỚI
        )
        
    except Exception as e:
        response_text = f"🚨 Lỗi hệ thống: {str(e)}"
        logging.error(f"Error: {e}", exc_info=True)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
    except: pass

    # --- D. LƯU VÀO DB VÀ TRẢ LỜI ---
    
    # Lưu vào DB: Lưu câu hỏi gốc + thông tin file (để lần sau AI nhớ là đã có file này)
    save_message(chat_id, "user", full_input_context)
    save_message(chat_id, "assistant", response_text)

    # Gửi tin nhắn trả lời (Chia nhỏ nếu quá dài)
    try:
        if len(response_text) > 4000:
            for x in range(0, len(response_text), 4000):
                chunk = response_text[x:x+4000]
                try:
                    await update.message.reply_text(chunk, parse_mode='Markdown')
                except:
                    await update.message.reply_text(chunk) # Fallback text thường
        else:
            try:
                await update.message.reply_text(response_text, parse_mode='Markdown')
            except Exception:
                await update.message.reply_text(response_text)
            
    except Exception as e:
        logging.error(f"Lỗi gửi tin Telegram: {e}")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Lắng nghe cả TEXT và DOCUMENT
    app.add_handler(MessageHandler((filters.TEXT | filters.Document.ALL) & ~filters.COMMAND, handle_message))
    
    print("\n🚀 TELEGRAM AGENT BOT ĐANG CHẠY...")
    app.run_polling()

if __name__ == "__main__":
    main()