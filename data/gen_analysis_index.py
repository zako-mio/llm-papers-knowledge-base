import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
# ★ L1 本地化（批 I · 裁定 L1=A）：⛔ 不再写死作者机绝对路径；由文件位置推导仓根。
#   输入（data/papers_master.json）与产物（docs/analysis/index.html）在仓内均存在
#   ⇒ 本地化后**行为等价**（实测：重跑产物与改动前逐字节相同）。
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ★ 产物归属声明：本件认领 docs/analysis/index.html（gate_tokens.py 的 G8/G9 用 ast 扫 OUT_PATH）。
OUT_PATH = os.path.join(BASE, "docs", "analysis", "index.html")
master = json.load(open(os.path.join(BASE, "data/papers_master.json"), encoding="utf-8"))
TOTAL = master["total"]
batch_meta = {p["slug"]: p for p in master["papers"]}
batches = [("B1_P3", "P3 · 必读核心", "#f59e0b"), ("B2_P2", "P2 · 重要", "#3b82f6"), ("B3_P1", "P1 · 基础补充", "#9ca3af")]
cards, done_total = [], 0
for bid, label, color in batches:
    bd = os.path.join(BASE, "docs", "analysis", bid)
    if not os.path.isdir(bd):
        continue
    slugs = sorted(os.listdir(bd))
    slugs = [s for s in slugs if os.path.isdir(os.path.join(bd, s))]
    done_total += len(slugs)
    items = []
    for s in slugs:
        m = batch_meta.get(s, {})
        has03 = os.path.exists(os.path.join(bd, s, "03-深度解读报告.html"))
        link = ("%s/%s/03-深度解读报告.html" % (bid, s)) if has03 else None
        era = m.get("_era", "?"); date = m.get("d", "?"); org = m.get("org", "")
        title = m.get("t", s)
        inner = '<a href="%s"><strong>%s</strong></a><span class="m">%s · %s · %s</span>' % (link, title, date, org, era) if link else '<span class="dis">%s</span><span class="m">%s · %s · %s</span>' % (title, date, org, era)
        items.append('<li>%s</li>' % inner)
    cards.append(
        '<section class="batch" style="--c:%s"><h2>%s <small>%s · %d 篇已完成</small></h2><ol>%s</ol></section>'
        % (color, bid, label, len(slugs), "".join(items)))
html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LLM 关键节点论文 · 深度解读总览</title>
<style>
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#0f1420;color:#e6e9f0;margin:0;line-height:1.7}
.wrap{max-width:900px;margin:0 auto;padding:40px 20px 80px}
h1{font-size:26px;border-bottom:2px solid #2b6cb0;padding-bottom:12px}
.sub{color:#93a1b8;margin-top:-6px}
.batch{margin-top:36px;border-left:4px solid var(--c);padding-left:16px}
.batch h2{font-size:19px;color:var(--c)}
.batch small{color:#7d8aa0;font-weight:400}
ol{list-style:none;padding:0}
li{background:#161d2e;border-radius:8px;padding:10px 14px;margin:8px 0;display:flex;flex-direction:column;gap:2px}
li a{color:#7cb3ff;text-decoration:none;font-size:15px}
li a:hover{text-decoration:underline}
.m{color:#8fa0b8;font-size:12px}
.dis{color:#cdd6e4;font-size:15px}
.note{background:#1a2233;border-radius:8px;padding:12px 16px;font-size:13px;color:#aeb9cc;margin-top:30px}
</style></head><body><div class="wrap">
<h1>LLM 关键节点论文 · 深度解读总览</h1>
    <p class="sub">__TOTAL__ 个关键节点 · 按优先级分批深度解读（六层结构：问题定位→概念内核→方法拆解→证据链→批判→启示）· 点击标题进入 HTML 解读版</p>
    __CARDS__
    <div class="note">进度：已完成深度解读 __DONE__ / __TOTAL__ 篇。批次顺序 B1(P3) → B2(P2) → B3(P1)。每篇目录含 00-源数据提取.md（AI 权威数据层）、01-深度解读报告.md（AI 镜像）、03-深度解读报告.html（人类阅读入口）。论文 PDF（Git LFS）下载入口见<a href="../timeline.html" style="color:#7cb3ff">互动时间线</a>。</div>
    </div></body></html>""".replace("__TOTAL__", str(TOTAL)).replace("__CARDS__", "".join(cards)).replace("__DONE__", str(done_total))
out = OUT_PATH
open(out, "w", encoding="utf-8").write(html)
h = open(out, "rb").read()
assert "\ufffd".encode() not in h
print("index.html written:", len(h), "bytes,", done_total, "entries linked")
