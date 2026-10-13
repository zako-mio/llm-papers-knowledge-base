#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_seo_meta.py — 站点**元数据门控**（批 J 统一件 · **硬档**）。

判据定义源（⛔ 不另造判据）：`solutions/_shared/SH4-seo-meta.md` §4.2；
实现形状沿用批 H 的 `12-factor-methodology-kg/gate_seo_meta.py`（S1–S10），批 J 做**四处判据硬化**
（全部带负向夹具，见 `--selftest`）：

  ★ 硬化 1 **去注释后再判**：`<!-- <meta name="description" content="x"> -->` 是假阳 ⇒ 先剥 HTML 注释。
  ★ 硬化 2 **canonical 必须自指**（SH4 §7 判据 3）：不仅要求存在，还要求它**等于该页自身 URL**
    （由 `seo_meta.pages_base_url` ＋ 页内相对路径拼出；`X/index.html` → `X/`）。
  ★ 硬化 3 **发布根感知**：扫描面 = `profile.publish_dir`（默认 `.`）；sitemap / robots / favicon
    一律在**发布根**判定（llm-papers 的发布根是 `docs/`，不是仓根）。
  ★ 硬化 4 **og 元组 5 项全判**：`og:title` / `og:description` / `og:type` / `og:url` / `og:image`。
    批 J 的目标是 `og_url_image_exempt` **为空**（⛔ 不以登记豁免换绿灯）。

执行强度：**hard**。★ 空集守卫（S1/S9）不随任何模式放宽。

判据（11 条）：
  S1  [blind] 空集守卫：产物页数 > 0 且 `<title>`、`<html lang>` 覆盖页数均 > 0
  S2  [hard]  每页有 `<title>`
  S3  [hard]  每页有 `<html lang>`
  S4  [hard]  每页有非空 `<meta name="description">`
  S5  [hard]  每页有 og:title / og:description / og:type / og:url / og:image
  S6  [hard]  每页有 `<link rel="canonical">`，为**绝对 URL** 且**自指**
  S7  [hard]  favicon：每页有 `<link rel="icon">`，或发布根存在 favicon 文件
  S8  [hard]  `sitemap.xml` 存在；`robots.txt` 存在且含 `Sitemap:` 指向它
  S9  [blind] 解析口径自检：每页解析出 ≥1 个 `<head>` 块
  S10 [report] description 长度分布（仅报告）
  S11 [report] canonical 自指偏差明细（仅报告；S6 已硬判，本项给出逐页差异便于修）

用法：
    python3 gate_seo_meta.py --site-root . --profile build/profile.json [--json]
    python3 gate_seo_meta.py --selftest
退出码：0 全过 / 1 有阻断级 FAIL / 2 输入错误 / 3 护栏拒读
"""
import argparse
import glob
import json
import os
import re
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

BLIND, HARD, REPORT = "blind", "hard", "report"
MODE = "hard"

HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
HEAD_BLOCK = re.compile(r"<head[^>]*>(.*?)</head>", re.I | re.S)
TITLE = re.compile(r"<title\s*>\s*[^<\s]", re.I)
LANG = re.compile(r"<html[^>]*\blang\s*=\s*\"[^\"]+\"", re.I)
DESC = re.compile(r'<meta[^>]*name\s*=\s*"description"[^>]*content\s*=\s*"([^"]*)"', re.I)
OG = re.compile(r'property\s*=\s*"(og:[a-z_]+)"', re.I)
CANON = re.compile(r'<link[^>]*rel\s*=\s*"canonical"[^>]*>', re.I)
CANON_HREF = re.compile(r'href\s*=\s*"([^"]*)"', re.I)
ICON = re.compile(r'<link[^>]*rel\s*=\s*"(?:icon|shortcut icon|apple-touch-icon)"', re.I)
ABSOLUTE = re.compile(r"^https?://[^/\s]+/", re.I)

OG_REQUIRED = ("og:title", "og:description", "og:type", "og:url", "og:image")
ROOT_FAVICONS = ("favicon.ico", "favicon.png", "favicon.svg")


class GuardError(Exception):
    """护栏拒读（exit 3）。"""


def load_json(path, label):
    if not os.path.isfile(path):
        raise GuardError("%s 不存在：%s" % (label, path))
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        raise GuardError("%s 非法 JSON：%s" % (label, exc))


def scan_base(site_root, profile):
    """★ 硬化 3：扫描面 = 发布根（profile.publish_dir）。"""
    pd = (profile.get("publish_dir") or ".").strip()
    if pd in ("", "."):
        return site_root
    return os.path.normpath(os.path.join(site_root, pd))


def product_pages(base, profile):
    cfg = profile.get("seo_meta") or {}
    skip = set(cfg.get("not_products") or [])
    out = []
    for p in sorted(glob.glob(os.path.join(base, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(p, base).replace(os.sep, "/")
        if "/vendor/" in "/" + rel or rel in skip:
            continue
        out.append(rel)
    return out


def page_url(base_url, rel):
    """页内相对路径 → 该页**自身**的规范 URL（`X/index.html` → `X/`）。"""
    if not base_url.endswith("/"):
        base_url += "/"
    if rel == "index.html":
        return base_url
    if rel.endswith("/index.html"):
        return base_url + rel[: -len("index.html")]
    return base_url + rel


def scan(base, rels):
    d = {}
    for rel in rels:
        raw = open(os.path.join(base, rel), encoding="utf-8", errors="replace").read()
        plain = HTML_COMMENT.sub("", raw)          # ★ 硬化 1
        heads = HEAD_BLOCK.findall(plain)
        head = "\n".join(heads)
        desc = DESC.search(head)
        cm = CANON.search(head)
        canon = ""
        if cm:
            hm = CANON_HREF.search(cm.group(0))
            canon = hm.group(1).strip() if hm else ""
        d[rel] = {"head": head, "heads": len(heads), "title": bool(TITLE.search(head)),
                  "lang": bool(LANG.search(plain)),
                  "desc": desc.group(1).strip() if desc else "",
                  "og": sorted(set(OG.findall(head))),
                  "canon": canon, "icon": bool(ICON.search(head))}
    return d


def judge(ctx):
    R = []
    site_root, profile = ctx["site_root"], ctx["profile"]
    cfg = profile.get("seo_meta") or {}
    base = scan_base(site_root, profile)
    base_url = (cfg.get("pages_base_url") or "").strip()
    if not base_url:
        raise GuardError("profile.seo_meta.pages_base_url 未声明（canonical 自指判据无基准）")
    ex_og = set(cfg.get("og_url_image_exempt") or [])
    ex_icon = set(cfg.get("favicon_exempt") or [])
    sitemap_reason = (cfg.get("sitemap_optional_reason") or "").strip()
    rels = product_pages(base, profile)
    P = scan(base, rels)

    def add(cid, name, ok, detail, klass):
        R.append((cid, name, bool(ok), detail, klass))

    n_title = sum(1 for v in P.values() if v["title"])
    n_lang = sum(1 for v in P.values() if v["lang"])
    why = []
    if not rels:
        why.append("产物 HTML 扫描面 0 个文件")
    if rels and n_title == 0:
        why.append("没有任何一页有 <title>")
    if rels and n_lang == 0:
        why.append("没有任何一页有 <html lang>")
    add("S1", "空集守卫（页数 / <title> / <html lang> 覆盖均非空）", not why,
        "；".join(why) if why else
        "产物 %d 页 · 有 <title> %d 页 · 有 <html lang> %d 页" % (len(rels), n_title, n_lang), BLIND)

    nostyle = sorted(r for r, v in P.items() if not v["heads"])
    add("S9", "解析口径自检（每页都解析出 ≥1 个 <head> 块）", not nostyle,
        "无 <head> 块的页：%s" % nostyle if nostyle else "%d 页全部解析出 <head> 块" % len(rels), BLIND)

    b2 = sorted(r for r, v in P.items() if not v["title"])
    add("S2", "每页有 <title>", not b2,
        "缺 <title> 的页：%s" % b2[:6] if b2 else "%d 页全部有 <title>" % len(rels), HARD)

    b3 = sorted(r for r, v in P.items() if not v["lang"])
    add("S3", "每页有 <html lang>", not b3,
        "缺 lang 的页：%s" % b3[:6] if b3 else "%d 页全部有 <html lang>" % len(rels), HARD)

    b4 = sorted(r for r, v in P.items() if not v["desc"])
    add("S4", "每页有非空 <meta name=\"description\">", not b4,
        "缺 description 的页：%d 页（例：%s）" % (len(b4), b4[:3]) if b4 else
        "%d 页全部有非空 description" % len(rels), HARD)

    b5 = []
    for rel, v in sorted(P.items()):
        need = set(OG_REQUIRED)
        if rel in ex_og:
            need -= {"og:url", "og:image"}
        miss = sorted(need - set(v["og"]))
        if miss:
            b5.append("%s 缺 %s" % (rel, miss))
    add("S5", "每页有 og:title/description/type/url/image（★ 目标：豁免表为空）", not b5,
        "；".join(b5[:3]) if b5 else
        "%d 页 og 5 项齐备（og:url/og:image 豁免登记 %d 项）" % (len(rels), len(ex_og)), HARD)

    b6, det6 = [], []
    for rel, v in sorted(P.items()):
        want = page_url(base_url, rel)
        if not v["canon"]:
            b6.append("%s 缺 canonical" % rel)
        elif not ABSOLUTE.match(v["canon"]):
            b6.append("%s canonical 非绝对 URL：%s" % (rel, v["canon"][:60]))
        elif v["canon"].rstrip("/") != want.rstrip("/"):
            b6.append("%s canonical 非自指：%s ≠ %s" % (rel, v["canon"][:60], want[:60]))
            det6.append("%s: %s → 期望 %s" % (rel, v["canon"], want))
    add("S6", "每页有 canonical，绝对 URL 且**自指**（SH4 §7 判据 3）", not b6,
        "；".join(b6[:3]) if b6 else "%d 页 canonical 全部绝对且自指" % len(rels), HARD)

    root_icon = [f for f in ROOT_FAVICONS if os.path.isfile(os.path.join(base, f))]
    b7 = sorted(r for r, v in P.items() if not v["icon"] and r not in ex_icon and not root_icon)
    add("S7", "favicon（每页 <link rel=icon>，或发布根有 favicon 文件）", not b7,
        "缺 favicon 的页：%d 页（例：%s）；发布根 favicon 文件：%s" % (len(b7), b7[:3], root_icon or "无")
        if b7 else "每页有 <link rel=icon> 或发布根有 favicon（%s）" % (root_icon or "link"), HARD)

    sm = os.path.isfile(os.path.join(base, "sitemap.xml"))
    rbp = os.path.join(base, "robots.txt")
    rb = os.path.isfile(rbp)
    rb_has = bool(rb and re.search(r"^\s*Sitemap\s*:", open(rbp, encoding="utf-8",
                                                             errors="replace").read(), re.I | re.M))
    b8 = []
    if not sm:
        b8.append("sitemap.xml 不存在")
    if not rb:
        b8.append("robots.txt 不存在")
    elif not rb_has:
        b8.append("robots.txt 未声明 Sitemap: 指向 sitemap.xml")
    if sitemap_reason:
        b8 = []
    add("S8", "sitemap.xml ＋ robots.txt(含 Sitemap:)", not b8,
        "；".join(b8) if b8 else ("sitemap 与 robots 齐备（发布根 %s）" % (profile.get("publish_dir") or ".")
                                  if not sitemap_reason else "未适用，理由已声明：%s" % sitemap_reason),
        HARD)

    lens = sorted(len(v["desc"]) for v in P.values() if v["desc"])
    add("S10", "description 长度分布（仅报告）", True,
        "有值 %d 条；长度 min/max = %s/%s" % (len(lens), lens[0] if lens else "-",
                                              lens[-1] if lens else "-"), REPORT)
    add("S11", "canonical 自指偏差明细（仅报告；S6 已硬判）", True,
        "；".join(det6[:3]) if det6 else "无偏差", REPORT)
    return R


def summarize(R):
    return {"judges": len(R), "fail_total": sum(1 for r in R if not r[2]),
            "blind_fail": sum(1 for r in R if r[4] == BLIND and not r[2]),
            "hard_fail": sum(1 for r in R if r[4] == HARD and not r[2])}


# --------------------------------------------------------------------------- selftest
BASE = "https://example.github.io/site/"


def _page(rel, head_extra=""):
    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
            '<title>t</title>'
            '<meta name="description" content="夹具描述">'
            '<meta property="og:title" content="t"><meta property="og:description" content="d">'
            '<meta property="og:type" content="website">'
            '<meta property="og:url" content="%s">'
            '<meta property="og:image" content="%sog.png">'
            '<link rel="canonical" href="%s">'
            '<link rel="icon" href="/favicon.ico">%s'
            '</head><body><main>hi</main></body></html>\n'
            % (page_url(BASE, rel), BASE, page_url(BASE, rel), head_extra))


FIX_PROFILE = {
    "site": "t", "form": "inline-single-source", "publish_dir": ".", "value_file": "v.json",
    "targets": [{"path": "a.html", "mode": "root-block", "family": "default"}],
    "gates": {"manifest": "m.json", "hard_blocking": ["token-consistency"], "commands": ["x"]},
    "seo_meta": {"not_products": [], "og_url_image_exempt": [], "favicon_exempt": [],
                 "pages_base_url": BASE},
}


def _fixture(tmp):
    os.makedirs(os.path.join(tmp, "sub"), exist_ok=True)
    with open(os.path.join(tmp, "a.html"), "w", encoding="utf-8") as fh:
        fh.write(_page("a.html"))
    with open(os.path.join(tmp, "sub", "b.html"), "w", encoding="utf-8") as fh:
        fh.write(_page("sub/b.html"))
    with open(os.path.join(tmp, "sub", "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_page("sub/index.html"))
    with open(os.path.join(tmp, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0"?><urlset></urlset>\n')
    with open(os.path.join(tmp, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write("Sitemap: %ssitemap.xml\n" % BASE)
    p = os.path.join(tmp, "profile.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(FIX_PROFILE, fh, ensure_ascii=False)
    return p


def _run_fixture(mutate=None):
    tmp = tempfile.mkdtemp(prefix="seo-")
    prof = _fixture(tmp)
    if mutate:
        mutate(tmp, prof)
    return judge({"site_root": tmp, "profile": json.load(open(prof, encoding="utf-8"))})


def selftest():
    cases = []

    def case(name, cid, mutate, expect_pass=False):
        try:
            R = _run_fixture(mutate)
        except Exception as exc:  # noqa: BLE001
            cases.append((name, False, "异常：%s" % exc))
            return
        got = {r[0]: r[2] for r in R}
        ok = all(r[2] for r in R) if expect_pass else (got.get(cid) is False)
        det = {r[0]: r[3] for r in R}.get(cid, "")
        cases.append((name, ok, "" if ok else "cid=%s → %s" % (cid, det[:170])))

    case("正向夹具应 0 FAIL（含 X/index.html → X/ 的自指口径）", None, None, expect_pass=True)

    def edit(name, fn):
        def _m(tmp, prof):
            fp = os.path.join(tmp, name)
            src = open(fp, encoding="utf-8").read()   # ★ 先读后写
            out = fn(src)
            assert out and out != src, "夹具自检：%s 未命中" % name
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write(out)
        return _m

    def setp(fn):
        def _m(tmp, prof):
            p = json.load(open(prof, encoding="utf-8"))
            fn(p)
            json.dump(p, open(prof, "w", encoding="utf-8"), ensure_ascii=False)
        return _m

    case("S1 负例：扫描面 0 个文件", "S1",
         setp(lambda p: p["seo_meta"].__setitem__("not_products",
                                                  ["a.html", "sub/b.html", "sub/index.html"])))
    case("S2 负例：某页缺 <title>", "S2",
         edit("a.html", lambda s: s.replace("<title>t</title>", "")))
    case("S3 负例：某页缺 <html lang>", "S3",
         edit("a.html", lambda s: s.replace('<html lang="zh-CN">', "<html>")))
    case("S4 负例：某页 description 为空", "S4",
         edit("a.html", lambda s: s.replace('content="夹具描述"', 'content=""')))
    case("★硬化1 负例：注释里的 description 不算数", "S4",
         edit("a.html", lambda s: s.replace('<meta name="description" content="夹具描述">',
                                            '<!-- <meta name="description" content="旧"> -->')))
    case("S5 负例：缺 og:type", "S5",
         edit("a.html", lambda s: s.replace('<meta property="og:type" content="website">', "")))
    case("★硬化4 负例：缺 og:image 且豁免表为空 ⇒ FAIL", "S5",
         edit("a.html", lambda s: s.replace(
             '<meta property="og:image" content="%sog.png">' % BASE, "")))
    case("S6 负例：某页缺 canonical", "S6",
         edit("a.html", lambda s: re.sub(r'<link rel="canonical"[^>]*>', "", s)))
    case("S6 负例：canonical 为相对 URL", "S6",
         edit("a.html", lambda s: s.replace('href="%sa.html"' % BASE, 'href="a.html"')))
    case("★硬化2 负例：canonical 指向别页（非自指）", "S6",
         edit("a.html", lambda s: s.replace('href="%sa.html"' % BASE, 'href="%ssub/b.html"' % BASE)))
    case("S7 负例：某页缺 favicon 且发布根无 favicon 文件", "S7",
         edit("a.html", lambda s: s.replace('<link rel="icon" href="/favicon.ico">', "")))
    case("S8 负例：缺 sitemap.xml", "S8",
         lambda t, p: os.remove(os.path.join(t, "sitemap.xml")))
    case("S8 负例：robots.txt 未声明 Sitemap:", "S8",
         edit("robots.txt", lambda s: "User-agent: *\n"))
    case("S9 负例：某页解析不出 <head> 块", "S9",
         edit("a.html", lambda s: re.sub(r"<head>.*?</head>", "", s, flags=re.S)))
    case("★硬化3 负例：publish_dir 指向子目录 ⇒ 扫描面随之（0 页 ⇒ S1 FAIL）", "S1",
         setp(lambda p: p.__setitem__("publish_dir", "docs")))

    ok = all(v for _, v, _ in cases)
    for name, res, note in cases:
        print("  [%s] %s%s" % ("PASS" if res else "FAIL", name, ("  ← " + note) if note else ""))
    print("\n=== gate_seo_meta.py 自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v, _ in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-root", default=".")
    ap.add_argument("--profile", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    site_root = os.path.abspath(a.site_root)
    pp = a.profile or "build/profile.json"
    if not os.path.isabs(pp):
        pp = os.path.join(site_root, pp)
    try:
        profile = load_json(pp, "profile")
        R = judge({"site_root": site_root, "profile": profile})
    except GuardError as exc:
        print("GUARD-REJECT: %s" % exc)
        return 3
    for cid, name, ok, detail, klass in R:
        print("[%s] %s %s %s — %s" % ("PASS" if ok else "FAIL", cid, name, klass, detail))
    c = summarize(R)
    print("\n=== 元数据门控（mode=%s）：%d 项判据，%d FAIL（blind %d / hard %d）==="
          % (MODE, c["judges"], c["fail_total"], c["blind_fail"], c["hard_fail"]))
    if a.json:
        print(json.dumps([{"id": i, "name": n, "ok": o, "class": k, "detail": d}
                          for i, n, o, d, k in R], ensure_ascii=False, indent=1))
    if c["blind_fail"]:
        print("阻断：空集守卫 FAIL（门控致盲，任何模式都不宽恕）")
        return 1
    if c["hard_fail"]:
        print("阻断：hard 类 FAIL（mode=%s）" % MODE)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
