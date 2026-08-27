#!/usr/bin/env python3
# web/frontend.py - DataChat BI-style frontend
import os, re, time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

API = os.getenv("API_URL", "http://localhost:9000")

st.set_page_config(
    page_title="DataChat 智能问数平台",
    page_icon="bar_chart",
    layout="wide",
    initial_sidebar_state="expanded"
)

CSS = """
<style>
[data-testid="stStatusWidget"] {display:none!important;}
header[data-testid="stHeader"] {display:none!important;}
div[data-testid="stDecoration"] {display:none!important;}
.stApp > header {display:none!important;}
button[kind="header"] {display:none!important;}
[data-testid="DeployButton"] {display:none!important;}
[data-testid="stToolbar"] {display:none!important;}
.stApp {background:#f5f7fa;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Helvetica Neue",sans-serif;color:#1f2329;}
.block-container {padding-top:0;padding-bottom:0;max-width:100%;}
section[data-testid="stSidebar"] {background:#fff;border-right:1px solid #e5e6eb;min-width:220px;max-width:220px;}
section[data-testid="stSidebar"] .block-container {padding-top:0;}
.stRadio > div {gap:2px;}
.stRadio label {display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:6px;margin:2px 0;transition:all 0.15s;cursor:pointer;border:none;color:#4e5969;font-size:14px;}
.stRadio label:hover {background:#f2f3f5;color:#1f2329;}
.stRadio [aria-checked="true"] label {background:#e8f3ff;color:#1677ff;font-weight:500;}
.stButton > button {background:#1677ff;color:#fff;border:none;border-radius:6px;padding:6px 18px;font-weight:500;font-size:14px;}
.stButton > button:hover {background:#4096ff;}
.stButton > button:active {background:#0958d9;}
.stChatMessage {border-radius:8px;border:1px solid #e5e6eb;background:#fff;padding:4px;margin:8px 0;box-shadow:0 1px 2px rgba(0,0,0,0.02);}
.stChatMessage [data-testid="chatAvatarIcon-user"] {background:#1677ff;}
.stChatMessage [data-testid="chatAvatarIcon-assistant"] {background:#722ed1;}
.stChatMessage [data-testid="chatAvatarIcon-user"] svg,.stChatMessage [data-testid="chatAvatarIcon-assistant"] svg {color:#fff;}
.stChatInput textarea {border:1px solid #e5e6eb;border-radius:8px;background:#fff;padding:12px 14px;font-size:14px;color:#1f2329;}
.stChatInput textarea:focus {border-color:#1677ff;box-shadow:0 0 0 2px rgba(22,119,255,0.1);}
.stChatInput [data-testid="stChatInputSendButton"] {background:#1677ff;}
[data-testid="stDataFrame"],[data-testid="stTable"] {border:1px solid #e5e6eb;border-radius:8px;overflow:hidden;background:#fff;}
[class*="dataframe"] th {background:#fafbfc;color:#1f2329;font-weight:600;text-align:left;padding:10px 14px;border-bottom:1px solid #e5e6eb;font-size:13px;}
[class*="dataframe"] td {padding:8px 14px;border-bottom:1px solid #f2f3f5;color:#1f2329;font-size:13px;}
[class*="dataframe"] tr:last-child td {border-bottom:none;}
.streamlit-expanderHeader {background:#fff;border:1px solid #e5e6eb;border-radius:8px;color:#1f2329;font-size:14px;}
.streamlit-expanderHeader:hover {background:#fafbfc;}
.stTextInput input,.stTextArea textarea {border:1px solid #e5e6eb;border-radius:6px;padding:6px 12px;font-size:14px;color:#1f2329;background:#fff;}
.stTextInput input:focus,.stTextArea textarea:focus {border-color:#1677ff;box-shadow:0 0 0 2px rgba(22,119,255,0.1);}
.stSlider [role="slider"] {background:#1677ff;}
hr {border-color:#e5e6eb;margin:8px 0;}
::-webkit-scrollbar {width:6px;height:6px;}
::-webkit-scrollbar-thumb {background:#c9cdd4;border-radius:3px;}
::-webkit-scrollbar-track {background:transparent;}
.badge {display:inline-block;padding:2px 10px;border-radius:10px;font-size:12px;font-weight:500;background:#e8f3ff;color:#1677ff;border:1px solid #bed5ff;}
.section-title {font-size:16px;font-weight:600;color:#1f2329;margin-bottom:4px;}
.section-desc {font-size:13px;color:#86909c;margin-bottom:12px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def fmt_amount(val):
    try:
        v = float(str(val).replace(",", "").replace("\u5143", "").replace(" ", ""))
        return f"{v:,.2f}"
    except (ValueError, TypeError):
        return val


def parse_table_from_text(text):
    rows = []
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        m = re.match(r'^[-*]\s+(.+?)[:：]\s*(.+?)\s*(?:\u5143|\u4e07\u5143|)?$', line)
        if m:
            col1 = m.group(1).strip()
            col2 = m.group(2).strip()
            col2 = re.sub(r'[^\d.,\-]', '', col2)
            if col2:
                rows.append([col1, col2])
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["指标", "数值"])
    for col in df.columns[1:]:
        df[col] = df[col].apply(fmt_amount)
    return df


def get_kpi_cards(text):
    df = parse_table_from_text(text)
    if df is None or len(df) == 0:
        return None
    cards_html = '<div style="display:flex;gap:12px;margin:12px 0;flex-wrap:wrap;">'
    for _, row in df.iterrows():
        cards_html += (
            '<div style="flex:1;min-width:140px;background:#fff;border:1px solid #e5e6eb;'
            'border-radius:8px;padding:14px 16px;box-shadow:0 1px 2px rgba(0,0,0,0.02);">'
            '<div style="font-size:12px;color:#86909c;margin-bottom:6px;">'
            + str(row["指标"])
            + '</div><div style="font-size:22px;font-weight:700;color:#1f2329;letter-spacing:-0.5px;">'
            + str(row["数值"])
            + '</div></div>'
        )
    cards_html += "</div>"
    return cards_html


# === 侧边栏导航 ===
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 12px 8px;display:flex;align-items:center;gap:10px;">
        <div style="width:32px;height:32px;background:linear-gradient(135deg,#1677ff,#722ed1);border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:14px;">DC</div>
        <div><div style="font-size:14px;font-weight:600;color:#1f2329;">DataChat</div><div style="font-size:11px;color:#86909c;">智能问数平台</div></div>
    </div>
    """, unsafe_allow_html=True)

    tab = st.radio(" ", ["Agent 智能问答", "RAG 知识库检索", "文档处理工作流"], label_visibility="collapsed")

    st.markdown('<hr style="border-color:#e5e6eb;margin:16px 0 8px;">', unsafe_allow_html=True)
    st.markdown("""
    <div style="padding:8px 12px 4px;font-size:12px;color:#86909c;font-weight:500;">技术栈</div>
    <div style="padding:4px 12px;font-size:12px;color:#4e5969;line-height:1.8;">
        <div><b style="color:#1f2329;">后端API</b>：FastAPI :9000</div>
        <div><b style="color:#1f2329;">数据源</b>：WSL MySQL mall_ads</div>
        <div><b style="color:#1f2329;">大模型</b>：Ollama Qwen2.5-7B</div>
        <div><b style="color:#1f2329;">向量库</b>：BGE-M3 ChromaDB</div>
        <div><b style="color:#1f2329;">重排</b>：BGE-Reranker-Base</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#e5e6eb;margin:12px 0 8px;">', unsafe_allow_html=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown(f'<div style="padding:4px 12px;font-size:12px;color:#86909c;">{now}</div>', unsafe_allow_html=True)

# === 顶部导航栏 ===
st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;background:#fff;border-bottom:1px solid #e5e6eb;padding:12px 24px;">
    <div style="display:flex;align-items:center;gap:12px;">
        <span style="font-size:18px;font-weight:600;color:#1f2329;">智能问数</span>
        <span class="badge">开发环境</span>
    </div>
    <div style="display:flex;align-items:center;gap:16px;">
        <span style="font-size:13px;color:#86909c;">分析师</span>
        <div style="width:32px;height:32px;background:#1677ff;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-size:13px;font-weight:500;">A</div>
    </div>
</div>
""", unsafe_allow_html=True)

# === 认证 ===
if "token" not in st.session_state:
    try:
        r = requests.post(f"{API}/auth/token", params={"user": "analyst"}, timeout=10)
        st.session_state.token = r.json()["token"]
    except Exception as e:
        st.error(f"无法连接后端服务：{e}")
        st.stop()
headers = {"Authorization": f"Bearer {st.session_state.token}"}

# === Agent 智能问答 ===
if tab == "Agent 智能问答":
    st.markdown("""
    <div style="padding:16px 24px 0;">
        <div class="section-title">Agent 智能问答</div>
        <div class="section-desc">自然语言数据查询 · 指标口径咨询 · 数值计算</div>
    </div>
    """, unsafe_allow_html=True)

    if "history" not in st.session_state:
        st.session_state.history = []
    if "timings" not in st.session_state:
        st.session_state.timings = []

    if not st.session_state.history:
        st.markdown("""
        <div style="padding:24px;margin:16px 24px;background:#fff;border:1px solid #e5e6eb;border-radius:8px;text-align:center;">
            <div style="font-size:48px;margin-bottom:12px;">&#x1F4AC;</div>
            <div style="font-size:16px;font-weight:600;color:#1f2329;margin-bottom:4px;">你好，我是 DataChat 智能助手</div>
            <div style="font-size:13px;color:#86909c;margin-bottom:16px;">我可以帮你查询电商指标、解答数据口径、进行数值计算</div>
        </div>
        <div style="padding:0 24px;">
            <div style="font-size:12px;color:#86909c;margin-bottom:8px;font-weight:500;">试试这样问：</div>
        </div>
        """, unsafe_allow_html=True)
        chip_cols = st.columns(4)
        suggestions = [
            "最近三天GMV是多少？",
            "复购率的口径是什么？",
            "最新一天的客单价乘以1.13",
            "2026-08-21支付用户数"
        ]
        for i, s in enumerate(suggestions):
            with chip_cols[i]:
                if st.button(s, key=f"chip_{i}", use_container_width=True):
                    st.session_state._pending_q = s

    pending_q = getattr(st.session_state, "_pending_q", None)
    if pending_q:
        del st.session_state._pending_q

    for i, (role, text) in enumerate(st.session_state.history):
        with st.chat_message(role):
            if role == "user":
                st.markdown(f'<div style="color:#1f2329;font-size:14px;">{text}</div>', unsafe_allow_html=True)
            else:
                kpi_html = get_kpi_cards(text)
                if kpi_html:
                    st.markdown(kpi_html, unsafe_allow_html=True)
                df = parse_table_from_text(text)
                if df is not None and kpi_html is None:
                    st.dataframe(df, use_container_width=True, hide_index=True)
                remaining = [l for l in text.split("\n") if not re.match(r'^\s*[-*]\s+', l.strip())]
                if remaining:
                    st.markdown("\n".join(remaining))
                if i < len(st.session_state.timings):
                    st.markdown(
                        f'<div style="font-size:11px;color:#c9cdd4;margin-top:8px;">响应耗时 {st.session_state.timings[i]:.2f}s</div>',
                        unsafe_allow_html=True
                    )

    q = st.chat_input("例如：最近三天GMV是多少？ / 复购率的口径是什么？ / 最新一天的客单价乘以1.13")
    if q or pending_q:
        question = q or pending_q
        st.session_state.history.append(("user", question))
        with st.chat_message("user"):
            st.markdown(f'<div style="color:#1f2329;font-size:14px;">{question}</div>', unsafe_allow_html=True)

        with st.spinner("AI 分析中..."):
            try:
                t0 = time.time()
                r = requests.post(
                    f"{API}/chat", headers=headers,
                    params={"q": question, "thread_id": "web"}, timeout=300
                )
                elapsed = time.time() - t0
                ans = r.json()["answer"]
            except Exception as e:
                ans = f"请求失败：{e}"
                elapsed = 0

        st.session_state.history.append(("assistant", ans))
        st.session_state.timings.append(elapsed)

        with st.chat_message("assistant"):
            kpi_html = get_kpi_cards(ans)
            if kpi_html:
                st.markdown(kpi_html, unsafe_allow_html=True)
            df = parse_table_from_text(ans)
            if df is not None and kpi_html is None:
                st.dataframe(df, use_container_width=True, hide_index=True)
            remaining = [l for l in ans.split("\n") if not re.match(r'^\s*[-*]\s+', l.strip())]
            if remaining:
                st.markdown("\n".join(remaining))
            st.markdown(
                f'<div style="font-size:11px;color:#c9cdd4;margin-top:8px;">响应耗时 {elapsed:.2f}s</div>',
                unsafe_allow_html=True
            )

# === RAG 知识库检索 ===
elif tab == "RAG 知识库检索":
    st.markdown("""
    <div style="padding:16px 24px 0;">
        <div class="section-title">知识库检索</div>
        <div class="section-desc">BM25 + 向量混合检索 · CrossEncoder 重排 · 引用溯源</div>
    </div>
    """, unsafe_allow_html=True)

    col_search, col_k = st.columns([5, 1])
    with col_search:
        q = st.text_input("检索问题", value="复购率的统计口径是什么？", label_visibility="collapsed")
    with col_k:
        top_k = st.slider("返回数量", min_value=1, max_value=5, value=3, label_visibility="visible")
        search_btn = st.button("检索", type="primary", use_container_width=True)

    if search_btn and q:
        with st.spinner("检索知识库中..."):
            try:
                t0 = time.time()
                r = requests.post(
                    f"{API}/kb/search", headers=headers,
                    params={"q": q, "top_k": top_k}, timeout=30
                )
                elapsed = time.time() - t0
                results = r.json()["results"]
                st.markdown(
                    f'<div style="font-size:12px;color:#86909c;margin:8px 24px;">检索完成，耗时 {elapsed:.2f}s，共命中 {len(results)} 条</div>',
                    unsafe_allow_html=True
                )
                for i, item in enumerate(results, 1):
                    with st.expander(f"结果 {i} | 来源：{item['source']} | 相关度 {item['score']:.3f}"):
                        st.markdown(
                            f'<div style="font-size:13px;color:#1f2329;line-height:1.8;">{item["content"]}</div>',
                            unsafe_allow_html=True
                        )
            except Exception as e:
                st.error(f"检索失败：{e}")

# === 文档处理工作流 ===
elif tab == "文档处理工作流":
    st.markdown("""
    <div style="padding:16px 24px 0;">
        <div class="section-title">文档处理工作流</div>
        <div class="section-desc">上传业务文档 · LLM 智能抽取 · 结构化入库</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown('<div style="padding:8px 0;font-size:14px;font-weight:500;color:#1f2329;">文档抽取</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("上传业务文档", type=["md", "txt", "pdf"], help="支持 Markdown / 文本 / PDF 格式")
        if uploaded:
            if st.button("开始处理", type="primary"):
                with st.spinner("解析 → LLM抽取 → 校验 → 入库中..."):
                    try:
                        t0 = time.time()
                        r = requests.post(
                            f"{API}/workflow/run", headers=headers,
                            files={"file": (uploaded.name, uploaded.getvalue())},
                            timeout=60
                        )
                        elapsed = time.time() - t0
                        result = r.json()
                        st.success(f"{result['report']}（处理耗时 {elapsed:.2f}s）")
                    except Exception as e:
                        st.error(f"处理失败：{e}")

    with col2:
        st.markdown('<div style="padding:8px 0;font-size:14px;font-weight:500;color:#1f2329;">知识库管理</div>', unsafe_allow_html=True)
        kb_file = st.file_uploader("上传新文档至知识库", type=["md", "txt", "pdf"], key="kb", help="上传后自动全量重建向量索引")
        if kb_file:
            if st.button("入库", type="primary", key="kb_btn"):
                with st.spinner("解析 → 切片 → 向量化 → 入库中..."):
                    try:
                        r = requests.post(
                            f"{API}/kb/upload", headers=headers,
                            files={"file": (kb_file.name, kb_file.getvalue())},
                            timeout=60
                        )
                        st.success(f"入库成功：{r.json()}")
                    except Exception as e:
                        st.error(f"入库失败：{e}")
