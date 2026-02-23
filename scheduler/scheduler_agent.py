# scheduler/scheduler_agent.py
import asyncio
import json
from planner.planner_agent import PlannerAgent
from executor.executor_agent import AgentExecutor

class AgentScheduler:
    def __init__(self):
        self.planner = PlannerAgent()
        self.executor = AgentExecutor()
        self.MAX_RETRIES = 1 

    async def process_request(self, user_query: str, chat_history: str = None, status_callback=None) -> str:
        """
        Xử lý yêu cầu từ người dùng.
        - user_query: Câu hỏi hiện tại.
        - chat_history: Lịch sử hội thoại (User: A, AI: B...) để Agent nhớ ngữ cảnh.
        """
        print(f"\n🚀 [Scheduler] New Request: {user_query}")
        
        if status_callback:
            await status_callback("Đang lập kế hoạch...", "Phân tích yêu cầu và chọn công cụ phù hợp.")
        feedback = None
        
        # --- REPLAN LOOP ---
        for attempt in range(self.MAX_RETRIES + 1):
            if attempt > 0:
                print(f"🔄 [Scheduler] Replanning (Attempt {attempt})... Reason: {feedback}")

            # 1. PLAN (Truyền chat_history vào Planner)
            plan = self.planner.create_plan(
                user_query, 
                previous_feedback=feedback, 
                chat_history=chat_history  # <--- QUAN TRỌNG: Truyền lịch sử vào đây
            )
            
            if not plan:
                return "❌ Lỗi: Không thể lập kế hoạch."
            
            if status_callback:
                plan_str = "\n".join([f"- {task.get('tool')}" for task in plan])
                await status_callback("Đã lập kế hoạch:", plan_str)


            print(f"📋 Plan: {json.dumps(plan, ensure_ascii=False)}")

            # 2. EXECUTE
            # Executor trả về (Success, Result)
            success, result = await self.executor.execute_plan(user_query, plan, chat_history, status_callback)

            # 3. EVALUATE & RETURN
            if success:
                # Chỉ trả về phần text (result) để hiển thị đẹp
                return str(result)
            else:
                feedback = result # Lưu lỗi để lần sau Replan dùng
                if status_callback:
                    await status_callback("Gặp lỗi, đang thử lại...", f"Lỗi: {result}")
        
        # Nếu thất bại toàn tập
        return f"⚠️ Xin lỗi, tôi không tìm thấy thông tin phù hợp. Lỗi chi tiết: {feedback}"