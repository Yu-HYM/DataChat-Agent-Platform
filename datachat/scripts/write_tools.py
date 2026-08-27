import sys
sys.stdout.reconfigure(encoding='utf-8')

content = '''#!/usr/bin/env python3
# app/tools.py - Agent 的三个工具：SQL查询 / 知识库检索 / 计算器
import ast, operator, re
import pymysql
from app.rag import retrieval

MYSQL_CONF = dict(host="localhost", user="agent_ro", password="123456",
                  database="mall_ads", charset="utf8mb4")

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}

DOC_KEYWORDS = ["入库", "合同", "订单", "客户", "文档", "最新", "新增", "写入", "记录"]


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    raise ValueError("不支持的运算")


def calculator(expression: str) -> str:
    """四则运算计算器。expression: 例如 '1.13 * 1899.43'"""
    tree = ast.parse(expression, mode="eval")
    return str(round(_safe_eval(tree.body), 4))


def sql_query(sql: str, question: str = "") -> str:
    """查询 mall_ads 数仓（只读）。sql: 一条 SELECT；question: 用户原始问题。
    共4张表：
    1. ads_trade_stats(dt,gmv,order_count,pay_user_count,avg_pay_amount) 每日交易
    2. ads_repurchase_rate(dt,order_user_count,repurchase_user_count,repurchase_rate) 复购
    3. ads_user_rfm(dt,user_id,r_score,f_score,m_score,rfm_label) RFM分层
    4. doc_extract(id,customer,product,amount,date,summary,src_file) 文档入库结果
    当 question 含"入库/合同/订单/客户/最新/文档"等关键词时，自动查询 doc_extract 表。"""
    if question and any(kw in question for kw in DOC_KEYWORDS):
        try:
            conn = pymysql.connect(**MYSQL_CONF)
            cur = conn.cursor()
            cur.execute(
                "SELECT id, customer, product, amount, date, summary, src_file "
                "FROM doc_extract ORDER BY id DESC LIMIT 10"
            )
            rows = cur.fetchall()
            conn.close()
            if not rows:
                return "doc_extract 表暂无数据"
            return "\\n".join(str(r) for r in rows)
        except Exception as e:
            return f"doc_extract 查询出错: {e}"
    s = sql.strip().rstrip(";")
    if not re.match(r"^(select|with|show)\\b", s, re.I):
        return "错误：仅允许 SELECT 查询"
    if ";" in s or re.search(r"\\b(insert|update|delete|drop|alter|create|grant)\\b", s, re.I):
        return "错误：检测到危险操作，已拦截"
    try:
        conn = pymysql.connect(**MYSQL_CONF)
        cur = conn.cursor()
        cur.execute(s)
        rows = cur.fetchall()
        conn.close()
        return "\\n".join(str(r) for r in rows[:20]) or "查询结果为空"
    except Exception as e:
        return f"SQL执行出错: {e}"


def kb_search(question: str) -> str:
    """检索数仓文档知识库，回答指标口径/字段含义类问题，返回带出处的内容"""
    hits = retrieval.search(question)
    if not hits:
        return "知识库未命中"
    return "\\n\\n".join(f"[来源:{h['source']}]\\n{h['content']}" for h in hits)
'''

with open("E:/简历项目/03-智能问数Agent平台/datachat/app/tools.py", "w", encoding="utf-8") as f:
    f.write(content)
print("OK, size:", len(content))
