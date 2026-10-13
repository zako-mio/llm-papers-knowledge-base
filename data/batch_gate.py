import os, sys, glob, json
sys.stdout.reconfigure(encoding="utf-8")
# ★ L1 本地化（批 I · 裁定 L1=A）：原先写死作者机绝对路径 `/home/…/0825-LLM关键节点论文全集`
#   ⇒ 他人机器与 CI 无法重跑。现改为**由本文件位置推导仓根**（data/ 的上一级）。
#   同时把产物面从上游语料的 `analysis/<批次>` 改为仓内 `docs/analysis/<批次>`。
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
batch_dir = os.path.join(BASE, "docs", "analysis", sys.argv[1] if len(sys.argv) > 1 else "B1_P3")
fails, rows = [], []
for d in sorted(os.listdir(batch_dir)):
    p = os.path.join(batch_dir, d)
    if not os.path.isdir(p):
        continue
    f00 = os.path.join(p, "00-源数据提取.md")
    f01 = os.path.join(p, "01-深度解读报告.md")
    f03 = os.path.join(p, "03-深度解读报告.html")
    row = {"slug": d}
    for k, f, mn in [("00", f00, 4500), ("01", f01, 18000), ("03", f03, 15000)]:
        if not os.path.exists(f):
            fails.append("%s missing %s" % (d, k))
            row[k] = "MISSING"
            continue
        b = os.path.getsize(f)
        row[k] = b
        if b < mn:
            fails.append("%s %s too small: %d" % (d, k, b))
    if os.path.exists(f03):
        import re
        h = open(f03, "rb").read().decode("utf-8", errors="replace")
        if "\ufffd" in h:
            fails.append("%s html U+FFFD" % d)
        hs = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", h, flags=re.S | re.I)
        if hs.count("<div") != hs.count("</div>"):
            fails.append("%s html div unbalanced %d/%d" % (d, hs.count("<div"), hs.count("</div>")))
    rows.append(row)
print(json.dumps({"batch": os.path.basename(batch_dir), "dirs": len(rows),
                  "gate": "PASS" if not fails else "FAIL", "fails": fails}, ensure_ascii=False))
for r in rows:
    print("%-38s 00=%-7s 01=%-7s 03=%-7s" % (r["slug"], r.get("00"), r.get("01"), r.get("03")))
