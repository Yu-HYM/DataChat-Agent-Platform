with open("E:/简历项目/03-智能问数Agent平台/datachat/app/tools.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '''def sql_query(sql: str) -> str:
    """查询 mall_ads 数仓（只读）。sql: 一条 SELECT。
    共4张表：
    1. ads_trade_stats(dt,gmv,order_count,pay_user_count,avg_pay_amount) 每日交易
    2. ads_repurchase_rate(dt,order_user_count,repurchase_user_count,repurchase_rate) 复购
    3. ads_user_rfm(dt,user_id,r_score,f_score,m_score,rfm_label) RFM分层
    4. doc_extract(id,customer,product,amount,date,summary,src_file) 文档入库结果
    重要：用户问"入库数据""最新""合同""订单""客户"时，必须查 doc_extract 表！"""
    s = sql.strip().rstrip(";")
    if not re.match(r"^(select|with|show)\b", s, re.I):
        return "错误：仅允许 SELECT 查询"
    if ";" in s or re.search(r"\b(insert|update|delete|drop|alter|create|grant)\b", s, re.I):
        return "错误：检测到危险操作，已拦截"
    try:
        conn = pymysql.connect(**MYSQL_CONF)
        cur = conn.cursor()
        cur.execute(s)
        rows = cur.fetchall()
        conn.close()
        return "\n".join(str(r) for r in rows[:20]) or "查询结果为空"
    except Exception as e:
        return f"SQL执行出错: {e}"   # 错误回传给 Agent，让它自己修正重试'''

new = '''DOC_KEYWORDS = ["入库", "合同", "订单", "客户", "文档", "最新", "新增", "写入", "记录"]

def sql_query(sql: str, question: str = "") -> str:
    """查询 mall_ads 数仓（只读）。sql: 一条 SELECT；question: 用户原始问题。
    共4张表：
    1. ads_trade_stats(dt,gmv,order_count,pay_user_count,avg_pay_amount) 每日交易
    2. ads_repurchase_rate(dt,order_user_count,repurchase_user_count,repurchase_rate) 复购
    3. ads_user_rfm(dt,user_id,r_score,f_score,m_score,rfm_label) RFM分层
    4. doc_extract(id,customer,product,amount,date,summary,src_file) 文档入库结果
    当 question 含"入库/合同/订单/客户/最新/文档"等关键词时，自动查询 doc_extract 表。"""
    # 关键词拦截：如果用户问题涉及入库/合同等，强制查 doc_extract
    if question and any(kw in question for kw in DOC_KEYWORDS):
        safe_sql = sql.strip().rstrip(";")
        if not re.search(r"\bdoc_extract\b", safe_sql, re.I):
            try:
                conn = pymysql.connect(**MYSQL_CONF)
                cur = conn.cursor()
                cur.execute("SELECT id, customer, product, amount, date, summary, src_file FROM doc_extract ORDER BY id DESC LIMIT 10")
                rows = cur.fetchall()
                conn.close()
                if not rows:
                    return "doc_extract 表暂无数据"
                return "\n".join(str(r) for r in rows)
            except Exception as e:
                return f"doc_extract 查询出错: {e}"
    s = sql.strip().rstrip(";")
    if not re.match(r"^(select|with|show)\b", s, re.I):
        return "错误：仅允许 SELECT 查询"
    if ";" in s or re.search(r"\b(insert|update|delete|drop|alter|create|grant)\b", s, re.I):
        return "错误：检测到危险操作，已拦截"
    try:
        conn = pymysql.connect(**MYSQL_CONF)
        cur = conn.cursor()
        cur.execute(s)
        rows = cur.fetchall()
        conn.close()
        return "\n".join(str(r) for r in rows[:20]) or "查询结果为空"
    except Exception as e:
        return f"SQL执行出错: {e}"'''

content = content.replace(old, new)

with open("E:/简历项目/03-智能问数Agent平台/datachat/app/tools.py", "w", encoding="utf-8") as f:
    f.write(content)

print("OK" if "DOC_KEYWORDS" in content else "FAIL")
