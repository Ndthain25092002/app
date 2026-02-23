import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

ALLOWED_TOOLS = ["mongo_db_query", "vector_search", "tavily_search", "content_writer","pdf_reader","facebook_poster"]

class PlannerAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.tools_description = """
        === DATA SOURCES ===

        1) INTERNAL DATABASE
           Tools:
             • mongo_db_query → dùng khi cần dữ liệu chính xác (lọc, đếm, match field).
             • vector_search  → dùng khi tìm kiểu mơ tả, không nhớ chính xác (semantic search).


           Ví dụ mongo_db_query:
             - Tìm khách có số điện thoại X
             - Đếm số hợp đồng trạng thái “pending”
             - Lọc khách theo nguồn

           Ví dụ vector_search:
             - “khách nào đang quan tâm bảo hiểm nhân thọ?”
             - “những người hay phàn nàn về chi phí?”

        2) FILE PROCESSING - `pdf_reader` & `excel_reader`
           - Dữ liệu: File PDF, Excel người dùng upload.
           - Dấu hiệu: Câu hỏi chứa đường dẫn file (VD: "downloads/...") hoặc user nhắc đến "file vừa gửi".

        3) EXTERNAL KNOWLEDGE
           Tool:
             • tavily_search → tin tức, thị trường, kiến thức xã hội, vĩ mô, tử vi, thời tiết, giá vàng…

        4) CONTENT & SOCIAL MEDIA
           Tools:
             • content_writer → Viết nội dung, email, bài post.
             • facebook_poster → Dùng để ĐĂNG BÀI lên Fanpage Facebook.
               - INPUT: Nội dung bài viết cần đăng.
               - LƯU Ý: Thường được dùng SAU bước content_writer.


        =======================
        """

    def _base_prompt(self):
        return f"""
         Bạn là AI Planner thông minh.

        {self.tools_description}

        === QUY TẮC QUYẾT ĐỊNH (DECISION LOGIC) - BẮT BUỘC ===
        1. **Internal Data (Ưu tiên số 1)**:
           - Nếu người dùng hỏi: "Ai", "Khách nào", "Danh sách", "Bao nhiêu người", "Tìm người"...
           - HOẶC hỏi về nhu cầu/vấn đề của khách hàng (VD: "Ai cần Sale-Marketing?").
           -> **BẮT BUỘC dùng `mongo_db_query` hoặc `vector_search`**.
           -> ⛔ TUYỆT ĐỐI KHÔNG DÙNG `tavily_search`.

        2. **External Knowledge**:
           - Chỉ dùng `tavily_search` khi hỏi kiến thức chung (VD: "Cách làm marketing", "Giá vàng", "Thời tiết").
        
        3. **SOCIAL MEDIA**:
           - Nếu người dùng yêu cầu "Đăng bài", "Post bài" -> Bắt buộc phải có bước `facebook_poster`.
           - Nếu chưa có nội dung, phải lập kế hoạch: `content_writer` -> `facebook_poster`.


        === FORMAT BẮT BUỘC ===
        Chỉ xuất ra JSON dạng:
        [
          {{"step": 1, "tool": "...", "instruction": "..."}}
        ]

        ❗Không viết giải thích.
        ❗Không viết prose.
        ❗Không viết code block Markdown.
        ❗Không dùng ký tự lạ.

        === REASONING POLICY ===
        - Bạn được phép suy nghĩ nội bộ nhưng không được in ra.
        - Chỉ in JSON cuối cùng.

        === INTENT CLASSIFICATION ===
        Trước khi lập kế hoạch, hãy tự xác định (trong đầu):
        - internal_data
        - external_info
        - mixed
        - chit_chat

        Sau đó lập plan phù hợp.
        """

    def _fix_json(self, bad_json: str):
        """Nếu model trả JSON lỗi → dùng model tự sửa."""
        repair_prompt = f"""
        JSON sau bị lỗi, hãy sửa để thành JSON hợp lệ và giữ nguyên meaning:

        {bad_json}

        Chỉ trả JSON hợp lệ, không giải thích.
        """
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": repair_prompt}],
            temperature=0
        )
        txt = response.choices[0].message.content.strip()
        txt = re.sub(r"```(?:json)?", "", txt).replace("```", "").strip()
        return txt

    def _validate(self, plan):
        """Check kế hoạch có hợp lệ không."""
        if not isinstance(plan, list):
            return False
        for step in plan:
            if not all(k in step for k in ["step", "tool", "instruction"]):
                return False
            if step["tool"] not in ALLOWED_TOOLS:
                return False
        return True

    def create_plan(self, user_query: str, previous_feedback: str = None, chat_history: str = None) -> list:

        user_prompt = f"Câu hỏi: \"{user_query}\""
        if chat_history:
            user_prompt += f"\n\nNgữ cảnh:\n{chat_history}"
        if previous_feedback:
            user_prompt += f"\n\nFeedback lỗi trước: {previous_feedback}\nHãy điều chỉnh hướng tiếp cận."

        system_prompt = self._base_prompt()

        # Step 1: Request planning
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )

        content = response.choices[0].message.content.strip()
        content = re.sub(r"```(?:json)?", "", content).replace("```", "").strip()

        # Step 2: Parse JSON
        try:
            plan = json.loads(content)
        except:
            # Step 3: Tự sửa JSON
            fixed = self._fix_json(content)
            plan = json.loads(fixed)

        # Step 4: Validate
        if not self._validate(plan):
            # Nếu vẫn sai → fallback
            return [{"step": 1, "tool": "tavily_search", "instruction": user_query}]

        return plan
