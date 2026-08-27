import os

# Read the current frontend.py to get the base
target = r"E:\简历项目\03-智能问数Agent平台\datachat\web\frontend.py"

code = '''#!/usr/bin/env python3
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
'''

with open(target, "w", encoding="utf-8") as f:
    f.write(code)

print("Part1 written, size:", len(code))
