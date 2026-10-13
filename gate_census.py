#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_census.py — 站点侧**令牌普查 / 增量冻结门控**（方案 §4.2 第 1 步「令牌普查门控」，Q2=A）。

★ 为什么判据长这样（`SH5 §4.0` 第 1 条「判据对象必须与断言对象一致」）：
  Q2=A 裁定「**先增量冻结**再按页面族分批」⇒ 判据**不判对错**（本站当前没有「对」的基准），
  只判**相对改动前基线的变化方向**：词汇表不得增加、页集合不得漂移、注入的令牌必须真被引用。
  ★ 判据的同期配置副本 = `data/token-baseline.json`（改动前一次采集，逐页冻结）。
  第 5 条「凡有登记表的判据，改盘面就要同批改登记表」⇒ TC2 是**双向**的：
  新增页 ⇒ FAIL（须同批登记）；基线里多出的页 ⇒ FAIL（登记过期）。

判据（6 条）：
  TC1 [blind] 空集守卫：页数 / 基线页 / 值注册表 / page_families 任一为 0 ⇒ FAIL
  TC2 [hard]  页集合双向一致（盘上 == 基线）
  TC3 [hard]  词汇表数不增（残余词汇表 = `:root` 名 − 值注册表名；≤ 基线值）
  TC4 [hard]  零令牌页清零且每页都有 `:root`（`no_root_pages` 逐页登记；登记过期 ⇒ FAIL）
  TC5 [hard]  注入的令牌**真被引用**（每页 ≥1 处 `var(--lp-…)`，且本页声明的每个 `--lp-…`
              至少被本页引用一次）—— 防「注入了但没人用 = 死令牌换绿灯」
  TC6 [report] 分布（仅报告）：`@media` 合计 / 每页 hex 计数变化

用法：
    python3 gate_census.py --site-root .
    python3 gate_census.py --site-root . --json
    python3 gate_census.py --selftest
退出码：0 全过 · 1 有 FAIL · 2 输入错误 · 3 护栏拒读
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

STYLE_RE = re.compile(r"(<style[^>]*>)(.*?)(</style>)", re.S | re.I)
ROOT_RE = re.compile(r":root\s*\{([^{}]*)\}")
TOKEN_DEF = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+)")
VAR_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
REGISTRY_NAME_RE = re.compile(r"^--lp-(?:bg|ink|line|mix)-\d{3}$")

BLIND, HARD, REPORT = "blind", "hard", "report"


class GateError(Exception):
    pass


def load_json(path, label):
    if not os.path.isfile(path):
        raise GateError("%s 不存在：%s" % (label, path))
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        raise GateError("%s 非法 JSON：%s" % (label, exc))


def facts(raw):
    style = "\n".join(m.group(2) for m in STYLE_RE.finditer(raw))
    m = ROOT_RE.search(style)
    root = dict(TOKEN_DEF.findall(m.group(1))) if m else {}
    return {"root": root, "style": style,
            "refs": set(VAR_RE.findall(style)),
            "media": len(re.findall(r"@media\b", style)),
            "hex": len(re.findall(r"#[0-9a-fA-F]{3,8}\b", style))}


def check(root, profile, baseline, contract=None):
    R = []

    def add(cid, name, cls, ok, detail):
        R.append({"id": cid, "name": name, "class": cls, "ok": bool(ok), "detail": detail})

    site_names = set(((contract or {}).get("binding") or {}).get("site_token_names", {}).values())

    pages = {}
    for p in sorted(glob.glob(os.path.join(root, "docs", "**", "*.html"), recursive=True)):
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        pages[rel] = facts(open(p, encoding="utf-8", errors="replace").read())
    bpages = baseline.get("pages") or {}
    pal = baseline.get("palette") or {}
    bcounts = baseline.get("counts") or {}
    fams = profile.get("page_families") or []

    add("TC1", "空集守卫（页数/基线页/值注册表/page_families 均非空）", BLIND,
        bool(pages) and bool(bpages) and bool(pal) and bool(fams),
        "页 %d / 基线页 %d / 值注册表 %d / 族 %d" % (len(pages), len(bpages), len(pal), len(fams)))

    new = sorted(set(pages) - set(bpages))
    gone = sorted(set(bpages) - set(pages))
    add("TC2", "页集合双向一致（盘上 == 改动前基线）", HARD, not new and not gone,
        ("新增未登记页：%s；" % new[:6] if new else "") + ("登记过期页：%s" % gone[:6] if gone else "")
        if (new or gone) else "%d 页与基线逐路径一致" % len(pages))

    resid = {}
    for r, f in pages.items():
        resid[r] = tuple(sorted(n for n in f["root"]
                                if not REGISTRY_NAME_RE.match(n) and n not in site_names))
    n_vocab = len(set(resid.values()))
    base_vocab = bcounts.get("vocab_count") or 0
    add("TC3", "词汇表数不增（残余词汇表指纹 = `:root` 名 − 值注册表名 − 站点级角色名；≤ 基线 %s 套）"
        % base_vocab, HARD,
        n_vocab <= base_vocab,
        "实测 %d 套（%s）" % (n_vocab, "未增加" if n_vocab <= base_vocab
                             else "★ 增加了 %d 套（Q2=A 增量冻结被破坏）" % (n_vocab - base_vocab)))

    zero = sorted(r for r, f in pages.items() if not f["root"])
    declared_noroot = set(profile.get("no_root_pages") or [])
    bad4 = [r for r in zero if r not in declared_noroot]
    stale4 = sorted(r for r in declared_noroot if r not in zero)
    add("TC4", "零令牌页清零 ＋ 每页有 `:root`（无根页逐页登记，双向）", HARD,
        not bad4 and not stale4,
        ("未登记的零令牌页：%s；" % bad4[:6] if bad4 else "")
        + ("登记过期（已非零令牌）：%s" % stale4 if stale4 else "")
        if (bad4 or stale4)
        else "零令牌页 0（基线 %s）· 登记无根页 %d 个且全部真的无根"
        % (bcounts.get("zero_token_count"), len(declared_noroot)))

    dead, noref, page_dead, site_dead = {}, [], {}, {}
    for r, f in pages.items():
        d = {n: sorted(x for x in f["root"] if x not in f["refs"]) for n in (0,)}
        u = d[0]
        if u:
            dead[r] = u
            page_dead[r] = sorted(n for n in u if not REGISTRY_NAME_RE.match(n) and n not in site_names)
            sd = sorted(n for n in u if REGISTRY_NAME_RE.match(n) or n in site_names)
            if sd:
                site_dead[r] = sd
        if not f["refs"]:
            noref.append(r)
    # ★ 判据分层（照批 H 的 G7：站点级 hard / 页级 report）：
    #   ① hard：**本批注入的**令牌（值注册表名 + 站点级角色名）必须真被本页引用；
    #   ② hard：页级零引用登记表**双向**（登记过期 ⇒ FAIL）—— 既有死令牌如实登记而非硬判，
    #      因为 Q2=A/⛔ 不改值 的前置下它们本轮**不许修**，硬判＝永久假 FAIL（SH5 §4.0 第 7 条）。
    reg_pz = {k: sorted(v) for k, v in (profile.get("page_level_zero_ref") or {}).items()}
    actual_pz = {k: v for k, v in page_dead.items() if v}
    bad_reg = {k: actual_pz.get(k, []) for k in reg_pz if reg_pz[k] != actual_pz.get(k, [])}
    new_pz = sorted(k for k in actual_pz if k not in reg_pz)
    add("TC5", "注入令牌真被引用（hard）＋ 页级零引用登记双向（既有死令牌如实登记）", HARD,
        not site_dead and not noref and not bad_reg and not new_pz,
        ("本批注入却零引用的页：%s；" % list(site_dead.items())[:4] if site_dead else "")
        + ("整页零 var() 引用：%s；" % noref[:5] if noref else "")
        + ("登记不一致：%s；" % list(bad_reg.items())[:3] if bad_reg else "")
        + ("未登记的死令牌页：%s" % new_pz[:5] if new_pz else "")
        if (site_dead or noref or bad_reg or new_pz)
        else "本批注入的令牌 %d 页全部被引用；页级既有死令牌 %d 枚 / %d 页与登记表双向一致"
        % (len(pages), sum(len(v) for v in actual_pz.values()), len(actual_pz)))

    add("TC6", "分布（仅报告）", REPORT, True,
        "@media 合计 %d（基线 %d）· hex 计数合计 %d"
        % (sum(f["media"] for f in pages.values()), bcounts.get("media_total") or 0,
           sum(f["hex"] for f in pages.values())))
    return R


def selftest():
    cases = []

    def case(name, ok):
        cases.append((name, bool(ok)))

    def run(files, baseline, profile=None):
        tmp = tempfile.mkdtemp(prefix="lp-gc-")
        try:
            for rel, body in files.items():
                p = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "w", encoding="utf-8").write(body)
            prof = profile or {"page_families": [{"glob": "docs/*.html", "family": "t"}],
                               "no_root_pages": [], "page_level_zero_ref": {}}
            return check(tmp, prof, baseline, {"binding": {"site_token_names": {}}})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def get(R, cid):
        for r in R:
            if r["id"] == cid:
                return r
        return {"ok": False, "detail": "缺判据"}

    BASE = {"palette": {"#111111": "--lp-bg-001"}, "pages": {"docs/a.html": {"hex_used": {"#111111": 1}}},
            "counts": {"vocab_count": 1, "zero_token_count": 1, "media_total": 0}}
    GOOD = {"docs/a.html": '<style>:root{--lp-bg-001:#111111}body{background:var(--lp-bg-001)}</style>'}
    R = run(GOOD, BASE)
    case("正向夹具 0 FAIL", all(r["ok"] for r in R))
    # TC2：新增页未登记
    R = run(dict(GOOD, **{"docs/b.html": GOOD["docs/a.html"]}), BASE)
    case("TC2 负例：新增页未登记 ⇒ FAIL", not get(R, "TC2")["ok"])
    # TC2：登记过期
    R = run({}, BASE)
    case("TC1/TC2 负例：盘上 0 页 ⇒ FAIL（空集守卫）", not get(R, "TC1")["ok"])
    # TC3：新增一套词汇表（残余指纹多一套）
    R = run(dict(GOOD, **{"docs/b.html":
                           '<style>:root{--lp-bg-001:#111111;--own:#222222}'
                           'body{background:var(--lp-bg-001);color:var(--own)}</style>'}),
            {"palette": BASE["palette"],
             "pages": {"docs/a.html": {}, "docs/b.html": {}},
             "counts": {"vocab_count": 1, "zero_token_count": 0, "media_total": 0}})
    case("TC3 负例：残余词汇表由 1 套变 2 套 ⇒ FAIL（增量冻结）", not get(R, "TC3")["ok"])
    # TC4：零令牌页未登记
    R = run(dict(GOOD, **{"docs/b.html": "<style>body{color:red}</style>"}),
            {"palette": BASE["palette"], "pages": {"docs/a.html": {}, "docs/b.html": {}},
             "counts": {"vocab_count": 1, "zero_token_count": 0, "media_total": 0}})
    case("TC4 负例：出现未登记的零令牌页 ⇒ FAIL", not get(R, "TC4")["ok"])
    # TC5：注入了但没人用（死令牌换绿灯）
    R = run({"docs/a.html": '<style>:root{--lp-bg-001:#111111}body{background:#111111}</style>'}, BASE)
    case("TC5 负例：注入了令牌却零引用 ⇒ FAIL", not get(R, "TC5")["ok"])
    # TC5：既有死令牌必须双向登记（未登记 ⇒ FAIL）
    R = run({"docs/a.html": '<style>:root{--lp-bg-001:#111111;--legacy:#222222}'
                            'body{background:var(--lp-bg-001)}</style>'},
            {"palette": BASE["palette"], "pages": {"docs/a.html": {}},
             "counts": {"vocab_count": 1, "zero_token_count": 0, "media_total": 0}})
    case("TC5 负例：既有死令牌未登记 ⇒ FAIL", not get(R, "TC5")["ok"])
    # TC5：登记过期（登记了但其实已被引用）
    R = run(GOOD, {"palette": BASE["palette"], "pages": {"docs/a.html": {}},
                   "counts": {"vocab_count": 1, "zero_token_count": 1, "media_total": 0}},
            profile={"page_families": [{"glob": "docs/*.html", "family": "t"}], "no_root_pages": [],
                     "page_level_zero_ref": {"docs/a.html": ["--ghost"]}})
    case("TC5 负例：页级零引用登记过期 ⇒ FAIL（双向）", not get(R, "TC5")["ok"])
    # 负例：空集守卫——基线为空
    R = run(GOOD, {"palette": {}, "pages": {}, "counts": {}})
    case("TC1 负例：基线为空 ⇒ FAIL（空集守卫）", not get(R, "TC1")["ok"])

    ok = all(v for _, v in cases)
    for n, v in cases:
        print("  [%s] %s" % ("PASS" if v else "FAIL", n))
    print("\n=== gate_census 自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-root", default=".")
    ap.add_argument("--profile", default="build/profile.json")
    ap.add_argument("--baseline", default="data/token-baseline.json")
    ap.add_argument("--value-file", default="vendor/pipeline/values/llm-papers-knowledge-base.json")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    root = os.path.abspath(a.site_root)
    try:
        profile = load_json(os.path.join(root, a.profile), "profile")
        baseline = load_json(os.path.join(root, a.baseline), "改动前令牌基线")
        contract = load_json(os.path.join(root, a.value_file), "站点值件")
    except GateError as exc:
        print("GUARD-REJECT: %s" % exc)
        return 3
    R = check(root, profile, baseline, contract)
    for r in R:
        print("[%s] %-4s %-5s %s — %s" % ("PASS" if r["ok"] else "FAIL", r["id"], r["class"],
                                          r["name"], r["detail"]))
    if a.json:
        print(json.dumps(R, ensure_ascii=False, indent=1))
    nf = sum(1 for r in R if not r["ok"])
    print("\n=== 令牌普查/增量冻结门控：%d 项判据，%d FAIL ===" % (len(R), nf))
    return 0 if nf == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
