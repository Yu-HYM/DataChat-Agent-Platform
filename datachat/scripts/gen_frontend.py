import os

code = '''#!/usr/bin/env python3
# web/frontend.py —— DataChat 企业BI风格前端
import os, re, time
import requests
import pandas as pd
import streamlit as st

API = os.getenv("API_URL", "http://localhost:9000")

st.set_page_config(
    page_title="DataChat 智能问数平台",
    page_icon="bar_chart",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
[data-testid="stStatusWidget"] {display: none !important;}
header[data-testid="stHeader"] {display: none !important;}
div[data-testid="stDecoration"] {display: none !important;}
.stApp > header {display: none !important;}
button[kind="header"] {display: none !important;}
[data-testid="DeployButton"] {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
.stApp {background: #f7f8fa; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;}
.block-container {padding-top: 1rem; padding-bottom: 2rem;}
.stButton > button {background: #2563eb; color: white; border: none; border-radius: 6px; padding: 0.45rem 1.2rem; font-weight: 500; transition: all 0.2s;}
.stButton > button:hover {background: #1d4ed8; box-shadow: 0 2px 8px rgba(37,99,235,0.25);}
.stButton > button:active {background: #1e40af;}
section[data-testid="stSidebar"] {background: #ffffff; border-right: 1px solid #e5e7eb;}
section[data-testid="stSidebar"] .block-container {padding-top: 2rem;}
.stRadio > div {gap: 0;}
.stRadio label {padding: 0.55rem 0.9rem; border-radius: 6px; margin: 0.15rem 0; transition: all 0.15s; cursor: pointer; border: 1px solid transparent;}
.stRadio label:hover {background: #f0f4ff;}
.stRadio [aria-checked="true"] label {background: #eff6ff; border-color: #2563eb; color: #1d4ed8; font-weight: 500;}
.stChatMessage {border-radius: 10px; border: 1px solid #e5e7eb; background: #ffffff; padding: 0.25rem; margin: 0.35rem 0;}
.stChatMessage [data-testid="chatAvatarIcon-user"] {background: #dbeafe;}
.stChatMessage [data-testid="chatAvatarIcon-assistant"] {background: #e0e7ff;}
.stChatInput textarea {border: 1px solid #d1d5db; border-radius: 8px; background: #ffffff;}
.stChatInput textarea:focus {border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37,99,235,0.1);}
hr {border-color: #e5e7eb; margin: 0.8rem 0;}
[data-testid="stDataFrame"] {border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; background: #ffffff;}
[class*="dataframe"] th {background: #f8fafc; color: #374151; font-weight: 600; text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid #e5e7eb;}
[class*="dataframe"] td {padding: 0.4rem 0.75rem; border-bottom: 1px solid #f3f4f6; color: #111827;}
.streamlit-expanderHeader {background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px;}
h1, h2, h3 {color: #111827;}
.env-tag {display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def fmt_amount(val):
    try:
        v = float(str(val).replace(",", "").replace("元", "").replace(" ", ""))
        return f"{v:,.2f}"
    except (ValueError, TypeError):
        return val

def parse_table_from_text(text):
    rows = []
    lines = text.strip().split("\\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        m = re.match(r'^[-*]\\s+(.+?)[:：]\\s*(.+?)\\s*(?:元|万元|)?$', line)
        if m:
            col1 = m.group(1).strip()
            col2 = m.group(2).strip()
            col2 = re.sub(r'[^\\d.,\\-]', '', col2)
            if col2:
                rows.append([col1, col2])
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["维度", "数值"])
    for col in df.columns[1:]:
        df[col] = df[col].apply(fmt_amount)
    return df

# Header
hdr_c1, hdr_c2 = st.columns([3, 1])
with hdr_c1:
    st.markdown('<div style="font-size:1.5rem;font-weight:700;color:#111827;">DataChat 智能问数平台</div><div style="color:#6b7280;font-size:0.85rem;margin-top:2px;">电商数仓 ADS 层自然语言查询 · RAG 口径咨询 · 文档智能处理</div>', unsafe_allow_html=True)
with hdr_c2:
    st.markdown('<div style="text-align:right;padding-top:0.8rem;"><span class="env-tag">DEV 开发环境</span></div>', unsafe_allow_html=True)
st.markdown('<hr style="border-color:#e5e7eb;margin:0.3rem 0 1rem 0;">', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown('<div style="font-weight:600;color:#111827;margin-bottom:0.5rem;">功能导航</div>', unsafe_allow_html=True)
    tab = st.radio(" ", ["Agent 智能问答", "RAG 知识库检索", "文档处理工作流"], label_visibility="collapsed")
    st.markdown('<hr style="border-color:#e5e7eb;margin:1rem 0;">', unsafe_allow_html=True)
    st.markdown('<div style="font-weight:600;color:#111827;font-size:0.9rem;margin-bottom:0.5rem;">技术栈</div><div style="font-size:0.78rem;color:#6b7280;line-height:1.7;"><div><b style="color:#374151;">后端API</b>: FastAPI @ localhost:9000</div><div><b style="color:#374151;">数据源</b>: WSL MySQL mall_ads ADS层</div><div><b style="color:#374151;">大模型</b>: Ollama Qwen2.5-7B</div><div><b style="color:#374151;">向量库</b>: BGE-M3 ChromaDB</div><div><b style="color:#374151;">重排</b>: BGE-Reranker-Base</div></div>', unsafe_allow_html=True)

# Token
if "token" not in st.session_state:
    try:
        r = requests.post(f"{API}/auth/token", params={"user": "analyst"}, timeout=10)
        st.session_state.token = r.json()["token"]
    except Exception as e:
        st.error(f"无法连接后端服务: {e}")
        st.stop()
headers = {"Authorization": f"Bearer {st.session_state.token}"}

if tab == "Agent 智能问答":
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#111827;">Agent 智能问答</div><div style="font-size:0.82rem;color:#6b7280;margin-bottom:0.8rem;">自然语言查询数仓指标 · 口径咨询 · 数值计算</div>', unsafe_allow_html=True)
    if "history" not in st.session_state:
        st.session_state.history = []
    if "timings" not in st.session_state:
        st.session_state.timings = []
    for i, (role, text) in enumerate(st.session_state.history):
        with st.chat_message(role):
            if role == "user":
                st.markdown(f'<div style="color:#111827;">{text}</div>', unsafe_allow_html=True)
            else:
                df = parse_table_from_text(text)
                if df is not None:
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    remaining = [l for l in text.split("\\n") if not re.match(r'^\\s*[-*]\\s+', l.strip())]
                    if remaining:
                        st.markdown("\\n".join(remaining))
                else:
                    st.markdown(text)
                if i < len(st.session_state.timings):
                    st.markdown(f'<div style="font-size:0.72rem;color:#9ca3af;margin-top:0.4rem;">响应耗时 {st.session_state.timings[i]:.2f}s</div>', unsafe_allow_html=True)
    q = st.chat_input("请输入业务问题", placeholder="最近三天的GMV是多少？ / 复购率的口径是什么？ / 最新一天的客单价乘以1.13是多少？")
    if q:
        st.session_state.history.append(("user", q))
        with st.chat_message("user"):
            st.markdown(f'<div style="color:#111827;">{q}</div>', unsafe_allow_html=True)
        with st.spinner("AI 思考中..."):
            try:
                t0 = time.time()
                r = requests.post(f"{API}/chat", headers=headers, params={"q": q, "thread_id": "web"}, timeout=300)
                elapsed = time.time() - t0
                ans = r.json()["answer"]
            except Exception as e:
                ans = f"请求失败: {e}"
                elapsed = 0
        st.session_state.history.append(("assistant", ans))
        st.session_state.timings.append(elapsed)
        with st.chat_message("assistant"):
            df = parse_table_from_text(ans)
            if df is not None:
                st.dataframe(df, use_container_width=True, hide_index=True)
                remaining = [l for l in ans.split("\\n") if not re.match(r'^\\s*[-*]\\s+', l.strip())]
                if remaining:
                    st.markdown("\\n".join(remaining))
            else:
                st.markdown(ans)
            st.markdown(f'<div style="font-size:0.72rem;color:#9ca3af;margin-top:0.4rem;">响应耗时 {elapsed:.2f}s</div>', unsafe_allow_html=True)

elif tab == "RAG 知识库检索":
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#111827;">知识库检索</div><div style="font-size:0.82rem;color:#6b7280;margin-bottom:0.8rem;">BM25 + 向量混合检索 · CrossEncoder 重排 · 引用溯源</div>', unsafe_allow_html=True)
    q = st.text_input("输入检索问题", value="复购率的统计口径是什么？", label_visibility="collapsed")
    col1, col2 = st.columns([3, 1])
    with col1:
        top_k = st.slider("返回结果数量", min_value=1, max_value=5, value=3)
    with col2:
        search_btn = st.button("检索", type="primary", use_container_width=True)
    if search_btn and q:
        with st.spinner("检索中..."):
            try:
                t0 = time.time()
                r = requests.post(f"{API}/kb/search", headers=headers, params={"q": q, "top_k": top_k}, timeout=30)
                elapsed = time.time() - t0
                results = r.json()["results"]
                st.markdown(f'<div style="font-size:0.78rem;color:#6b7280;margin-bottom:0.5rem;">检索完成，耗时 {elapsed:.2f}s，共命中 {len(results)} 条</div>', unsafe_allow_html=True)
                for i, item in enumerate(results, 1):
                    with st.expander(f"结果 {i} | 来源：{item['source']} | 相关度 {item['score']:.3f}"):
                        st.markdown(f'<div style="font-size:0.88rem;color:#111827;line-height:1.7;">{item["content"]}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"检索失败: {e}")

elif tab == "文档处理工作流":
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#111827;">文档处理工作流</div><div style="font-size:0.82rem;color:#6b7280;margin-bottom:0.8rem;">上传业务文档，LLM 智能抽取，结构化入库</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("上传业务文档", type=["md", "txt", "pdf"], help="支持 Markdown / 文本 / PDF 格式")
    if uploaded:
        if st.button("开始处理", type="primary"):
            with st.spinner("解析 -> LLM抽取 -> 校验 -> 入库中..."):
                try:
                    t0 = time.time()
                    r = requests.post(f"{API}/workflow/run", headers=headers, files={"file": (uploaded.name, uploaded.getvalue())}, timeout=60)
                    elapsed = time.time() - t0
                    result = r.json()
                    st.success(f"{result['report']}（处理耗时 {elapsed:.2f}s）")
                except Exception as e:
                    st.error(f"处理失败: {e}")
    st.markdown('<hr style="border-color:#e5e7eb;margin:1.5rem 0 1rem 0;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:1rem;font-weight:600;color:#111827;margin-bottom:0.8rem;">知识库文档管理</div>', unsafe_allow_html=True)
    kb_file = st.file_uploader("上传新文档至知识库", type=["md", "txt", "pdf"], key="kb", help="上传后自动全量重建向量索引")
    if kb_file:
        if st.button("入库", type="primary", key="kb_btn"):
            with st.spinner("解析 -> 切片 -> 向量化 -> 入库中..."):
                try:
                    r = requests.post(f"{API}/kb/upload", headers=headers, files={"file": (kb_file.name, kb_file.getvalue())}, timeout=60)
                    st.success(f"入库成功：{r.json()}")
                except Exception as e:
                    st.error(f"入库失败: {e}")
'''

p = os.path.join(os.path.dirname(__file__), "frontend.py")
with open(p, "w", encoding="utf-8") as f:
    f.write(code.lstrip())
print("frontend.py written OK, size:", len(code))
