#!/usr/bin/env python3
# 阶段一收尾验证：关键包导入 + MySQL(agent_ro) 连通
import fastapi, uvicorn, langgraph, chromadb, sentence_transformers
import jieba, pypdf, pymysql, jwt, slowapi, loguru, streamlit, requests
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph
print('all imports OK')

conn = pymysql.connect(host='localhost', user='agent_ro', password='123456',
                       database='mall_ads', charset='utf8mb4')
cur = conn.cursor()
cur.execute('select dt,gmv,order_count from ads_trade_stats order by dt desc limit 2')
print('mysql agent_ro OK:', cur.fetchall())
conn.close()
print('STAGE 1 VERIFY PASS')
