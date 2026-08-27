import os

target = r"E:\简历项目\03-智能问数Agent平台\datachat\web\frontend.py"

code = '''

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
                remaining = [l for l in text.split("\\n") if not re.match(r'^\\s*[-*]\\s+', l.strip())]
                if remaining:
                    st.markdown("\\n".join(remaining))
                if i < len(st.session_state.timings):
                    st.markdown(f'<div style="font-size:11px;color:#c9cdd4;margin-top:8px;">Response time {st.session_state.timings[i]:.2f}s</div>', unsafe_allow_html=True)

    q = st.chat_input("Enter your question", placeholder="e.g. GMV for past 3 days / repurchase rate / AOV * 1.13")
    if q or pending_q:
        question = q or pending_q
        st.session_state.history.append(("user", question))
        with st.chat_message("user"):
            st.markdown(f'<div style="color:#1f2329;font-size:14px;">{question}</div>', unsafe_allow_html=True)
        with st.spinner("Analyzing data..."):
            try:
                t0 = time.time()
                r = requests.post(f"{API}/chat", headers=headers, params={"q": question, "thread_id": "web"}, timeout=300)
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
            remaining = [l for l in ans.split("\\n") if not re.match(r'^\\s*[-*]\\s+', l.strip())]
            if remaining:
                st.markdown("\\n".join(remaining))
            st.markdown(f'<div style="font-size:11px;color:#c9cdd4;margin-top:8px;">Response time {elapsed:.2f}s</div>', unsafe_allow_html=True)
'''

with open(target, "a", encoding="utf-8") as f:
    f.write(code)

print("Part4 written")
