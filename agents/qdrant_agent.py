import os
import logging
import uuid
from bson import ObjectId
from database.mongodb import get_collection, db
from agents.embedding_llm import embed
from config import QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION, QDRANT_DISTANCE

logger = logging.getLogger("qdrant_agent")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import VectorParams, Distance
except Exception as e:
    raise ImportError("qdrant-client is required for qdrant_agent. Install with 'pip install qdrant-client'")


def _get_client():
    if QDRANT_API_KEY:
        return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return QdrantClient(url=QDRANT_URL)


def build_qdrant_index(collection_name: str = QDRANT_COLLECTION):
    """
    Build (create) Qdrant collection and upsert vectors from MongoDB documents.
    This is idempotent: repeated calls will upsert/overwrite existing points.
    """
    client = _get_client()

    # Gather documents and vectors
    collections_to_scan = ["project", "documents"]
    points = []
    total = 0
    vector_size = 384

    for coll_name in collections_to_scan:
        coll = get_collection(coll_name)
        docs = list(coll.find({}))
        logger.info(f"Loaded {len(docs)} docs from MongoDB collection '{coll_name}'")

        for doc in docs:
            combined_text = ""
            if coll_name == "project":
                text_fields = [
                    "full_name", "company", "pain_points", "expectation",
                    "need_support_field", "industry", "position",
                    "care_history", "course", "note"
                ]
                parts = [str(doc[f]) for f in text_fields if f in doc and doc[f]]
                combined_text = " | ".join(parts)
            else:
                combined_text = doc.get("sum_text") or doc.get("full_text") or ""

            if not combined_text or not str(combined_text).strip():
                continue

            vec = embed(str(combined_text))
            if vec is None:
                logger.warning(f"embed returned None for doc {doc.get('_id')}")
                continue

            if vector_size is None:
                vector_size = len(vec)

            payload = {
                "doc_id": str(doc.get("_id")),
                "collection": coll_name,
                "title": doc.get("filename") or doc.get("full_name") or "",
                "snippet": str(combined_text)[:500]
            }

            # Do NOT use MongoDB ObjectId string as Qdrant point id (Qdrant requires integer or UUID).
            # Keep the original Mongo `_id` in the payload (`doc_id`) so we can fetch the document later.
            # Let Qdrant assign the point id automatically by not providing `id`.
            # Ensure vector is a plain Python list (JSON serializable)
            v = vec.tolist() if hasattr(vec, "tolist") else list(vec)

            # Build a plain dict for upsert. Assign a UUID id (valid point id)
            point = {"id": str(uuid.uuid4()), "vector": v, "payload": payload}
            points.append(point)
            total += 1

            if total % 200 == 0:
                logger.info(f"Prepared {total} points for upsert to Qdrant")

    if not points:
        raise RuntimeError("No vectors produced → Cannot build Qdrant collection")

    # Create collection if not exists
    try:
        # If collection exists, this call will raise; handle gracefully by skipping
        client.get_collection(collection_name=collection_name)
        logger.info(f"Qdrant collection '{collection_name}' exists. Will upsert points.")
    except Exception:
        if vector_size is None:
            raise RuntimeError("Cannot determine vector size for Qdrant collection")
        logger.info(f"Creating Qdrant collection '{collection_name}' (size={vector_size})")

        # Map distance string to enum
        dist_map = {
            "cosine": Distance.COSINE,
            "euclid": Distance.EUCLID,
            "l2": Distance.EUCLID,
            "dot": Distance.DOT
        }
        dist = dist_map.get(str(QDRANT_DISTANCE).lower(), Distance.COSINE)

        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=dist)
        )

    # Upsert points in batches. If validation fails (e.g. vector size mismatch),
    # recreate the collection with the detected vector_size and retry once.
    BATCH = 256
    recreated = False
    try:
        for i in range(0, len(points), BATCH):
            batch = points[i:i+BATCH]
            client.upsert(collection_name=collection_name, points=batch)
            logger.info(f"Upserted points {i}..{i+len(batch)} to Qdrant")
    except Exception as e:
        # If validation error likely due to vector size mismatch, attempt recreate
        logger.warning(f"Upsert failed: {e}")
        if not recreated and vector_size is not None:
            logger.info("Attempting to recreate Qdrant collection with correct vector size and retry upsert...")
            # Map distance string to enum
            dist_map = {
                "cosine": Distance.COSINE,
                "euclid": Distance.EUCLID,
                "l2": Distance.EUCLID,
                "dot": Distance.DOT
            }
            dist = dist_map.get(str(QDRANT_DISTANCE).lower(), Distance.COSINE)

            client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=dist)
            )
            recreated = True

            # Retry uploading all points once
            for i in range(0, len(points), BATCH):
                batch = points[i:i+BATCH]
                client.upsert(collection_name=collection_name, points=batch)
                logger.info(f"Upserted points {i}..{i+len(batch)} to Qdrant (retry)")
        else:
            raise

    logger.info(f"Qdrant indexing complete. Total points upserted: {total}")


def rag_search(query: str, top_k: int = 5, filters: dict = None, collection_name: str = QDRANT_COLLECTION):
    """
    Semantic search using Qdrant
    Returns list of dicts similar to faiss_agent.rag_search
    """
    if not query or not query.strip():
        return []

    client = _get_client()
    q_vec = embed(query)
    if q_vec is None:
        logger.warning("Embedding returned None")
        return []

    # Search Qdrant
    try:
        hits = client.search(collection_name=collection_name, query_vector=q_vec, limit=min(top_k * 3, 100), with_payload=True)
    except Exception as e:
        logger.error(f"Qdrant search error: {e}")
        return []

    results = []
    for hit in hits:
        payload = hit.payload or {}
        doc_id = payload.get("doc_id")
        coll_name = payload.get("collection") or "project"

        if not doc_id:
            continue

        try:
            coll = db[coll_name]
            full_doc = coll.find_one({"_id": ObjectId(doc_id)})
            if not full_doc:
                continue

            # Apply structured filters (basic exact match)
            if filters:
                match = True
                for f, v in filters.items():
                    if f not in full_doc or str(full_doc.get(f)).lower() != str(v).lower():
                        match = False
                        break
                if not match:
                    continue

            results.append({
                "score": float(hit.score) if hasattr(hit, 'score') else 0.0,
                "doc": full_doc,
                "doc_id": doc_id,
                "snippet": payload.get("snippet", "")
            })

            if len(results) >= top_k:
                break

        except Exception as e:
            logger.warning(f"Error fetching doc {doc_id}: {e}")
            continue

    logger.info(f"RAG returned {len(results)} results from Qdrant")
    return results


def rag_semantic_search(query: str, top_k: int = 5, include_fields: list = None):
    results = rag_search(query, top_k)

    simplified = []
    for result in results:
        doc = result["doc"]
        doc["_id"] = str(doc["_id"]) if doc.get("_id") else doc.get("_id")
        if include_fields:
            doc = {k: doc.get(k, None) for k in include_fields if k in doc}

        simplified.append({
            "similarity_score": result.get("score", 0.0),
            "data": doc
        })

    return simplified
