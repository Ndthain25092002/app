# agents/tools/facebook_tool.py
import os
import requests
import logging

logger = logging.getLogger("facebook_tool")

class FacebookTool:
    def __init__(self):
        self.page_id = os.getenv("FACEBOOK_PAGE_ID")
        self.access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.api_url = f"https://graph.facebook.com/v19.0/{self.page_id}/feed"

    def post_status(self, message: str):
        """
        Đăng bài viết dạng văn bản (Status) lên Fanpage
        """
        if not self.page_id or not self.access_token:
            return "❌ Lỗi: Chưa cấu hình FACEBOOK_PAGE_ID hoặc FACEBOOK_ACCESS_TOKEN trong .env"

        try:
            payload = {
                "message": message,
                "access_token": self.access_token
            }
            
            response = requests.post(self.api_url, data=payload)
            data = response.json()

            if response.status_code == 200:
                post_id = data.get("id")
                # Tạo link trực tiếp đến bài viết
                post_link = f"https://facebook.com/{post_id}"
                return f"✅ Đã đăng bài thành công!\nLink: {post_link}"
            else:
                error_msg = data.get("error", {}).get("message", "Unknown error")
                logger.error(f"FB API Error: {error_msg}")
                return f"❌ Đăng bài thất bại. Lỗi từ Facebook: {error_msg}"

        except Exception as e:
            return f"❌ Lỗi hệ thống khi đăng bài: {str(e)}"