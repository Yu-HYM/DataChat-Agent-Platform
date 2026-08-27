#!/usr/bin/env python3
# app/pipeline.py —— 文档处理工作流：解析->抽取->校验->入库->报告
import json
import pymysql
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from app.rag.ingest import parse_file, clean_text
import os

MYSQL_CONF = dict(host="localhost", user="root", password="123456",
                  database="mall_ads", charset="utf8mb4")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://172.30.224.1:11434")

llm = ChatOllama(model="qwen2.5:7b-instruct-q4_K_M",
                 base_url=OLLAMA_URL,
                 temperature=0, format="json")

EXTRACT_PROMPT = """从以下文本抽取业务信息，输出 json：
{{"customer": "客户名或null", "product": "产品名或null",
  "amount": 数字或null, "date": "yyyy-MM-dd或null", "summary": "50字内摘要"}}
文本：{text}"""

def node_parse(state):
    state["text"] = clean_text(parse_file(state["path"]))
    return state

def node_extract(state):
    try:
        out = llm.invoke(EXTRACT_PROMPT.format(text=state["text"][:3000]))
        raw = out.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        state["info"] = json.loads(raw)
    except Exception as e:
        state["error"] = f"LLM抽取失败: {e}"
        state["info"] = {}
    return state

def node_validate(state):
    info = state.get("info", {})
    if info.get("amount") is not None:
        try:
            info["amount"] = float(info["amount"])
        except (ValueError, TypeError):
            info["amount"] = None
    if not info.get("customer"):
        state["error"] = "未抽取到客户名"
    return state

def node_load(state):
    if state.get("error"):
        return state
    try:
        conn = pymysql.connect(**MYSQL_CONF)
        conn.cursor().execute(
            """CREATE TABLE IF NOT EXISTS doc_extract(
               id BIGINT AUTO_INCREMENT PRIMARY KEY, customer VARCHAR(64),
               product VARCHAR(64), amount DECIMAL(16,2), date VARCHAR(20),
               summary VARCHAR(255), src_file VARCHAR(128))""")
        i = state["info"]
        conn.cursor().execute(
            "INSERT INTO doc_extract(customer,product,amount,date,summary,src_file) "
            "VALUES(%s,%s,%s,%s,%s,%s)",
            (i.get("customer"), i.get("product"), i.get("amount"),
             i.get("date"), i.get("summary"), state["path"]))
        conn.commit()
        conn.close()
    except Exception as e:
        state["error"] = f"入库失败: {e}"
    return state

def node_report(state):
    if state.get("error"):
        state["report"] = f"处理失败: {state['error']}"
    else:
        i = state["info"]
        state["report"] = (f"已入库: 客户[{i.get('customer')}] 产品[{i.get('product')}] "
                           f"金额[{i.get('amount')}] 日期[{i.get('date')}] 摘要[{i.get('summary')}]")
    return state

def build():
    g = StateGraph(dict)
    for name, fn in [("parse", node_parse), ("extract", node_extract),
                     ("validate", node_validate), ("load", node_load),
                     ("report", node_report)]:
        g.add_node(name, fn)
    g.add_edge(START, "parse")
    g.add_edge("parse", "extract"); g.add_edge("extract", "validate")
    g.add_edge("validate", "load"); g.add_edge("load", "report")
    g.add_edge("report", END)
    return g.compile()

def run(path: str) -> str:
    return build().invoke({"path": path})["report"]

if __name__ == "__main__":
    import sys
    doc_path = sys.argv[1] if len(sys.argv) > 1 else "kb_docs/订单合同样例.md"
    print(f"Processing: {doc_path}")
    print(run(doc_path))
