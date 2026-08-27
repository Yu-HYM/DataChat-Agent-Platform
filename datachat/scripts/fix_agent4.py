with open("E:/简历项目/03-智能问数Agent平台/datachat/app/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '''def agent_node(state):
    msgs = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in msgs):
        msgs = [SystemMessage(content=SYSTEM_PROMPT)] + msgs
    return {"messages": [llm.invoke(msgs)]}'''

new = '''def agent_node(state):
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

content = content.replace(old, new)

with open("E:/简历项目/03-智能问数Agent平台/datachat/app/agent.py", "w", encoding="utf-8") as f:
    f.write(content)

print("OK" if "last_user_msg" in content else "FAIL")
