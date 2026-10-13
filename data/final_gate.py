import json, os, sys, glob
sys.stdout.reconfigure(encoding="utf-8")
# ★ L1 本地化（批 I · 裁定 L1=A）：⛔ 不再写死作者机绝对路径；由文件位置推导仓根。
#   ⚠ 本件是**历史一批的门控**，不在本轮的门控集（gate-manifest.json）内、CI 不调用它。
#   本地化只改路径常量；其 `assert m["total"] == 125` 是**过期字面量**（仓内
#   data/papers_master.json 实测 total=133）⇒ 如实登记为「既有缺陷·本轮⛔ 不改判据」
#   （改它＝改判据，超出 L1 裁定的范围；见报告 decisions/warnings）。
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails, warns = [], []

# 1) master manifest
m = json.load(open(os.path.join(BASE, "data/papers_master.json"), encoding="utf-8"))
assert m["total"] == 125, "master total != 125"
ids = [p.get("id") or p.get("ext_url") or p.get("slug") for p in m["papers"]]
if len(ids) != len(set(ids)):
    fails.append("duplicate keys in master")

# 2) narratives embedded in html
nar = json.load(open(os.path.join(BASE, "data/era_narratives.json"), encoding="utf-8"))

# 3) timeline.html gates
hp = os.path.join(BASE, "timeline.html")
raw = open(hp, "rb").read()
try:
    html = raw.decode("utf-8")
except Exception as e:
    fails.append("html utf-8 decode: %s" % e)
    html = raw.decode("utf-8", errors="replace")
if "\ufffd" in html:
    fails.append("html contains U+FFFD")
if html.count("<div") != html.count("</div>"):
    fails.append("div unbalanced: %d vs %d" % (html.count("<div"), html.count("</div>")))
n_card = html.count('class="paper-card') + html.count("paper-card ")
if html.count("paper-card") < 98:
    fails.append("paper-card <98 (%d)" % html.count("paper-card"))
if html.count("era-block") < 5:
    fails.append("era-block <5")
for k, v in nar.items():
    if v["text"][:20] not in html:
        fails.append("narrative %s missing in html" % k)

# 4) README gates
rp = os.path.join(BASE, "README.md")
rd = open(rp, "rb").read().decode("utf-8")
if "\ufffd" in rd:
    fails.append("README U+FFFD")
n_abs = rd.count("arxiv.org/abs")
n_ext = rd.count("外部链接")
n_p3route = sum(1 for ln in rd.splitlines() if ln.strip().startswith(("1.", "2.", "3.")) and "——" in ln)
if n_abs + n_ext < 98:
    fails.append("README resource rows %d+%d <98" % (n_abs, n_ext))

# 5) disk PDFs full audit
missing, bad = [], []
for p in m["papers"]:
    if not p.get("id"):
        continue
    era_dir = None
    for d in sorted(glob.glob(os.path.join(BASE, "papers", "*"))):
        if os.path.basename(d).startswith(p["_era"]):
            era_dir = d
    fn = os.path.join(era_dir, "%s_%s_%s.pdf" % (p["d"], p["p"], p["slug"]))
    if not os.path.exists(fn):
        missing.append(os.path.basename(fn))
        continue
    with open(fn, "rb") as fh:
        head = fh.read(5)
    size = os.path.getsize(fn)
    if head != b"%PDF-" or size < 40000:
        bad.append("%s head=%r size=%d" % (os.path.basename(fn), head, size))
if missing:
    fails.append("missing PDFs: %s" % missing)
if bad:
    fails.append("bad PDFs: %s" % bad)

result = {
    "gate": "PASS" if not fails else "FAIL",
    "master_total": m["total"],
    "pdf_on_disk": len(glob.glob(os.path.join(BASE, "papers", "*", "*.pdf"))),
    "html_kb": round(os.path.getsize(hp) / 1024),
    "readme_abs_links": n_abs,
    "readme_ext_links": n_ext,
    "p3_route_lines": n_p3route,
    "verified_vs_cited": (
        sum(1 for p in m["papers"] if p["conf"] == "verified"),
        sum(1 for p in m["papers"] if p["conf"] == "cited"),
    ),
    "fails": fails,
    "warnings": warns,
}
print(json.dumps(result, ensure_ascii=False, indent=1))
