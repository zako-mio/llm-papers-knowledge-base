import json, os, sys, glob
sys.stdout.reconfigure(encoding="utf-8")
try:
    import pymupdf as fitz
except Exception:
    import fitz
BASE = "/home/zako-mio/opencode/archive/Mission-file/2026-08/0825-LLM关键节点论文全集"
m = json.load(open(os.path.join(BASE, "data/papers_master.json"), encoding="utf-8"))
problems, ok = [], 0
for p in m["papers"]:
    if not p.get("id"):
        continue
    # locate pdf by slug pattern
    found = glob.glob(os.path.join(BASE, "papers", "*", "*_%s.pdf" % p["slug"])) or \
            glob.glob(os.path.join(BASE, "papers", "*", "%s_*_%s.pdf" % (p["d"], p["slug"])))
    if not found:
        problems.append("%s (id=%s): PDF not found for slug" % (p["slug"], p["id"]))
        continue
    f = found[0]
    try:
        doc = fitz.open(f)
        txt = doc[0].get_text()[:400]
        doc.close()
    except Exception as e:
        problems.append("%s: open fail %s" % (p["slug"], e))
        continue
    # expected keywords from title
    t = p["t"]
    # take first 2-3 significant tokens
    import re
    kw = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", t)[:3]
    hit = sum(1 for k in kw if k.lower() in txt.lower())
    ok += 1
    if hit < 2 and kw:
        problems.append("%s: title-mismatch? kw=%s pdf_head='%s'" % (p["slug"], kw, " ".join(txt.split()[:20])))
print(json.dumps({"checked": ok, "issues": len(problems)}, ensure_ascii=False))
for x in problems:
    print(" •", x)
