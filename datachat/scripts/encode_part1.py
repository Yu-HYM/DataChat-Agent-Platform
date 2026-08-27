import base64, sys

# Original working frontend.py content (before my UI rewrite)
orig = '''#!/usr/bin/env python3
# web/frontend.py - DataChat frontend
import os, re, time
import requests
import pandas as pd
import streamlit as st

API = os.getenv("API_URL", "http://localhost:9000")

st.set_page_config(page_title="DataChat", page_icon="bar_chart", layout="wide", initial_sidebar_state="expanded")

CSS = """
<style>
[data-testid="stStatusWidget"] {display:none!important;}
header[data-testid="stHeader"] {display:none!important;}
div[data-testid="stDecoration"] {display:none!important;}
.stApp > header {display:none!important;}
button[kind="header"] {display:none!important;}
[data-testid="DeployButton"] {display:none!important;}
[data-testid="stToolbar"] {display:none!important;}
.stApp {background:#f7f8fa;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;}
.block-container {padding-top:1rem;padding-bottom:2rem;}
.stButton > button {background:#2563eb;color:white;border:none;border-radius:6px;padding:0.45rem 1.2rem;font-weight:500;}
.stButton > button:hover {background:#1d4ed8;}
.stButton > button:active {background:#1e40af;}
section[data-testid="stSidebar"] {background:#fff;border-right:1px solid #e5e7eb;}
.stRadio > div {gap:0;}
.stRadio label {padding:0.55rem 0.9rem;border-radius:6px;margin:0.15rem 0;cursor:pointer;border:1px solid transparent;}
.stRadio label:hover {background:#f0f4ff;}
.stRadio [aria-checked="true"] label {background:#eff6ff;border-color:#2563eb;color:#1d4ed8;font-weight:500;}
.stChatMessage {border-radius:10px;border:1px solid #e5e7eb;background:#fff;padding:0.25rem;margin:0.35rem 0;}
.stChatMessage [data-testid="chatAvatarIcon-user"] {background:#dbeafe;}
.stChatMessage [data-testid="chatAvatarIcon-assistant"] {background:#e0e7ff;}
.stChatInput textarea {border:1px solid #d1d5db;border-radius:8px;background:#fff;}
.stChatInput textarea:focus {border-color:#2563eb;}
hr {border-color:#e5e7eb;margin:0.8rem 0;}
[class*="dataframe"] th {background:#f8fafc;color:#374151;font-weight:600;text-align:left;padding:0.5rem 0.75rem;border-bottom:1px solid #e5e7eb;}
[class*="dataframe"] td {padding:0.4rem 0.75rem;border-bottom:1px solid #f3f4f6;color:#111827;}
.streamlit-expanderHeader {background:#fff;border:1px solid #e5e7eb;border-radius:8px;}
h1,h2,h3 {color:#111827;}
.env-tag {display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:500;background:#eff6ff;color:#2563eb;border:1px solid #bfdbfe;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
'''

encoded = base64.b64encode(orig.encode("utf-8")).decode("ascii")
print(encoded)
