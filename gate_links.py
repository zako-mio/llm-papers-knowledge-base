#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_links.py — 站点侧**链路门控**（方案 §4.2 第 1 步「链路门控」，Q5=A 的落点门控）。

★ 判据对象（`SH5 §4.0` 第 4 条：判据对象 == 断言对象）：`docs/**/*.html` 的 `<a href>`／
  `<link href>`／`<area href>` 三类锚的 `href` 属性值。⛔ 不判正文里出现的裸 URL 字样
  （那会命中「文档自述」一类的**假阳**，见 §4.0 第 2 条），⛔ 不判 `<script>` 里的字符串。

判据（7 条）：
  LK1 [blind] 空集守卫：页数 / href 总数 / 外站登记表 任一为 0 ⇒ FAIL
  LK2 [hard]  站内锚可达：相对路径锚必须能在仓内解析到**存在的文件**（Q5=A 即此判据的实例）
  LK3 [hard]  页内锚命中：`#id`／`path#id` 的 `id` 必须真的在目标文件里出现
  LK4 [hard]  站外锚登记：每个外部 host 必须显式登记（**fail-closed**：未登记即 FAIL），
              ★ 登记表**双向**：登记了却没人用的 host ⇒ FAIL（登记过期）
  LK5 [hard]  已知断链登记双向：profile.known_broken_links 的每一项必须**真的**还断着；
              盘上断链必须**全部**在册（新增断链 ⇒ FAIL）
  LK6 [report] 站外锚分布（仅报告）
  LK7 [blind] 解析口径自检：`href` 抽取数必须等于 `<a|area|link` 标签里带 href 的属性数
              （防解析口径漏读——批 H 的「注释里出现令牌块字样」同族陷阱）

用法：
    python3 gate_links.py --site-root .
    python3 gate_links.py --site-root . --json
    python3 gate_links.py --selftest
退出码：0 全过 · 1 有阻断级 FAIL · 2 输入错误 · 3 护栏拒读
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys
import tempfile
from urllib.parse import unquote

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))

HREF_RE = re.compile(r"<(?:a|area|link)\b[^>]*?\bhref\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", re.I)
ANY_HREF_RE = re.compile(r"\bhref\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", re.I)
STYLE_SCRIPT_RE = re.compile(r"<(style|script)\b[^>]*>.*?</\1>", re.S | re.I)
# ★ HTML 注释也要剥：`<!-- <a href="ghost.html"> -->` 里的字样**不是**锚。
#   这是 `SH5 §4.0` 第 2 条「假阳样本」的直接落点（批 H 的「注释里出现令牌块字样」同族）。
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
ID_RE = re.compile(r"\bid\s*=\s*[\"']([^\"']+)[\"']")
SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*):")

BLIND, HARD, REPORT = "blind", "hard", "report"


class GateError(Exception):
    """护栏拒读（exit 3）。"""


def load_json(path, label):
    if not os.path.isfile(path):
        raise GateError("%s 不存在：%s" % (label, path))
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        raise GateError("%s 非法 JSON：%s" % (label, exc))


def scrub(raw):
    """剥掉 `<style>`/`<script>` 段与 HTML 注释（判据面只留真正的标记）。"""
    return COMMENT_RE.sub("", STYLE_SCRIPT_RE.sub("", raw))


def extract_links(raw):
    """抽取锚 href。★ 先剥 `<style>`/`<script>`/注释（⛔ 不把脚本与注释里的字符串当锚）。"""
    body = scrub(raw)
    return [m.group(1) if m.group(1) is not None else m.group(2) for m in HREF_RE.finditer(body)]


def check(root, profile):
    R = []

    def add(cid, name, cls, ok, detail):
        R.append({"id": cid, "name": name, "class": cls, "ok": bool(ok), "detail": detail})

    pages = {}
    for p in sorted(glob.glob(os.path.join(root, "docs", "**", "*.html"), recursive=True)):
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        raw = open(p, encoding="utf-8", errors="replace").read()
        ids = set(ID_RE.findall(scrub(raw)))
        pages[rel] = {"hrefs": extract_links(raw), "ids": ids,
                      "raw_hrefs": len(ANY_HREF_RE.findall(scrub(raw)))}

    total_hrefs = sum(len(f["hrefs"]) for f in pages.values())
    ext_reg = {d["host"]: d for d in (profile.get("link_registry") or {}).get("external_hosts", [])}
    known = {d["link"]: d for d in (profile.get("known_broken_links") or [])}

    add("LK1", "空集守卫（页数 / href 总数 / 外站登记表均非空）", BLIND,
        bool(pages) and total_hrefs > 0 and bool(ext_reg),
        "页 %d / href %d / 外站登记 %d" % (len(pages), total_hrefs, len(ext_reg)))

    internal_missing, anchor_missing, external_used = [], [], {}
    for rel, f in pages.items():
        base = os.path.dirname(os.path.join(root, rel))
        for h in f["hrefs"]:
            h = h.strip()
            if not h or h.startswith("//"):
                continue
            m = SCHEME_RE.match(h)
            if m:
                if m.group(1).lower() in ("http", "https"):
                    host = re.sub(r"^https?://([^/]+).*$", r"\1", h).lower()
                    external_used.setdefault(host, []).append(rel)
                continue
            path, _, frag = h.partition("#")
            if not path:                      # 同页锚
                if frag and frag not in f["ids"]:
                    anchor_missing.append("%s → #%s" % (rel, frag))
                continue
            # ★ URL 解码：站内锚里存在**百分号编码**的路径（如 list.html 的
            #   `03-%E6%B7%B1%E5%BA%A6%E8%A7%A3%E8%AF%BB%E6%8A%A5%E5%91%8A.html`），
            #   不解码会判成断链 = **假 FAIL**（实测踩到）。
            tgt = os.path.normpath(os.path.join(base, unquote(path)))
            if not os.path.exists(tgt):
                internal_missing.append("%s → %s" % (rel, h))
                continue
            if frag and tgt.endswith(".html"):
                t = open(tgt, encoding="utf-8", errors="replace").read()
                if frag not in set(ID_RE.findall(scrub(t))):
                    anchor_missing.append("%s → %s" % (rel, h))

    new_broken = [x for x in internal_missing if x.split(" → ")[1] not in known]
    stale = [k for k in known if k not in {x.split(" → ")[1] for x in internal_missing}]
    add("LK2", "站内锚可达（相对路径锚必须解析到存在的文件）", HARD,
        not new_broken and not stale,
        ("新增断链：%s；" % new_broken[:6] if new_broken else "")
        + ("登记过期（已不存在的登记项）：%s" % stale if stale else "")
        if (new_broken or stale)
        else "%d 页 %d 条站内锚全部可达（已知断链在册 %d 条）"
        % (len(pages), total_hrefs - sum(len(v) for v in external_used.values()), len(known)))

    add("LK3", "页内锚命中（#id 必须真的存在）", HARD, not anchor_missing,
        "未命中：%s" % anchor_missing[:6] if anchor_missing else "全部页内锚均命中目标 id")

    unreg = sorted(h for h in external_used if h not in ext_reg)
    unused = sorted(h for h in ext_reg if h not in external_used)
    add("LK4", "站外锚登记（fail-closed：未登记 host ⇒ FAIL；★ 双向）", HARD,
        not unreg and not unused,
        ("未登记 host：%s；" % unreg if unreg else "")
        + ("登记过期 host：%s" % unused if unused else "")
        if (unreg or unused)
        else "%d 个外站 host 全部登记且均在用" % len(external_used))

    add("LK5", "已知断链登记双向（在册的必须真断 · 断的必须全在册）", HARD,
        not new_broken and not stale,
        "见 LK2 明细" if (new_broken or stale) else "在册 %d 条，双向一致" % len(known))

    add("LK6", "站外锚分布（仅报告）", REPORT, True,
        "；".join("%s×%d" % (h, len(v)) for h, v in sorted(external_used.items())) or "无外站锚")

    parse_bad = [r for r, f in pages.items() if len(f["hrefs"]) != f["raw_hrefs"]]
    add("LK7", "解析口径自检（锚内 href 抽取数 == 属性面 href 数）", BLIND, not parse_bad,
        "口径不一致页：%s" % parse_bad[:5] if parse_bad
        else "%d 页解析口径一致（%d 条）" % (len(pages), total_hrefs))
    return R


# --------------------------------------------------------------------------- 自检
def selftest():
    cases = []

    def case(name, ok):
        cases.append((name, bool(ok)))

    def run(files, profile):
        tmp = tempfile.mkdtemp(prefix="lp-gl-")
        try:
            for rel, body in files.items():
                p = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "w", encoding="utf-8").write(body)
            return check(tmp, profile)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def get(R, cid):
        for r in R:
            if r["id"] == cid:
                return r
        return {"ok": False, "detail": "缺判据"}

    PROF = {"link_registry": {"external_hosts": [{"host": "arxiv.org", "why": "论文源"}]},
            "known_broken_links": []}
    GOOD = {"docs/index.html": '<a href="a.html">x</a><a href="https://arxiv.org/abs/1">e</a>',
            "docs/a.html": '<h1 id="top">A</h1><a href="#top">t</a>'}
    R = run(GOOD, PROF)
    case("正向夹具 0 FAIL", all(r["ok"] for r in R))
    # 负例：Q5 的原始缺陷（../README.md 解析到 docs 之外且不存在）
    R = run({"docs/index.html": '<a href="../README.md">r</a>',
             "docs/a.html": '<h1 id="top">A</h1>'}, PROF)
    case("LK2 负例：../README.md 断链 ⇒ FAIL（Q5 的负向夹具）", not get(R, "LK2")["ok"])
    # 负例：假阳样本——URL 只出现在**正文文字**里，不得被当成锚
    R = run({"docs/index.html": '<p>见 https://nope.example/x 说明</p><a href="a.html">a</a>',
             "docs/a.html": "<p>y</p>"}, PROF)
    case("LK2 假阳样本：正文里的裸 URL 不算锚", get(R, "LK2")["ok"])
    # 负例：注释里出现 href 字样
    R = run({"docs/index.html": '<!-- <a href="ghost.html">x</a> --><p>y</p>',
             "docs/a.html": "<p>y</p>"}, PROF)
    case("LK2 假阳样本：注释里的锚不算锚（⛔ 不误判）", get(R, "LK2")["ok"])
    # 负例：未登记外站 host
    R = run({"docs/index.html": '<a href="https://evil.example/x">x</a>', "docs/a.html": "<p>y</p>"}, PROF)
    case("LK4 负例：未登记外站 host ⇒ FAIL", not get(R, "LK4")["ok"])
    # 负例：登记过期（登记了但没人用）
    R = run({"docs/index.html": '<a href="a.html">x</a>', "docs/a.html": "<p>y</p>"}, PROF)
    case("LK4 负例：登记过期 host ⇒ FAIL（双向）", not get(R, "LK4")["ok"])
    # 负例：页内锚未命中
    R = run({"docs/index.html": '<a href="a.html#nope">x</a>', "docs/a.html": '<h1 id="top">A</h1>'},
            {"link_registry": {"external_hosts": [{"host": "arxiv.org", "why": "w"}]}})
    case("LK3 负例：页内锚未命中 ⇒ FAIL", not get(R, "LK3")["ok"])
    # 负例：空集守卫（0 页）
    R = run({}, PROF)
    case("LK1 负例：0 页被扫 ⇒ FAIL（空集守卫）", not get(R, "LK1")["ok"])
    # 负例：已知断链登记过期
    R = run({"docs/index.html": '<a href="a.html">x</a>', "docs/a.html": "<p>y</p>"},
            {"link_registry": {"external_hosts": [{"host": "arxiv.org", "why": "w"}]},
             "known_broken_links": [{"link": "old.html", "why": "w"}]})
    case("LK5 负例：登记过期（已不存在的断链仍留册）⇒ FAIL", not get(R, "LK5")["ok"])

    ok = all(v for _, v in cases)
    for n, v in cases:
        print("  [%s] %s" % ("PASS" if v else "FAIL", n))
    print("\n=== gate_links 自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-root", default=".")
    ap.add_argument("--profile", default="build/profile.json")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    root = os.path.abspath(a.site_root)
    try:
        profile = load_json(os.path.join(root, a.profile), "profile")
    except GateError as exc:
        print("GUARD-REJECT: %s" % exc)
        return 3
    R = check(root, profile)
    for r in R:
        print("[%s] %-4s %-5s %s — %s" % ("PASS" if r["ok"] else "FAIL", r["id"], r["class"],
                                          r["name"], r["detail"]))
    if a.json:
        print(json.dumps(R, ensure_ascii=False, indent=1))
    nf = sum(1 for r in R if not r["ok"])
    print("\n=== 链路门控：%d 项判据，%d FAIL ===" % (len(R), nf))
    return 0 if nf == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
