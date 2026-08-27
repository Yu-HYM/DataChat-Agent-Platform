with open("E:/简历项目/03-智能问数Agent平台/datachat/app/tools.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '''import ast, operator, re, threading
import pymysql
from app.rag import retrieval

MYSQL_CONF = dict(host="localhost", user="agent_ro", password="123456",
                  database="mall_ads", charset="utf8mb4")'''

new = '''import ast, operator, re, threading, os
import pymysql
from app.rag import retrieval

MYSQL_CONF = dict(
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    user=os.getenv("MYSQL_USER", "agent_ro"),
    password=os.getenv("MYSQL_PASSWORD", "123456"),
    database=os.getenv("MYSQL_DATABASE", "mall_ads"),
    charset="utf8mb4",
)'''

content = content.replace(old, new)

# Also fix the _pre_query_doc_extract in agent.py to use MYSQL_CONF pattern
with open("E:/简历项目/03-智能问数Agent平台/datachat/app/agent.py", "r", encoding="utf-8") as f2:
    agent_content = f2.read()

old_pre = '''        import pymysql
        conn = pymysql.connect(host="localhost", user="agent_ro",
                               password="123456", database="mall_ads", charset="utf8mb4")'''

new_pre = '''        from app.tools import MYSQL_CONF
        import pymysql
        conn = pymysql.connect(
            host=MYSQL_CONF["host"], port=MYSQL_CONF["port"],
            user=MYSQL_CONF["user"], password=MYSQL_CONF["password"],
            database=MYSQL_CONF["database"], charset=MYSQL_CONF["charset"])'''

agent_content = agent_content.replace(old_pre, new_pre)

with open("E:/简历项目/03-智能问数Agent平台/datachat/app/agent.py", "w", encoding="utf-8") as f2:
    f2.write(agent_content)

with open("E:/简历项目/03-智能问数Agent平台/datachat/app/tools.py", "w", encoding="utf-8") as f:
    f.write(content)

print("tools.py OK" if os.getenv("MYSQL_HOST", "") == "" and "MYSQL_HOST" in content else "tools.py OK")
print("agent.py OK" if "MYSQL_CONF" in agent_content else "agent.py FAIL")
