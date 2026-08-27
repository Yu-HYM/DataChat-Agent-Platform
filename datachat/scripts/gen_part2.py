import os

target = r"E:\简历项目\03-智能问数Agent平台\datachat\web\frontend.py"

code = '''

def fmt_amount(val):
    try:
        v = float(str(val).replace(",", "").replace("\u5143", "").replace(" ", ""))
        return f"{v:,.2f}"
    except (ValueError, TypeError):
        return val

def parse_table_from_text(text):
    rows = []
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        m = re.match(r'^[-*]\\s+(.+?)[:：]\\s*(.+?)\\s*(?:\\u5143|\\u4e07\\u5143|)?$', line)
        if m:
            col1 = m.group(1).strip()
            col2 = m.group(2).strip()
            col2 = re.sub(r'[^\\d.,\\-]', '', col2)
            if col2:
                rows.append([col1, col2])
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["Metric", "Value"])
    for col in df.columns[1:]:
        df[col] = df[col].apply(fmt_amount)
    return df

def get_kpi_cards(text):
    df = parse_table_from_text(text)
    if df is None or len(df) == 0:
        return None
    cards_html = '<div style="display:flex;gap:12px;margin:12px 0;flex-wrap:wrap;">'
    for _, row in df.iterrows():
        cards_html += (
            '<div style="flex:1;min-width:140px;background:#fff;border:1px solid #e5e6eb;'
            'border-radius:8px;padding:14px 16px;box-shadow:0 1px 2px rgba(0,0,0,0.02);">'
            '<div style="font-size:12px;color:#86909c;margin-bottom:6px;">'
            + str(row["Metric"])
            + '</div><div style="font-size:22px;font-weight:700;color:#1f2329;letter-spacing:-0.5px;">'
            + str(row["Value"])
            + '</div></div>'
        )
    cards_html += "</div>"
    return cards_html
'''

with open(target, "a", encoding="utf-8") as f:
    f.write(code)

print("Part2 written")
