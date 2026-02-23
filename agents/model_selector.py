"""
agents/model_selector.py
Use a small GPT prompt to choose the most appropriate model for a given query.
The function provides a heuristic fallback and then asks GPT to pick among allowed models.
"""
import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = logging.getLogger("model_selector")

# Restrict to GPT-4-family models only (user requested "only use model 4")
DEFAULT_MODELS = ["gpt-4", "gpt-4o", "gpt-4o-mini"]


def _heuristic_pick(user_question: str, query_meta: dict | None = None) -> str | None:
    """Simple heuristic to narrow down choices.
    Returns a model name if confident, otherwise None to let GPT decide.
    """
    q = (user_question or "").lower()
    # If user asks for a count or very short factual query, prefer cheaper model
    if any(k in q for k in ["bao nhiêu", "tổng số", "số lượng", "count", "có mấy", "có bao nhiêu"]):
        return "gpt-3.5-turbo"

    # If query contains the word 'semantic' or asks for similarity/insights, prefer stronger model
    if any(k in q for k in ["tương tự", "tương tự như", "phân tích", "phân loại", "insights", "đề xuất"]):
        return "gpt-4o"

    # If query likely needs JSON-only strict output (structured), use mid model
    if len(q.split()) < 8:
        return "gpt-4o-mini"

    return None


def choose_model(user_question: str, query_meta: dict | None = None, allowed_models: list | None = None) -> str:
    """Choose a model for given user question.

    Flow:
    1. Try heuristic pick.
    2. If heuristic unsure, call GPT (very small prompt) to pick from allowed_models.
    3. Fallback to first allowed model.
    """
    if allowed_models is None:
        allowed_models = DEFAULT_MODELS

    # 1) Heuristic
    pick = _heuristic_pick(user_question, query_meta)
    if pick and pick in allowed_models:
        logger.info(f"ModelSelector: heuristic picked {pick}")
        return pick

    # 2) Ask GPT to decide — small, deterministic prompt
    prompt = (
        "You are a model selection assistant. Given a short user query and optional metadata, "
        "choose the most appropriate model for generating a JSON-structured query. Return only the model name string, exactly one of the following options: "
        + ", ".join(allowed_models)
        + ".\n\n"
        "Query: \"" + (user_question or "") + "\"\n"
    )

    try:
        # Use a GPT-4-family model for the meta selection call
        resp = client.responses.create(
            model="gpt-4o",
            input=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_output_tokens=50,
        )
        # Extract output text
        out = None
        if hasattr(resp, "output_text"):
            out = resp.output_text.strip()
        else:
            # Fallback parsing
            try:
                out = str(resp)
            except Exception:
                out = None

        if out:
            # Clean result to match allowed models
            out = out.strip().split()[0]
            if out in allowed_models:
                logger.info(f"ModelSelector: GPT chose model {out}")
                return out
            else:
                logger.info(f"ModelSelector: GPT suggested '{out}', not in allowed list {allowed_models}")
    except Exception as e:
        logger.exception("Model selection GPT call failed: %s", e)

    # 3) Fallback
    fallback = allowed_models[0]
    logger.info(f"ModelSelector: fallback to {fallback}")
    return fallback


def choose_pipeline(user_question: str, query_meta: dict | None = None, allowed: list | None = None) -> str:
    """Decide whether to use the structured Text-to-Query (t2q) path or RAG (rag).

    Returns one of: 't2q' or 'rag'.
    Flow:
      1) Simple heuristics
      2) Ask a small deterministic GPT prompt if unclear
      3) Fallback to 't2q'
    """
    if allowed is None:
        allowed = ["t2q", "rag"]

    q = (user_question or "").lower()

    # Heuristics: explicit count / filter / field requests -> prefer t2q
    count_keywords = ["bao nhiêu", "tổng số", "số lượng", "count", "có mấy", "có bao nhiêu"]
    field_clues = ["tên", "sdt", "số điện thoại", "email", "ngành", "công ty", "khách chính", "khách phụ", "tham gia"]
    rag_clues = ["tương tự", "liên quan", "gợi ý", "semantic", "tìm kiếm ngữ nghĩa", "gần giống", "similar", "similarity", "insights"]

    if any(k in q for k in count_keywords) or any(k in q for k in field_clues):
        return "t2q"

    if any(k in q for k in rag_clues):
        return "rag"

    # If very short and likely structured (e.g., "Liệt kê khách chính")
    if len(q.split()) < 6:
        return "t2q"

    # Last resort: ask a small GPT prompt to choose between t2q and rag
    prompt = (
        "You are a lightweight router that must choose between two pipelines: 't2q' (structured Text-to-Query) "
        "or 'rag' (semantic retrieval). Return exactly one word: t2q or rag.\n"
        "Consider that 't2q' should be used for explicit filter/count/listing requests, exact-field matches, and numeric/date operations. "
        "Use 'rag' for open-ended, exploratory, similarity, or insight-seeking queries.\n"
        "Query: \"" + (user_question or "") + "\"\n"
    )

    try:
        resp = client.responses.create(
            model="gpt-4o",
            input=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_output_tokens=20,
        )
        out = None
        if hasattr(resp, "output_text"):
            out = resp.output_text.strip().lower()
        else:
            out = str(resp).strip().lower()

        # sanitize
        if out:
            if "t2q" in out:
                return "t2q"
            if "rag" in out:
                return "rag"
    except Exception:
        logger.exception("Pipeline selector GPT call failed, falling back.")

    # fallback
    return "t2q"
