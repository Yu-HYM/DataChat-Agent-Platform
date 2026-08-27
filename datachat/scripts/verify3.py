import sys
sys.stdout.reconfigure(encoding='utf-8')
data1 = open("E:/简历项目/03-智能问数Agent平台/datachat/app/tools.py", "rb").read()
data2 = open("E:/简历项目/03-智能问数Agent平台/datachat/app/agent.py", "rb").read()
compile(data1, "tools.py", "exec")
compile(data2, "agent.py", "exec")
print("Both compile OK")
print("tools.py has MYSQL_HOST:", b"MYSQL_HOST" in data1)
print("agent.py has MYSQL_CONF:", b"MYSQL_CONF" in data2)
