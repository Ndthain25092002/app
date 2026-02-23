"""
agents/field_config.py
Cấu hình chi tiết cho các trường dữ liệu, enum values, và kiểu dữ liệu
"""

# Các trường enum (cần exact match, không regex)
ENUM_FIELDS = {
    "participation_type": {
        "values": ["Khách chính", "Khách phụ", "Tham gia kèm theo"],
        "description": "Loại tham gia"
    },
    "customer_type": {
        "values": ["Khách hàng mới", "Khách hàng cũ", "Học bảo lưu", "Học viên bảo lưu", "Sách"],
        "description": "Loại khách hàng"
    },
    "status": {
        "values": ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8 - Đã thanh toán", "Đã hủy", "Pending"],
        "description": "Trạng thái CRM"
    },
    "contract_source": {
        "values": ["chat_bot", "conversion ads", "data kho", "data mkt cũ", "email marketing", "fanpage", "fanpage - dktv", "fanpage-ads", "fanpage-seeding", "hotline", "học bảo lưu", "học viên cũ", "học viên ws", "khách hàng cũ", "khách hàng giới thiệu", "kols - mkt", "kols - sales", "link doc", "livestream", "marketing tự tìm kiếm", "nguồn tự nhiên", "nhân sự bm", "nhân sự công ty giới thiệu", "sale tự tìm kiếm", "seminar mkt", "seminar sale", "sếp dũng", "test thêm mới nguồn", "thành viên bm", "tiktok", "vãng lai", "vé tặng", "website", "zalo công ty"],
        "description": "Nguồn hợp đồng"
    },
    "contact_source": {
        "values": ["chat_bot", "conversion ads", "data kho", "data mkt cũ", "email marketing", "fanpage", "fanpage - dktv", "fanpage-ads", "fanpage-seeding", "hotline", "học bảo lưu", "học viên cũ", "học viên ws", "khách hàng cũ", "khách hàng giới thiệu", "kols - mkt", "kols - sales", "link doc", "livestream", "marketing tự tìm kiếm", "nguồn tự nhiên", "nhân sự bm", "nhân sự công ty giới thiệu", "sale tự tìm kiếm", "seminar mkt", "seminar sale", "sếp dũng", "test thêm mới nguồn", "thành viên bm", "tiktok", "vãng lai", "vé tặng", "website", "zalo công ty"],
        "description": "Nguồn liên hệ"
    },
    "paid": {
        "description": "Trạng thái thanh toán - xử lý như text thường (regex)"
    }
}

# Các trường kiểu số (không nên dùng regex)
NUMERIC_FIELDS = {
    "care_count": {"type": "integer", "description": "Số lần chăm sóc"},
}

# Các trường kiểu ngày (có thể so sánh ngày)
DATE_FIELDS = {
    "next_care_date": {"type": "date", "description": "Ngày chăm sóc tiếp theo"},
    "created_at": {"type": "date", "description": "Ngày tạo"}
}

# Các trường kiểu text với regex
TEXT_FIELDS = {
    "full_name": {"type": "text", "description": "Tên đầy đủ khách hàng"},
    "phone": {"type": "phone", "description": "Số điện thoại", "normalize": True},
    "email": {"type": "text", "description": "Địa chỉ email"},
    "company": {"type": "text", "description": "Tên công ty"},
    "website": {"type": "text", "description": "Website"},
    "industry": {"type": "text", "description": "Lĩnh vực hoạt động"},
    "company_size": {"type": "text", "description": "Quy mô công ty"},
    "position": {"type": "text", "description": "Chức vụ"},
    "need_support_field": {"type": "text", "description": "Lĩnh vực cần hỗ trợ"},
    "pain_points": {"type": "text", "description": "Vấn đề khó khăn"},
    "expectation": {"type": "text", "description": "Mong muốn"},
    "care_history": {"type": "text", "description": "Lịch sử chăm sóc"},
    "course": {"type": "text", "description": "Khóa học đã tham gia"},
    "contract_owner": {"type": "text", "description": "Chủ hợp đồng/CSKH"},
    "contact_owner": {"type": "text", "description": "Chủ liên hệ/Lead"},
    "first_owner": {"type": "text", "description": "Chủ sở hữu đầu tiên"},
    "contract_source": {"type": "text", "description": "Nguồn hợp đồng"},
    "contact_source": {"type": "text", "description": "Nguồn liên hệ"},
    "paid_amount": {"type": "text", "description": "Số tiền đã thanh toán"},
    "invoice": {"type": "text", "description": "Hóa đơn"},
    "ticket_number": {"type": "text", "description": "Số vé"},
    "ticket_type": {"type": "text", "description": "Loại vé"},
    "note": {"type": "text", "description": "Ghi chú"},
    "address": {"type": "text", "description": "Địa chỉ"},
    "registration_url": {"type": "text", "description": "URL đăng ký"},
    "contract_id": {"type": "text", "description": "ID hợp đồng"},
    "status_color": {"type": "text", "description": "Màu trạng thái"},
    "checkin_time": {"type": "text", "description": "Thời gian check-in"}
}

# Tất cả các trường có thể tìm kiếm với regex (full-text search)
SEARCHABLE_TEXT_FIELDS = list(TEXT_FIELDS.keys())

# Tất cả các trường có thể lọc
FILTERABLE_FIELDS = {
    **{k: "enum" for k in ENUM_FIELDS.keys()},
    **{k: "numeric" for k in NUMERIC_FIELDS.keys()},
    **{k: "date" for k in DATE_FIELDS.keys()},
    **{k: "text" for k in TEXT_FIELDS.keys()}
}

# Hàm để kiểm tra loại trường
def get_field_type(field_name: str) -> str:
    """Xác định loại trường"""
    if field_name in ENUM_FIELDS:
        return "enum"
    if field_name in NUMERIC_FIELDS:
        return "numeric"
    if field_name in DATE_FIELDS:
        return "date"
    if field_name in TEXT_FIELDS:
        return "text"
    return "unknown"

def is_enum_field(field_name: str) -> bool:
    """Kiểm tra xem trường có phải enum không"""
    return field_name in ENUM_FIELDS

def is_numeric_field(field_name: str) -> bool:
    """Kiểm tra xem trường có phải số không"""
    return field_name in NUMERIC_FIELDS

def is_date_field(field_name: str) -> bool:
    """Kiểm tra xem trường có phải ngày không"""
    return field_name in DATE_FIELDS

def is_text_field(field_name: str) -> bool:
    """Kiểm tra xem trường có phải text không"""
    return field_name in TEXT_FIELDS

def is_phone_field(field_name: str) -> bool:
    """Kiểm tra xem trường có phải phone không"""
    return field_name in TEXT_FIELDS and TEXT_FIELDS[field_name].get("type") == "phone"

def should_normalize_phone(field_name: str) -> bool:
    """Kiểm tra xem trường phone có nên chuẩn hóa không"""
    return is_phone_field(field_name) and TEXT_FIELDS[field_name].get("normalize", False)
