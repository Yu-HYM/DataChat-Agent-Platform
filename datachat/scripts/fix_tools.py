with open("E:/简历项目/03-智能问数Agent平台/datachat/app/tools.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '''def sql_query(sql: str) -> str:
    """查询数仓 ADS 指标库（只读）。sql: 一条 SELECT 语句。
    库表：ads_trade_stats(dt,gmv,order_count,pay_user_count,avg_pay_amount)
         ads_repurchase_rate(dt,repurchase_rate) ads_user_rfm(user_id,rfm_label)"""'''

new = '''def sql_query(sql: str) -> str:
    """查询数仓 ADS 指标库（只读）。sql: 一条 SELECT 语句。
    库表：
    ads_trade_stats(dt,gmv,order_count,pay_user_count,avg_pay_amount) 每日交易指标
    ads_repurchase_rate(dt,order_user_count,repurchase_user_count,repurchase_rate) 复购率
    ads_user_rfm(dt,user_id,r_score,f_score,m_score,rfm_label) 用户RFM分层
    doc_extract(id,customer,product,amount,date,summary,src_file) 业务文档抽取结果
    提示：问入库数据/合同/订单/客户 → 查 doc_extract；问GMV/订单/客单价 → 查 ads_trade_stats"""'''

content = content.replace(old, new)

with open("E:/简历项目/03-智能问数Agent平台/datachat/app/tools.py", "w", encoding="utf-8") as f:
    f.write(content)

print("OK" if "doc_extract" in content else "FAIL")
