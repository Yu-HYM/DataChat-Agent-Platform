import sys
f = open("web/frontend.py", "rb")
data = f.read()
f.close()
try:
    compile(data, "frontend.py", "exec")
    print("Compile OK, size:", len(data))
except SyntaxError as e:
    print("SyntaxError:", e)
