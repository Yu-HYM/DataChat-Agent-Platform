target = r"E:\简历项目\03-智能问数Agent平台\datachat\web\frontend.py"
with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# Fix the broken split - replace literal newline in split with proper \n
# The broken pattern: split("\n") where \n is a literal newline
# We need: split("\n") where \n is the escape sequence
content = content.replace('split("\n")', 'split("\\n")')

# Also fix the split("\\n") in part4/5 which might have same issue
# And fix re.match patterns with \\s etc
# In the gen script, \\\\s became \\s in output, but we need \\s in the Python source
# Actually in the gen script: \\s (raw) -> \s in output. In Python, \s in regex is wrong, needs \\s
# Wait no: in Python source code, r'\\s' means regex \s. But if the file has r'\s' that's also correct.
# The issue is: in the gen script (raw string), \\s becomes \s in output. 
# In Python, r'\s' is the regex for whitespace. So that's correct.
# But for non-raw strings like re.match, we need \\s to produce \s
# Let me check what we have

# Actually let me just fix the split issue and the regex issue
# The gen script uses raw strings for CSS, but for code parts it uses regular strings
# In part2 gen: "\\n" -> \n (newline) -> this is the broken one
# I need to change the gen to use \\\\n -> \\n (literal backslash-n) in output

# Let me just fix the current file directly
import re

# Fix split: replace split(actual_newline) with split("\n")
content = content.replace('split("\n")', 'split("\\n")')

# Fix regex patterns: \\s should be \s in the output
# The gen script writes \\s which becomes \s in output (correct for regex)
# But \\d etc should also be correct

# Fix the join("\\n") patterns too
content = content.replace('join("\n")', 'join("\\n")')

# Fix re.match patterns
content = content.replace("r'^[-*]\\s+", "r'^[-*]\\s+")
content = content.replace("re.sub(r'[^\\d.,\\-]'", "re.sub(r'[^\\d.,\\-]'")

# Let me check what we actually have
print("Checking for issues...")
for i, line in enumerate(content.split("\n"), 1):
    if "split(" in line and "\n" in line:
        print(f"  Line {i}: {line[:80]}")

with open(target, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed!")
