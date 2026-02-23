import os
import logging
from datetime import datetime
from typing import Optional, Dict

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

from database.mongodb import get_collection
from agents.embedding_llm import embed

logger = logging.getLogger("pdf_ingest")
logging.basicConfig(level=logging.INFO)


def _extract_text_from_pdf(path: str) -> str:
    if PdfReader is None:
        raise RuntimeError("PyPDF2 not installed. Install with `pip install PyPDF2`")
    reader = PdfReader(path)
    texts = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
            texts.append(txt)
        except Exception:
            continue
    return "\n".join(texts)


def _simple_summary(text: str, max_chars: int = 1000) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    # Take first 3 sentences if available
    sentences = text.split('. ')
    if len(sentences) <= 3:
        return text[:max_chars]
    summary = '. '.join(sentences[:3])
    if not summary.endswith('.'): summary += '.'
    return summary[:max_chars]


def ingest_pdf(file_path: str, metadata: Optional[Dict] = None, collection_name: str = "documents", create_embedding: bool = True) -> Dict:
    """
    Ingest a PDF file: extract full text, build a simple summary, store to MongoDB

    Returns the inserted document (with `_id` as string) on success.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")

    text = _extract_text_from_pdf(file_path)
    summary = _simple_summary(text, max_chars=1200)

    stat = os.stat(file_path)
    meta = metadata or {}
    meta.update({
        "filename": os.path.basename(file_path),
        "filepath": os.path.abspath(file_path),
        "size": stat.st_size,
        "ingested_at": datetime.utcnow(),
    })

    doc = {
        "filename": os.path.basename(file_path),
        "meta": meta,
        "full_text": text,
        "sum_text": summary,
    }

    # Optionally compute embedding for the summary (or truncated full_text)
    if create_embedding:
        try:
            to_embed = summary or (text[:2000] if text else "")
            vec = embed(to_embed)
            # Convert to plain python list for MongoDB
            if hasattr(vec, "tolist"):
                vec = vec.tolist()
            doc["embedding"] = vec
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")

    coll = get_collection(collection_name)
    res = coll.insert_one(doc)

    inserted = coll.find_one({"_id": res.inserted_id})
    inserted["_id"] = str(inserted["_id"])
    logger.info(f"Inserted document into '{collection_name}': {inserted.get('_id')}")
    return inserted


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest a PDF into MongoDB with summary and embedding")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("--collection", default="documents", help="MongoDB collection to insert into")
    args = parser.parse_args()

    out = ingest_pdf(args.pdf, collection_name=args.collection)
    print("Inserted:", out.get("_id"))
