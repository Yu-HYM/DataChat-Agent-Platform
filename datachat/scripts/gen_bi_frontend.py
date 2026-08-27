import os, sys

frontend_code = r'''#!/usr/bin/env python3
# web/frontend.py - DataChat BI-style frontend
import os, re, time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

API = os.getenv("API_URL", "http://localhost:9000")

st.set_page_config(
    page_title="DataChat - Intelligent Data Query Platform",
    page_icon="bar_chart",
    layout="wide",
    initial_sidebar_state="expanded"
)

CSS = """
<style>
/* === Hide native Streamlit elements === */
[data-testid="stStatusWidget"] {display:none!important;}
header[data-testid="stHeader"] {display:none!important;}
div[data-testid="stDecoration"] {display:none!important;}
.stApp > header {display:none!important;}
button[kind="header"] {display:none!important;}
[data-testid="DeployButton"] {display:none!important;}
[data-testid="stToolbar"] {display:none!important;}

/* === Global === */
.stApp {
    background: #f5f7fa;
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
    color: #1f2329;
}
.block-container {padding-top: 0; padding-bottom: 0; max-width: 100%;}
element-container {padding-top: 0; padding-bottom: 0;}
div[data-styled-container="true"] {padding-top: 0;}

/* === Sidebar === */
section[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e5e6eb;
    min-width: 220px;
    max-width: 220px;
}
section[data-testid="stSidebar"] .block-container {padding-top: 0;}

/* Sidebar nav */
.stRadio > div {gap: 2px;}
.stRadio label {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 6px;
    margin: 2px 0;
    transition: all 0.15s ease;
    cursor: pointer;
    border: none;
    color: #4e5969;
    font-size: 14px;
}
.stRadio label:hover {background: #f2f3f5; color: #1f2329;}
.stRadio [aria-checked="true"] label {
    background: #e8f3ff;
    color: #1677ff;
    font-weight: 500;
}

/* === Buttons === */
.stButton > button {
    background: #1677ff;
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 6px 18px;
    font-weight: 500;
    font-size: 14px;
    transition: all 0.15s;
    line-height: 1.4;
}
.stButton > button:hover {background: #4096ff;}
.stButton > button:active {background: #0958d9;}
.stButton > button:disabled {background: #c9cdd4;}

/* === Chat === */
.stChatMessage {
    border-radius: 8px;
    border: 1px solid #e5e6eb;
    background: #ffffff;
    padding: 4px;
    margin: 8px 0;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.stChatMessage [data-testid="chatAvatarIcon-user"] {background: #1677ff;}
.stChatMessage [data-testid="chatAvatarIcon-assistant"] {background: #722ed1;}
.stChatMessage [data-testid="chatAvatarIcon-user"] svg,
.stChatMessage [data-testid="chatAvatarIcon-assistant"] svg {color: #fff;}

.stChatInput textarea {
    border: 1px solid #e5e6eb;
    border-radius: 8px;
    background: #fff;
    padding: 12px 14px;
    font-size: 14px;
    color: #1f2329;
}
.stChatInput textarea:focus {border-color: #1677ff; box-shadow: 0 0 0 2px rgba(22,119,255,0.1);}
.stChatInput [data-testid="stChatInputSendButton"] {background: #1677ff;}

/* === Cards & Tables === */
.kpi-card {
    background: #fff;
    border: 1px solid #e5e6eb;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
[data-testid="stDataFrame"], [data-testid="stTable"] {
    border: 1px solid #e5e6eb;
    border-radius: 8px;
    overflow: hidden;
    background: #fff;
}
[class*="dataframe"] th {
    background: #fafbfc;
    color: #1f2329;
    font-weight: 600;
    text-align: left;
    padding: 10px 14px;
    border-bottom: 1px solid #e5e6eb;
    font-size: 13px;
}
[class*="dataframe"] td {
    padding: 8px 14px;
    border-bottom: 1px solid #f2f3f5;
    color: #1f2329;
    font-size: 13px;
}
[class*="dataframe"] tr:last-child td {border-bottom: none;}

/* === Expander === */
.streamlit-expanderHeader {
    background: #fff;
    border: 1px solid #e5e6eb;
    border-radius: 8px;
    color: #1f2329;
    font-size: 14px;
}
.streamlit-expanderHeader:hover {background: #fafbfc;}

/* === Input / Text === */
.stTextInput input, .stTextArea textarea {
    border: 1px solid #e5e6eb;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 14px;
    color: #1f2329;
    background: #fff;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #1677ff;
    box-shadow: 0 0 0 2px rgba(22,119,255,0.1);
}

/* === Slider === */
.stSlider [role="slider"] {background: #1677ff;}

/* === Divider === */
hr {border-color: #e5e6eb; margin: 8px 0;}

/* === Scrollbar === */
::-webkit-scrollbar {width: 6px; height: 6px;}
::-webkit-scrollbar-thumb {background: #c9cdd4; border-radius: 3px;}
::-webkit-scrollbar-track {background: transparent;}

/* === Utility === */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 500;
    background: #e8f3ff;
    color: #1677ff;
    border: 1px solid #bed5ff;
}
.section-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2329;
    margin-bottom: 4px;
}
.section-desc {
    font-size: 13px;
    color: #86909c;
    margin-bottom: 12px;
}
"""
st.markdown(CSS, unsafe_allow_html=True)

# === Helper Functions ===
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
    df = pd.DataFrame(rows, columns=["Metric", "Value"])
    for col in df.columns[1:]:
        df[col] = df[col].apply(fmt_amount)
    return df

def get_kpi_cards(text):
    df = parse_table_from_text(text)
    if df is None or len(df) == 0:
        return None
    cards_html = '<div style="display:flex;gap:12px;margin:12px 0;flex-wrap:wrap;">'
    for _, row in df.iterrows():
        cards_html += f'''
        <div style="flex:1;min-width:140px;background:#fff;border:1px solid #e5e6eb;border-radius:8px;padding:14px 16px;box-shadow:0 1px 2px rgba(0,0,0,0.02);">
            <div style="font-size:12px;color:#86909c;margin-bottom:6px;">{row['Metric']}</div>
            <div style="font-size:22px;font-weight:700;color:#1f2329;letter-spacing:-0.5px;">{row['Value']}</div>
        </div>'''
    cards_html += '</div>'
    return cards_html

# === Sidebar Navigation ===
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 12px 8px;display:flex;align-items:center;gap:10px;">
        <div style="width:32px;height:32px;background:linear-gradient(135deg,#1677ff,#722ed1);border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:14px;">DC</div>
        <div>
            <div style="font-size:14px;font-weight:600;color:#1f2329;">DataChat</div>
            <div style="font-size:11px;color:#86909c;">Intelligent BI Platform</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)

    tab = st.radio(
        " ",
        [
            "\U0001f4ac  Agent Q&A",
            "\U0001f50d  Knowledge Base",
            "\U0001f4c4  Document Workflow"
        ],
        label_visibility="collapsed"
    )

    st.markdown('<hr style="border-color:#e5e6eb;margin:16px 0 8px;">', unsafe_allow_html=True)

    st.markdown("""
    <div style="padding:8px 12px 4px;font-size:12px;color:#86909c;font-weight:500;">TECH STACK</div>
    <div style="padding:4px 12px;font-size:12px;color:#4e5969;line-height:1.8;">
        <div><b style="color:#1f2329;">API</b>: FastAPI :9000</div>
        <div><b style="color:#1f2329;">Data</b>: MySQL mall_ads</div>
        <div><b style="color:#1f2329;">LLM</b>: Qwen2.5-7B</div>
        <div><b style="color:#1f2329;">Embed</b>: BGE-M3 Chroma</div>
        <div><b style="color:#1f2329;">Rerank</b>: BGE-Reranker</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#e5e6eb;margin:12px 0 8px;">', unsafe_allow_html=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown(f'<div style="padding:4px 12px;font-size:12px;color:#86909c;">{now}</div>', unsafe_allow_html=True)

# === Top Header Bar ===
st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;background:#fff;border-bottom:1px solid #e5e6eb;padding:12px 24px;">
    <div style="display:flex;align-items:center;gap:12px;">
        <span style="font-size:18px;font-weight:600;color:#1f2329;">Intelligent Data Query</span>
        <span class="badge">DEV</span>
    </div>
    <div style="display:flex;align-items:center;gap:16px;">
        <span style="font-size:13px;color:#86909c;">Analyst</span>
        <div style="width:32px;height:32px;background:#1677ff;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-size:13px;font-weight:500;">A</div>
    </div>
</div>
""", unsafe_allow_html=True)

# === Auth Token ===
if "token" not in st.session_state:
    try:
        r = requests.post(f"{API}/auth/token", params={"user": "analyst"}, timeout=10)
        st.session_state.token = r.json()["token"]
    except Exception as e:
        st.error(f"Cannot connect to backend: {e}")
        st.stop()
headers = {"Authorization": f"Bearer {st.session_state.token}"}

# === Agent Q&A ===
if tab.startswith("\U0001f4ac"):
    st.markdown("""
    <div style="padding:16px 24px 0;">
        <div class="section-title">Agent Q&A</div>
        <div class="section-desc">Natural language data query | Metric caliber consultation | Numeric computation</div>
    </div>
    """, unsafe_allow_html=True)

    if "history" not in st.session_state:
        st.session_state.history = []
    if "timings" not in st.session_state:
        st.session_state.timings = []

    if not st.session_state.history:
        st.markdown("""
        <div style="padding:24px;margin:16px 24px;background:#fff;border:1px solid #e5e6eb;border-radius:8px;text-align:center;">
            <div style="font-size:48px;margin-bottom:12px;">\U0001f4ac</div>
            <div style="font-size:16px;font-weight:600;color:#1f2329;margin-bottom:4px;">Hello, I am DataChat Assistant</div>
            <div style="font-size:13px;color:#86909c;margin-bottom:16px;">You can ask me about e-commerce metrics, data calibers, or computation</div>
        </div>
        <div style="padding:0 24px;">
            <div style="font-size:12px;color:#86909c;margin-bottom:8px;font-weight:500;">TRY ASKING:</div>
        </div>
        """, unsafe_allow_html=True)
        chip_cols = st.columns(4)
        suggestions = [
            "What is the GMV for the past 3 days?",
            "What is the definition of repurchase rate?",
            "Calculate latest AOV * 1.13",
            "How many paying users on 2026-08-21?"
        ]
        for i, s in enumerate(suggestions):
            with chip_cols[i]:
                if st.button(s, key=f"chip_{i}", use_container_width=True):
                    st.session_state._pending_question = s

    pending_q = getattr(st.session_state, "_pending_question", None)
    if pending_q:
        del st.session_state._pending_question

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
                        f'<div style="font-size:11px;color:#c9cdd4;margin-top:8px;">\u23f1 Response time {st.session_state.timings[i]:.2f}s</div>',
                        unsafe_allow_html=True
                    )

    q = st.chat_input(
        "Enter your question",
        placeholder="e.g. GMV for past 3 days / repurchase rate definition / latest AOV * 1.13"
    )
    if q or pending_q:
        question = q or pending_q
        st.session_state.history.append(("user", question))
        with st.chat_message("user"):
            st.markdown(f'<div style="color:#1f2329;font-size:14px;">{question}</div>', unsafe_allow_html=True)

        with st.spinner("Analyzing data..."):
            try:
                t0 = time.time()
                r = requests.post(
                    f"{API}/chat", headers=headers,
                    params={"q": question, "thread_id": "web"}, timeout=300
                )
                elapsed = time.time() - t0
                ans = r.json()["answer"]
            except Exception as e:
                ans = f"Request failed: {e}"
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
                f'<div style="font-size:11px;color:#c9cdd4;margin-top:8px;">\u23f1 Response time {elapsed:.2f}s</div>',
                unsafe_allow_html=True
            )

# === RAG Knowledge Base ===
elif tab.startswith("\U0001f50d"):
    st.markdown("""
    <div style="padding:16px 24px 0;">
        <div class="section-title">Knowledge Base Search</div>
        <div class="section-desc">BM25 + Vector Hybrid Retrieval | CrossEncoder Reranking</div>
    </div>
    """, unsafe_allow_html=True)

    col_search, col_btn = st.columns([5, 1])
    with col_search:
        q = st.text_input("Search", value="What is the statistical definition of repurchase rate?", label_visibility="collapsed")
    with col_btn:
        top_k = st.slider("Top K", min_value=1, max_value=5, value=3, label_visibility="visible")
        search_btn = st.button("Search", type="primary", use_container_width=True)

    if search_btn and q:
        with st.spinner("Searching knowledge base..."):
            try:
                t0 = time.time()
                r = requests.post(
                    f"{API}/kb/search", headers=headers,
                    params={"q": q, "top_k": top_k}, timeout=30
                )
                elapsed = time.time() - t0
                results = r.json()["results"]
                st.markdown(
                    f'<div style="font-size:12px;color:#86909c;margin:8px 24px;">Search completed in {elapsed:.2f}s, {len(results)} results</div>',
                    unsafe_allow_html=True
                )
                for i, item in enumerate(results, 1):
                    with st.expander(f"Result {i} | Source: {item['source']} | Score: {item['score']:.3f}"):
                        st.markdown(
                            f'<div style="font-size:13px;color:#1f2329;line-height:1.8;">{item["content"]}</div>',
                            unsafe_allow_html=True
                        )
            except Exception as e:
                st.error(f"Search failed: {e}")

# === Document Workflow ===
elif tab.startswith("\U0001f4c4"):
    st.markdown("""
    <div style="padding:16px 24px 0;">
        <div class="section-title">Document Processing Workflow</div>
        <div class="section-desc">Upload business documents, LLM intelligent extraction, structured storage</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown('<div style="padding:8px 0;font-size:14px;font-weight:500;color:#1f2329;">Document Extraction</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload business document", type=["md", "txt", "pdf"], help="Supports Markdown / Text / PDF")
        if uploaded:
            if st.button("Process", type="primary"):
                with st.spinner("Parse -> LLM Extract -> Validate -> Store..."):
                    try:
                        t0 = time.time()
                        r = requests.post(
                            f"{API}/workflow/run", headers=headers,
                            files={"file": (uploaded.name, uploaded.getvalue())},
                            timeout=60
                        )
                        elapsed = time.time() - t0
                        result = r.json()
                        st.success(f"{result['report']} ({elapsed:.2f}s)")
                    except Exception as e:
                        st.error(f"Processing failed: {e}")

    with col2:
        st.markdown('<div style="padding:8px 0;font-size:14px;font-weight:500;color:#1f2329;">Knowledge Base Management</div>', unsafe_allow_html=True)
        kb_file = st.file_uploader("Upload to KB", type=["md", "txt", "pdf"], key="kb", help="Full vector index rebuild after upload")
        if kb_file:
            if st.button("Store", type="primary", key="kb_btn"):
                with st.spinner("Parse -> Chunk -> Embed -> Store..."):
                    try:
                        r = requests.post(
                            f"{API}/kb/upload", headers=headers,
                            files={"file": (kb_file.name, kb_file.getvalue())},
                            timeout=60
                        )
                        st.success(f"Stored: {r.json()}")
                    except Exception as e:
                        st.error(f"Storage failed: {e}")
'''

# Write the file
target = r"E:\简历项目\03-智能问数Agent平台\datachat\web\frontend.py"
with open(target, "w", encoding="utf-8") as f:
    f.write(frontend_code.lstrip())
print("frontend.py written OK, size:", len(frontend_code))
