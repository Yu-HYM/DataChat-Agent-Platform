#!/usr/bin/env python3
# app/rag/retrieval.py —— 混合检索(BM25+Ollama向量) + CrossEncoder重排
import jieba, os
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
import chromadb
from langchain_ollama import OllamaEmbeddings
from rank_bm25 import BM25Okapi
from pathlib import Path

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://172.30.224.1:11434")
CHROMA_DIR = str(Path(__file__).resolve().parents[2] / "chroma_db")
EMBED_MODEL = "bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-base"

class OllamaEF:
    def __init__(self, base_url, model):
        self.ollama = OllamaEmbeddings(base_url=base_url, model=model)
    def __call__(self, input):
        return self.ollama.embed_documents(input)

_reranker = _docs = _meta = _bm25 = _id2idx = _reranker_available = None

def _lazy_init():
    global _reranker, _docs, _meta, _bm25, _id2idx, _reranker_available
    if _docs is not None:
        return
    ef = OllamaEF(OLLAMA_URL, EMBED_MODEL)
    col = chromadb.PersistentClient(path=CHROMA_DIR).get_collection("datachat_kb", embedding_function=ef)
    data = col.get(include=["documents", "metadatas"])
    _docs = data["documents"]
    _ids = col.get()["ids"]
    _id2idx = {n: i for i, n in enumerate(_ids)}
    _meta = data["metadatas"]
    _bm25 = BM25Okapi([list(jieba.cut(d)) for d in _docs])
    try:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(RERANK_MODEL, device="cpu")
        _reranker_available = True
    except Exception as e:
        _reranker_available = False
        print(f"Reranker not available: {e}")

def search(question: str, top_k: int = 3):
    _lazy_init()
    scores = _bm25.get_scores(list(jieba.cut(question)))
    kw_hits = {}
    for idx in scores.argsort()[::-1][:10]:
        kw_hits[int(idx)] = float(scores[idx])
    ef = OllamaEF(OLLAMA_URL, EMBED_MODEL)
    col = chromadb.PersistentClient(path=CHROMA_DIR).get_collection("datachat_kb", embedding_function=ef)
    res = col.query(query_texts=[question], n_results=10)
    vec_hits = {}
    for r, i in enumerate(res["ids"][0]):
        if i in _id2idx:
            vec_hits[_id2idx[i]] = 10 - r
    merged = {}
    for idx in set(kw_hits) | set(vec_hits):
        merged[idx] = kw_hits.get(idx, 0) + vec_hits.get(idx, 0)
    cands = sorted(merged, key=merged.get, reverse=True)[:8]
    if _reranker_available and _reranker is not None:
        pairs = [(question, _docs[i]) for i in cands]
        scores = _reranker.predict(pairs)
        top = sorted(zip(cands, scores), key=lambda x: -x[1])[:top_k]
    else:
        top = [(i, merged.get(i, 0)) for i in cands[:top_k]]
    return [{"content": _docs[i], "source": _meta[i]["source"],
             "score": float(s)} for i, s in top]

if __name__ == "__main__":
    for r in search("复购率是怎么定义的"):
        print(round(r["score"], 3), r["source"], r["content"][:80])
