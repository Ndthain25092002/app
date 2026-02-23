import asyncio
import json
import logging
import re
from datetime import datetime
from bson import ObjectId 

# --- Import service cũ ---
from agents.text_to_json_llm import generate_query
from agents.mongo_text2query import build_mongo_query
from agents.mongo_agent import mongo_find
from database.mongodb import get_collection

# --- Import Service mới ---
from agents.rag_service import RAGService 
from agents.tavily_agent import TavilyAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.field_config import is_enum_field, is_numeric_field, is_date_field
from agents.content_writer_agent import ContentWriterAgent 
from agents.tools.office_tool import OfficeTool
from agents.tools.facebook_tool import FacebookTool

# ==============================================================================
# HELPER: SERIALIZE MONGO
# ==============================================================================
def serialize_mongo_doc(doc):
    """Chuyển đổi ObjectId, datetime sang string để tránh lỗi JSON"""
    if not isinstance(doc, dict):
        return doc
    new_doc = {}
    for k, v in doc.items():
        if isinstance(v, datetime):
            new_doc[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(v, ObjectId):
            new_doc[k] = str(v)
        elif isinstance(v, list):
            new_list = []
            for item in v:
                if isinstance(item, (datetime, ObjectId)):
                    new_list.append(str(item))
                elif isinstance(item, dict):
                    new_list.append(serialize_mongo_doc(item))
                else:
                    new_list.append(item)
            new_doc[k] = new_list
        else:
            try:
                json.dumps(v)
                new_doc[k] = v
            except:
                new_doc[k] = str(v)
    return new_doc

# ==============================================================================
# CLASS AGENT EXECUTOR
# ==============================================================================
class AgentExecutor:
    def __init__(self):
        self.tavily = TavilyAgent()
        self.synthesizer = SynthesizerAgent()
        self.writer = ContentWriterAgent() 
        self.office_tool = OfficeTool()
        self.facebook_tool = FacebookTool()
        
        self.context = ""
        self.last_generated_content = "" # Lưu nội dung vừa viết để đăng Face

    def _extract_file_path(self, text: str) -> str:
        """Trích xuất đường dẫn file từ câu lệnh."""
        match = re.search(r'(downloads/[^\s"\'\n]+)', text)
        if match:
            return match.group(1)
        return text.strip()

    async def execute_plan(self, user_query: str, plan, chat_history: str = "", status_callback=None):
        self.context = ""
        self.last_generated_content = ""
        has_useful_data = False
        error_log = []

        # ---------------------------------------------------------
        # 1. XỬ LÝ & VALIDATE PLAN
        # ---------------------------------------------------------
        if isinstance(plan, str):
            try:
                plan = json.loads(plan)
            except Exception:
                return False, "Lỗi hệ thống: Planner trả về JSON sai định dạng."

        if isinstance(plan, dict):
            plan = [plan]

        if not isinstance(plan, list):
            return False, "Lỗi hệ thống: Plan không hợp lệ."

        print(f"--- Executing Plan ({len(plan)} steps) ---")

        # ---------------------------------------------------------
        # 2. VÒNG LẶP THỰC THI TỪNG BƯỚC
        # ---------------------------------------------------------
        for i, task in enumerate(plan, 1):
            if not isinstance(task, dict): continue
                
            tool = task.get("tool")
            instruction = task.get("instruction")
            
            # --- Fallback key ---
            if not tool and "action" in task: tool = task.get("action")
            
            # --- Fallback instruction ---
            if not instruction and "parameters" in task:
                params = task.get("parameters")
                instruction = json.dumps(params, ensure_ascii=False) if isinstance(params, dict) else str(params)

            # --- Fallback tối hậu: Dùng query gốc ---
            if not instruction or not str(instruction).strip():
                print(f"⚠️ Warning: Step '{tool}' thiếu instruction. Fallback về user_query.")
                instruction = user_query 

            # >>> GỌI CALLBACK ĐỂ HIỆN LOG LÊN TELEGRAM <<<
            if status_callback:
                await status_callback(f"Đang chạy bước {i}/{len(plan)}: {tool}", f"Chi tiết: {instruction[:100]}...")

            # --- Retry Loop ---
            for attempt in range(2):
                try:
                    step_result = ""
                    
                    # Tool 1: Mongo Query
                    if tool == "mongo_db_query":
                        print(f"   --> 🔎 Mongo Query: {instruction}")
                        llm_query = generate_query(instruction)
                        if llm_query:
                            mongo_filter = build_mongo_query(llm_query)
                            results = mongo_find(mongo_filter)
                            
                            if isinstance(results, dict) and "count" in results:
                                has_useful_data = True
                                step_result = f"Kết quả đếm: {results['count']} bản ghi."
                            else:
                                results_list = results[:10] if isinstance(results, list) else []
                                if results_list:
                                    has_useful_data = True
                                    clean_results = [serialize_mongo_doc(doc) for doc in results_list]
                                    step_result = f"Tìm thấy {len(results_list)} bản ghi:\n{json.dumps(clean_results, ensure_ascii=False, indent=2)}"
                                else:
                                    step_result = "Mongo Query: Không tìm thấy kết quả nào."
                        else:
                            step_result = "Lỗi: Không thể tạo câu query Mongo."

                    # Tool 2: PDF Reader
                    elif tool == "pdf_reader":
                        file_path = self._extract_file_path(instruction)
                        print(f"   --> 📄 Reading PDF: {file_path}")
                        content = self.office_tool.read_pdf(file_path)
                        if content and "Lỗi" not in content: has_useful_data = True
                        step_result = f"Nội dung PDF:\n{content}"
                
                    # Tool 3: Excel Reader
                    elif tool == "excel_reader":
                        file_path = self._extract_file_path(instruction)
                        print(f"   --> 📊 Reading Excel: {file_path}")
                        content = self.office_tool.read_excel(file_path)
                        if content and "Lỗi" not in content: has_useful_data = True
                        step_result = content

                    # Tool 4: Vector Search
                    elif tool == "vector_search":
                        print(f"   --> 🧠 Hybrid RAG Search: {instruction}")
                        structured_info = generate_query(instruction)
                        clean_filters = {}
                        if structured_info and structured_info.get("filters"):
                            for k, v in structured_info.get("filters", {}).items():
                                if is_enum_field(k) or is_numeric_field(k) or is_date_field(k):
                                    clean_filters[k] = v
                        
                        rag_results = RAGService.search_combined(instruction, {"filters": clean_filters}, 5)
                        
                        if rag_results: 
                            has_useful_data = True
                            data_list = []
                            for r in rag_results:
                                item = r.get("data", {})
                                clean_item = serialize_mongo_doc(item) 
                                clean_item["_similarity"] = f"{r.get('similarity_score', 0):.2f}"
                                data_list.append(clean_item)
                            step_result = f"RAG Results:\n{json.dumps(data_list, ensure_ascii=False, indent=2)}"
                        else:
                            step_result = "RAG Service: Không tìm thấy tài liệu phù hợp."
                        
                    # Tool 5: Tavily Search
                    elif tool == "tavily_search":
                        print(f"   --> 🌐 Tavily Search: {instruction}")
                        tavily_res = await self.tavily.run(instruction)
                        if tavily_res.get('results'):
                            has_useful_data = True
                            step_result = json.dumps(tavily_res.get('results'), ensure_ascii=False, indent=2)
                        else:
                            step_result = "Không tìm thấy tin tức online."

                    # Tool 6: Content Writer
                    elif tool == "content_writer":
                        print(f"   --> ✍️ Content Writer: {instruction}")
                        written_content = await self.writer.run(
                            instruction=instruction, 
                            context_data=self.context,
                            chat_history=chat_history # Có nhớ lịch sử
                        )
                        has_useful_data = True
                        self.last_generated_content = written_content # Lưu để đăng face
                        step_result = f"NỘI DUNG ĐÃ SOẠN:\n{written_content}"

                    # Tool 7: Facebook Poster
                    elif tool == "facebook_poster":
                        print(f"   --> 📱 Facebook Poster: {instruction}")
                        # Ưu tiên lấy nội dung vừa viết
                        content_to_post = self.last_generated_content if self.last_generated_content else instruction
                        
                        if content_to_post:
                            result = self.facebook_tool.post_status(content_to_post)
                            step_result = result
                            has_useful_data = True
                        else:
                            step_result = "Lỗi: Không có nội dung để đăng."

                    # Lưu kết quả bước này vào context chung
                    self.context += f"\n[Step {task.get('step', 0)}] {tool}: {step_result}\n"
                    break # Thành công -> Thoát retry loop

                except Exception as e:
                    if attempt == 1: 
                        logging.error(f"Error tool {tool}: {e}", exc_info=True)
                        error_log.append(str(e))
                    else: await asyncio.sleep(1)
        
        # ---------------------------------------------------------
        # 3. KIỂM TRA KẾT QUẢ CUỐI CÙNG
        # ---------------------------------------------------------
        writer_used = "content_writer" in [t.get('tool') for t in plan if isinstance(t, dict)]
        fb_used = "facebook_poster" in [t.get('tool') for t in plan if isinstance(t, dict)]
        
        # Nếu không có data và cũng không viết lách/đăng bài -> Coi như thất bại
        if not has_useful_data and not writer_used and not fb_used:
            return False, "Không tìm thấy dữ liệu nào phù hợp."

        if error_log:
            return False, "; ".join(error_log)

        # ---------------------------------------------------------
        # 4. TỔNG HỢP TRẢ LỜI
        # ---------------------------------------------------------
        if status_callback:
            await status_callback("Đang tổng hợp...", "Viết câu trả lời cuối cùng.")

        print("[Executor] Synthesizing final answer...")
        final_answer = await self.synthesizer.synthesize(user_query, self.context, chat_history)
        return True, final_answer