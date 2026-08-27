f = open("E:/简历项目/03-智能问数Agent平台/datachat/web/frontend.py", "rb")
data = f.read()
f.close()
# Find line 194
lines = data.split(b"\n")
for i in range(190, min(201, len(lines))):
    print(f"Line {i+1}: {lines[i][:80]}")
    if i == 193:  # line 194
        print(f"  Hex: {lines[i].hex()}")
