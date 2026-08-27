import sys
sys.stdout.reconfigure(encoding='utf-8')
files = [
    "E:/简历项目/03-智能问数Agent平台/datachat/app/tools.py",
    "E:/简历项目/03-智能问数Agent平台/datachat/app/agent.py"
]
for f in files:
    data = open(f, "rb").read()
    try:
        compile(data, f, "exec")
        print(f"OK: {f}")
    except SyntaxError as e:
        print(f"FAIL: {f} -> {e}")
