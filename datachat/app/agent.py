#!/usr/bin/env python3
# app/agent.py —— LangGraph 多工具 Agent（思考-工具调用循环）
from typing import Annotated, TypedDict
from langchain_ollama import ChatOllama
from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from app.tools import sql_query, kb_search, calculator, set_question
import threading
import os

SYSTEM_PROMPT = """你是电商数仓智能问数助手，基于 mall_ads 数仓回答业务问题。

=== 可用工具 ===
1. sql_query：执行 MySQL 查询（mall_ads 库，账号 agent_ro 只读）
2. kb_search：查询指标口径、数仓文档、业务定义
3. calculator：四则运算

=== 数仓表结构与业务含义 ===

【ads_trade_stats】每日交易事实表（主键 dt）
  dt          日期  '2026-08-19'~'2026-08-21' 共3天
  gmv         成交金额（GMV）  单位：元
  order_count 成交订单数
  pay_user_count 支付用户数
  avg_pay_amount 客单价 = gmv/order_count  单位：元

【ads_repurchase_rate】每日复购统计表（主键 dt）
  dt              日期
  order_user_count 下单用户数（当日有下单的去重用户数）
  repurchase_user_count 复购用户数（90天内二次及以上下单的去重用户数）
  repurchase_rate  复购率 = repurchase_user_count / order_user_count

【ads_user_rfm】用户RFM分层表（主键 dt+user_id，2824行）
  dt         日期
  user_id    用户ID
  r_score    最近购买得分 1-5档（5=最近30天内购买，1=超过90天）
  f_score    购买频次得分 1-5档（5=高频购买，1=低频购买）
  m_score    消费金额得分 1-5档（5=高消费，1=低消费）
  rfm_label  RFM分群标签 共8类：
    - 重要价值客户(R5F5M5)：R高F高M高，最优质客户
    - 重要保持客户(R5F1M5)：R高F低M高，需提升粘性
    - 重要发展客户(R5F5M1)：R高F高M低，有消费潜力
    - 重要挽留客户(R1F5M5)：R低F高M高，需挽留
    - 一般价值客户(R5F1M1)：R高F低M低
    - 一般保持客户(R1F5M1)：R低F高M低
    - 一般发展客户(R1F1M5)：R低F低M高
    - 一般挽留客户(R1F1M1)：R低F低M低

【doc_extract】业务文档抽取结果（合同/订单等结构化数据）
  id        自增ID
  customer  客户名称
  product   产品名称
  amount    金额  单位：元
  date      签订日期
  summary   业务摘要
  src_file  来源文件

=== 指标口径 ===
- GMV：Gross Merchandise Volume，成交总额，所有已支付订单的商品金额汇总
- 客单价(AOV)：平均每单消费金额 = GMV / 订单数
- 复购率：在统计周期内，发生二次及以上购买的用户数 / 购买用户总数
- 支付用户数：完成支付的去重用户数
- RFM模型：R(Recency最近购买时间)、F(Frequency购买频次)、M(Monetary消费金额)三维度评估客户价值

=== 数据范围 ===
- 日期覆盖：2026-08-19 至 2026-08-21（共3天，示例数据）
- 日期格式：字符串 'YYYY-MM-DD'，SQL 用 dt>='2026-08-19' 字符串比较
- 所有金额单位：元

=== 工具选择指引 ===
- 问具体数值/趋势/对比 → sql_query（查表）
- 问定义/口径/业务含义 → kb_search（查文档）
- 问计算/换算/百分比 → calculator（在sql_query查出数字后再用）
- 问合同/订单/客户信息/入库数据/最新入库 → sql_query 查 doc_extract 表
- 问RFM分群/客户分层 → sql_query 查 ads_user_rfm 表
- 问复购率/回购 → sql_query 查 ads_repurchase_rate 表
- 问GMV/订单数/客单价/支付用户 → sql_query 查 ads_trade_stats 表
- 复合问题：先 sql_query 查数，再 calculator 计算，或先 kb_search 查口径再 sql_query 查数

=== 关键规则 ===
1. 日期查询必须使用 2026 年，不要编造数据或日期
2. sql_query 返回错误时，阅读错误信息修正 SQL 后重试，最多 3 次
3. 需要计算时，先用 sql_query 查出数字，再用 calculator 计算，不要在 SQL 里做计算
4. 查询 doc_extract 用 date 字段筛选日期，用 customer/product 搜索客户或产品
5. 回答末尾注明数据日期或引用来源，不确定就说不确定，不要编造数字
6. 金额输出带千分位，如 410,354.42 元"""

class AgentState(TypedDict):
    messages: Annotated[list, lambda a, b: a + b]

tools = [sql_query, kb_search, calculator]
llm = ChatOllama(model="qwen2.5:7b-instruct-q4_K_M",
                 base_url=os.getenv("OLLAMA_BASE_URL", "http://172.30.224.1:11434"),
                 temperature=0).bind_tools(tools)

def _extract_last_user_msg(msgs):
    for m in reversed(msgs):
        if hasattr(m, "type") and m.type == "human":
            return m.content
    return ""


DOC_KEYWORDS = ["入库", "合同", "订单", "客户", "文档", "最新", "新增", "写入", "记录"]

def _pre_query_doc_extract(question: str) -> str:
    """检测到入库类关键词时，直接查 doc_extract 表，把结果注入上下文，
    避免7B模型因判断失误不调用工具。"""
    if not question or not any(kw in question for kw in DOC_KEYWORDS):
        return ""
    try:
        from app.tools import MYSQL_CONF
        import pymysql
        conn = pymysql.connect(
            host=MYSQL_CONF["host"], port=MYSQL_CONF["port"],
            user=MYSQL_CONF["user"], password=MYSQL_CONF["password"],
            database=MYSQL_CONF["database"], charset=MYSQL_CONF["charset"])
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
        return "【doc_extract 预查询结果】\n" + "\n".join(lines)
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
                    f"不要再反问用户指的是哪张表：\n{pre}"
        )]
    return {"messages": [llm.invoke(msgs)]}

def route(state):
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", route, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")
memory = MemorySaver()
agent_app = graph.compile(checkpointer=memory)

def chat(question: str, thread_id: str = "default") -> str:
    out = agent_app.invoke({"messages": [("user", question)]},
                           config={"configurable": {"thread_id": thread_id}})
    return out["messages"][-1].content

if __name__ == "__main__":
    print("=== Test 1: GMV ===")
    print(chat("最近三天的GMV是多少"))
    print("\n=== Test 2: 复购率口径 ===")
    print(chat("复购率的口径是什么"))
    print("\n=== Test 3: 计算器 ===")
    print(chat("把最新一天的GMV乘以1.13是多少"))
