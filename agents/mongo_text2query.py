"""
agents/mongo_text2query.py
Hàm build_mongo_query: chấp nhận dict, JSON string hoặc free-text.
Trả về filter dict an toàn để dùng với pymongo.
RAG sẽ xử lý semantic search, không dùng semantic_filters
"""
import json
from typing import Any, Dict, List

def build_mongo_query(query_json):
    """
    Accept:
      - dict (already parsed)
      - JSON string (parse it)

    Returns a dict với structured filters từ LLM
    RAG sẽ xử lý semantic search riêng biệt

    Returns:
      {
        "operation": "find" | "count",
        "type": "find" | "count",
        "filters": dict,
        "entity": str,
        "fields": list,
        "options": dict
      }
    """
    # ====== Normalize input ======
    if isinstance(query_json, str):
        if not query_json.strip():
            raise ValueError("Empty query string provided to build_mongo_query.")
        try:
            query_json = json.loads(query_json)
        except json.JSONDecodeError:
            # Nếu parse lỗi, không thể xử lý - để RAG xử lý
            raise ValueError(f"Invalid JSON string: {query_json}")

    elif not isinstance(query_json, dict):
        raise ValueError(f"query must be dict or JSON string, got {type(query_json)}")

    # ====== Determine operation ======
    q_type = query_json.get("type", "find")
    operation = "count" if q_type == "count" else "find"

    # ====== Build filters từ LLM ======
    filters = {}
    for k, v in query_json.get("filters", {}).items():
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        filters[k] = v

    # ====== Return structured filters ONLY (không semantic) ======
    return {
        "operation": operation,
        "type": operation,
        "filters": filters or {},
        "search_text": query_json.get("search_text", ""),
        "entity": query_json.get("entity", "customer"),
        "fields": query_json.get("fields", []),
        "options": query_json.get("options", {})
    }


