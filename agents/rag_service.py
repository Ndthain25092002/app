# agents/rag_service.py
import logging
from agents.qdrant_agent import rag_semantic_search

logger = logging.getLogger("rag_service")

class RAGService:
    # ... (Hàm search_with_rag GIỮ NGUYÊN) ...
    @staticmethod
    def search_with_rag(query_text: str, structured_filters: dict = None, top_k: int = 5):
        # Code cũ giữ nguyên
        logger.info(f"RAG search: '{query_text[:100]}...'")
        if not query_text or not query_text.strip(): return []
        try:
            results = rag_semantic_search(query=query_text, top_k=top_k, include_fields=None)
            logger.info(f"RAG returned {len(results)} semantic results")
            return results
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return []

    @staticmethod
    def search_combined(search_text: str, filters: dict = None, top_k: int = 5):
        logger.info(f"Combined search - text: '{search_text}', filters: {filters}")
        
        # Lấy kết quả semantic (Lấy nhiều hơn top_k để trừ hao khi lọc)
        rag_results = RAGService.search_with_rag(search_text, top_k=top_k * 3)
        
        if not rag_results:
            return []
        
        # Nếu không có filter, trả về luôn
        if not filters or not filters.get("filters"):
            return rag_results[:top_k]
        
        target_filters = filters.get("filters", {})
        filtered_results = []
        
        for result in rag_results:
            doc = result["data"]
            matches = True
            
            for field, target_val in target_filters.items():
                doc_val = doc.get(field)
                
                # --- LOGIC SO SÁNH THÔNG MINH HƠN ---
                if doc_val is None:
                    matches = False
                    break
                
                # 1. Nếu doc_val là List (Ví dụ: tags, multiple choices) -> Check exists
                if isinstance(doc_val, list):
                    if target_val not in doc_val:
                        matches = False
                        break
                # 2. Nếu target_val là List (Lọc $in)
                elif isinstance(target_val, list):
                    if doc_val not in target_val:
                        matches = False
                        break
                # 3. So sánh bằng thông thường (Exact Match cho Enum/Number)
                else:
                    # Chuyển về string để so sánh an toàn nếu khác kiểu
                    if str(doc_val).lower() != str(target_val).lower():
                        matches = False
                        break
            
            if matches:
                filtered_results.append(result)
                if len(filtered_results) >= top_k:
                    break
        
        logger.info(f"After filtering: {len(filtered_results)} results")
        return filtered_results