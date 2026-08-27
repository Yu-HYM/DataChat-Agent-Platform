# DataChat 智能问数平台 — Code Wiki

> 代码文档，覆盖项目结构、核心模块、数据流、配置说明、开发指南

---

## 一、项目结构

```
datachat/
├── app/                          # Python 后端（FastAPI + LangGraph）
│   ├── __init__.py
│   ├── main.py                   # FastAPI 入口（路由/鉴权/限流/日志）
│   ├── agent.py                  # LangGraph Agent 核心（状态图/工具绑定/会话记忆）
│   ├── tools.py                  # Agent 三工具（sql_query/kb_search/calculator）
│   ├── pipeline.py               # 文档处理工作流（5节点流水线）
│   ├── auth.py                   # JWT 鉴权
│   └── rag/
│       ├── __init__.py
│       ├── ingest.py             # RAG 入库（解析/清洗/切片/向量化）
│       └── retrieval.py          # RAG 检索（BM25+向量混合+CrossEncoder重排）
├── web/
│   └── frontend.py               # Streamlit 前端（BI风格UI）
├── kb_docs/                      # 知识库语料（md/txt/pdf）
│   ├── A01-指标口径手册.md
│   ├── A02-库表结构说明.md
│   ├── A03-数据加工说明.md
│   └── 订单合同样例.md
├── chroma_db/                    # ChromaDB 向量库持久化目录
├── logs/                         # 日志目录
├── scripts/                      # 开发/调试脚本
├── requirements.txt              # Python 依赖
├── Dockerfile                    # 容器镜像构建
├── docker-compose.yml            # Docker Compose 编排
├── .dockerignore
└── deploy.sh                     # 一键部署脚本
```

---

## 二、核心模块详解

### 2.1 app/main.py — FastAPI 服务入口

**职责**：对外暴露 REST API，处理鉴权、限流、日志

**路由表**：

| 方法 | 路径 | 功能 | 鉴权 | 限流 |
|---|---|---|---|---|
| GET | `/` | 健康检查 | 无 | 无 |
| POST | `/auth/token` | 获取 JWT Token | 无 | 无 |
| POST | `/chat` | Agent 智能问答 | 需要 | 10次/分 |
| POST | `/kb/search` | RAG 知识库检索 | 需要 | 无 |
| POST | `/kb/upload` | 上传文档入库（全量重建） | 需要 | 无 |
| POST | `/workflow/run` | 文档工作流处理 | 需要 | 无 |

**关键实现**：

```python
# JWT 鉴权：HTTPBearer 自动从 Authorization 头提取 token
bearer = HTTPBearer(auto_error=False)

# 限流：SlowAPI 基于 IP
limiter = Limiter(key_func=get_remote_address)

# 日志：Loguru 写入 logs/datachat.log
logger.add("logs/datachat.log", rotation="10 MB", retention="7 days")
```

**请求流程**：
```
Client → FastAPI Route → Depends(verify JWT) → 业务逻辑 → 返回
                                                        ↓
                                              agent.chat() / pipeline.run()
```

---

### 2.2 app/agent.py — LangGraph Agent 核心

**职责**：构建多工具 Agent，实现思考-工具调用循环

**状态图拓扑**：
```
START ──→ agent_node ──(有tool_calls)──→ ToolNode ──→ agent_node
                          │
                          └──(无tool_calls)──→ END
```

**核心数据结构**：
```python
class AgentState(TypedDict):
    messages: Annotated[list, lambda a, b: a + b]  # 消息列表，追加合并
```

**SystemPrompt 包含 6 板块**：
1. 可用工具列表
2. 4 张表结构与业务含义（ads_trade_stats / ads_repurchase_rate / ads_user_rfm / doc_extract）
3. 指标口径（GMV/客单价/复购率/RFM）
4. 数据范围（2026-08-19~21）
5. 工具选择指引
6. 关键规则（日期/重试/金额格式）

**doc_extract 预查询机制**：
```python
DOC_KEYWORDS = ["入库", "合同", "订单", "客户", "文档", "最新", "新增", "写入", "记录"]

def _pre_query_doc_extract(question: str) -> str:
    """命中关键词时直接查 doc_extract，结果注入上下文"""
    if any(kw in question for kw in DOC_KEYWORDS):
        # SELECT ... FROM doc_extract ORDER BY id DESC LIMIT 10
        # 返回结果作为 SystemMessage 注入
```

**线程安全**：
```python
# 每个请求独立设置 question，避免并发串扰
set_question(user_q)  # 存入 threading.local()
```

**对外入口**：
```python
def chat(question: str, thread_id: str = "default") -> str:
    out = agent_app.invoke(
        {"messages": [("user", question)]},
        config={"configurable": {"thread_id": thread_id}}
    )
    return out["messages"][-1].content
```

---

### 2.3 app/tools.py — Agent 三工具

#### sql_query(sql, question)

**功能**：只读 MySQL 查询，支持 doc_extract 关键词自动拦截

**安全三重防线**：
```
1. 数据库层：agent_ro 只读账号（仅 SELECT 权限）
2. 正则白名单：^select|^with|^show 才放行
3. 关键词黑名单：insert/update/delete/drop/alter/create/grant 全部拦截
4. 单语句校验：分号检测，防止拼接攻击
```

**doc_extract 自动拦截**：
```python
DOC_KEYWORDS = ["入库", "合同", "订单", "客户", "文档", "最新", ...]
if any(kw in effective_q for kw in DOC_KEYWORDS):
    # 直接查 doc_extract 表，不走 LLM 生成 SQL
    return query_doc_extract()
```

**MySQL 配置（环境变量驱动）**：
```python
MYSQL_CONF = dict(
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    user=os.getenv("MYSQL_USER", "agent_ro"),
    password=os.getenv("MYSQL_PASSWORD", "123456"),
    database=os.getenv("MYSQL_DATABASE", "mall_ads"),
    charset="utf8mb4",
)
```

#### kb_search(question)

**功能**：RAG 混合检索，返回带来源的文档片段

**流程**：
```
question → jieba 分词 → BM25 关键词召回(Top10)
        → BGE-M3 向量召回(Top10)
        → 加权融合 → Top8 候选
        → CrossEncoder 重排 → Top3 结果
```

#### calculator(expression)

**功能**：AST 安全四则运算，禁止任意代码执行

**安全实现**：
```python
def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    raise ValueError("不支持的运算")  # 其他类型一律拒绝
```

**支持运算**：加/减/乘/除/幂 + 负数，不支持变量/函数调用/属性访问

---

### 2.4 app/rag/ingest.py — RAG 入库

**职责**：文档解析 → 清洗 → 切片 → 向量化 → ChromaDB 持久化

**处理流程**：
```
kb_docs/*.md/pdf/txt
  ↓ parse_file()          # pypdf 读 PDF / read_text 读 md
  ↓ clean_text()          # ETL 清洗：去页码/纯数字行/过短行/重复行(md5)
  ↓ splitter.split_text() # RecursiveCharacterTextSplitter(400字/60字重叠)
  ↓ 切片级去重            # 前64字符 md5 相同视为重复
  ↓ Ollama bge-m3 嵌入    # GPU 加速，1024 维
  ↓ ChromaDB upsert       # 集合 datachat_kb，余弦空间
```

**嵌入函数适配**：
```python
class OllamaEF:
    """适配 chromadb 嵌入函数接口，内部调 Ollama API"""
    def __init__(self, base_url, model):
        self.ollama = OllamaEmbeddings(base_url=base_url, model=model)
    def __call__(self, input):
        return self.ollama.embed_documents(input)
```

**运行方式**：
```bash
python -m app.rag.ingest  # 全量重建
```

---

### 2.5 app/rag/retrieval.py — RAG 检索

**职责**：混合检索 + CrossEncoder 重排

**三段式检索**：
```
① BM25 关键词召回
   - jieba 分词 + BM25Okapi 评分
   - 取 Top10
② Chroma 向量召回
   - Ollama bge-m3 嵌入 + 余弦相似度
   - 取 Top10
③ 融合 + 重排
   - 加权求和融合两路结果
   - CrossEncoder(bge-reranker-base, CPU) 精排
   - 返回 Top3
```

**惰性初始化**：
```python
def _lazy_init():
    """首次调用时加载文档到内存建 BM25 索引"""
    global _docs, _bm25, _reranker  # 全局缓存，避免重复加载
    if _docs is not None:
        return
    # 加载 Chroma 数据 → 建 BM25 → 加载 Reranker
```

**降级策略**：Reranker 加载失败时自动降级为融合分数排序，不影响基本检索

---

### 2.6 app/pipeline.py — 文档工作流

**职责**：业务文档自动解析 → LLM 抽取 → 校验 → 入库 → 报告

**5 节点流水线**：
```
START → node_parse → node_extract → node_validate → node_load → node_report → END
```

| 节点 | 输入 | 输出 | 异常处理 |
|---|---|---|---|
| parse | 文件路径 | 清洗后文本 | 读文件异常 |
| extract | 文本 | JSON 结构化信息 | LLM JSON 解析失败 try-except |
| validate | JSON | 校验后数据 | 客户名为空标记 error |
| load | 校验数据 | MySQL 入库 | 入库异常标记 error |
| report | 状态 | 报告文本 | error 时返回失败原因 |

**LLM 抽取 Prompt**：
```
从以下文本抽取业务信息，输出 json：
{"customer": "客户名或null", "product": "产品名或null",
 "amount": 数字或null, "date": "yyyy-MM-dd或null", "summary": "50字内摘要"}
```

**JSON 解析容错**：
```python
raw = out.content.strip()
if raw.startswith("```"):
    raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
state["info"] = json.loads(raw)
```

**运行方式**：
```bash
python -m app.pipeline kb_docs/订单合同样例.md
```

---

### 2.7 app/auth.py — JWT 鉴权

**职责**：Token 签发与验证

**配置**：
```python
SECRET = "change-me-in-prod"  # 生产环境必须修改
TOKEN_EXPIRE = 7200           # 2 小时
```

**签发流程**：
```python
def make_token(user: str) -> str:
    return jwt.encode({"sub": user, "exp": int(time.time()) + 7200}, SECRET)
```

**验证流程**：
```python
def verify(cred) -> dict:
    # 1. 检查 token 是否存在
    # 2. PyJWT 解码（自动校验过期时间）
    # 3. 返回 payload（含 sub/username）
    # 4. 异常：401 缺少/过期/无效
```

---

### 2.8 web/frontend.py — Streamlit 前端

**职责**：用户交互界面，BI 风格

**页面结构**：
```
┌─────────────────────────────────────────────┐
│ 智能问数  [开发环境]              分析师 [A] │  ← Header
├──────────┬──────────────────────────────────┤
│ DataChat │  [功能切换]                        │
│ 智能平台 │  ┌── Agent 智能问答 ──────────┐   │
│          │  │ 欢迎卡片 + 快捷按钮       │   │
│ ● Agent  │  │ 对话区域 + KPI 表格       │   │
│   RAG    │  │ 输入框                    │   │
│   工作流 │  └──────────────────────────┘   │
│          │  ┌── RAG 知识库检索 ─────────┐   │
│ 技术栈   │  │ 检索 + 结果列表           │   │
│ API:9000 │  └──────────────────────────┘   │
│ 数据源   │  ┌── 文档处理工作流 ─────────┐   │
│ LLM      │  │ 文档抽取 + 知识库管理    │   │
│ Embed    │  └──────────────────────────┘   │
│ Rerank   │                                  │
└──────────┴──────────────────────────────────┘
```

**API 交互**：
```python
API_URL = os.getenv("API_URL", "http://localhost:9000")

# 自动获取 token
if "token" not in st.session_state:
    st.session_state.token = requests.post(f"{API_URL}/auth/token").json()["token"]

# Agent 问答
r = requests.post(f"{API_URL}/chat",
    headers={"Authorization": f"Bearer {token}"},
    params={"q": q, "thread_id": "web"}, timeout=180)
```

**UI 美化**：
- 自定义 CSS 隐藏 Deploy 按钮、原生 Header/Toolbar
- 商务配色：主色 `#1677ff`、背景 `#f5f7fa`、卡片白底
- KPI 卡片渲染数值结果
- 金额千分位格式化
- 响应耗时展示

---

## 三、数据流

### 3.1 Agent 问答数据流

```
用户输入: "最近三天GMV是多少"
  ↓
Streamlit chat_input
  ↓ POST /chat?q=最近三天GMV是多少&thread_id=web
FastAPI verify() → agent.chat("最近三天GMV是多少", "web")
  ↓
agent_app.invoke({messages: [("user", ...)]}, {thread_id: "web"})
  ↓
agent_node:
  ├── _extract_last_user_msg() → "最近三天GMV是多少"
  ├── set_question("最近三天GMV是多少")  → threading.local()
  ├── _pre_query_doc_extract("最近三天GMV是多少") → 空(无命中关键词)
  └── llm.invoke(messages) → 生成 tool_call: sql_query("SELECT dt,gmv FROM ads_trade_stats ORDER BY dt DESC LIMIT 3")
  ↓
ToolNode:
  └── sql_query("SELECT dt,gmv...", "最近三天GMV是多少"):
      ├── question 无命中 DOC_KEYWORDS → 走 SQL 流程
      ├── 正则白名单: SELECT ✓
      ├── 关键词黑名单: 无危险词 ✓
      ├── pymysql 连接 mall_ads
      ├── 执行 SQL → [(2026-08-21, 410354.42), (2026-08-20, 456966.77), (2026-08-19, 591020.68)]
      └── 返回结果文本
  ↓
agent_node (第二次):
  └── llm.invoke(messages + tool_result) → 生成最终回答
  ↓
返回: "最近三天GMV分别为：2026-08-21: 410,354.42元；2026-08-20: 456,966.77元；2026-08-19: 591,020.68元"
```

### 3.2 RAG 检索数据流

```
用户输入: "复购率是怎么定义的"
  ↓ POST /kb/search?q=复购率是怎么定义的&top_k=3
FastAPI → retrieval.search("复购率是怎么定义的")
  ↓
_lazy_init():
  ├── ChromaDB 加载 datachat_kb 集合
  ├── 内存缓存 _docs, _meta, _bm25
  └── 加载 CrossEncoder(bge-reranker-base)
  ↓
BM25: jieba.cut("复购率是怎么定义的") → BM25Okapi 评分 → Top10
  ↓
向量: Ollama bge-m3 embed → Chroma query → Top10
  ↓
融合: kw_hits + vec_hits → 加权求和 → Top8
  ↓
重排: CrossEncoder.predict([(q, doc1), (q, doc2), ...]) → Top3
  ↓
返回: [{content, source, score}, ...]
```

### 3.3 文档工作流数据流

```
用户上传: 订单合同样例.md
  ↓ POST /workflow/run
FastAPI → pipeline.run("/tmp/datachat/订单合同样例.md")
  ↓
StateGraph.invoke():
  ├── node_parse: parse_file() + clean_text() → 清洗后文本
  ├── node_extract: llm.invoke(EXTRACT_PROMPT.format(text)) → JSON {"customer": "北京星云科技", ...}
  ├── node_validate: float(amount), 检查 customer 非空
  ├── node_load: CREATE TABLE IF NOT EXISTS doc_extract + INSERT
  └── node_report: "已入库: 客户[北京星云科技有限公司] ..."
  ↓
返回: {"report": "已入库: 客户[北京星云科技有限公司] 产品[企业级数据中台标准版] 金额[368000.0] 日期[2026-08-15] ..."}
```

---

## 四、配置说明

### 4.1 环境变量

| 变量 | 默认值 | 说明 | 生效范围 |
|---|---|---|---|
| OLLAMA_BASE_URL | http://172.30.224.1:11434 | Ollama 服务地址 | agent.py / pipeline.py / retrieval.py / ingest.py |
| MYSQL_HOST | localhost | MySQL 主机 | tools.py |
| MYSQL_PORT | 3306 | MySQL 端口 | tools.py |
| MYSQL_USER | agent_ro | MySQL 用户名 | tools.py |
| MYSQL_PASSWORD | 123456 | MySQL 密码 | tools.py |
| MYSQL_DATABASE | mall_ads | MySQL 数据库 | tools.py |
| HF_ENDPOINT | https://hf-mirror.com | HuggingFace 镜像 | retrieval.py / Dockerfile |
| API_URL | http://localhost:9000 | FastAPI 地址 | frontend.py |

### 4.2 Docker Compose 环境变量

| 变量 | API 容器 | Web 容器 | 说明 |
|---|---|---|---|
| OLLAMA_BASE_URL | http://host.docker.internal:11434 | 同左 | 容器访问宿主机 Ollama |
| MYSQL_HOST | host.docker.internal | 同左 | 容器访问宿主机 MySQL |
| MYSQL_USER | agent_ro | 同左 | 只读账号 |
| API_URL | — | http://api:9000 | Web 容器访问 API 容器（Docker 内部网络） |

### 4.3 ChromaDB 集合

| 属性 | 值 |
|---|---|
| 集合名 | datachat_kb |
| 嵌入函数 | OllamaEF(Ollama bge-m3) |
| 距离度量 | cosine |
| 持久化路径 | ./chroma_db |
| 文档数 | 动态（kb_docs 下文件数 × 切片数） |

### 4.4 MySQL 表结构

**ads_trade_stats（每日交易事实表）**

| 字段 | 类型 | 说明 |
|---|---|---|
| dt | VARCHAR(20) PK | 日期，格式 YYYY-MM-DD |
| gmv | DECIMAL(16,2) | 成交总额（元） |
| order_count | BIGINT | 成交订单数 |
| pay_user_count | BIGINT | 支付用户数 |
| avg_pay_amount | DECIMAL(16,2) | 客单价（元） |

**ads_repurchase_rate（每日复购统计表）**

| 字段 | 类型 | 说明 |
|---|---|---|
| dt | VARCHAR(20) PK | 日期 |
| order_user_count | BIGINT | 当日下单用户数 |
| repurchase_user_count | BIGINT | 复购用户数 |
| repurchase_rate | DECIMAL(10,4) | 复购率 |

**ads_user_rfm（RFM 分层表）**

| 字段 | 类型 | 说明 |
|---|---|---|
| dt | VARCHAR(20) | 日期 |
| user_id | VARCHAR(20) | 用户 ID |
| r_score | INT | 最近购买得分（1-5） |
| f_score | INT | 购买频次得分（1-5） |
| m_score | INT | 消费金额得分（1-5） |
| rfm_label | VARCHAR(10) | RFM 分群标签 |

**doc_extract（文档抽取结果表）**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK AUTO_INCREMENT | 自增 ID |
| customer | VARCHAR(64) | 客户名称 |
| product | VARCHAR(64) | 产品名称 |
| amount | DECIMAL(16,2) | 金额（元） |
| date | VARCHAR(20) | 签订日期 |
| summary | VARCHAR(255) | 业务摘要 |
| src_file | VARCHAR(128) | 来源文件 |

---

## 五、部署指南

### 5.1 Docker Compose 部署

**前置条件**：
- Docker Desktop 已安装（WSL2 后端）
- Ollama 已启动并拉取 qwen2.5:7b + bge-m3
- MySQL mall_ads 库就绪
- 端口 9000/8501 未被占用

**部署命令**：
```bash
cd datachat
docker compose up -d --build
```

**验证**：
```bash
docker compose ps
# 预期：datachat-api Up(healthy), datachat-web Up
```

**访问**：
- 前端：http://localhost:8501
- API：http://localhost:9000
- Ollama：http://localhost:11434

**停止/重启**：
```bash
docker compose down          # 停止并删除容器
docker compose restart       # 重启
docker compose logs -f api   # 查看 API 日志
```

### 5.2 本地开发模式

```bash
# 终端1：启动 WSL MySQL
wsl -d Ubuntu-22.04 -e "sudo service mysql start"

# 终端2：启动 FastAPI（WSL）
wsl -d Ubuntu-22.04 -e "cd /home/hadoop/datachat && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 9000"

# 终端3：启动 Streamlit（WSL）
wsl -d Ubuntu-22.04 -e "cd /home/hadoop/datachat && source venv/bin/activate && streamlit run web/frontend.py --server.address 0.0.0.0 --server.port 8501"

# Ollama（Windows 宿主机，已自启）
```

### 5.3 重建 RAG 知识库

```bash
# 方式1：API 接口
curl -X POST "http://localhost:9000/kb/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@kb_docs/A01-指标口径手册.md"

# 方式2：命令行
python -m app.rag.ingest
```

---

## 六、安全说明

| 风险点 | 防护措施 | 说明 |
|---|---|---|
| SQL 注入 | 只读账号 + 正则白名单 + 关键词黑名单 + 分号检测 | 四重防线 |
| 任意代码执行 | AST 白名单求值计算器 | 仅支持数字+四则运算 |
| LLM Prompt 注入 | SystemPrompt 明确工具边界 | 限制 LLM 只能调用三工具 |
| 未授权访问 | JWT Bearer Token 鉴权 | 401 拦截 |
| 接口滥用 | SlowAPI 限流 10次/分钟 | 429 拦截 |
| 敏感信息泄露 | 只读账号 + 无敏感数据 | agent_ro 仅 SELECT |
