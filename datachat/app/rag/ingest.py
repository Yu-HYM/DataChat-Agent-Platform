#!/usr/bin/env python3
# app/rag/ingest.py —— 文档解析/清洗/切片/向量化入库
# 使用 Ollama bge-m3 嵌入（GPU加速，无需下载 sentence-transformers 权重）
import hashlib, re, os
from pathlib import Path
import chromadb
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://172.30.224.1:11434")
KB_DIR = Path(__file__).resolve().parents[2] / "kb_docs"
CHROMA_DIR = str(Path(__file__).resolve().parents[2] / "chroma_db")
EMBED_MODEL = "bge-m3"

class OllamaEF:
    """适配 chromadb 嵌入函数接口，内部调 Ollama API"""
    def __init__(self, base_url, model):
        self.ollama = OllamaEmbeddings(base_url=base_url, model=model)
    def __call__(self, input):
        return self.ollama.embed_documents(input)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=400, chunk_overlap=60,
    separators=["\n\n", "\n。", "。", "；", "\n", "，", " ", ""])

def parse_pdf(path):
    reader = PdfReader(str(path))
    return "\n".join(p.extract_text() or "" for p in reader.pages)

def parse_file(path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return parse_pdf(path)
    return path.read_text(encoding="utf-8", errors="ignore")

def clean_text(text: str) -> str:
    lines, seen = [], set()
    for ln in text.splitlines():
        s = ln.strip()
        if not s or re.fullmatch(r"[\d\s\-—|]+", s) or len(s) < 4:
            continue
        h = hashlib.md5(s.encode()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        lines.append(s)
    return "\n".join(lines)

def build_kb():
    ef = OllamaEF(OLLAMA_URL, EMBED_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection("datachat_kb", embedding_function=ef,
                                          metadata={"hnsw:space": "cosine"})
    for f in sorted(KB_DIR.iterdir()):
        if f.suffix.lower() not in (".pdf", ".md", ".txt"):
            continue
        text = clean_text(parse_file(f))
        chunks = splitter.split_text(text)
        uniq = {}
        for c in chunks:
            uniq.setdefault(hashlib.md5(c[:64].encode()).hexdigest(), c)
        ids_list = []
        docs_list = []
        metas_list = []
        for i, (h, c) in enumerate(uniq.items()):
            ids_list.append(f"{f.name}:{h}")
            docs_list.append(c)
            metas_list.append({"source": f.name, "chunk": i})
        if docs_list:
            col.upsert(ids=ids_list, documents=docs_list, metadatas=metas_list)
        print(f"{f.name}: {len(uniq)} chunks")
    print("total:", col.count())

if __name__ == "__main__":
    build_kb()

