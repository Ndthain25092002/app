# agents/tools/office_tool.py
import pandas as pd
from pypdf import PdfReader
import logging

logger = logging.getLogger("office_tool")

class OfficeTool:
    def read_excel(self, file_path: str) -> str:
        """Đọc file Excel và trả về dạng text tóm tắt hoặc JSON string"""
        try:
            df = pd.read_excel(file_path)
            # Trả về 5 dòng đầu và thông tin cột để LLM hiểu cấu trúc
            summary = f"Cấu trúc file: {list(df.columns)}\n\nDữ liệu mẫu (5 dòng đầu):\n{df.head().to_markdown(index=False)}"
            return summary
        except Exception as e:
            return f"Lỗi đọc Excel: {e}"

    def export_excel(self, data: list, output_path: str) -> str:
        """Xuất dữ liệu list[dict] ra file Excel"""
        try:
            df = pd.DataFrame(data)
            df.to_excel(output_path, index=False)
            return f"Đã xuất file Excel tại: {output_path}"
        except Exception as e:
            return f"Lỗi xuất Excel: {e}"

    def read_pdf(self, file_path: str) -> str:
        """Đọc nội dung text từ PDF"""
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text[:5000] # Giới hạn ký tự để không tràn token LLM
        except Exception as e:
            return f"Lỗi đọc PDF: {e}"