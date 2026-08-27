import os

target = r"E:\简历项目\03-智能问数Agent平台\datachat\web\frontend.py"

code = '''

# === Sidebar Navigation ===
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 12px 8px;display:flex;align-items:center;gap:10px;">
        <div style="width:32px;height:32px;background:linear-gradient(135deg,#1677ff,#722ed1);border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:14px;">DC</div>
        <div><div style="font-size:14px;font-weight:600;color:#1f2329;">DataChat</div><div style="font-size:11px;color:#86909c;">Intelligent BI Platform</div></div>
    </div>
    """, unsafe_allow_html=True)

    tab = st.radio(" ", ["\\U0001f4ac  Agent Q&A", "\\U0001f50d  Knowledge Base", "\\U0001f4c4  Document Workflow"], label_visibility="collapsed")

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
'''

with open(target, "a", encoding="utf-8") as f:
    f.write(code)

print("Part3 written")
