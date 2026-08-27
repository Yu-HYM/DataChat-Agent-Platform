with open("E:/简历项目/03-智能问数Agent平台/datachat/app/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '''def agent_node(state):
    msgs = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in msgs):
        msgs = [SystemMessage(content=SYSTEM_PROMPT)] + msgs
    # 线程安全：每个请求独立设置 question，不修改全局
    set_question(_extract_last_user_msg(msgs))
    return {"messages": [llm.invoke(msgs)]}'''

new = '''DOC_KEYWORDS = ["入库", "合同", "订单", "客户", "文档", "最新", "新增", "写入", "记录"]

def _pre_query_doc_extract(question: str) -> str:
    """检测到入库类关键词时，直接查 doc_extract 表，把结果注入上下文，
    避免7B模型因判断失误不调用工具。"""
    if not question or not any(kw in question for kw in DOC_KEYWORDS):
        return ""
    try:
        import pymysql
        conn = pymysql.connect(host="localhost", user="agent_ro",
                               password="123456", database="mall_ads", charset="utf8mb4")
        cur = conn.cursor()
        cur.execute(
            "SELECT id, customer, product, amount, date, summary, src_file "
            "FROM doc_extract ORDER BY id DESC LIMIT 10"
        )
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return ""
        lines = [f"id={r[0]}, 客户={r[1]}, 产品={r[2]}, 金额={r[3]}, 日期={r[4]}, 摘要={r[5]}, 来源={r[6]}" for r in rows]
        return "【doc_extract 预查询结果】\\n" + "\\n".join(lines)
    except Exception as e:
        return f"doc_extract 预查询出错: {e}"


def agent_node(state):
    msgs = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in msgs):
        msgs = [SystemMessage(content=SYSTEM_PROMPT)] + msgs
    # 线程安全：每个请求独立设置 question，不修改全局
    user_q = _extract_last_user_msg(msgs)
    set_question(user_q)
    # 入库类问题：预查 doc_extract，结果注入上下文
    pre = _pre_query_doc_extract(user_q)
    if pre:
        # 在用户消息后注入一条 system 提示，强制引导模型基于真实数据回答
        msgs = list(msgs) + [SystemMessage(
            content=f"以下是 doc_extract 表的最新数据，你必须基于这些数据回答用户问题，"
                    f"不要再反问用户指的是哪张表：\\n{pre}"
        )]
    return {"messages": [llm.invoke(msgs)]}'''

content = content.replace(old, new)

with open("E:/简历项目/03-智能问数Agent平台/datachat/app/agent.py", "w", encoding="utf-8") as f:
    f.write(content)

print("OK" if "_pre_query_doc_extract" in content else "FAIL")
