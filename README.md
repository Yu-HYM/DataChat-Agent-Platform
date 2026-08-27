# DataChat 智能问数Agent平台

> 基于 LangGraph + Ollama + ChromaDB 的电商数仓智能问数系统，支持自然语言查询、多轮对话、知识库检索、文档结构化抽取等能力。

---

## 📌 项目简介

DataChat 是一个面向电商数据仓库的智能问数平台，用户通过自然语言提问，系统自动理解业务意图、调用 SQL 查询、检索知识库、执行计算，最终返回可解释的分析结果。

项目采用 **Agent + RAG** 架构，基于 LangGraph 构建多工具调用工作流，结合本地大模型与向量知识库，实现"提问—思考—工具调用—回答"的完整闭环。

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                     Streamlit 前端                       │
│              (对话界面 / 结果展示 / 文件上传)              │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP API
┌────────────────────────▼─────────────────────────────────┐
│                    FastAPI 后端服务                       │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  JWT认证  │  │  限流保护     │  │  日志/健康检查     │  │
│  └──────────┘  └──────┬───────┘  └───────────────────┘  │
│                       │                                  │
│  ┌────────────────────▼──────────────────────────────┐  │
│  │              LangGraph Agent 核心                  │  │
│  │   ┌─────────┐   ┌─────────┐   ┌───────────────┐   │  │
│  │   │  思考节点 │──▶│ 工具调用 │──▶│  多轮记忆      │   │  │
│  │   └─────────┘   └────┬────┘   └───────────────┘   │  │
│  │                       │                            │  │
│  │         ┌─────────────┼─────────────┐              │  │
│  │    ▼         ▼              ▼              ▼       │  │
│  │  SQL查询   知识库检索      计算器      文档抽取      │  │
│  └────────────────────────────────────────────────────┘  │
└────────┬───────────────────┬────────────────────────────┘
         │                   │
┌────────▼──────┐   ┌────────▼────────┐
│   MySQL数仓   │   │   ChromaDB      │
│  (mall_ads)   │   │  向量知识库     │
└───────────────┘   └─────────────────┘
         ▲                   ▲
┌────────┴───────────────────┴────────┐
│            Ollama 本地大模型        │
│       (LLM 推理 / Embedding)        │
└─────────────────────────────────────┘
```

---

## 🛠️ 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | 0.115 |
| Agent 框架 | LangGraph | 0.2 |
| LLM 接入 | LangChain + Ollama | 0.2 |
| 向量数据库 | ChromaDB | 0.5 |
| Embedding | sentence-transformers | 3.x |
| 前端 | Streamlit | 1.38 |
| 数据库 | MySQL (只读) | 8.0 |
| 部署 | Docker + docker-compose | 3.8 |
| 认证 | JWT (PyJWT) | 2.9 |
| 限流 | slowapi | 0.1.9 |
| 日志 | loguru | 0.7 |
| 检索增强 | BM25 + 向量混合检索 | rank-bm25 0.2 |

---

## ✨ 核心功能

### 1. 自然语言问数
- 支持中文自然语言提问，自动生成 SQL 并执行
- 覆盖 GMV、订单量、客单价、复购率、RFM 分层等业务指标
- 回答附带可解释的 SQL 和数据来源

### 2. LangGraph 多工具 Agent
- 基于 StateGraph 构建"思考-工具调用"循环
- 支持多轮对话记忆（MemorySaver 持久化）
- 内置工具：SQL 查询、知识库检索、计算器

### 3. RAG 知识库检索
- 混合检索：向量相似度 + BM25 关键词召回
- 支持 PDF/Markdown 文档上传与自动向量化
- 指标口径、库表结构、业务文档统一管理

### 4. 文档结构化抽取
- 上传合同/订单文档，自动抽取关键字段（客户、产品、金额、日期）
- 结构化结果存入 MySQL，支持后续问答查询

### 5. 工程化能力
- JWT 接口认证
- 接口限流保护（10次/分钟）
- Docker 一键部署
- 日志轮转与健康检查

---

## 📂 项目结构

```
datachat/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── agent.py             # LangGraph Agent 核心
│   ├── auth.py              # JWT 认证
│   ├── pipeline.py          # 文档抽取流水线
│   ├── tools.py             # Agent 工具集
│   └── rag/
│       ├── __init__.py
│       ├── ingest.py        # 知识库构建
│       └── retrieval.py     # 混合检索
├── web/
│   └── frontend.py          # Streamlit 前端
├── scripts/                 # 辅助脚本（验证/修复/测试）
├── kb_docs/                 # 知识库文档
├── chroma_db/               # 向量数据库（运行时生成）
├── logs/                    # 日志目录
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── deploy.sh
└── .dockerignore
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Ollama（本地大模型服务）
- MySQL 8.0（数仓数据源）
- Docker（可选，推荐部署方式）

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/Yu-HYM/DataChat-Agent-Platform.git
cd datachat

# 2. 修改 docker-compose.yml 中的数据库配置
#    MYSQL_HOST / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE

# 3. 启动服务
docker-compose up -d

# 4. 访问
# API 服务:  http://localhost:9000
# Web 界面:  http://localhost:8501
```

### 方式二：本地运行

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 配置环境变量
export OLLAMA_BASE_URL=http://localhost:11434
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=agent_ro
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=mall_ads

# 4. 启动 API 服务
uvicorn app.main:app --host 0.0.0.0 --port 9000

# 5. 启动前端（新终端）
streamlit run web/frontend.py --server.port 8501
```

---

## 🔌 API 接口

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/` | GET | 健康检查 | - |
| `/auth/token` | POST | 获取 JWT Token | - |
| `/chat` | POST | 对话问答 | JWT |
| `/kb/search` | POST | 知识库检索 | JWT |
| `/kb/upload` | POST | 上传文档并构建知识库 | JWT |
| `/workflow/run` | POST | 文档结构化抽取 | JWT |

### 示例

```bash
# 获取 Token
curl -X POST http://localhost:9000/auth/token -d 'user=demo'

# 对话提问
curl -X POST "http://localhost:9000/chat?q=上周GMV是多少" \
  -H "Authorization: Bearer <your_token>"
```

---

## 📊 数仓表说明

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| `ads_trade_stats` | 每日交易事实表 | dt, gmv, order_count, pay_user_count, avg_pay_amount |
| `ads_repurchase_rate` | 每日复购统计表 | dt, order_user_count, repurchase_user_count, repurchase_rate |
| `ads_user_rfm` | 用户 RFM 分层表 | dt, user_id, r_score, f_score, m_score, rfm_label |
| `doc_extract` | 文档抽取结果表 | id, customer, product, amount, date, summary, src_file |

---

## 🧠 设计亮点

1. **Agent 自主决策**：基于 LangGraph 的状态机设计，模型自主判断是否需要调用工具、调用哪个工具，支持多轮工具调用链。

2. **混合检索策略**：向量检索 + BM25 关键词召回结合，兼顾语义匹配和关键词精确匹配，提升知识库命中率。

3. **安全只读设计**：数据库使用只读账号（agent_ro），从根源防止 SQL 注入导致的数据篡改风险。

4. **本地模型隐私安全**：基于 Ollama 本地部署大模型，数据不出内网，适合企业敏感数据场景。

5. **工程化完备**：JWT 认证、接口限流、日志轮转、健康检查、Docker 容器化，生产可用。

---

## 📝 License

MIT License
