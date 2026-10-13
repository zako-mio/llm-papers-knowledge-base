import os, re, sys, json, glob
sys.stdout.reconfigure(encoding="utf-8")
# ★ L1 本地化（批 I · 裁定 L1=A）：⛔ 不再写死作者机绝对路径；由文件位置推导仓根。
#   ★ 实测更正：原指向的上游语料目录里**根本没有 `analysis/` 子目录**（0825 语料实测无该目录）
#   ⇒ 该生成器在改动前**必然 FileNotFoundError**（不是「能跑但结果不同」）。本地化同时把
#   输入面改到仓内 `docs/analysis/B3_P1`（那里 00/01/03 三件齐备）。
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B3 = os.path.join(BASE, "docs", "analysis", "B3_P1")
CSS = """
*{box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;background:#f7f8fa;color:#1f2430;line-height:1.8;margin:0}
.wrap{max-width:900px;margin:0 auto;padding:36px 20px 80px}
h1{font-size:25px;border-bottom:3px solid #2b6cb0;padding-bottom:10px;color:#14304f}
h2{font-size:19px;margin-top:34px;color:#2b6cb0;border-left:5px solid #2b6cb0;padding-left:10px}
h3{font-size:16px;color:#3a4a63;margin-top:22px}
p{margin:10px 0;}
blockquote{background:#eef3fa;border-left:4px solid #4a90d9;margin:12px 0;padding:10px 16px;color:#2c3e50}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}
th,td{border:1px solid #cbd5e1;padding:7px 10px;text-align:left;vertical-align:top}
th{background:#e8eef6}
tr:nth-child(even){background:#f4f7fb}
.num{color:#b45309;font-weight:700;font-family:ui-monospace,Consolas,monospace}
.infer{color:#9a6b2f;font-style:italic;background:#fdf6e3;padding:0 3px;border-radius:3px}
code{background:#eef1f5;padding:1px 5px;border-radius:4px;font-size:13px}
hr{border:none;border-top:1px dashed #cbd5e1;margin:26px 0}
.selfcheck{font-size:11px;color:#90a0b5;margin-top:40px;border-top:1px solid #dde3ea;padding-top:12px;font-family:ui-monospace,monospace}
"""
def md_to_html(md):
    lines = md.split("\n")
    out, in_ul, in_ol, in_table, in_bq = [], False, False, False, False
    table_rows = []
    def flush_table():
        nonlocal table_rows, in_table, out
        if not table_rows: return
        # simple: assume two-column-ish; render as table
        out.append("<table>")
        for r in table_rows:
            cells = [c.strip() for c in r.strip().strip("|").split("|")]
            tag = "th" if cells and all("--" not in c for c in cells) and len(table_rows) > 0 and table_rows.index(r)==0 else "td"
            out.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>")
        out.append("</table>")
        table_rows = []
    def inline(t):
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<![\w.])(\d[\d.,%×+\-~]*\d|[\d.]+%|\d+\.?\d* [kKmMtT]?)", lambda m: f'<span class="num">{m.group(1)}</span>', t)
        t = re.sub(r"(（推断）)", lambda m: f'<span class="infer">{m.group(1)}</span>', t)
        t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
        return t
    for ln in lines:
        if re.match(r"^\s*\|.*\|\s*$", ln):
            in_table = True; table_rows.append(ln); continue
        else:
            if in_table: flush_table(); in_table=False
        if ln.startswith("# "): out.append(f"<h1>{inline(ln[2:])}</h1>")
        elif ln.startswith("## "): out.append(f"<h2>{inline(ln[3:])}</h2>")
        elif ln.startswith("### "): out.append(f"<h3>{inline(ln[4:])}</h3>")
        elif ln.strip()=="---": out.append("<hr>")
        elif ln.strip().startswith(">"): out.append(f"<blockquote>{inline(ln.strip()[1:])}</blockquote>")
        elif re.match(r"^\s*[-*] ", ln):
            if not in_ul: out.append("<ul>"); in_ul=True
            out.append(f"<li>{inline(re.sub(r'^\s*[-*] ','',ln))}</li>")
        elif re.match(r"^\s*\d+[.)] ", ln):
            if not in_ol: out.append("<ol>"); in_ol=True
            out.append(f"<li>{inline(re.sub(r'^\s*\d+[.)] ','',ln))}</li>")
        else:
            if in_ul: out.append("</ul>"); in_ul=False
            if in_ol: out.append("</ol>"); in_ol=False
            if ln.strip(): out.append(f"<p>{inline(ln)}</p>")
    if in_table: flush_table()
    if in_ul: out.append("</ul>")
    if in_ol: out.append("</ol>")
    return "\n".join(out)
result = {}
for d in sorted(os.listdir(B3)):
    p = os.path.join(B3, d)
    if not os.path.isdir(p): continue
    md_path = os.path.join(p, "01-深度解读报告.md")
    html_path = os.path.join(p, "03-深度解读报告.html")
    if not os.path.exists(md_path): continue
    md = open(md_path, encoding="utf-8").read()
    title = d
    m0 = re.match(r"#\s+(.+)", md)
    if m0: title = m0.group(1)
    body = md_to_html(md)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · 深度解读</title><style>{CSS}</style></head><body><div class="wrap">
{body}
<div class="selfcheck">数据依据：本页 00-源数据提取.md | 推断处已标注（推断）| 生成：批量转换脚本</div>
</div></body></html>"""
    open(html_path, "w", encoding="utf-8").write(html)
    h = open(html_path, "rb").read().decode("utf-8")
    ok = ("\ufffd" not in h) and (h.count("<div") == h.count("</div>")) and len(h) > 8000
    result[d] = {"ok": ok, "kb": len(h)//1024}
print(json.dumps(result, ensure_ascii=False))
print("total", len(result), "ok", sum(1 for v in result.values() if v["ok"]))
