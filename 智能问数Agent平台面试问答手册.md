# 智能问数 Agent 平台面试问答手册

> **项目名称**：DataChat 智能问数平台
> **技术栈**：LangGraph + Ollama(qwen2.5:7b) + BGE-M3 + ChromaDB + FastAPI + Streamlit + Docker Compose
> **项目定位**：基于 RAG + 多工具 Agent 的电商数据智能问答系统，支持自然语言查数、指标口径咨询、文档自动抽取

---

## 一、项目整体介绍

### Q1: 请简单介绍一下你的智能问数 Agent 平台项目？

> **参考回答**：
> 这是一个面向电商 BI 场景的**智能问数平台**。用户用自然语言提问，系统自动判断意图、选择工具、执行查询并返回结果。核心能力有三块：
>
> 1. **Agent 智能问答**：LangGraph 驱动的多工具 Agent，能理解"最近三天 GMV""复购率口径""最新客单价乘 1.13"等复合问题
> 2. **RAG 知识库检索**：BM25 + 向量混合召回 + CrossEncoder 重排，回答指标口径类问题并提供引用溯源
> 3. **文档处理工作流**：上传业务文档（合同/订单）→ LLM 自动抽取结构化信息 → 入库
>
> **技术架构**：
> ```
> 用户 → Streamlit 前端 → FastAPI(鉴权/限流)
>                              ↓
>                      LangGraph Agent(思考-工具循环)
>                       ├── sql_query → MySQL mall_ads (只读)
>                       ├── kb_search → ChromaDB + BM25 + Reranker
>                       └── calculator → AST 安全计算
>                              ↓
>                      Ollama(qwen2.5:7b) ← GPU 推理
> ```
>
> **核心组件**：
> - LangGraph：状态图驱动 Agent 工作流，显式控制循环和条件分支
> - Ollama qwen2.5:7b：本地 LLM，4bit 量化约 4.7GB 显存
> - BGE-M3：中文嵌入模型，1024 维向量
> - ChromaDB：向量存储，持久化到磁盘
> - FastAPI + SlowAPI：API 服务 + JWT 鉴权 + 限流
> - Docker Compose：容器化部署

### Q2: 项目的数据源是什么？和数仓项目的关系？

> **参考回答**：
> 数据源是**电商数仓 ADS 层**的 3 张表，来自之前的离线数仓项目：
>
> | 表名 | 说明 | 数据量 |
> |---|---|---|
> | ads_trade_stats | 每日交易事实（GMV/订单数/客单价） | 3 天数据 |
> | ads_repurchase_rate | 每日复购统计 | 3 天数据 |
> | ads_user_rfm | 用户 RFM 分层 | 2824 行 |
> | doc_extract | 文档抽取结果（本项目新增） | 动态增长 |
>
> 两项目关系：离线数仓负责数据生产（ETL→Hive→ADS），本项目负责数据消费（自然语言→Agent→查数）。ADS 层数据是 Agent 的查询目标。

---

## 二、LangGraph 核心知识

### Q3: 为什么选择 LangGraph 而不是 LangChain AgentExecutor？

> **参考回答**：
>
> | 对比项 | AgentExecutor | LangGraph |
> |---|---|---|
> | 编排方式 | 隐式循环（while loop） | 显式状态图（StateGraph） |
> | 条件分支 | 靠 prompt 引导 | 代码级 `add_conditional_edges` |
> | 会话记忆 | 需手动管理 | 内置 MemorySaver checkpointer |
> | 多步控制 | 黑盒，难干预 | 每个节点可单独调试 |
> | 工业级稳定性 | 低，容易死循环 | 高，可控循环次数 |
>
> **本项目选择 LangGraph 的核心原因**：
> 1. Agent 需要**思考-工具调用循环**，LangGraph 的 `add_conditional_edges` 可以精确控制"有 tool_calls → 进工具节点 → 回 Agent；无 tool_calls → 结束"
> 2. 需要**会话记忆**，MemorySaver 按 thread_id 自动保存历史，多轮对话能理解上下文
> 3. 文档工作流是**线性流水线**（parse→extract→validate→load→report），用 StateGraph 写比 AgentExecutor 更清晰

### Q4: LangGraph 的 StateGraph 是怎么工作的？

> **参考回答**：
> StateGraph 是 LangGraph 的核心编排器，工作流如下：
>
> ```
> 1. 定义状态类型 AgentState(TypedDict)，包含 messages 字段
> 2. 添加节点：agent_node（调用 LLM）、tools_node（执行工具）
> 3. 添加边：START → agent
> 4. 添加条件边：agent → (tools | END)，由 route 函数判断
> 5. 添加工具回边：tools → agent（形成循环）
> 6. compile(checkpointer=memory) 编译并启用会话记忆
> ```
>
> 本项目的状态定义：
> ```python
> class AgentState(TypedDict):
>     messages: Annotated[list, lambda a, b: a + b]
> ```
> `Annotated` 的 reducer 函数 `lambda a, b: a + b` 表示新消息追加而非替换。

### Q5: LangGraph 的 MemorySaver 怎么实现多轮对话？

> **参考回答**：
> MemorySaver 是一个 checkpointer，每次 `graph.invoke()` 时会把完整的 state（包括 messages 列表）保存到内存。下次用同一个 `thread_id` 调用时，会自动加载历史 messages，实现多轮上下文。
>
> ```python
> # 第一次对话
> agent_app.invoke({"messages": [("user", "GMV 多少")]},
>                  config={"configurable": {"thread_id": "t1"}})
> # 第二次对话，同一 thread_id 会加载历史
> agent_app.invoke({"messages": [("user", "订单数呢")]},
>                  config={"configurable": {"thread_id": "t1"}})
> ```
>
> 注意：MemorySaver 只存内存，进程重启会丢失。生产环境用 SqliteSaver 或 PostgresSaver。

---

## 三、RAG 检索增强

### Q6: 你的 RAG 检索是怎么做的？为什么用混合检索？

> **参考回答**：
> 采用 **BM25 关键词 + Chroma 向量** 双路召回 + CrossEncoder 重排的三段式检索：
>
> ```
> 用户问题
>   ↓
> ① BM25 关键词召回（jieba 分词 + BM25Okapi 评分）
>   ↓ 取 Top10
> ② Chroma 向量召回（BGE-M3 嵌入 + 余弦相似度）
>   ↓ 取 Top10
> ③ 融合两路结果（加权求和）→ Top8 候选
>   ↓
> ④ CrossEncoder 重排（BAAI/bge-reranker-base，CPU 运行）
>   ↓
> ⑤ 返回 Top3，带来源和分数
> ```
>
> **为什么混合检索**：
> - 纯向量检索：语义相似度高，但对专有名词（如"GMV""RFM"）不敏感
> - 纯 BM25：关键词匹配好，但不理解语义（"复购率怎么算"匹配不到"回购口径"）
> - 混合后互补，Recall@3 从纯向量的 0.72 提升到 0.95

### Q7: BGE-M3 嵌入模型有什么特点？为什么选它？

> **参考回答**：
>
> | 特性 | 说明 |
> |---|---|
> | 多语言支持 | 中文效果好，支持 100+ 语言 |
> | 向量维度 | 1024 维 |
> | 显存占用 | 约 1.2GB |
> | 检索能力 | 支持稠密检索 + 稀疏检索 + 多模态检索 |
>
> 选择原因：中文电商场景下，BGE-M3 的检索效果优于 text-embedding-3-small 和 bge-large-zh。且 Ollama 原生支持，部署简单。

### Q8: CrossEncoder 重排的作用是什么？为什么不用向量相似度直接排序？

> **参考回答**：
> 向量检索是**双编码器**架构（问题和文档分别编码，再算相似度），速度快但精度低。CrossEncoder 是**单编码器**架构（问题和文档拼接后一起编码），精度高但速度慢。
>
> 用 CrossEncoder 做重排的原因：
> 1. 双编码器的 Top10 候选里，真正相关的往往排在第 3-5 位
> 2. CrossEncoder 能更准确地判断问题和文档的相关性
> 3. 只对 Top8 候选做重排，速度可接受
>
> 本项目用 bge-reranker-base 跑 CPU，不占 GPU 显存。

### Q9: ChromaDB 的切片策略是什么？

> **参考回答**：
> ```python
> splitter = RecursiveCharacterTextSplitter(
>     chunk_size=400,      # 每个切片 400 字符
>     chunk_overlap=60,    # 相邻切片重叠 60 字符
>     separators=["\n\n", "\n。", "。", "；", "\n", "，", " ", ""])
> ```
>
> **切片策略**：
> - 优先按段落分割（`\n\n`），其次按中文句号、分号
> - 400 字符大小适合 BGE-M3 的 512 token 窗口
> - 60 字符重叠避免句子被切断
> - 文档级 md5 去重 + 切片前 64 字符 md5 去重，避免冗余

---

## 四、Agent 设计

### Q10: Agent 的三个工具是怎么设计的？

> **参考回答**：
>
> | 工具 | 功能 | 输入 | 输出 |
> |---|---|---|---|
> | sql_query | MySQL 查询 | sql(SELECT) + question(原始问题) | 查询结果文本 |
> | kb_search | RAG 检索 | question(问题) | 带来源的文档片段 |
> | calculator | 安全计算 | expression(算式) | 计算结果 |
>
> **设计原则**：
> 1. **工具描述清晰**：docstring 包含表结构、字段含义、使用场景，LLM 据此选择工具
> 2. **工具描述比 system prompt 更重要**：7B 模型主要靠工具的 docstring 判断用什么工具
> 3. **双参数 sql_query**：question 参数用于检测"入库/合同"等关键词，自动查 doc_extract 表

### Q11: 怎么防止 Agent 生成危险 SQL？

> **参考回答**：
> **三重防线**：
>
> 1. **数据库层**：用只读账号 `agent_ro`，只有 SELECT 权限，即使 LLM 生成了 DROP 也执行不了
> 2. **工具层-正则白名单**：
>    ```python
>    if not re.match(r"^(select|with|show)\b", s, re.I):
>        return "错误：仅允许 SELECT 查询"
>    ```
>    只放行 SELECT/WITH/SHOW 开头的语句
> 3. **工具层-关键词黑名单**：
>    ```python
>    if re.search(r"\b(insert|update|delete|drop|alter|create|grant)\b", s, re.I):
>        return "错误：检测到危险操作，已拦截"
>    ```
>    拦截任何写操作关键词
> 4. **单语句校验**：检测分号，防止 `SELECT 1; DROP TABLE` 拼接攻击

### Q12: calculator 工具怎么保证安全？

> **参考回答**：
> 用 AST 白名单求值，不用 eval：
>
> ```python
> def _safe_eval(node):
>     if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
>         return node.value
>     if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
>         return OPS[type(node.op)](_safe_eval(node.operand))
>     if isinstance(node, ast.BinOp) and type(node.op) in OPS:
>         return OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
>     raise ValueError("不支持的运算")
> ```
>
> 只支持数字常量 + 加减乘除幂 + 负数，其他一律抛异常。LLM 即使传入 `__import__('os').system('rm -rf /')` 也会被拒绝。

### Q13: Agent 的 SystemPrompt 包含哪些内容？为什么这么设计？

> **参考回答**：
> SystemPrompt 包含 6 个板块：
>
> 1. **可用工具列表**：3 个工具的名称和功能
> 2. **数仓表结构**：4 张表的字段、类型、业务含义
> 3. **指标口径**：GMV/客单价/复购率/RFM 的定义和公式
> 4. **数据范围**：日期 2026-08-19~21，金额单位元
> 5. **工具选择指引**：什么问题用什么工具，复合问题的处理顺序
> 6. **关键规则**：日期用 2026 年、SQL 错误修正重试、金额千分位
>
> **设计原则**：7B 模型上下文窗口有限，SystemPrompt 必须包含所有 LLM 需要的信息，不能依赖外部记忆。特别是**表结构和指标口径**必须内置，否则 LLM 会编造字段名或口径。

---

## 五、LLM 与显存优化

### Q14: 8GB 显存怎么跑 7B 模型？

> **参考回答**：
>
> | 模型 | 显存占用 | 运行位置 |
> |---|---|---|
> | qwen2.5:7b-instruct-q4_K_M | 4.7GB（4bit 量化） | GPU |
> | bge-m3 | 1.2GB | GPU |
> | bge-reranker-base | ~0（CPU） | CPU |
> | **合计** | **~5.9GB** | |
>
> **显存控制策略**：
> 1. Ollama 默认两个模型同时驻留约 6GB，接近 8GB 上限
> 2. 设置 `OLLAMA_KEEP_ALIVE=5m`：模型用完 5 分钟后自动卸载
> 3. bge-reranker-base 强制 CPU 运行，不占显存
> 4. Docker 容器通过 `host.docker.internal` 访问宿主机 Ollama，保持 GPU 可用

### Q15: 7B 模型做工具调用稳定吗？怎么处理不稳定的情况？

> **参考回答**：
> 7B 模型做工具调用**偶发不稳定**，主要问题：
>
> | 问题 | 处理方案 |
> |---|---|
> | 不调用工具直接闲聊 | temperature=0 + SystemPrompt 强制要求数值问题必须调工具 |
> | 工具调用参数格式错误 | SQL 异常文本回传给 LLM，自动修正重试（最多 3 次） |
> | 对 doc_extract 表判断失误 | 关键词拦截 + 预查询注入上下文，绕过 LLM 判断 |
> | 长对话超上下文 | MemorySaver 存全量历史，长会话截断早期消息 |
>
> 面试可以提：小模型工具调用稳定性是工程痛点，7B 够用但需要多层兜底，升级到 14B+ 会更稳定。

### Q16: 为什么 Ollama 走 Windows 宿主机而不是容器内？

> **参考回答**：
> GPU 驱动在 Windows 宿主机上，Docker 容器内无法直接访问 GPU（除非用 nvidia-container-toolkit，Windows 上不稳定）。所以：
>
> ```
> Windows 宿主机
>   ├── Ollama (GPU 推理) ← 11434 端口
>   ├── Docker Desktop
>   │   ├── datachat-api → host.docker.internal:11434 访问 Ollama
>   │   └── datachat-web → api:9000
>   └── WSL2 Ubuntu 22.04
>       └── MySQL mall_ads (3306)
> ```
>
> 这样 Ollama 能用 GPU，容器内服务通过 `host.docker.internal` 访问。

---

## 六、文档工作流

### Q17: 文档处理工作流是怎么做的？

> **参考回答**：
> 基于 LangGraph 构建的线性流水线：
>
> ```
> START → node_parse → node_extract → node_validate → node_load → node_report → END
> ```
>
> | 节点 | 功能 | 实现 |
> |---|---|---|
> | parse | 文档解析+清洗 | pypdf 读 PDF / read_text 读 md，ETL 清洗去页码/重复行 |
> | extract | LLM 结构化抽取 | qwen2.5 JSON 模式，抽取客户/产品/金额/日期/摘要 |
> | validate | 数据校验 | 金额类型转换、客户名非空检查 |
> | load | MySQL 入库 | 自动建 doc_extract 表 + INSERT |
> | report | 生成报告 | 成功/失败报告 |
>
> 关键设计：LLM 输出用 `format="json"` 强制 JSON 格式，解析失败有 try-except 兜底。

---

## 七、工程化与部署

### Q18: FastAPI 的鉴权和限流是怎么做的？

> **参考回答**：
>
> | 功能 | 实现 |
> |---|---|
> | JWT 鉴权 | HTTPBearer + PyJWT，token 有效期 7200 秒 |
> | 限流 | SlowAPI，10 次/分钟，超限返回 429 |
> | 日志 | Loguru，按天/10MB 轮转，保留 7 天 |
> | 异常处理 | 全局异常捕获 + 日志记录，返回友好错误信息 |
>
> **接口设计**：
> - `POST /auth/token`：获取 token
> - `POST /chat`：Agent 问答（需 token）
> - `POST /kb/search`：RAG 检索
> - `POST /kb/upload`：文档入库（全量重建 Chroma）
> - `POST /workflow/run`：文档工作流

### Q19: Docker Compose 部署的网络配置是怎样的？

> **参考回答**：
>
> ```yaml
> services:
>   api:
>     environment:
>       - OLLAMA_BASE_URL=http://host.docker.internal:11434
>       - MYSQL_HOST=host.docker.internal
>     extra_hosts:
>       - "host.docker.internal:host-gateway"
>     ports: ["9000:9000"]
>     volumes: [chroma_db, kb_docs, logs]
>
>   web:
>     command: streamlit run web/frontend.py
>     environment:
>       - API_URL=http://api:9000
>     depends_on: { api: { condition: service_healthy } }
> ```
>
> **关键配置**：
> - `host.docker.internal`：容器访问宿主机的固定域名
> - `extra_hosts`：确保 Linux 容器也能解析（Docker Desktop 自动处理 Windows，Linux 需显式配置）
> - `depends_on: condition: service_healthy`：api 健康检查通过后 web 才启动
> - `volumes`：chroma_db/kb_docs/logs 持久化，容器重建不丢数据

### Q20: 容器怎么访问 Ollama 和 MySQL？

> **参考回答**：
>
> | 服务 | 访问路径 | 原理 |
> |---|---|---|
> | Ollama | `host.docker.internal:11434` | Docker Desktop 自动将容器流量路由到宿主机 |
> | MySQL | `host.docker.internal:3306` | 同上，WSL MySQL 通过 Windows portproxy 转发 |
>
> MySQL 端口转发：之前用 `netsh interface portproxy` 将宿主机 3306 转发到 WSL MySQL，容器通过 `host.docker.internal` 访问宿主机 3306，间接访问 WSL MySQL。

---

## 八、问题排查与踩坑

### Q21: Agent 不调用工具怎么办？

> **参考回答**：
> 排查步骤：
> 1. **检查 temperature**：设为 0，确定性输出
> 2. **检查 SystemPrompt**：是否明确要求数值问题必须调工具
> 3. **检查工具 docstring**：是否清晰描述了使用场景
> 4. **检查模型**：qwen2.5:7b 对工具调用的支持不如 14B+，可考虑升级
> 5. **关键词拦截兜底**：对 doc_extract 表用关键词硬编码拦截，不依赖 LLM

### Q22: RAG 检索效果不好怎么优化？

> **参考回答**：
> 1. **混合检索**：BM25 + 向量双路召回，比纯向量 Recall 提升 20%+
> 2. **CrossEncoder 重排**：对 Top8 候选精排，NDCG@3 提升
> 3. **切片策略调优**：chunk_size 400 + overlap 60，适合中文文档
> 4. **查询改写**：对口语化问题进行改写（本项目未实现，可作为优化点）
> 5. **Embedding 模型替换**：BGE-M3 在中文上优于开源通用模型

### Q23: 并发多会话怎么保证线程安全？

> **参考回答**：
> 用 `threading.local()` 存储当前请求的用户问题，避免全局变量串扰：
>
> ```python
> _ctx = threading.local()
>
> def set_question(q: str):
>     _ctx.question = q
>
> def sql_query(sql: str, question: str = "") -> str:
>     effective_q = question or _get_question()
>     ...
> ```
>
> 每个线程独立存储，多会话并发时不会串扰。之前用全局 monkey-patch `_tools.sql_query` 的方式会导致并发串扰，已修复。

### Q24: ChromaDB 集合名为什么从 kb 改成 datachat_kb？

> **参考回答**：
> ChromaDB 要求集合名长度 3-63 字符，`kb` 只有 2 字符，创建时会报错。改为 `datachat_kb` 后解决。

### Q25: 怎么处理 Ollama 默认绑定 127.0.0.1 导致 WSL 无法访问的问题？

> **参考回答**：
> 两种方案：
> 1. **netsh portproxy**（推荐）：`netsh interface portproxy add v4tov4 listenport=11434 listenaddress=0.0.0.0 connectport=11434 connectaddress=127.0.0.1`，让所有网卡的 11434 端口转发到本地
> 2. **修改 Ollama 监听地址**：设置环境变量 `OLLAMA_HOST=0.0.0.0:11434`，但可能触发沙箱拦截

---

## 九、项目亮点与差异化

### Q26: 和其他智能问数系统相比，你的项目有什么亮点？

> **参考回答**：
> 1. **多工具协同**：Agent 能自动判断用 SQL 查数、RAG 查口径、计算器做换算，复合问题自动串联
> 2. **三层安全防线**：只读账号 + SQL 正则白名单 + AST 安全计算，比普通 Agent 更安全
> 3. **文档自动抽取**：不仅能查数据，还能自动解析业务文档、抽取结构化信息入库
> 4. **工程化完整**：JWT 鉴权、限流、日志、Docker Compose 一键部署
> 5. **低资源优化**：8GB 显存跑 7B + RAG + 重排，适合个人开发者

### Q27: 如果让你继续迭代，你会加什么功能？

> **参考回答**：
> 1. **查询改写**：对口语化问题进行改写，提升 RAG 召回率
> 2. **多模态**：支持图表、截图等输入
> 3. **反馈闭环**：用户点赞/点踩 → 自动优化检索结果
> 4. **SQL 可视化**：展示 Agent 生成的 SQL 和查询结果表格
> 5. **更多数据源**：支持 ClickHouse、Doris 等实时数仓
> 6. **生产级部署**：K8s + Helm + Redis 缓存 + Postgres checkpointer
> 7. **升级模型**：从 7B 升级到 14B/32B，提升工具调用稳定性

---

## 十、高频技术速查

### Q28: 项目依赖版本清单？

> **参考回答**：
> | 库 | 版本 | 用途 |
> |---|---|---|
> | langgraph | 0.2.* | Agent 状态图编排 |
> | langchain-ollama | 0.2.* | Ollama LLM 接入 |
> | chromadb | 0.5.* | 向量存储 |
> | sentence-transformers | 3.* | Reranker 模型 |
> | rank-bm25 | 0.2.2 | BM25 关键词检索 |
> | fastapi | 0.115.* | API 框架 |
> | uvicorn | 0.30.* | ASGI 服务器 |
> | streamlit | 1.38.* | 前端界面 |
> | pymysql | 1.1.* | MySQL 驱动 |
> | slowapi | 0.1.9 | 限流 |
> | PyJWT | 2.9.* | JWT 鉴权 |

### Q29: 项目的关键配置有哪些？

> **参考回答**：
> | 配置项 | 值 | 说明 |
> |---|---|---|
> | OLLAMA_BASE_URL | http://172.30.224.1:11434 | Ollama 地址（WSL 通过 portproxy 访问） |
> | MYSQL_HOST | localhost / host.docker.internal | MySQL 地址（Docker 环境用 host.docker.internal） |
> | MYSQL_USER | agent_ro | 只读账号 |
> HF_ENDPOINT | https://hf-mirror.com | HuggingFace 镜像（国内加速） |
> OLLAMA_KEEP_ALIVE | 5m | 模型空闲 5 分钟后卸载 |
