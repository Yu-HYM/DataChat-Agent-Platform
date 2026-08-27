with open("E:/简历项目/03-智能问数Agent平台/datachat/app/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add import threading after existing imports
old_import = "from app.tools import sql_query, kb_search, calculator"
new_import = "from app.tools import sql_query, kb_search, calculator, set_question\nimport threading"
content = content.replace(old_import, new_import)

# 2. Replace the broken agent_node with clean version
old_node = '''def agent_node(state):
    msgs = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in msgs):
        msgs = [SystemMessage(content=SYSTEM_PROMPT)] + msgs
    # 把最新用户消息传给 sql_query 做关键词拦截
    last_user_msg = ""
    for m in reversed(msgs):
        if hasattr(m, "type") and m.type == "human":
            last_user_msg = m.content
            break
    import functools
    for t in tools:
        original = t
        def make_wrapper(fn, q):
            @functools.wraps(fn)
            def wrapper(sql, question=q):
                return fn(sql, question=question)
            return wrapper
    # 给 sql_query 绑定 question 参数
    import app.tools as _tools
    _tools.sql_query = make_wrapper(_tools.sql_query, last_user_msg)
    return {"messages": [llm.invoke(msgs)]}'''

new_node = '''def _extract_last_user_msg(msgs):
    for m in reversed(msgs):
        if hasattr(m, "type") and m.type == "human":
            return m.content
    return ""


def agent_node(state):
    msgs = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in msgs):
        msgs = [SystemMessage(content=SYSTEM_PROMPT)] + msgs
    # 线程安全：每个请求独立设置 question，不修改全局
    set_question(_extract_last_user_msg(msgs))
    return {"messages": [llm.invoke(msgs)]}'''

content = content.replace(old_node, new_node)

with open("E:/简历项目/03-智能问数Agent平台/datachat/app/agent.py", "w", encoding="utf-8") as f:
    f.write(content)

print("OK" if "_extract_last_user_msg" in content and "functools" not in content else "FAIL")
