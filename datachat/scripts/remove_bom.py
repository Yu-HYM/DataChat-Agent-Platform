p = "/mnt/e/简历项目/03-智能问数Agent平台/datachat/web/frontend.py"
data = open(p, "rb").read()
bom = b"\xef\xbb\xbf"
if data[:3] == bom:
    data = data[3:]
open(p, "wb").write(data)
print("BOM removed, size:", len(data))
