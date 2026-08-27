import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from sentence_transformers import CrossEncoder
m = CrossEncoder("BAAI/bge-reranker-base", device="cpu")
print("Reranker loaded OK")
