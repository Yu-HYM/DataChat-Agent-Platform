with open("E:/简历项目/03-智能问数Agent平台/datachat/web/frontend.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the closing triple-single-quote with triple-double-quote
# The pattern is: </style>\n'''  ->  </style>\n"""
old = "</style>\n'''"
new = '</style>\n"""'
content = content.replace(old, new, 1)

with open("E:/简历项目/03-智能问数Agent平台/datachat/web/frontend.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed! Checking...")

# Now check compilation
try:
    compile(content, "frontend.py", "exec")
    print("Compile OK!")
except SyntaxError as e:
    print(f"Still error: {e}")
