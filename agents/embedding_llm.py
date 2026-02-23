import os

# Tăng thời gian chờ từ 10s lên 60s hoặc 100s
os.environ['HF_HUB_ETAG_TIMEOUT'] = '100'
os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '100'
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("sentence-transformers/paraphrase-MiniLM-L6-v2")

def embed(text: str):
    return _model.encode(text)
