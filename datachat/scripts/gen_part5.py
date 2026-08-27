import os

target = r"E:\简历项目\03-智能问数Agent平台\datachat\web\frontend.py"

code = '''

# === RAG Knowledge Base ===
elif tab.startswith("\U0001f50d"):
    st.markdown("""
    <div style="padding:16px 24px 0;">
        <div class="section-title">Knowledge Base Search</div>
        <div class="section-desc">BM25 + Vector Hybrid Retrieval | CrossEncoder Reranking</div>
    </div>
    """, unsafe_allow_html=True)
    col_search, col_k = st.columns([5, 1])
    with col_search:
        q = st.text_input("Search", value="What is the statistical definition of repurchase rate?", label_visibility="collapsed")
    with col_k:
        top_k = st.slider("Top K", min_value=1, max_value=5, value=3, label_visibility="visible")
        search_btn = st.button("Search", type="primary", use_container_width=True)
    if search_btn and q:
        with st.spinner("Searching knowledge base..."):
            try:
                t0 = time.time()
                r = requests.post(f"{API}/kb/search", headers=headers, params={"q": q, "top_k": top_k}, timeout=30)
                elapsed = time.time() - t0
                results = r.json()["results"]
                st.markdown(f'<div style="font-size:12px;color:#86909c;margin:8px 24px;">Search completed in {elapsed:.2f}s, {len(results)} results</div>', unsafe_allow_html=True)
                for i, item in enumerate(results, 1):
                    with st.expander(f"Result {i} | Source: {item['source']} | Score: {item['score']:.3f}"):
                        st.markdown(f'<div style="font-size:13px;color:#1f2329;line-height:1.8;">{item["content"]}</div>', unsafe_allow_html=True)
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
                        r = requests.post(f"{API}/workflow/run", headers=headers, files={"file": (uploaded.name, uploaded.getvalue())}, timeout=60)
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
                        r = requests.post(f"{API}/kb/upload", headers=headers, files={"file": (kb_file.name, kb_file.getvalue())}, timeout=60)
                        st.success(f"Stored: {r.json()}")
                    except Exception as e:
                        st.error(f"Storage failed: {e}")
'''

with open(target, "a", encoding="utf-8") as f:
    f.write(code)

print("Part5 written")
