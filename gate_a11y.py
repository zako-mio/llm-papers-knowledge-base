#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_a11y.py — 站点**无障碍门控**（批 J 统一件 · **硬档**）。

判据定义源（⛔ 不另造判据）：`solutions/_shared/SH2-a11y-baseline.md` §4.2；
实现形状沿用批 H 的 `12-factor-methodology-kg/gate_a11y.py`（A1–A7），批 J 做**三处判据硬化**
（全部带负向夹具，见 `--selftest`）：

  ★ 硬化 1 **形态感知**（批 I 的 I6 教训）：`:focus-visible` 的引用面 = 页面内联 `<style>`
    **∪ 页内 `<link rel="stylesheet">` 指向的本地 CSS**。批 H 的 A4/A7 只扫内联 `<style>`
    ⇒ 对**外链站**（control-theory / algorithm-kg 的外链族）会**形态错位**：判据对象 ≠ 断言对象。
  ★ 硬化 2 **去注释后再判**（SH5 §4.2 第 2 条）：`/* … :focus-visible … */` 与
    `<!-- <a href="#main"> -->` 都是假阳 ⇒ HTML 注释与 CSS 注释一律先剥离。
  ★ 硬化 3 **skip link 的目标必须真的存在**（「巧合余部解析」）：`href="#main-nav"` 命中前缀
    口径却**不是** skip link ⇒ A3 改为「href 前缀匹配 **且** 该 `#id` 在同页存在」。

执行强度：**hard**（批 J 转硬档）。★ 空集守卫（A1/A7）不随任何模式放宽。

判据（7 条）：
  A1 [blind] 空集守卫：产物页数 > 0，且至少一页有 `<main>`、至少一页有图件文本等价载体
  A2 [hard]  每页有且仅有 1 个 `<main>`（`main_landmark_exempt` 逐页登记，★ 批 J 目标＝该表为空）
  A3 [hard]  每页有 skip link（`href="#main|#content|#skip"` **且目标 id 在同页存在**）
  A4 [hard]  每页的 CSS 语料（内联 ∪ 本地外链，剥注释）声明 `:focus-visible`
  A5 [hard]  图件文本等价（`<img>` 必有 `alt`；`<svg>` 必有 `role="img"` ＋ `aria-label`/`<title>`）
  A6 [hard]  豁免登记不得过期（声明项必须存在且**真的**违反）
  A7 [blind] 解析口径自检：每页的 CSS 语料**可解析**（有内联 `<style>` 或有可解析的本地外链 CSS），
             且全站 CSS 源集合非空（防「正则哑火 ⇒ 判据恒真」）

用法：
    python3 gate_a11y.py --site-root . --profile build/profile.json [--json]
    python3 gate_a11y.py --selftest
退出码：0 全过 / 1 有阻断级 FAIL / 2 输入错误 / 3 护栏拒读
"""
import argparse
import fnmatch
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
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.I | re.S)
LINK_CSS = re.compile(r'<link[^>]*rel\s*=\s*"stylesheet"[^>]*>', re.I)
HREF_ATTR = re.compile(r'href\s*=\s*"([^"]*)"', re.I)
ANCHOR_FULL = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
SKIP_HREF = re.compile(r'href\s*=\s*"#(?:main|content|skip)', re.I)
SKIP_SIGNAL = re.compile(r"跳到|跳至|跳转|skip", re.I)
ID_ATTR = re.compile(r'\bid\s*=\s*"([^"]+)"', re.I)
MAIN = re.compile(r"<main\b", re.I)
IMG = re.compile(r"<img\b[^>]*>", re.I)
# ★★ 批 J 判据实现更正（★ 判据对象 == 断言对象；⛔ 未放宽判据）：
#    批 H 的写法是 `<svg\b[^>]*>(.*?)</svg>`，`findall` 只捕获**开标签之后的内容**，
#    却拿 `ROLE_IMG` / `ARIA_LABEL` 去搜**捕获组**——于是「写在开标签上的 `role="img"` /
#    `aria-label="…"`」被判定为**不存在**（写的正是合法且标准的位置）。
#    ⇒ 改为整段捕获（开标签 ＋ 内容），`role`/`aria-label` 在整段里找、`<title>` 在内容里找。
#    ★ 这不是放宽：无标签的 `<svg>` 照旧 FAIL（见 --selftest 的 A5 负例）。
SVG = re.compile(r"(<svg\b[^>]*>)(.*?)(</svg\s*>)", re.I | re.S)
ALT = re.compile(r"\balt\s*=", re.I)
ROLE_IMG = re.compile(r'role\s*=\s*"img"', re.I)
ARIA_LABEL = re.compile(r'aria-label\s*=\s*"[^"]+"', re.I)
URL_SCHEME = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|data:|#)", re.I)


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
    """★ 硬化 1b：扫描面 = 发布根（`profile.publish_dir`），与 seo 门控同口径。"""
    pd = (profile.get("publish_dir") or ".").strip()
    if pd in ("", "."):
        return site_root
    return os.path.normpath(os.path.join(site_root, pd))


def product_pages(base, profile):
    cfg = profile.get("a11y") or {}
    skip = set(cfg.get("not_products") or [])
    out = []
    for p in sorted(glob.glob(os.path.join(base, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(p, base).replace(os.sep, "/")
        if "/vendor/" in "/" + rel or rel in skip:
            continue
        out.append(rel)
    return out


def local_css_texts(site_root, rel, plain):
    """页内 `<link rel="stylesheet">` 指向的**本地** CSS 文本（形态感知的核心）。"""
    texts, missing, n_ext = [], [], 0
    base = os.path.dirname(os.path.join(site_root, rel))
    for tag in LINK_CSS.findall(plain):
        m = HREF_ATTR.search(tag)
        if not m:
            continue
        href = m.group(1).strip()
        if not href or URL_SCHEME.match(href):
            if href:
                n_ext += 1
            continue
        href = href.split("?")[0].split("#")[0]
        target = os.path.normpath(os.path.join(base, href.lstrip("/")))
        if os.path.isfile(target):
            texts.append(open(target, encoding="utf-8", errors="replace").read())
        else:
            missing.append(href)
    return texts, missing, n_ext


def scan(site_root, rels):
    d = {}
    for rel in rels:
        raw = open(os.path.join(site_root, rel), encoding="utf-8", errors="replace").read()
        plain = HTML_COMMENT.sub("", raw)
        styles = STYLE_BLOCK.findall(plain)
        linked, missing, n_ext = local_css_texts(site_root, rel, plain)
        corpus = CSS_COMMENT.sub("", "\n".join(styles) + "\n" + "\n".join(linked))
        ids = set(ID_ATTR.findall(plain))
        skip = False
        skip_target = None
        # ★ 硬化 3：skip link = href 前缀命中 #main/#content/#skip **且** 目标 #id 在同页存在
        #           **且** 锚文本/类名给出 skip 信号（防 `<nav id="main-nav">` 一类「巧合余部」）
        for attrs, text in ANCHOR_FULL.findall(plain):
            if not SKIP_HREF.search(attrs):
                continue
            t = re.search(r'href\s*=\s*"#([^"]+)"', attrs, re.I)
            if not t:
                continue
            name = t.group(1)
            signal = bool(SKIP_SIGNAL.search(text)) or "skip" in attrs.lower()
            if name in ids and signal:
                skip = True
                skip_target = name
                break
            if skip_target is None:
                skip_target = name
        svgs = SVG.findall(plain)
        d[rel] = {
            "raw": plain, "css": corpus,
            "main": len(MAIN.findall(plain)),
            "skip": skip, "skip_target": skip_target,
            "focus": ":focus-visible" in corpus,
            "styles": len(styles), "linked": len(linked), "linked_missing": missing,
            "external_css_refs": n_ext, "css_sources": len(styles) + len(linked),
            "imgs": IMG.findall(plain),
            "svg_no_label": [t for (t, inner, _) in svgs
                             if not (ROLE_IMG.search(t) and (ARIA_LABEL.search(t) or "<title" in inner.lower()))],
            "svg": len(svgs),
        }
    return d


def exempt_pages(v):
    out = set()
    for e in v or []:
        if isinstance(e, str):
            out.add(e)
        elif isinstance(e, dict) and e.get("page"):
            out.add(e["page"])
    return out


def judge(ctx):
    R = []
    site_root, profile = ctx["site_root"], ctx["profile"]
    cfg = profile.get("a11y") or {}
    ex_main = exempt_pages(cfg.get("main_landmark_exempt"))
    ex_skip = exempt_pages(cfg.get("skiplink_exempt"))
    base = scan_base(site_root, profile)
    rels = product_pages(base, profile)
    P = scan(base, rels)

    def add(cid, name, ok, detail, klass):
        R.append((cid, name, bool(ok), detail, klass))

    n_main = sum(1 for v in P.values() if v["main"])
    n_carrier = sum(1 for v in P.values()
                    if any(ALT.search(i) for i in v["imgs"]) or v["svg"] or ROLE_IMG.search(v["raw"]))

    why = []
    if not rels:
        why.append("产物 HTML 扫描面 0 个文件")
    if rels and n_main == 0:
        why.append("没有任何一页含 <main>（判据无从谈起）")
    if rels and n_carrier == 0:
        why.append("没有任何一页含图件文本等价载体（img/svg/role=img 全 0）")
    add("A1", "空集守卫（页数 > 0 且 <main> 与图件载体均非空）", not why,
        "；".join(why) if why else
        "产物 %d 页 · 含 <main> %d 页 · 含图件文本等价载体 %d 页" % (len(rels), n_main, n_carrier), BLIND)

    # ★ 硬化 1+2：A7 改为「CSS 语料可解析」——外链站不再因「无内联 <style>」被误判
    blind = sorted(r for r, v in P.items() if v["css_sources"] == 0)
    total_src = sum(v["css_sources"] for v in P.values())
    why7 = []
    if blind:
        why7.append("CSS 语料不可解析的页：%s" % blind[:8])
    if rels and total_src == 0:
        why7.append("全站 CSS 源集合为空（内联 <style> 与本地外链 CSS 均 0）")
    add("A7", "解析口径自检（每页 CSS 语料可解析；全站 CSS 源集合非空）", not why7,
        "；".join(why7) if why7 else
        "%d 页全部可解析（内联 %d 源 / 本地外链 %d 源）"
        % (len(rels), sum(1 for v in P.values() if v["styles"]),
           sum(1 for v in P.values() if v["linked"])), BLIND)

    bad = sorted(r for r, v in P.items() if v["main"] != 1 and r not in ex_main)
    add("A2", "每页有且仅有 1 个 <main>（豁免项逐页登记）", not bad,
        "违反的页：%s" % bad[:8] if bad else
        "%d 页全部合格（豁免登记 %d 项：%s）" % (len(rels), len(ex_main), sorted(ex_main) or "无"), HARD)

    bad3 = sorted(r for r, v in P.items() if not v["skip"] and r not in ex_skip)
    add("A3", "每页有 skip link（href 前缀命中 #main/#content/#skip ＋ 目标 #id 存在 ＋ 锚文本/类名含 skip 信号）", not bad3,
        "缺/失效 skip link 的页：%d 页（例：%s）" % (len(bad3), bad3[:3]) if bad3 else
        "%d 页全部有 skip link（豁免登记 %d 项）" % (len(rels), len(ex_skip)), HARD)

    bad4 = sorted(r for r, v in P.items() if not v["focus"])
    add("A4", "每页 CSS 语料声明 :focus-visible（键盘焦点可见；形态感知）", not bad4,
        "缺 :focus-visible 的页：%d 页（例：%s）" % (len(bad4), bad4[:3]) if bad4 else
        "%d 页全部声明 :focus-visible" % len(rels), HARD)

    bad5, ci, cs = [], 0, 0
    for rel, v in P.items():
        for i in v["imgs"]:
            ci += 1
            if not ALT.search(i):
                bad5.append("%s 的 <img> 缺 alt：%s" % (rel, i[:60]))
        for s in v["svg_no_label"]:
            cs += 1
            bad5.append("%s 的 <svg> 缺 role=\"img\" 或 aria-label/<title>" % rel)
    add("A5", "图件文本等价（img 必有 alt；svg 必有 role=img ＋ 文本）", not bad5,
        "；".join(bad5[:4]) if bad5 else
        "核对 <img> %d 个 / 无标签 <svg> %d 个，全部合格" % (ci, cs), HARD)

    stale = []
    for r in sorted(ex_main):
        if r not in P:
            stale.append("main_landmark_exempt 声明的页不存在：%s" % r)
        elif P[r]["main"] == 1:
            stale.append("main_landmark_exempt 登记过期（该页其实合格）：%s" % r)
    for r in sorted(ex_skip):
        if r not in P:
            stale.append("skiplink_exempt 声明的页不存在：%s" % r)
        elif P[r]["skip"]:
            stale.append("skiplink_exempt 登记过期（该页其实有 skip link）：%s" % r)
    add("A6", "豁免登记不得过期（声明项须存在且真的违反）", not stale,
        "；".join(stale[:4]) if stale else
        "豁免登记 %d 项全部成立" % (len(ex_main) + len(ex_skip)), HARD)
    return R


def summarize(R):
    return {"judges": len(R), "fail_total": sum(1 for r in R if not r[2]),
            "blind_fail": sum(1 for r in R if r[4] == BLIND and not r[2]),
            "hard_fail": sum(1 for r in R if r[4] == HARD and not r[2])}


# --------------------------------------------------------------------------- selftest
FIX_CSS = (":root{--text:#e6e8ee;}\n"
           "a:focus-visible{outline:2px solid #4f8cff;}\n")


def _page(main='<main id="main"><a href="#main" class="skip">跳到主内容</a>'
               '<img src="x.png" alt="示意图"></main>',
          css=FIX_CSS, extra=""):
    return ('<!DOCTYPE html><html lang="zh-CN"><head><style>\n' + css + '</style></head>'
            '<body>' + main + extra + '</body></html>\n')


FIX_PROFILE = {
    "site": "t", "form": "inline-single-source", "publish_dir": ".", "value_file": "v.json",
    "targets": [{"path": "a.html", "mode": "root-block", "family": "default"}],
    "gates": {"manifest": "m.json", "hard_blocking": ["token-consistency"], "commands": ["x"]},
    "a11y": {"not_products": ["hand.html"], "main_landmark_exempt": [], "skiplink_exempt": []},
}


def _fixture(tmp):
    with open(os.path.join(tmp, "a.html"), "w", encoding="utf-8") as fh:
        fh.write(_page())
    with open(os.path.join(tmp, "b.html"), "w", encoding="utf-8") as fh:
        fh.write(_page())
    # ★ 外链 CSS 形态页：自身无 :focus-visible，规则在本地外链 CSS 里
    with open(os.path.join(tmp, "ext.css"), "w", encoding="utf-8") as fh:
        fh.write(":root{--x:#fff}\na:focus-visible{outline:1px solid #000}\n")
    with open(os.path.join(tmp, "c.html"), "w", encoding="utf-8") as fh:
        fh.write('<!DOCTYPE html><html lang="zh-CN"><head><link rel="stylesheet" href="ext.css">'
                 '</head><body><main id="main"><a href="#main">跳到主内容</a></main></body></html>\n')
    with open(os.path.join(tmp, "hand.html"), "w", encoding="utf-8") as fh:
        fh.write("<!DOCTYPE html><html><body>手写页</body></html>\n")
    p = os.path.join(tmp, "profile.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(FIX_PROFILE, fh, ensure_ascii=False)
    return p


def _run_fixture(mutate=None):
    tmp = tempfile.mkdtemp(prefix="a11y-")
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
        cases.append((name, ok, "" if ok else "cid=%s → %s" % (cid, det[:160])))

    case("正向夹具应 0 FAIL", None, None, expect_pass=True)
    case("★硬化1：外链 CSS 页（c.html）的 :focus-visible 判为**存在**", "A4",
         lambda t, p: None, expect_pass=True)
    case("★硬化1：A7 不因「无内联 <style>」误判（c.html 是外链页）", "A7",
         lambda t, p: None, expect_pass=True)

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

    def no_main(tmp, prof):
        for n in ("a.html", "b.html"):
            with open(os.path.join(tmp, n), "w", encoding="utf-8") as fh:
                fh.write(_page().replace("<main id=\"main\">", "<div>").replace("</main>", "</div>"))
        # ★ c.html 是外链页，也要一并去掉 <main>，否则「无 main」的负例不成立
        fp = os.path.join(tmp, "c.html")
        src = open(fp, encoding="utf-8").read()
        out = src.replace("<main id=\"main\">", "<div>").replace("</main>", "</div>")
        assert out != src, "夹具自检：c.html 未命中"
        with open(fp, "w", encoding="utf-8") as fh:
            fh.write(out)

    case("A1 负例：扫描面 0 个文件", "A1",
         setp(lambda p: p["a11y"].__setitem__("not_products",
                                              ["a.html", "b.html", "c.html", "hand.html"])))
    case("A1 负例：没有任何一页含 <main>", "A1", no_main)
    case("A2 负例：某页出现两个 <main>（地标重复）", "A2",
         edit("b.html", lambda s: s.replace("</body>", "<main>dup</main></body>")))
    case("A3 负例：某页缺 skip link", "A3",
         edit("b.html", lambda s: s.replace('<a href="#main" class="skip">跳到主内容</a>', "")))
    case("★硬化3 负例：href=\"#main-nav\" 命中前缀但目标不存在 ⇒ A3 FAIL", "A3",
         edit("a.html", lambda s: s.replace('<a href="#main" class="skip">跳到主内容</a>',
                                            '<a href="#main-nav" class="skip">跳到主内容</a>')))
    case("★硬化3 负例：目标 #id 存在但无 skip 信号（如 <nav id=\"main-nav\"> 的导航链）", "A3",
         edit("a.html", lambda s: s.replace('<a href="#main" class="skip">跳到主内容</a>',
                                            '<a href="#main-nav">导航</a>')
                .replace("<main id=\"main\">", "<nav id=\"main-nav\">x</nav><main id=\"main\">")))
    case("★硬化2 负例：注释里的 skip link 不算数", "A3",
         edit("b.html", lambda s: s.replace('<a href="#main" class="skip">跳到主内容</a>',
                                            '<!-- <a href="#main">旧</a> -->')))
    case("A4 负例：某页 CSS 语料缺 :focus-visible", "A4",
         edit("b.html", lambda s: s.replace("a:focus-visible{outline:2px solid #4f8cff;}\n", "")))
    case("★硬化2 负例：CSS 注释里的 :focus-visible 不算数", "A4",
         edit("b.html", lambda s: s.replace("a:focus-visible{outline:2px solid #4f8cff;}\n",
                                            "/* a:focus-visible{} */\n")))
    case("A5 负例：<img> 缺 alt", "A5",
         edit("a.html", lambda s: s.replace(' alt="示意图"', "")))
    case("A5 负例：<svg> 缺 role=img/aria-label", "A5",
         edit("a.html", lambda s: s.replace("</main>",
                                            '<svg viewBox="0 0 10 10"><path d="M0 0"/></svg></main>')))
    # ★★ 判据实现更正的**回归夹具**：标签写在**开标签**上是合法的，必须判为 PASS
    case("★A5 更正：aria-label 写在 <svg> **开标签**上 ⇒ 必须 PASS（批 H 的实现在此处假 FAIL）",
         "A5", edit("b.html", lambda s: s.replace(
             "</main>", '<svg role="img" aria-label="示意图" viewBox="0 0 10 10">'
                        '<path d="M0 0"/></svg></main>')), expect_pass=True)
    case("★A5 更正：<title> 写在 <svg> **内容**里 ⇒ 必须 PASS", "A5",
         edit("b.html", lambda s: s.replace(
             "</main>", '<svg role="img" viewBox="0 0 10 10"><title>示意图</title>'
                        '<path d="M0 0"/></svg></main>')), expect_pass=True)
    case("★A5 更正反向：有 role=img 但**无**任何标签 ⇒ 照旧 FAIL", "A5",
         edit("b.html", lambda s: s.replace(
             "</main>", '<svg role="img" viewBox="0 0 10 10"><path d="M0 0"/></svg></main>')))
    case("A6 负例：豁免登记过期（该页其实合格）", "A6",
         setp(lambda p: p["a11y"]["main_landmark_exempt"].append("a.html")))
    case("A6 负例：豁免声明的页不存在", "A6",
         setp(lambda p: p["a11y"]["skiplink_exempt"].append("ghost.html")))
    case("A7 负例：某页 CSS 源全无（内联与外链都无）", "A7",
         edit("b.html", lambda s: re.sub(r"<style>.*?</style>", "", s, flags=re.S)))
    case("A7 负例：本地外链 CSS 文件不存在", "A7",
         edit("c.html", lambda s: s.replace('href="ext.css"', 'href="ghost.css"')))
    case("★硬化1b 负例：publish_dir 指向子目录 ⇒ 扫描面随之（0 页 ⇒ A1 FAIL）", "A1",
         setp(lambda p: p.__setitem__("publish_dir", "docs")))

    ok = all(v for _, v, _ in cases)
    for name, res, note in cases:
        print("  [%s] %s%s" % ("PASS" if res else "FAIL", name, ("  ← " + note) if note else ""))
    print("\n=== gate_a11y.py 自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v, _ in cases if not v)))
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
    print("\n=== 无障碍门控（mode=%s）：%d 项判据，%d FAIL（blind %d / hard %d）==="
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
