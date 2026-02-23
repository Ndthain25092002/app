import re
from bson import ObjectId
from database.mongodb import db
# from config import ENTITY_TO_COLLECTION # Có thể bỏ nếu hardcode collection
from agents.field_config import (
    is_enum_field, is_numeric_field, is_date_field,
    is_phone_field, should_normalize_phone, TEXT_FIELDS, ENUM_FIELDS
)

# ============================
# HELPERS
# ============================

def normalize_phone(phone: str):
    if not isinstance(phone, str):
        phone = str(phone)
    return "".join([c for c in phone if c.isdigit()])

def build_filter(filters: dict):
    if not filters:
        return {}

    mongo = {}
    for k, v in filters.items():
        if v is None: continue

        # 1. PHONE
        if is_phone_field(k):
            digits = normalize_phone(v)
            mongo[k] = {"$regex": digits}
            continue

        # 2. ENUM FIELDS (SỬA: Dùng Regex neo đầu cuối để ignore case)
        # Giúp "Khách chính" khớp được "Khách Chính" hoặc "khách chính"
        if is_enum_field(k):
            if isinstance(v, str):
                mongo[k] = {"$regex": f"^{re.escape(v)}$", "$options": "i"}
            else:
                mongo[k] = v
            continue

        # 3. NUMERIC FIELDS
        if is_numeric_field(k):
            try:
                mongo[k] = int(v) if isinstance(v, str) else v
            except (ValueError, TypeError):
                mongo[k] = v
            continue

        # 4. DATE FIELDS
        if is_date_field(k):
            mongo[k] = v
            continue

        # 5. TEXT FIELDS (Mặc định chứa - contains)
        if isinstance(v, str):
            mongo[k] = {"$regex": re.escape(v), "$options": "i"}
        elif isinstance(v, list):
            mongo[k] = {"$in": v}
        else:
            mongo[k] = v

    return mongo

def build_semantic(semantic_filters: list):
    return {}

def build_full_text_search(search_text: str):
    if not search_text or not search_text.strip():
        return {}
    
    text_field_names = list(TEXT_FIELDS.keys())
    regex_pattern = {"$regex": search_text.strip(), "$options": "i"}
    
    or_conditions = [
        {field: regex_pattern}
        for field in text_field_names
    ]
    return {"$or": or_conditions}

def combine_filters(filters: dict, semantic: dict, full_text: dict = None):
    parts = []
    if filters: parts.append(filters)
    if full_text: parts.append(full_text)
    
    if len(parts) == 0: return {}
    elif len(parts) == 1: return parts[0]
    else: return {"$and": parts}

def projection_from_fields(fields: list):
    if not fields: return None
    return {f: 1 for f in fields}

# ============================
# MAIN
# ============================

def mongo_find(query_json: dict):
    # SỬA QUAN TRỌNG: Đảm bảo đúng tên collection trong DB của bạn
    # Nếu DB của bạn tên là "project", hãy sửa dòng dưới thành "project"
    coll_name = "project" 
    
    # Debug: In ra để biết đang query vào đâu
    print(f"DEBUG: Querying collection '{coll_name}'")
    
    coll = db[coll_name]

    # Build filters
    filters = build_filter(query_json.get("filters", {}))
    
    # Full-text search
    search_text = query_json.get("search_text", "")
    full_text = build_full_text_search(search_text) if search_text else None
    
    # Combine
    mongo_filter = combine_filters(filters, {}, full_text)
    
    # Debug: In ra câu query thực tế gửi vào Mongo
    print(f"DEBUG: Mongo Filter: {mongo_filter}")

    # COUNT MODE
    if query_json.get("type") == "count" or query_json.get("operation") == "count":
        return {"count": coll.count_documents(mongo_filter)}

    # FIND MODE
    projection = projection_from_fields(query_json.get("fields", []))
    
    limit = query_json.get("options", {}).get("limit", 20)
    try: limit = int(limit)
    except: limit = 20

    cursor = coll.find(mongo_filter, projection).limit(limit)

    results = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        if "_id" in doc: doc.pop("_id")
        results.append(doc)

    return results