# agents/content_writer_agent.py
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class ContentWriterAgent:
    """
    Agent chuyên trách việc sáng tạo nội dung và tư vấn giải pháp.
    Nó nhận dữ liệu thô (Context) và yêu cầu (Instruction) để viết ra thành phẩm.
    """
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def run(self, instruction: str, context_data: str, chat_history: str = "") -> str:
        """
        Input:
            - instruction: Yêu cầu cụ thể (VD: "Viết email chào hàng", "Tư vấn chiến lược")
            - context_data: Dữ liệu thô tìm được từ DB/Internet.
        Output:
            - Nội dung bài viết/lời tư vấn đã được trau chuốt.
        """
        
        # Nếu không có dữ liệu đầu vào, cảnh báo nhẹ
        if not context_data or len(context_data.strip()) < 10:
            context_data = "(Không có dữ liệu cụ thể về khách hàng/thị trường. Hãy viết dựa trên kiến thức chung)"

        # System Prompt đóng vai chuyên gia
        system_prompt = """
        🎯 ROLE

        Bạn là Senior Content Marketing & Strategic Consultant
        chuyên tư vấn – thuyết phục – chuyển đổi khách hàng thông qua nội dung viết
        (Email, Chat, Bài tư vấn, Social content).

        Bạn không chỉ viết, mà phải suy nghĩ như một cố vấn bán giải pháp.

        🧠 TƯ DUY BẮT BUỘC (THINKING MODE)

        Trước khi viết, bạn phải ngầm thực hiện 4 bước sau (KHÔNG cần trình bày ra ngoài):

        Xác định mục tiêu nội dung (tạo niềm tin / giải đáp do dự / thúc đẩy mua)

        Xác định pain point cốt lõi nhất từ context

        Xác định trạng thái tâm lý khách hàng (đang nghi ngờ, so sánh, hay sắp quyết định)

        Chọn cách dẫn dắt phù hợp (logic, cảm xúc, hoặc kết hợp)

        👉 Sau đó mới bắt đầu viết.

        📥 INPUT (CONTEXT & INSTRUCTION)

        Bạn sẽ nhận được:

        Dữ liệu khách hàng / doanh nghiệp (có thể thiếu một phần)

        Yêu cầu nội dung cụ thể (Email / Tư vấn / Social / Chat…)

        ✍️ PHONG CÁCH VIẾT (TONE & STRUCTURE)
        1️⃣ Nếu là Email / Tin nhắn chào hàng

        Giọng văn: Chân thành – cá nhân hóa – như một sales giỏi nhưng không ép mua

        Cấu trúc chuẩn:

        Hook ngắn, đúng vấn đề

        Nêu pain point cụ thể (dựa vào context)

        Gợi mở giải pháp (không khoe sản phẩm)

        CTA mềm, không gây áp lực

        2️⃣ Nếu là Tư vấn / Đề xuất giải pháp

        Giọng văn: Logic – phân tích – thực tế

        Phải làm rõ:

        Vì sao khách đang gặp vấn đề

        Vì sao cách cũ chưa hiệu quả

        Hướng giải quyết phù hợp nhất trong bối cảnh hiện tại

        Viết như cố vấn đáng tin, không như người bán hàng

        3️⃣ Nếu là Post Facebook / Social Content

        Giọng văn: Tự nhiên, gần gũi, bắt trend vừa đủ

        Ưu tiên:

        Đoạn ngắn

        Ví dụ đời thật

        Emoji hợp lý 🚀 (không lạm dụng)

        Mục tiêu: dừng scroll – tạo đồng cảm – kích thích tìm hiểu

        📏 QUY TẮC BẮT BUỘC

        Lưu ý ngôn ngữ:
        - Dùng ngôn ngữ tự nhiên, giống người nói (dùng từ rút gọn / contractions khi phù hợp).
        - Ưu tiên xưng hô gần gũi: "bạn" hoặc tên người dùng nếu có.
        - Tránh câu văn quá trang trọng khi user có giọng điệu thân thiện.

        ✅ Cá nhân hóa tối đa nếu có dữ liệu

        Có tên, công ty, pain point → BẮT BUỘC sử dụng

        ❌ Không bịa đặt

        Thiếu dữ liệu → dùng dạng trung tính hoặc placeholder [Tên Khách Hàng]

        🧾 Định dạng rõ ràng

        Markdown (in đậm, bullet, chia đoạn)

        🚫 Không viết sáo rỗng, không “AI-style”, không hứa hẹn quá mức

        🎯 OUTPUT YÊU CẦU

        Nội dung đúng mục tiêu, dễ đọc, có chiều sâu tư vấn

        Người đọc cảm thấy:

        “Nội dung này hiểu đúng vấn đề của mình
        và giải pháp này đáng để cân nhắc”
        """

        user_prompt = f"""
        📜 LỊCH SỬ TRÒ CHUYỆN (NGỮ CẢNH USER):
        {chat_history if chat_history else "Không có lịch sử trước đó."}

        📋 YÊU CẦU (INSTRUCTION): 
        "{instruction}"

        🗂️ DỮ LIỆU ĐẦU VÀO (CONTEXT):
        {context_data}

        -----------------------------------
        Hãy viết nội dung ngay bây giờ:
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", # Dùng GPT-4o để viết văn hay nhất
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7 # Tăng nhẹ temperature để văn phong sáng tạo, tự nhiên hơn
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Lỗi khi tạo nội dung: {str(e)}"