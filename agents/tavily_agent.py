# app/agents/tavily_agent.py
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()

class TavilyAgent:
    """
    Lightweight Tavily web search agent (async).
    """
    def __init__(self, api_key: str | None = None, endpoint: str | None = None):
        # Lấy key từ biến môi trường hoặc từ tham số truyền vào
        env_key = os.getenv("TAVILY_API_KEY")
        self.api_key = api_key or env_key
        self.endpoint = endpoint or "https://api.tavily.com/search"
        
        if not self.api_key:
            self.disabled = True
            print("[Tavily] Warning: No API Key found. Agent disabled.")
        else:
            self.disabled = False

    async def _call_api(self, query: str, max_results: int = 5):
        if self.disabled:
            return {}
            
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.endpoint, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    # Không raise Exception để tránh crash cả luồng, chỉ return dict rỗng/lỗi
                    print(f"[Tavily] Error {resp.status}: {text}")
                    return {"error": text}
                return await resp.json()

    async def run(self, query: str, max_results: int = 5) -> dict:
        if self.disabled:
            return {"error": "Tavily API key not configured", "query": query}
            
        try:
            data = await self._call_api(query, max_results)
            return {
                "answer": data.get("answer", "") if isinstance(data, dict) else "",
                "results": data.get("results", []) if isinstance(data, dict) else [],
                "raw": data
            }
        except Exception as e:
            print(f"[Tavily] Exception: {e}")
            return {"results": [], "error": str(e)}