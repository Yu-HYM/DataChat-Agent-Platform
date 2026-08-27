import sys
sys.stdout.reconfigure(encoding='utf-8')
with open("web/frontend.py", "rb") as f:
    data = f.read()
print("Size:", len(data), "bytes")
bom = data[:3] == b"\xef\xbb\xbf"
print("BOM:", bom)
try:
    compile(data, "web/frontend.py", "exec")
    print("Compile OK")
except SyntaxError as e:
    print("SyntaxError:", e)
