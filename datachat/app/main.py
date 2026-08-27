#!/usr/bin/env python3
# app/main.py —— FastAPI 服务入口
import os
from pathlib import Path
from loguru import logger
from fastapi import FastAPI, Depends, UploadFile, File, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from app import agent, pipeline
from app.auth import verify, make_token

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logger.add(str(LOG_DIR / "datachat.log"), rotation="10 MB", retention="7 days", encoding="utf-8")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="DataChat 智能问数平台")
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
def rate_hit(request, exc):
    return JSONResponse({"error": "请求过于频繁"}, status_code=429)

@app.get("/")
def root():
    return {"service": "DataChat", "status": "ok"}

@app.post("/auth/token")
def token(user: str = "demo"):
    t = make_token(user)
    return {"token": t, "expires_in": 7200}

@app.post("/chat")
@limiter.limit("10/minute")
def chat(request: Request, q: str, thread_id: str = "default", user=Depends(verify)):
    logger.info(f"user={user['sub']} q={q} thread={thread_id}")
    try:
        ans = agent.chat(q, thread_id)
        return {"answer": ans}
    except Exception as e:
        logger.exception("chat failed")
        return {"answer": f"服务异常: {e}"}

@app.post("/kb/search")
def kb_search(q: str, top_k: int = 3, user=Depends(verify)):
    from app.rag.retrieval import search
    return {"results": search(q, top_k)}

@app.post("/kb/upload")
def upload(file: UploadFile = File(...), user=Depends(verify)):
    dst = Path("kb_docs") / file.filename
    dst.write_bytes(file.file.read())
    from app.rag.ingest import build_kb
    build_kb()
    return {"status": "ok", "file": file.filename}

@app.post("/workflow/run")
def run_workflow(file: UploadFile = File(...), user=Depends(verify)):
    tmp_dir = Path("/tmp/datachat")
    tmp_dir.mkdir(exist_ok=True)
    dst = tmp_dir / file.filename
    dst.write_bytes(file.file.read())
    return {"report": pipeline.run(str(dst))}

