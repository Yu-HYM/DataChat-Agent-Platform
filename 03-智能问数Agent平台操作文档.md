# 项目三 智能问数 Agent 平台 操作文档

## 文档信息

- 项目名称：DataChat 智能数据助手（RAG 知识库 + LangGraph 多工具 Agent + 文档工作流 + 工程化部署）
- 适用环境：Windows 11（Ollama 走 Windows 宿主机用 GPU）+ WSL2 Ubuntu 22.04（Python 服务）或纯 Windows Python 3.10，RTX 4060 8GB
- 技术栈：Ollama（qwen2.5:7b-instruct-q4_K_M、bge-m3）、LangGraph、Chroma、sentence-transformers、FastAPI、Streamlit、MySQL、Docker Compose
- 前置依赖：项目一产出的 `mall_ads` 指标库（未做项目一可用阶段二的独立建表）
- 三个模块的关系：模块 A（RAG）回答指标口径类问题并给引用溯源；模块 B（Agent）负责自然语言转 SQL 直接查数，是核心；模块 C（工作流）负责文档自动抽取入库。三者共用一个 FastAPI 服务对外

## 架构

```
用户(浏览器/接口)
   │
Streamlit 前端 ──> FastAPI(JWT鉴权/限流/日志)
                     │
              LangGraph Agent(多轮思考-工具调用循环)
               ├── sql_query_tool ──────> MySQL mall_ads(项目一ADS层)
               ├── kb_search_tool ──────> 混合检索(BM25+Chroma向量) -> Rerank -> 引用溯源
               └── calculator_tool
                     │
              Ollama(Windows宿主机, GPU): qwen2.5:7b + bge-m3
              文档工作流(LangGraph): 解析->抽取->校验->入库->报告
```

目录规划：

```
datachat/
  ├── app/
  │   ├── main.py          # FastAPI 入口
  │   ├── agent.py         # LangGraph Agent 核心
  │   ├── tools.py         # 三个工具实现
  │   ├── rag/
  │   │   ├── ingest.py    # 文档解析/清洗/切片/向量化
  │   │   └── retrieval.py # 混合检索+重排
  │   ├── pipeline.py      # 文档处理工作流
  │   └── auth.py          # JWT 鉴权
  ├── web/
  │   └── frontend.py      # Streamlit 前端
  ├── kb_docs/             # 知识库语料(pdf/md/txt)
  ├── chroma_db/           # 向量库持久化
  ├── requirements.txt
  ├── Dockerfile
  └── docker-compose.yml
```

---

## 阶段一 环境准备

### 1.1 Windows 安装 Ollama 并拉模型

从 ollama.com 下载 Windows 版安装。模型按 8GB 显存预算选择：

| 用途 | 模型 | 显存占用 |
|---|---|---|
| Agent 主模型（推理+工具调用+SQL生成） | qwen2.5:7b-instruct-q4_K_M | 约 4.7GB |
| Embedding | bge-m3 | 约 1.2GB |
| Rerank | BAAI/bge-reranker-base（CPU 跑，sentence-transformers 加载） | 占内存不占显存 |

```powershell
ollama pull qwen2.5:7b-instruct-q4_K_M
ollama pull bge-m3
ollama serve   # 默认 11434 端口，安装版开机自启可不执行
ollama run qwen2.5:7b-instruct-q4_K_M "你好"
```

显存控制：两个模型同时驻留约 6GB，接近上限。设置环境变量 `OLLAMA_MAX_LOADED_MODELS=1`、`OLLAMA_KEEP_ALIVE=5m` 让模型用完自动卸载，面试时把这套显存预算讲成亮点。

### 1.2 Python 环境

```bash
# WSL 或 Windows 均可，Python 3.10
mkdir -p datachat && cd datachat
python3 -m venv venv && source venv/bin/activate
```

`requirements.txt`：

```text
fastapi==0.115.*
uvicorn==0.30.*
langgraph==0.2.*
langchain-core==0.3.*
langchain-ollama==0.2.*
langchain-text-splitters==0.3.*
chromadb==0.5.*
sentence-transformers==3.*
rank-bm25==0.2.2
jieba==0.42.*
pypdf==5.*
pymysql==1.1.*
cryptography==42.*
PyJWT==2.9.*
slowapi==0.1.9
loguru==0.7.*
streamlit==1.38.*
requests==2.32.*
python-multipart==0.0.9
```

```bash
pip install -r requirements.txt
# 首次运行会自动下载 bge-m3 与 bge-reranker-base 权重，配置镜像加速
export HF_ENDPOINT=https://hf-mirror.com
```

---

## 阶段二 数据侧准备（Agent 的查询对象）

复用项目一的 `mall_ads` 库；独立做本项目时执行最小建表：

```sql
CREATE DATABASE IF NOT EXISTS mall_ads DEFAULT CHARACTER SET utf8mb4;
USE mall_ads;
CREATE TABLE ads_trade_stats(
  dt VARCHAR(20) PRIMARY KEY, gmv DECIMAL(16,2), order_count BIGINT,
  pay_user_count BIGINT, avg_pay_amount DECIMAL(16,2));
CREATE TABLE ads_repurchase_rate(
  dt VARCHAR(20) PRIMARY KEY, order_user_count BIGINT,
  repurchase_user_count BIGINT, repurchase_rate DECIMAL(10,4));
CREATE TABLE ads_user_rfm(
  user_id VARCHAR(20) PRIMARY KEY, r_score INT, f_score INT,
  m_score INT, rfm_label VARCHAR(10));
-- 示例数据
INSERT INTO ads_trade_stats VALUES
 ('2026-08-16', 182345.67, 128, 96, 1899.43),
 ('2026-08-17', 201234.10, 141, 105, 1916.51),
 ('2026-08-18', 195678.90, 133, 101, 1937.41);
INSERT INTO ads_repurchase_rate VALUES
 ('2026-08-18', 133, 41, 0.3083);
-- 只读账号给 Agent 用
CREATE USER 'agent_ro'@'%' IDENTIFIED BY '123456';
GRANT SELECT ON mall_ads.* TO 'agent_ro'@'%';
FLUSH PRIVILEGES;
```

同时准备知识库语料（放进 `kb_docs/`）：

1. 项目一写的数仓文档：`数仓分层说明.md`、`指标口径说明.md`
2. 一份带表格的 PDF（如公司制度节选，用于验证 PDF 解析）

`指标口径说明.md` 示例内容：

```markdown
# 指标口径说明

## GMV
GMV 指当日已支付订单（status=1）的 total_amount 总和，含运费，不含已取消订单。口径表：ads_trade_stats.gmv。

## 复购率
复购率 = 当日下单用户中历史累计下单次数>=2 的人数 / 当日下单用户总数。口径表：ads_repurchase_rate。

## RFM
R 为最近一次下单距今天数（7天内5分，14天内4分，21天内3分，28天内2分，其余1分）；F 为近30天下单次数；M 为近30天支付金额。rfm_label 为三分拼接。
```

---

## 阶段三 模块 A RAG 知识库（解析-清洗-切片-混合检索-重排）

### 3.1 文档解析与入库 ingest.py

ETL 思路的清洗规则：去页码/页眉页脚、短行过滤、md5 去重、中文优先切片。

```python
#!/usr/bin/env python3
# app/rag/ingest.py
import hashlib, re
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

KB_DIR = Path(__file__).resolve().parents[2] / "kb_docs"
CHROMA_DIR = str(Path(__file__).resolve().parents[2] / "chroma_db")
EMBED_MODEL = "BAAI/bge-m3"

splitter = RecursiveCharacterTextSplitter(
    chunk_size=400, chunk_overlap=60,
    separators=["\n\n", "\n。", "。", "；", "\n", "，", " ", ""])

def parse_pdf(path):
    reader = PdfReader(str(path))
    return "\n".join(p.extract_text() or "" for p in reader.pages)

def parse_file(path: Path):
    if path.suffix.lower() == ".pdf":
        return parse_pdf(path)
    return Path(path).read_text(encoding="utf-8", errors="ignore")

def clean_text(text: str) -> str:
    """ETL 清洗：去页码/纯数字行/过短行/重复行"""
    lines, seen = [], set()
    for ln in text.splitlines():
        s = ln.strip()
        if not s or re.fullmatch(r"[\d\s\-—|]+", s) or len(s) < 4:
            continue
        h = hashlib.md5(s.encode()).hexdigest()
        if h in seen:          # 完全重复行只留一条
            continue
        seen.add(h)
        lines.append(s)
    return "\n".join(lines)

def build_kb():
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(EMBED_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection("kb", embedding_function=ef,
                                          metadata={"hnsw:space": "cosine"})
    for f in KB_DIR.iterdir():
        if f.suffix.lower() not in (".pdf", ".md", ".txt"):
            continue
        text = clean_text(parse_file(f))
        chunks = splitter.split_text(text)
        # 语义级再去重：前 64 字符 md5 相同视为重复切片
        uniq = {}
        for c in chunks:
            uniq.setdefault(hashlib.md5(c[:64].encode()).hexdigest(), c)
        for i, (h, c) in enumerate(uniq.items()):
            col.upsert(ids=[f"{f.name}:{h}"], documents=[c],
                       metadatas=[{"source": f.name, "chunk": i}])
        print(f"{f.name}: {len(uniq)} chunks")
    print("total:", col.count())

if __name__ == "__main__":
    build_kb()
```

```bash
export HF_ENDPOINT=https://hf-mirror.com
python -m app.rag.ingest
# 预期输出每个文件的 chunk 数与 total
```

### 3.2 混合检索与重排 retrieval.py

```python
#!/usr/bin/env python3
# app/rag/retrieval.py
import jieba
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from pathlib import Path

CHROMA_DIR = str(Path(__file__).resolve().parents[2] / "chroma_db")
EMBED_MODEL = "BAAI/bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-base"   # CPU 运行，避开显存

_reranker = _docs = _meta = _bm25 = None

def _lazy_init():
    """首次调用时把库内文档载入内存建 BM25 索引"""
    global _reranker, _docs, _meta, _bm25
    if _docs is not None:
        return
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(EMBED_MODEL)
    col = chromadb.PersistentClient(path=CHROMA_DIR).get_collection("kb", embedding_function=ef)
    data = col.get(include=["documents", "metadatas"])
    _docs = data["documents"]
    id2idx = {i: n for n, i in enumerate(col.get()["ids"])}
    _meta = data["metadatas"]
    _bm25 = BM25Okapi([list(jieba.cut(d)) for d in _docs])
    _reranker = CrossEncoder(RERANK_MODEL, device="cpu")
    return id2idx

def search(question: str, top_k: int = 3):
    """BM25 关键词 + Chroma 向量 -> 融合 -> CrossEncoder 重排"""
    id2idx = _lazy_init()
    # 1 关键词召回
    kw_hits = {}
    scores = _bm25.get_scores(list(jieba.cut(question)))
    for idx in scores.argsort()[::-1][:10]:
        kw_hits[int(idx)] = float(scores[idx])
    # 2 向量召回
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(EMBED_MODEL)
    col = chromadb.PersistentClient(path=CHROMA_DIR).get_collection("kb", embedding_function=ef)
    res = col.query(query_texts=[question], n_results=10)
    vec_hits = {id2idx[i]: 10 - r for r, i in enumerate(res["ids"][0])}
    # 3 融合两路召回
    merged = {}
    for idx in set(kw_hits) | set(vec_hits):
        merged[idx] = kw_hits.get(idx, 0) + vec_hits.get(idx, 0)
    cands = sorted(merged, key=merged.get, reverse=True)[:8]
    # 4 重排
    pairs = [(question, _docs[i]) for i in cands]
    scores = _reranker.predict(pairs)
    top = sorted(zip(cands, scores), key=lambda x: -x[1])[:top_k]
    return [{"content": _docs[i], "source": _meta[i]["source"],
             "score": float(s)} for i, s in top]

if __name__ == "__main__":
    for r in search("复购率是怎么定义的"):
        print(round(r["score"], 3), r["source"], r["content"][:80])
```

```bash
python -m app.rag.retrieval
# 预期：命中《指标口径说明.md》中复购率段落
```

---

## 阶段四 模块 B LangGraph 多工具 Agent（核心）

### 4.1 三个工具 tools.py

工具函数签名与 docstring 会转成模型可见的工具描述，务必写清楚。

```python
#!/usr/bin/env python3
# app/tools.py
import ast, operator, re
import pymysql
from app.rag import retrieval

MYSQL_CONF = dict(host="localhost", user="agent_ro", password="123456",
                  database="mall_ads", charset="utf8mb4")

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}

def _safe_eval(node):
    """AST 白名单求值，禁止任意代码执行"""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    raise ValueError("不支持的运算")

def calculator(expression: str) -> str:
    """四则运算计算器。expression: 例如 '1.13 * 1899.43'"""
    tree = ast.parse(expression, mode="eval")
    return str(round(_safe_eval(tree.body), 4))

def sql_query(sql: str) -> str:
    """查询数仓 ADS 指标库（只读）。sql: 一条 SELECT 语句。
    库表：ads_trade_stats(dt,gmv,order_count,pay_user_count,avg_pay_amount)
         ads_repurchase_rate(dt,repurchase_rate) ads_user_rfm(user_id,rfm_label)"""
    s = sql.strip().rstrip(";")
    if not re.match(r"^(select|with|show)\b", s, re.I):
        return "错误：仅允许 SELECT 查询"
    if ";" in s or re.search(r"\b(insert|update|delete|drop|alter|create|grant)\b", s, re.I):
        return "错误：检测到危险操作，已拦截"
    try:
        conn = pymysql.connect(**MYSQL_CONF)
        cur = conn.cursor()
        cur.execute(s)
        rows = cur.fetchall()
        conn.close()
        return "\n".join(str(r) for r in rows[:20]) or "查询结果为空"
    except Exception as e:
        return f"SQL执行出错: {e}"   # 错误回传给 Agent，让它自己修正重试

def kb_search(question: str) -> str:
    """检索数仓文档知识库，回答指标口径/字段含义类问题，返回带出处的内容"""
    hits = retrieval.search(question)
    if not hits:
        return "知识库未命中"
    return "\n\n".join(f"[来源:{h['source']}]\n{h['content']}" for h in hits)
```

### 4.2 Agent 状态图 agent.py

```python
#!/usr/bin/env python3
# app/agent.py
from typing import Annotated, TypedDict
from langchain_ollama import ChatOllama
from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from app.tools import sql_query, kb_search, calculator
import os

SYSTEM_PROMPT = """你是电商数仓的智能问数助手，可调用以下工具：
1. sql_query：查询指标库 MySQL（mall_ads 库，含 ads_trade_stats 每日GMV/订单数/客单价、
   ads_repurchase_rate 复购率、ads_user_rfm 用户分层）。
2. kb_search：查询指标口径与数仓文档，口径类问题优先用它。
3. calculator：四则运算。
规则：
- 用户问数值先想清楚需要哪张表哪个字段，生成标准 MySQL SELECT，日期用字符串比较如 dt>='2026-08-01'。
- sql_query 返回错误时，阅读错误信息修正 SQL 后重试，最多 3 次。
- 回答末尾注明数据日期或引用来源。不确定就说不确定，不要编造数字。"""

class AgentState(TypedDict):
    messages: Annotated[list, lambda a, b: a + b]

tools = [sql_query, kb_search, calculator]
llm = ChatOllama(model="qwen2.5:7b-instruct-q4_K_M",
                 base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                 temperature=0).bind_tools(tools)

def agent_node(state):
    msgs = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in msgs):
        msgs = [SystemMessage(content=SYSTEM_PROMPT)] + msgs
    return {"messages": [llm.invoke(msgs)]}

def route(state):
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", route, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")
memory = MemorySaver()          # 会话记忆：按 thread_id 保存历史
agent_app = graph.compile(checkpointer=memory)

def chat(question: str, thread_id: str = "default") -> str:
    out = agent_app.invoke({"messages": [("user", question)]},
                           config={"configurable": {"thread_id": thread_id}})
    return out["messages"][-1].content

if __name__ == "__main__":
    print(chat("最近三天的GMV是多少"))
    print(chat("复购率的口径是什么"))
    print(chat("把最新一天的GMV乘以1.13是多少"))
```

```bash
python -m app.agent
```

预期行为（多轮工具调用闭环）：

1. 问「最近三天的GMV」→ Agent 生成 `SELECT dt,gmv FROM ads_trade_stats ORDER BY dt DESC LIMIT 3` → 工具返回 3 行 → Agent 总结回答
2. 问「复购率口径」→ Agent 调 kb_search → 返回带 `[来源:指标口径说明.md]` 的内容
3. SQL 报错场景：手工在 tools.py 抛错实验 → Agent 读错误信息自动修正重试

常见问题：

| 现象 | 处理 |
|---|---|
| 模型不调工具直接闲聊 | system prompt 强调数值问题必须调用工具；temperature 设 0 |
| 工具调用参数 json 偶发格式错 | 重试即可；面试可讲小模型工具调用稳定性与重试设计 |
| 长对话超上下文 | MemorySaver 存全量历史，长会话截断早期 messages |

---

## 阶段五 模块 C 文档处理工作流 pipeline.py

业务场景：上传业务文档 → 解析 → LLM 抽取结构化信息 → 校验 → 入库 → 生成报告。

```python
#!/usr/bin/env python3
# app/pipeline.py
import json
import pymysql
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from app.rag.ingest import parse_file, clean_text
import os

MYSQL_CONF = dict(host="localhost", user="root", password="123456",
                  database="mall_ads", charset="utf8mb4")
llm = ChatOllama(model="qwen2.5:7b-instruct-q4_K_M",
                 base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                 temperature=0, format="json")

EXTRACT_PROMPT = """从以下文本抽取业务信息，输出 json：
{{"customer": "客户名或null", "product": "产品名或null",
  "amount": 数字或null, "date": "yyyy-MM-dd或null", "summary": "50字内摘要"}}
文本：{text}"""

def node_parse(state):
    state["text"] = clean_text(parse_file(state["path"]))
    return state

def node_extract(state):
    out = llm.invoke(EXTRACT_PROMPT.format(text=state["text"][:3000]))
    state["info"] = json.loads(out.content)
    return state

def node_validate(state):
    info = state["info"]
    if info.get("amount") is not None:
        info["amount"] = float(info["amount"])
    if not info.get("customer"):
        state["error"] = "未抽取到客户名"
    return state

def node_load(state):
    if state.get("error"):
        return state
    conn = pymysql.connect(**MYSQL_CONF)
    conn.cursor().execute(
        """CREATE TABLE IF NOT EXISTS doc_extract(
           id BIGINT AUTO_INCREMENT PRIMARY KEY, customer VARCHAR(64),
           product VARCHAR(64), amount DECIMAL(16,2), date VARCHAR(20),
           summary VARCHAR(255), src_file VARCHAR(128))""")
    i = state["info"]
    conn.cursor().execute(
        "INSERT INTO doc_extract(customer,product,amount,date,summary,src_file) "
        "VALUES(%s,%s,%s,%s,%s,%s)",
        (i.get("customer"), i.get("product"), i.get("amount"),
         i.get("date"), i.get("summary"), state["path"]))
    conn.commit(); conn.close()
    return state

def node_report(state):
    if state.get("error"):
        state["report"] = f"处理失败: {state['error']}"
    else:
        i = state["info"]
        state["report"] = (f"已入库: 客户[{i.get('customer')}] 产品[{i.get('product')}] "
                           f"金额[{i.get('amount')}] 日期[{i.get('date')}] 摘要[{i.get('summary')}]")
    return state

def build():
    g = StateGraph(dict)
    for name, fn in [("parse", node_parse), ("extract", node_extract),
                     ("validate", node_validate), ("load", node_load),
                     ("report", node_report)]:
        g.add_node(name, fn)
    g.add_edge(START, "parse")
    g.add_edge("parse", "extract"); g.add_edge("extract", "validate")
    g.add_edge("validate", "load"); g.add_edge("load", "report")
    g.add_edge("report", END)
    return g.compile()

def run(path: str) -> str:
    return build().invoke({"path": path})["report"]

if __name__ == "__main__":
    print(run("kb_docs/订单合同样例.md"))   # 自备一份样例文档
```

---

## 阶段六 工程化封装（FastAPI + 鉴权 + 限流 + 日志）

### 6.1 JWT 鉴权 auth.py

```python
#!/usr/bin/env python3
# app/auth.py
import time
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET = "change-me-in-prod"
bearer = HTTPBearer(auto_error=False)

def make_token(user: str) -> str:
    return jwt.encode({"sub": user, "exp": int(time.time()) + 7200},
                      SECRET, algorithm="HS256")

def verify(cred: HTTPAuthorizationCredentials = Depends(bearer)):
    if cred is None:
        raise HTTPException(401, "缺少 token")
    try:
        return jwt.decode(cred.credentials, SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "token 过期")
    except jwt.PyJWTError:
        raise HTTPException(401, "token 无效")
```

### 6.2 服务入口 main.py

```python
#!/usr/bin/env python3
# app/main.py
from pathlib import Path
from loguru import logger
from fastapi import FastAPI, Depends, UploadFile, File, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from app import agent, pipeline
from app.auth import verify, make_token

logger.add("logs/datachat.log", rotation="10 MB", retention="7 days", encoding="utf-8")
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="DataChat 智能问数平台")
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
def rate_hit(request, exc):
    return JSONResponse({"error": "请求过于频繁"}, status_code=429)

@app.post("/auth/token")
def token(user: str = "demo"):
    return {"token": make_token(user), "expires_in": 7200}

@app.post("/chat")
@limiter.limit("10/minute")
def chat(request: Request, q: str, thread_id: str = "default", user=Depends(verify)):
    logger.info(f"user={user['sub']} q={q} thread={thread_id}")
    try:
        return {"answer": agent.chat(q, thread_id)}
    except Exception as e:
        logger.exception("chat failed")
        return {"answer": f"服务异常: {e}"}

@app.post("/kb/upload")
def upload(file: UploadFile = File(...), user=Depends(verify)):
    dst = Path("kb_docs") / file.filename
    dst.write_bytes(file.file.read())
    from app.rag.ingest import build_kb
    build_kb()                       # 简化处理：全量重建
    return {"status": "ok", "file": file.filename}

@app.post("/workflow/run")
def run_workflow(file: UploadFile = File(...), user=Depends(verify)):
    dst = Path("/tmp") / file.filename
    dst.write_bytes(file.file.read())
    return {"report": pipeline.run(str(dst))}
```

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9000
# 验证
curl -X POST "localhost:9000/auth/token?user=alice"
# 拿到 token 后
curl -H "Authorization: Bearer <token>" -X POST "localhost:9000/chat?q=最新一天的复购率&thread_id=t1"
```

### 6.3 Streamlit 前端 web/frontend.py

```python
#!/usr/bin/env python3
# web/frontend.py
import os
import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:9000")
st.set_page_config(page_title="DataChat")
st.title("DataChat 智能问数助手")

if "token" not in st.session_state:
    st.session_state.token = requests.post(f"{API}/auth/token").json()["token"]
if "history" not in st.session_state:
    st.session_state.history = []

q = st.chat_input("例如：最近三天GMV / 复购率口径 / 1.13*最新客单价")
if q:
    st.session_state.history.append(("user", q))
    with st.spinner("Agent 思考中..."):
        try:
            r = requests.post(f"{API}/chat",
                              headers={"Authorization": f"Bearer {st.session_state.token}"},
                              params={"q": q, "thread_id": "web"}, timeout=180)
            ans = r.json()["answer"]
        except Exception as e:
            ans = f"请求失败: {e}"
    st.session_state.history.append(("ai", ans))

for role, text in st.session_state.history:
    st.chat_message(role).write(text)
```

```bash
streamlit run web/frontend.py
# 浏览器 8501，多轮上下文由 thread_id=web + 服务端 MemorySaver 维持
```

---

## 阶段七 Docker Compose 一键部署

Ollama 留在 Windows 宿主机（保住 GPU），容器内服务通过 `host.docker.internal` 访问。

`Dockerfile`：

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY . .
EXPOSE 9000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
```

`docker-compose.yml`：

```yaml
services:
  api:
    build: .
    ports: ["9000:9000"]
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - ./chroma_db:/app/chroma_db
      - ./kb_docs:/app/kb_docs
      - ./logs:/app/logs

  web:
    build: .
    command: streamlit run web/frontend.py --server.address 0.0.0.0
    ports: ["8501:8501"]
    environment:
      - API_URL=http://api:9000
    depends_on: [api]
```

```bash
docker compose up -d --build
docker compose ps   # 预期 api、web 两个服务 Up
```

---

## 最终验证清单

| 模块 | 验证问题 | 期望 |
|---|---|---|
| RAG | 复购率是怎么定义的 | 返回口径段落并带来源 |
| RAG | PDF 表格内容 | 能命中 PDF 切片 |
| Agent SQL | 最近三天的GMV | 调 sql_query，返回 3 行并总结 |
| Agent 安全 | 让它删表 | 工具层拦截危险语句 |
| Agent 溯源 | GMV 口径 | 走 kb_search 而非 SQL |
| Agent 串联 | 最新客单价乘1.13 | sql_query + calculator 两步 |
| 记忆 | 追问"那订单数呢" | 同 thread_id 理解上下文 |
| 安全 | 无 token 调 /chat | 401 |
| 限流 | 1 分钟连打 11 次 | 429 |
| 工作流 | 上传订单样例文档 | doc_extract 入库 + 返回报告 |
| 部署 | docker compose up | 前端可正常问答 |

## 高频面试问题对照

| 问题 | 对应实现 |
|---|---|
| 为什么选 LangGraph 而不是 AgentExecutor | 显式状态图、条件边可控循环、checkpointer 内置记忆，工业界主流 |
| 幻觉怎么降低 | 口径类问题强制走 RAG 引用溯源；数值必须来自 SQL 结果；prompt 声明不确定就说不确定 |
| 检索效果怎么优化 | BM25+向量混合召回融合，CrossEncoder 重排，切片 400 字带 60 重叠 |
| SQL 误操作怎么防 | 只读账号 + 正则白名单只放行 SELECT + 单语句校验，工具层双保险 |
| Agent 出错怎么办 | SQL 异常文本回传给模型自动修正重试；FastAPI 全局异常日志 |
| 和大数据专业怎么结合 | Agent 查询的库就是自己搭的数仓 ADS 层，理解指标口径、分层和调度全链路 |
| 8G 显存怎么跑 7B | 4bit 量化约 4.7G + bge-m3 1.2G，rerank 放 CPU，OLLAMA_KEEP_ALIVE 控制卸载 |
