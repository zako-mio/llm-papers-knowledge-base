import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
# ★ L1 本地化（批 I · 裁定 L1=A）：⛔ 不再写死作者机绝对路径；由文件位置推导仓根。
#   ⚠ 本件读 e1–e5.json 并**就地覆写** data/papers_master.json；其产物已与仓内逐字节一致
#   （实测 sha256 相同），故本地化后重跑为幂等。
base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
eras = ["e1.json", "e2.json", "e3.json", "e4.json", "e5.json"]
master, seen, problems = [], {}, []
for f in eras:
    d = json.load(open(os.path.join(base, f), encoding="utf-8"))
    for i, pap in enumerate(d["papers"]):
        key = pap.get("id") or pap.get("ext_url") or pap.get("slug")
        if key in seen:
            problems.append("DUPLICATE %s in %s and %s" % (key, seen[key], f))
        else:
            seen[key] = f
        pap["_era"] = d["era"]
        missing = [k for k in ("t", "org", "d", "p", "c", "prev", "need", "win", "imp", "conf", "slug") if k not in pap]
        if missing:
            problems.append("%s[%d] %s: missing %s" % (f, i, pap.get("slug"), missing))
        master.append(pap)
stats = {}
dl = 0
for pap in master:
    stats[pap["p"]] = stats.get(pap["p"], 0) + 1
    if pap.get("id"):
        dl += 1
out = {
    "total": len(master),
    "downloadable": dl,
    "index_only": len(master) - dl,
    "priority": stats,
    "era_counts": {e: sum(1 for m in master if m["_era"] == e) for e in ["E1", "E2", "E3", "E4", "E5"]},
    "papers": master,
}
with open(os.path.join(base, "papers_master.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print(json.dumps({"total": len(master), "downloadable": dl, "priority": stats,
                  "era_counts": out["era_counts"], "problems": problems}, ensure_ascii=False))
