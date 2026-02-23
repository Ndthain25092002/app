# agents/synthesizer_agent.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class SynthesizerAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def synthesize(self, user_query: str, context: str, chat_history: str = "") -> str:
        """
        Tổng hợp dữ liệu từ Context thành câu trả lời cuối cùng cho User.
        """
        if not context:
            return "Xin lỗi, tôi không tìm thấy dữ liệu nào để trả lời câu hỏi của bạn."

        system_prompt = """
            You are the Synthesizer Agent responsible for producing the final reply
            shown to the user on Telegram. Write like a helpful human assistant.

            GOALS:
            - Preserve the important facts from the collected data.
            - Rephrase and edit so the reply feels natural, concise, and personal.

            TONE & STYLE (use when appropriate):
            - Friendly, conversational, and empathetic.
            - Use contractions (I'm, don't, it's) and speak directly to the user ("you").
            - Keep paragraphs short (1-3 lines) and use at most 3 bullets in a row.
            - Avoid robotic phrases like "as an AI" or long process descriptions.

            STRUCTURE:
            - Start with 1 short empathic/opening sentence or jump straight to the answer.
            - Present the key points clearly and briefly.
            - End with a single light CTA (suggest next step or ask if they want more).

            PERSONALIZATION:
            - If chat history or a name is available, use it to personalize the reply.
            - Mirror the user's tone (formal vs casual) when evident.

            LENGTH: Aim for 4–8 short sentences for typical answers. If a detailed
            explanation is required, include a one-line TL;DR at the top.

            DO NOT:
            - Produce lengthy numbered reports or internal metadata.
            - Invent facts not supported by the provided context.
        """

        user_prompt = f"""
        USER QUESTION: "{user_query}"

        CHAT HISTORY:
        {chat_history if chat_history else 'Không có lịch sử.'}

        RAW CONTEXT (gồm các kết quả, trích đoạn):
        {context}

        Hãy viết câu trả lời cuối cùng, tự nhiên và thân thiện, phù hợp để gửi
        trực tiếp trên Telegram. Nếu phù hợp, mở đầu bằng 1 câu tóm tắt (TL;DR).
        """
           
        try:
            resp = self.client.responses.create(
                model="gpt-4o",
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_output_tokens=1200,
            )

            raw_text = getattr(resp, "output_text", None)
            if not raw_text:
                try:
                    parts = []
                    for out_item in getattr(resp, "output", []) or []:
                        content_list = out_item.get("content", []) if isinstance(out_item, dict) else []
                        for c in content_list:
                            if isinstance(c, dict) and "text" in c:
                                parts.append(c["text"])
                    raw_text = "".join(parts).strip() if parts else None
                except Exception:
                    raw_text = None

            if not raw_text:
                raw_text = str(resp)

            return raw_text.strip()
        except Exception as e:
            return f"Lỗi khi tổng hợp câu trả lời: {e}" 
        