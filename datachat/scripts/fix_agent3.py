with open("E:/简历项目/03-智能问数Agent平台/datachat/app/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '''=== 工具选择指引 ===
- 问具体数值/趋势/对比 → sql_query（查表）
- 问定义/口径/业务含义 → kb_search（查文档）
- 问计算/换算/百分比 → calculator（在sql_query查出数字后再用）
- 问合同/订单/客户信息 → sql_query 查 doc_extract 表
- 复合问题：先 sql_query 查数，再 calculator 计算，或先 kb_search 查口径再 sql_query 查数'''

new = '''=== 工具选择指引 ===
- 问具体数值/趋势/对比 → sql_query（查表）
- 问定义/口径/业务含义 → kb_search（查文档）
- 问计算/换算/百分比 → calculator（在sql_query查出数字后再用）
- 问合同/订单/客户信息/入库数据/最新入库 → sql_query 查 doc_extract 表
- 问RFM分群/客户分层 → sql_query 查 ads_user_rfm 表
- 问复购率/回购 → sql_query 查 ads_repurchase_rate 表
- 问GMV/订单数/客单价/支付用户 → sql_query 查 ads_trade_stats 表
- 复合问题：先 sql_query 查数，再 calculator 计算，或先 kb_search 查口径再 sql_query 查数'''

content = content.replace(old, new)

with open("E:/简历项目/03-智能问数Agent平台/datachat/app/agent.py", "w", encoding="utf-8") as f:
    f.write(content)

print("OK" if "最新入库" in content else "FAIL")
