import os
from dotenv import load_dotenv

load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

ENTITY_TO_COLLECTION = {
    "customer": "project"
}

RAG_ENGINE = os.getenv("RAG_ENGINE", "qdrant")  # "faiss" | "chroma" | "qdrant"

# Qdrant settings
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "project_vectors")
QDRANT_DISTANCE = os.getenv("QDRANT_DISTANCE", "Cosine")

# (FAISS removed) No local FAISS index configuration.

