from langchain_ollama import OllamaEmbeddings
print("OllamaEmbeddings OK")
from chromadb.utils import embedding_functions
print("chromadb EF OK")
import requests
r = requests.post("http://172.30.224.1:11434/api/embeddings", json={"model": "bge-m3", "prompt": "test"})
print(f"Ollama embeddings API: {r.status_code}, dim={len(r.json().get('embedding', []))}")
