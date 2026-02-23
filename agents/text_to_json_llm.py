import json
import re
import logging
from string import Template
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load env & client
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Optional model selector
try:
    from agents.model_selector import choose_model
except Exception:
    choose_model = None

# Logger setup (có thể cấu hình theo môi trường)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("text2query")

# Template an toàn: dùng string.Template để tránh vấn đề với {}
PROMPT_TEMPLATE = Template(
    """
Bạn là một **Text-to-Query Generator**.
Nhiệm vụ của bạn là chuyển đổi các yêu cầu ngôn ngữ tự nhiên bằng tiếng Việt thành một đối tượng JSON truy vấn có cấu trúc, tuân thủ nghiêm ngặt theo SPECIFICATION và RULES.

--- SPECIFICATION (Schema & Fields) ---

**Entity: "customer" (Mặc định)**
* **Fields:**
    * full_name: Tên đầy đủ khách hàng (string)
    * phone: Số điện thoại (string)
    * email: Địa chỉ email (string)
    * company: Tên công ty (string)
    * industry: Lĩnh vực hoạt động (string)
    * company_size: Quy mô công ty (string)
    * position: Chức vụ (string)
    * need_support_field: Lĩnh vực cần hỗ trợ (string)
    * pain_points: Vấn đề khó khăn (string)
    * next_care_date: Ngày chăm sóc tiếp theo (string, ngày tháng)
    * care_count: Số lần chăm sóc (integer)
    * course: Khóa học đã tham gia (string)
    * contract_owner: Chủ hợp đồng/CSKH (string)
    * contact_owner: Chủ liên hệ/Lead (string)
    * status: Trạng thái CRM (string)
    * customer_type: Loại khách hàng (string: "Khách hàng mới", "Khách hàng cũ")
    * paid: Trạng thái thanh toán (string)
    * paid_amount: Tổng số tiền đã thanh toán (string)
    * participation_type: Loại tham gia (string: "Khách chính", "Khách phụ")

--- RULES ---
1.  **Đầu ra bắt buộc là JSON**: CHỈ xuất ra đối tượng JSON, không có bất kỳ giải thích, văn bản, hoặc chú thích nào khác.
2.  **Sử dụng tên trường chính xác**: Dùng chính xác tên trường được liệt kê trong SPECIFICATION.
3.  **Mặc định**: `entity` luôn là "customer".

4.  **Phát hiện Ý định (Intent Detection)**:
    * **SĐT**: Nếu chứa 10 chữ số $\rightarrow$ thêm vào `filters.phone`.
    * **Tên riêng**: Nếu chứa tên riêng $\rightarrow$ thêm vào `filters.full_name`. (Giả định tìm kiếm mờ/gần đúng).
    * **Nguồn**: "chat_bot", "conversion ads", "data kho", "data mkt cũ", "email marketing", "fanpage", "fanpage - dktv", "fanpage-ads", "fanpage-seeding", "hotline", "học bảo lưu", "học viên cũ", "học viên ws", "khách hàng cũ", "khách hàng giới thiệu", "kols - mkt", "kols - sales", "link doc", "livestream", "marketing tự tìm kiếm", "nguồn tự nhiên", "nhân sự bm", "nhân sự công ty giới thiệu", "sale tự tìm kiếm", "seminar mkt", "seminar sale", "sếp dũng", "test thêm mới nguồn", "thành viên bm", "tiktok", "vãng lai", "vé tặng", "website", "zalo công ty"
 $\rightarrow$ thêm vào `filters.contract_source`.
    * **Lĩnh vực**: "bảo hiểm", "bất động sản", "công nghiệp: điện", "công nghệ thông tin", "du lịch", "dược phẩm", "dịch vụ", "giáo dục", "hàng tiêu dùng", "khách sạn", "kinh doanh tmđt", "kinh doanh tự do", "kinh doanh: ô tô", "làm đẹp", "mẹ & bé", "mỹ phẩm", "nghệ thuật, giải trí", "nông nghiệp", "phòng khám", "salon tóc", "sản xuất", "thiết kế nội thất", "thẩm mỹ/spa", "thời trang", "thực phẩm và dịch vụ ăn uống", "trang sức", "truyền thông", "tài chính & ngân hàng", "vận chuyển", "xuất nhập khẩu", "xây dựng", "đào tạo", "đầu tư"
 $\rightarrow$ thêm vào `filters.industry`.
    * **Ngày tháng**: Ngày tháng cụ thể $\rightarrow$ thêm vào `filters.next_care_date` hoặc `filters.created_at`.

5.  **Ánh xạ Tiếng Việt (Mapping) - ƯU TIÊN CAO**:
    * "khách chính" hoặc "khách chính" → `filters.participation_type = "Khách chính"`
    * "khách phụ" → `filters.participation_type = "Khách phụ"`
    * "tham gia kèm theo" → `filters.participation_type = "Tham gia kèm theo"`
    * "khách hàng mới" → `filters.customer_type = "Khách hàng mới"`
    * "khách hàng cũ" hoặc "khách cũ" → `filters.customer_type = "Khách hàng cũ"`
    * "học bảo lưu" → `filters.customer_type = "Học bảo lưu"`
    * "học viên bảo lưu" → `filters.customer_type = "Học viên bảo lưu"`
    * "sách" → `filters.customer_type = "Sách"`
    * "thành viên bm" → có thể ánh xạ tới `filters.contract_source = "Thành viên BM"` hoặc `filters.contact_source = "Thành viên BM"`
    * Các nguồn khác: dùng chính xác tên từ danh sách nguồn được liệt kê ở trên
    
    **CHÍNH XÁC**: Giá trị phải khớp CHÍNH XÁC với database, KHÔNG biến tưởng hay thêm bớt chữ.

6.  **Semantic Search**:
    * RAG sẽ xử lý semantic search riêng biệt
    * LLM chỉ sinh structured filters, không cần `semantic_filters`
    * Nếu user search một keyword chung (không chỉ định trường cụ thể) → thêm vào `search_text`
    * `search_text` sẽ search trên TẤT CẢ các trường text: tên, công ty, email, ngành, vấn đề, v.v.

7.  **Auto-Fields (fields mặc định)**:
    * Nếu câu hỏi bắt đầu bằng: “khách nào”, “ai”, “những ai”… $\rightarrow$ tự động thêm: `fields: ["full_name", "phone", "company", "contract_owner", "industry", "course"]`.

8.  **COUNT Detection (Ưu tiên cao nhất)**:
    * Nếu câu hỏi chứa bất kỳ từ nào sau đây: ["bao nhiêu", "tổng số", "số lượng", "count", "bao nhiêu người", "có mấy", "có bao nhiêu"] $\rightarrow$ **BẮT BUỘC** sinh:
        * `"type": "count"`
        * **Cấm** sinh `fields` và `sort`.
        * Chỉ sinh `filters` và/hoặc `semantic_filters` (nếu không có filters có cấu trúc).

--- VÍ DỤ ---
**Ví dụ 1: Đếm khách chính**
Câu hỏi: "Có bao nhiêu khách chính?"
Kỳ vọng JSON:
{
  "entity": "customer",
  "type": "count",
  "filters": {"participation_type": "Khách chính"},
  "semantic_filters": [],
  "fields": [],
  "sort": {},
  "options": {"limit": null}
}

**Ví dụ 2: Liệt kê khách chính**
Câu hỏi: "Liệt kê khách chính"
Kỳ vọng JSON:
{
  "entity": "customer",
  "type": "find",
  "filters": {"participation_type": "Khách chính"},
  "semantic_filters": [],
  "fields": ["full_name", "phone", "company", "contract_owner"],
  "sort": {},
  "options": {"limit": 20}
}

**Ví dụ 3: Đếm khách hàng mới**
Câu hỏi: "Tổng số khách hàng mới?"
Kỳ vọng JSON:
{
  "entity": "customer",
  "type": "count",
  "filters": {"customer_type": "Khách hàng mới"},
  "search_text": "",
  "fields": [],
  "sort": {},
  "options": {"limit": null}
}

**Ví dụ 4: Tìm kiếm keyword trên tất cả trường**
Câu hỏi: "Tìm khách hàng liên quan tới 'thời trang'"
Kỳ vọng JSON:
{
  "entity": "customer",
  "type": "find",
  "filters": {},
  "search_text": "thời trang",
  "fields": ["full_name", "phone", "company", "industry", "pain_points"],
  "sort": {},
  "options": {"limit": 20}
}

--- OUTPUT FORMAT ---
Trả về **CHỈ** một JSON hợp lệ duy nhất, không văn bản, không chú thích, không markdown, không codeblock.
JSON mẫu phải tương tự cấu trúc (không cần semantic_filters):

{
  "entity": "string | null",
  "type": "string | null",
  "filters": "object",
  "search_text": "string (tìm kiếm trên tất cả text fields)",
  "fields": "array",
  "sort": "object",
  "options": {
    "limit": "number | null",
    "skip": "number | null"
  }
}

Nếu không thể xác định filters nào, trả về filters: {} và giữ cấu trúc mặc định.
Câu hỏi người dùng: $question
"""
)

# Whitelist keys and default schema
DEFAULT_OUTPUT = {
    "entity": "customer",
    "type": "find",
    "filters": {},
    "search_text": "",
    "fields": [],
    "sort": {},
    "options": {"limit": 20},
}

ALLOWED_TOP_LEVEL = set(DEFAULT_OUTPUT.keys())

def strip_code_blocks(text: str) -> str:
    """Loại bỏ fence markdown ```json ... ``` và các fence khác."""
    # Remove triple-backtick blocks
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```", "", text)
    # Remove inline backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()

def extract_json_blob(text: str) -> str:
    """
    Cố gắng extract JSON theo thứ tự ưu tiên:
    1) Nếu user model trả <json> ... </json>, dùng phần trong đó.
    2) Nếu có dấu ngoặc nhọn đầu và cuối, lấy substring từ first '{' tới last '}'.
    3) Trả nguyên text nếu không tìm được.
    """
    # 1) <json>...</json>
    m = re.search(r"<json>(.*?)</json>", text, re.S | re.I)
    if m:
        return m.group(1).strip()

    # 2) Find first { and last } and return content between
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        return text[first:last + 1]

    # fallback: return original (may fail parse)
    return text

def auto_detect_count(user_question: str, parsed_query: dict) -> dict:
    """
    Auto-detect COUNT queries nếu LLM miss
    Nếu câu hỏi chứa count keywords nhưng type không phải "count" → sửa thành count
    """
    count_keywords = ["bao nhiêu", "tổng số", "số lượng", "count", "bao nhiêu người", "có mấy", "có bao nhiêu"]
    
    # Check nếu user_question chứa bất kỳ count keyword nào
    question_lower = user_question.lower()
    is_count_query = any(keyword in question_lower for keyword in count_keywords)
    
    if is_count_query and parsed_query.get("type") != "count":
        logger.info(f"Auto-detecting COUNT query: {user_question[:100]}")
        parsed_query["type"] = "count"
        # Remove fields và sort vì COUNT không cần
        parsed_query.pop("fields", None)
        parsed_query.pop("sort", None)
    
    return parsed_query

def normalize_and_whitelist(obj: dict) -> dict:
    """
    Normalize output to DEFAULT_OUTPUT and whitelist keys.
    - Giữ các field hợp lệ, ghi đè default bằng values từ model khi hợp lệ.
    - Nếu model trả type="count", đảm bảo không có "fields" or "sort" (theo RULES).
    """
    out = DEFAULT_OUTPUT.copy()

    # Only keep allowed top-level keys
    for k, v in obj.items():
        if k in ALLOWED_TOP_LEVEL:
            out[k] = v

    # Enforce entity default always "customer" (rule 3)
    out["entity"] = "customer"

    # Enforce count rule: if type == count, remove fields and sort
    if isinstance(out.get("type"), str) and out["type"].lower() == "count":
        out["fields"] = []
        out["sort"] = {}

    # Options: ensure limit is integer and sensible
    try:
        limit = int(out.get("options", {}).get("limit", 20))
        if limit <= 0 or limit > 1000:
            limit = 20
    except Exception:       
        limit = 20
    out["options"] = {"limit": limit}

    # Ensure filters is a dict
    if not isinstance(out.get("filters"), dict):
        out["filters"] = {}

    # Ensure semantic_filters is a list
    if not isinstance(out.get("semantic_filters"), list):
        out["semantic_filters"] = []

    # Ensure fields is a list
    if not isinstance(out.get("fields"), list):
        out["fields"] = []

    # Ensure sort is a dict
    if not isinstance(out.get("sort"), dict):
        out["sort"] = {}

    return out

def parse_response_to_json(raw_text: str) -> dict:
    """Từ text thô -> cố gắng parse thành dict hợp lệ."""
    if raw_text is None:
        return None

    cleaned = strip_code_blocks(raw_text)
    json_candidate = extract_json_blob(cleaned)

    # Try json.loads directly
    try:
        parsed = json.loads(json_candidate)
        if isinstance(parsed, dict):
            return normalize_and_whitelist(parsed)
    except Exception as e:
        logger.debug("Direct json.loads failed: %s", e)
        # Try to salvage by removing trailing commas (common model error)
        try:
            # remove trailing commas before } or ]
            sanitized = re.sub(r",\s*(\}|])", r"\1", json_candidate)
            parsed = json.loads(sanitized)
            if isinstance(parsed, dict):
                return normalize_and_whitelist(parsed)
        except Exception as e2:

            
            logger.debug("Sanitized json.loads failed: %s", e2)

    # If still can't parse, log and return None
    logger.warning("Không parse được JSON từ output. Raw output head: %s", raw_text[:500])
    return None

def generate_query(user_question: str, model: str = "gpt-4o", max_tokens: int = 800, use_model_selector: bool = True):
    """
    Gọi OpenAI Responses API để tạo JSON truy vấn.
    Trả về dict đã normalize hoặc None nếu không parse được.
    """
    if not user_question or not user_question.strip():
        raise ValueError("user_question is required")

    # Build prompt safely
    prompt = PROMPT_TEMPLATE.safe_substitute(question=user_question.strip())

    # System message to enforce JSON-only
    system_msg = (
        "SYSTEM: Bạn chỉ được trả về một JSON hợp lệ duy nhất, không được thêm văn bản."
        " Nếu có thể, chỉ bắt đầu và kết thúc output bằng dấu ngoặc { }."
    )

    try:
        # If enabled, try to pick a model automatically using the selector
        chosen_model = model
        if use_model_selector and choose_model is not None:
            try:
                # Force GPT-4-family models only per user request
                chosen_model = choose_model(user_question, allowed_models=["gpt-4", "gpt-4o", "gpt-4o-mini"])
                logger.info(f"Model selector chose model: %s", chosen_model)
            except Exception:
                logger.exception("Model selector failed, falling back to provided model %s", model)

        response = client.responses.create(
            model=chosen_model,
            input=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_output_tokens=max_tokens,
        )
    except Exception as e:
        logger.exception("Gọi API thất bại: %s", e)
        return None

    # Extract text from response robustly
    raw_text = None
    try:
        # Preferred: .output_text if available
        if hasattr(response, "output_text"):
            raw_text = response.output_text
        else:
            # Fallback: try to collect textual parts
            parts = []
            if hasattr(response, "output") and isinstance(response.output, list):
                for item in response.output:
                    # each item may have 'content' list
                    if isinstance(item, dict):
                        if "content" in item and isinstance(item["content"], list):
                            for c in item["content"]:
                                if isinstance(c, dict) and c.get("type") == "output_text":
                                    parts.append(c.get("text", ""))
                        # Some SDK versions put 'text' directly
                        if item.get("type") == "output_text" and "text" in item:
                            parts.append(item["text"])
            raw_text = "\n".join(parts) if parts else str(response)
    except Exception as e:
        logger.exception("Không thể đọc response: %s", e)
        raw_text = str(response)

    # Parse to JSON
    parsed = parse_response_to_json(raw_text)

    if parsed is None:
        # As a last resort, try to ask the model to output JSON only (very rarely)
        logger.error("Failed to parse JSON from model output. Returning None. Raw output (truncated): %s", raw_text[:1000])
        return None

    # Auto-detect COUNT queries
    parsed = auto_detect_count(user_question, parsed)

    # Success
    return parsed
