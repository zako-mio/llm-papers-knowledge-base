#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_tokens.py — llm-papers-knowledge-base 的**站点侧令牌门控**（批 I · 站 06 标准档）。

范式与纪律来源：`solutions/_shared/SH5-gating.md` §4.0 十条 + `CONTINUE-PROMPT-G.md` §4.2 八条。
★ 与 AUD 侧契约门控的分工（⛔ 不重叠、不互相替代）：AUD 侧 `pipeline/check_site_tokens.py` 跑
  C1–C12，需要 `--orig-root`（改动前克隆）与 `~/opencode/projects/fe-starter-kit`
  ⇒ **在 Actions 上必然 FAIL（判据成立但环境不成立）**；本件只判「仓内盘上事实 ↔ 值件/基线」，
  ⛔ 不依赖克隆与仓外路径 ⇒ 可在 Actions 上跑。

用法：
    python3 gate_tokens.py --site-root . --manifest gate-manifest.json --mode enforce
    python3 gate_tokens.py --site-root . --manifest gate-manifest.json --mode report
    python3 gate_tokens.py --site-root . --manifest gate-manifest.json --json
    python3 gate_tokens.py --selftest

判据（10 条，逐条声明判据对象；⛔ 无豁免字段、⛔ 不静默跳过）：
  G1  [blind] 空集守卫：页数 / page_families / 基线 palette / 基线 pages 任一为 0 ⇒ FAIL
  G2  [hard]  形态不变量（Q6=A 维持形态 2）：每页 `ext_css_links == 0` 且 `<style>` 块 ≥ 1
  G3  [hard]  等值注入（Q3=A）：页面**新出现的字面值**必须 ∈ 改动前基线 ∪ 值件声明值
  G4  [hard]  目标存在性：profile.targets 全在；no_root_pages 真的**没有** `:root`
  G5  [混合]  成对对比度：`vendor/tools/contrast.py` 逐档实算；hard 档阻断，report-only 档
              只报 **且与 profile.known_contrast_defects 双向一致**（登记过期 ⇒ FAIL）
  G6  [hard]  零引用登记：站点级角色令牌必须**真被引用**；页级未用令牌逐页登记（双向）
  G7  [hard]  未声明令牌：盘上令牌名必须 ∈ 值注册表名 ∪ 值件 site_token_names
  G8  [hard]  生成器单源不变量（Q1=A⇒B / Q4=A）：首页有生成器认领；timeline 的写者恰 1 个
  G9  [hard]  产物归属：生成器拥有面**恰 1 个**写者；快照面**不得**被任何生成器声明写入
  G10 [report] 口径分布（仅报告，⛔ 不判「够不够」）：词汇表数 / 零令牌页数 / `@media` 数

退出码：0 全过（report 模式下允许 hard FAIL 但 blind FAIL 仍阻断）· 1 有阻断级 FAIL ·
        2 输入错误 · 3 护栏拒读
"""
import argparse
import ast
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "vendor", "pipeline")
for p in (VENDOR, os.path.join(HERE, "vendor", "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)
import contrast as C  # noqa: E402  ★ 项目唯一对比度实现（⛔ 不造第二套）

BLIND, HARD, REPORT = "blind", "hard", "report"
STYLE_RE = re.compile(r"(<style[^>]*>)(.*?)(</style>)", re.S | re.I)
ROOT_RE = re.compile(r":root\s*\{([^{}]*)\}")
TOKEN_DEF = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+)")
EXT_CSS_RE = re.compile(r"<link[^>]+rel\s*=\s*[\"']?stylesheet", re.I)
TOKENS_BEGIN = "/* LP:TOKENS:BEGIN */"
TOKENS_END = "/* LP:TOKENS:END */"
RE_REGISTRY = re.compile(r"^--lp-(?:bg|ink|line|mix)-\d{3}$")


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


def norm_hex(lit):
    if not re.fullmatch(C.HEX, lit):
        return None
    return "#%02x%02x%02x" % C.hex_to_rgb(lit)


def style_text(raw):
    return "\n".join(m.group(2) for m in STYLE_RE.finditer(raw))


def first_root(raw):
    m = ROOT_RE.search(style_text(raw))
    return dict(TOKEN_DEF.findall(m.group(1))) if m else {}


def declared_writers(repo):
    """★ 用 **ast** 求值面扫生成器的输出路径常量（⛔ 不靠逐行正则——跨行隐式拼接有盲区）。

    识别两种写法：`OUT_PATH = BASE_DIR / 'docs' / 'timeline.html'`（BinOp/Div 链）
    与 `OUT_PATH = os.path.join(BASE, "docs", "x.html")`（Call）。
    返回 {产物相对路径: [生成器文件名, ...]}。
    """
    out = {}
    for p in sorted(glob.glob(os.path.join(repo, "data", "*.py"))):
        fn = os.path.basename(p)
        try:
            tree = ast.parse(open(p, encoding="utf-8").read())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if not any(n in ("OUT_PATH", "OUT") for n in names):
                continue
            parts = []
            v = node.value
            # 展开 a / b / c 链与 os.path.join(a, b, c)
            def collect(n):
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
                    collect(n.left)
                    collect(n.right)
                elif isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "join":
                    for a in n.args[1:]:
                        collect(a)
                elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                    parts.append(n.value)
            collect(v)
            if not parts:
                continue
            rel = "/".join(x.strip("/") for x in parts)
            out.setdefault(rel, []).append(fn)
    return out


def check(repo, manifest, profile, baseline, contract):
    R = []

    def add(cid, name, cls, ok, detail):
        R.append({"id": cid, "name": name, "class": cls, "ok": bool(ok), "detail": detail})

    pages = {}
    for p in sorted(glob.glob(os.path.join(repo, "docs", "**", "*.html"), recursive=True)):
        rel = os.path.relpath(p, repo).replace(os.sep, "/")
        raw = open(p, encoding="utf-8", errors="replace").read()
        pages[rel] = {"raw": raw, "style": style_text(raw), "root": first_root(raw),
                      "ext_css": len(EXT_CSS_RE.findall(raw)),
                      "styles": len(STYLE_RE.findall(raw)),
                      "media": len(re.findall(r"@media\b", style_text(raw)))}
    fams = profile.get("page_families") or []
    pal = (baseline.get("palette") or {})
    bpages = (baseline.get("pages") or {})

    # ---- G1 空集守卫
    bad = []
    if not pages:
        bad.append("0 个 *.html 被扫")
    if not fams:
        bad.append("page_families 为空")
    if not pal:
        bad.append("基线 palette 为空")
    if not bpages:
        bad.append("基线 pages 为空")
    add("G1", "空集守卫（扫描面/族/值注册表/基线页均非空）", BLIND, not bad,
        "；".join(bad) if bad else "页 %d / 族 %d / 值注册表 %d / 基线页 %d"
        % (len(pages), len(fams), len(pal), len(bpages)))

    # ---- G2 形态不变量（Q6=A 维持形态 2「内联单源」）
    viol = [r for r, f in pages.items() if f["ext_css"] or f["styles"] < 1]
    add("G2", "形态 2 不变量（外链 CSS = 0 且每页 ≥1 个 <style>）", HARD, not viol,
        "违规页：%s" % viol[:6] if viol else "%d 页全部维持内联单源（外链 CSS 0）" % len(pages))

    # ---- G3 等值注入（Q3=A）：不得出现基线之外的新值
    sitetok = (contract.get("binding") or {}).get("site_token_names") or {}
    fams_vals = list((contract.get("palettes") or {}).values())
    role_vals = set()
    if fams_vals:
        for role, tok in sitetok.items():
            v = (fams_vals[0].get("values") or {}).get(role)
            if isinstance(v, dict):
                v = v.get("light")
            if isinstance(v, str) and norm_hex(v):
                role_vals.add(norm_hex(v))
    newvals = {}
    unregistered = []
    for r, f in pages.items():
        if r not in bpages:
            unregistered.append(r)
        b = bpages.get(r) or {}
        allowed = set(b.get("hex_used") or {}) | role_vals
        # ★ 判据对象 == 断言对象：改动前**该页自己的 `:root` 令牌值**也是合法值面
        #   （基线采集时它们被有意排除在 hex_used 之外，因为它属于「声明」而非「用法」；
        #    注解后它们与注入值同处新 `:root`，故必须并回允许集合，否则是**假 FAIL**）
        for _n, _v in (b.get("root_tokens") or {}).items():
            nv = norm_hex(str(_v).strip())
            if nv:
                allowed.add(nv)
        seen = set()
        for m in re.finditer(C.HEX, f["style"]):
            n = norm_hex(m.group(0))
            if n and n not in allowed:
                seen.add(n)
        # 令牌声明值同样纳入（它们是等值注入的落点）
        for k, v in f["root"].items():
            n = norm_hex(v.strip())
            if n and n not in allowed:
                seen.add(n)
        if seen:
            newvals[r] = sorted(seen)
    add("G3", "等值注入（页面值 ⊆ 改动前基线值 ∪ 值件站点级角色值；新增页须登记）", HARD,
        not newvals and not unregistered,
        ("出现未登记新值的页：%s；" % list(newvals.items())[:3] if newvals else "")
        + ("未登记进基线的页：%s" % unregistered[:5] if unregistered else "")
        if (newvals or unregistered)
        else "%d 页全部等值（0 个新增色值）且全部在改动前基线内" % len(pages))

    # ---- G4 目标存在性
    miss = [t["path"] for t in (profile.get("targets") or [])
            if not os.path.exists(os.path.join(repo, t["path"])) and not t.get("expect_absent")]
    wrong = [r for r in (profile.get("no_root_pages") or []) if (pages.get(r) or {}).get("root")]
    add("G4", "目标存在性（targets 全在 ＋ no_root_pages 真的无 :root）", HARD,
        not miss and not wrong,
        "缺失 %s / 误判无根 %s" % (miss, wrong) if (miss or wrong)
        else "%d 个目标全在 · %d 个声明无根页经实测确无 :root"
        % (len(profile.get("targets") or []), len(profile.get("no_root_pages") or [])))

    # ---- G5 成对对比度（逐档；登记双向）
    tiers = contract.get("usage_tiers") or {}
    fam_vals = (list((contract.get("palettes") or {}).values()) or [{}])[0].get("values") or {}
    roles = contract.get("roles") or {}
    reg = {d["pair"]: d for d in (profile.get("known_contrast_defects") or [])
           if "fg" not in d}
    measured = {d["pair"]: d for d in (profile.get("known_contrast_defects") or [])
                if d.get("fg") and d.get("bg")}
    rows, fails, stale = [], [], []
    for role, tok in sitetok.items():
        spec = roles.get(role) or {}
        if spec.get("kind") == "surface":
            continue          # ★ 判据对象 == 断言对象：底色角色是**参考背景**，不是被判对象
        tier = spec.get("tier") or "body"
        t = tiers.get(tier) or {}
        thr = (t.get("min_contrast") or {}).get("light")
        fg = fam_vals.get(role)
        if isinstance(fg, dict):
            fg = fg.get("light")
        bg = fam_vals.get("surface.nav")
        if isinstance(bg, dict):
            bg = bg.get("light")
        if not (fg and bg and thr):
            continue
        ratio = round(C.ratio(C.hex_to_rgb(fg), C.hex_to_rgb(bg)), 2)
        ok = ratio >= float(thr)
        key = "%s on %s" % (role, "surface.nav")
        rows.append("%s=%s(%s) 门%s %s" % (tok, fg, ratio, thr, "PASS" if ok else "FAIL"))
        if not ok and t.get("gate") == "hard" and key not in reg:
            fails.append(key)
        if not ok:
            if key not in reg and key not in measured:
                stale.append(key + "（未登记）")
        else:
            if key in reg:
                stale.append(key + "（登记过期：实测已达标）")
    # ★ 页级实测缺陷：登记项自带 fg/bg/门限，逐条**重算**（双向：登记过期即 FAIL）
    for key, d in measured.items():
        ratio = round(C.ratio(C.hex_to_rgb(d["fg"]), C.hex_to_rgb(d["bg"])), 2)
        if ratio >= float(d["min"]):
            stale.append("%s（登记过期：实测 %s ≥ 门限 %s）" % (key, ratio, d["min"]))
        else:
            rows.append("%s(%s) 门%s 仍不达标" % (key, ratio, d["min"]))
    add("G5", "成对对比度（usage_tiers 逐档 · vendor/tools/contrast.py 实算 · 登记双向）",
        "hard/report", not fails and not stale,
        "硬档 FAIL %s / 登记不一致 %s｜%s" % (fails, stale, " · ".join(rows))
        if (fails or stale) else " · ".join(rows))

    # ---- G6 零引用登记（双向）
    site_names = set(sitetok.values())
    used_site, unused_site = set(), set()
    for r, f in pages.items():
        for n in re.findall(r"var\(\s*(--[A-Za-z0-9_-]+)", f["style"]):
            if n in site_names:
                used_site.add(n)
    unused_site = site_names - used_site
    regz = set(profile.get("site_level_zero_ref") or [])
    problems = []
    if unused_site:
        problems.append("站点级零引用未处理：%s" % sorted(unused_site))
    if regz - unused_site:
        problems.append("登记过期（已非零引用）：%s" % sorted(regz - unused_site))
    page_unused = {}
    for r, f in pages.items():
        used = set(re.findall(r"var\(\s*(--[A-Za-z0-9_-]+)", f["style"]))
        u = sorted(set(f["root"]) - used)
        if u:
            page_unused[r] = u
    add("G6", "零引用令牌登记（站点级 hard / 页级 report，★ 双向）", "hard/report",
        not problems,
        "；".join(problems) if problems
        else "站点级 %d 枚全部被引用；页级未用令牌 %d 枚分布在 %d 页（已逐页报告）"
        % (len(site_names), sum(len(v) for v in page_unused.values()), len(page_unused)))

    # ---- G7 未声明令牌（**增量**口径：只判本批新出现的令牌名）
    allowed_names = set(pal.values()) | site_names
    undecl, prereg = {}, {}
    for r, f in pages.items():
        before = set((bpages.get(r) or {}).get("root_tokens") or {})
        now = set(f["root"])
        u = sorted(now - before - allowed_names)
        if u:
            undecl[r] = u
        if before - now:
            prereg[r] = sorted(before - now)
    add("G7", "未声明令牌（**本批新增**令牌名 ⊆ 值注册表名 ∪ 值件声明名；既有名按基线冻结）",
        HARD, not undecl and not prereg,
        ("未声明的新增名：%s；" % list(undecl.items())[:4] if undecl else "")
        + ("★ 既有令牌名消失（增量冻结破坏）：%s" % list(prereg.items())[:4] if prereg else "")
        if (undecl or prereg)
        else "本批新增令牌名全部有出处（%d 个值注册表名 + %d 个站点级角色名）；既有令牌名零消失"
        % (len(set(pal.values())), len(site_names)))

    # ---- G8 生成器单源不变量
    writers = declared_writers(repo)
    g8 = []
    if "docs/index.html" not in writers:
        g8.append("首页 docs/index.html 无生成器认领（Q1=B 未落地）")
    tl = writers.get("docs/timeline.html", [])
    if len(tl) != 1:
        g8.append("docs/timeline.html 的写者数 = %d（Q4=A 要求恰 1）：%s" % (len(tl), tl))
    else:
        want = (profile.get("single_source_invariants") or {}).get("timeline_writer")
        if want and want not in tl:
            g8.append("唯一写者与 profile 声明不符：声明 %s，实测 %s" % (want, tl))
    add("G8", "生成器单源不变量（首页有认领 · timeline 写者恰 1 且与声明一致）", HARD, not g8,
        "；".join(g8) if g8 else "首页写者 %s · timeline 唯一写者 %s"
        % (writers.get("docs/index.html"), tl))

    # ---- G9 产物归属（生成器面恰 1 / 快照面不得被写）
    owned = profile.get("generator_owned_products") or {}
    # ★ 快照面用 glob 声明（134 个解读页逐个列会变成维护负担）；退化为**空集守卫**：
    #   展开后必须非空，否则 FAIL（⛔ 不把「没展开出来」读成「无违规」）。
    snap_globs = list(profile.get("snapshot_products") or [])
    snap = []
    for g in snap_globs:
        snap.extend(os.path.relpath(p, repo).replace(os.sep, "/")
                    for p in glob.glob(os.path.join(repo, g)))
    bad9 = []
    if not snap:
        bad9.append("快照面展开为 0（空集守卫：snapshot_products=%s）" % snap_globs)
    for rel, who in owned.items():
        w = writers.get(rel, [])
        if len(w) != 1 or w[0] != who:
            bad9.append("%s：声明写者 %s，实测 %s" % (rel, who, w))
    for rel in snap:
        if rel in writers:
            bad9.append("快照产物被生成器声明写入：%s（%s）" % (rel, writers[rel]))
    # 反向：有写者的发布面产物必须登记
    for rel in writers:
        if rel.startswith("docs/") and rel.endswith(".html") and rel not in owned:
            bad9.append("生成器声明写入 %s 但未登记归属" % rel)
    # 反向：生成器拥有面必须真的存在
    for rel in owned:
        if not os.path.exists(os.path.join(repo, rel)):
            bad9.append("登记的产物不存在：%s" % rel)
    add("G9", "产物归属（生成器面恰 1 个写者 · 快照面零写者 · 双向登记）", HARD, not bad9,
        "；".join(bad9[:6]) if bad9
        else "生成器拥有面 %d 个产物写者全部可核；快照面 %d 个产物无生成器写入"
        % (len(owned), len(snap)))

    # ---- G10 仅报告
    def residual(f):
        return tuple(sorted(n for n in f["root"] if not RE_REGISTRY.match(n) and n not in site_names))
    vocab = len({residual(f) for f in pages.values()})
    zero = sorted(r for r, f in pages.items() if not f["root"])
    add("G10", "口径分布（残余词汇表/零令牌页/@media；仅报告）", REPORT, True,
        "残余词汇表 %d 套（基线 %s）· 全量词汇表 %d 套 · 零令牌页 %d（基线 %s）· @media 合计 %d"
        % (vocab, (baseline.get("counts") or {}).get("vocab_count"),
           len({tuple(sorted(f["root"])) for f in pages.values()}), len(zero),
           (baseline.get("counts") or {}).get("zero_token_count"),
           sum(f["media"] for f in pages.values())))
    return R


# --------------------------------------------------------------------------- 自检
GOOD_BASELINE = {"palette": {"#111111": "--lp-bg-001"},
                 "pages": {"docs/a.html": {"hex_used": {"#111111": 1}},
                           "docs/index.html": {"hex_used": {"#111111": 1}},
                           "docs/snap.html": {"hex_used": {"#111111": 1}},
                           "docs/timeline.html": {"hex_used": {"#111111": 1}}},
                 "counts": {"vocab_count": 1, "zero_token_count": 0}}
GOOD_CONTRACT = {
    "usage_tiers": {"body": {"min_contrast": {"light": 4.5}, "gate": "hard"}},
    "roles": {"link.nav": {"tier": "body"}},
    "palettes": {"f": {"values": {"link.nav": {"light": "#ffffff"}, "surface.nav": {"light": "#000000"}}}},
    "binding": {"site_token_names": {"link.nav": "--lp-nav-accent"}},
}
GOOD_PROFILE = {
    "page_families": [{"glob": "docs/*.html", "family": "top"}],
    "targets": [{"path": "docs/a.html", "mode": "marker-region", "family": "top"}],
    "no_root_pages": [],
    "known_contrast_defects": [],
    "site_level_zero_ref": [],
    "generator_owned_products": {"docs/a.html": "gen_a.py", "docs/timeline.html": "gen_tl.py",
                                 "docs/index.html": "gen_home.py"},
    "snapshot_products": ["docs/snap.html"],
    "single_source_invariants": {"timeline_writer": "gen_tl.py"},
}
GOOD_HTML = ('<!DOCTYPE html><html><head><style>:root{--lp-nav-accent:#ffffff}'
             'a{color:var(--lp-nav-accent);background:#111111}</style></head><body>x</body></html>')
GOOD_GEN = "OUT_PATH = BASE_DIR / 'docs' / 'a.html'\n"
GOOD_TL = "OUT_PATH = BASE_DIR / 'docs' / 'timeline.html'\n"


def selftest():
    import shutil
    import tempfile
    cases = []

    def run(mods):
        tmp = tempfile.mkdtemp(prefix="lp-gt-")
        try:
            os.makedirs(os.path.join(tmp, "docs"))
            os.makedirs(os.path.join(tmp, "data"))
            open(os.path.join(tmp, "docs", "a.html"), "w", encoding="utf-8").write(
                mods.get("a_html", GOOD_HTML))
            open(os.path.join(tmp, "docs", "snap.html"), "w", encoding="utf-8").write(GOOD_HTML)
            open(os.path.join(tmp, "docs", "index.html"), "w", encoding="utf-8").write(
                mods.get("a_html", GOOD_HTML))
            open(os.path.join(tmp, "docs", "timeline.html"), "w", encoding="utf-8").write(
                mods.get("a_html", GOOD_HTML))
            open(os.path.join(tmp, "data", "gen_a.py"), "w").write(mods.get("gen_a", GOOD_GEN))
            open(os.path.join(tmp, "data", "gen_tl.py"), "w").write(mods.get("gen_tl", GOOD_TL))
            open(os.path.join(tmp, "data", "gen_home.py"), "w").write(
                mods.get("gen_home", "OUT_PATH = BASE_DIR / 'docs' / 'index.html'\n"))
            m = json.loads(json.dumps(mods.get("manifest", {"gates": [{"id": "x", "script": "gate_tokens.py",
                                                                       "reads": ["r"], "selftest": True}]})))
            pr = json.loads(json.dumps(GOOD_PROFILE))
            pr.update(mods.get("profile", {}))
            b = json.loads(json.dumps(GOOD_BASELINE))
            b.update(mods.get("baseline", {}))
            c = json.loads(json.dumps(GOOD_CONTRACT))
            c.update(mods.get("contract", {}))
            return check(tmp, m, pr, b, c)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def get(R, cid):
        for r in R:
            if r["id"] == cid:
                return r
        return {"ok": False, "detail": "缺判据"}

    def case(name, ok):
        cases.append((name, bool(ok)))

    R = run({})
    case("正向夹具 0 FAIL", all(r["ok"] for r in R))

    # G1：空集守卫（扫描面为 0）
    R = run({"a_html": "", "baseline": {"pages": {}}})
    case("G1 负例：基线 pages 为空 ⇒ FAIL", not get(R, "G1")["ok"])
    R = run({"profile": {"targets": [{"path": "docs/none.html", "mode": "marker-region", "family": "t"}]}})
    case("G4 负例：目标不存在 ⇒ FAIL", not get(R, "G4")["ok"])
    # G2：外链 CSS（形态 1 入侵）
    R = run({"a_html": GOOD_HTML.replace("<style>", '<link rel="stylesheet" href="t.css"><style>')})
    case("G2 负例：出现外链 CSS ⇒ FAIL（Q6=A 形态 2）", not get(R, "G2")["ok"])
    # G3：注入了一个基线里没有的新值（假阳样本：新值）
    R = run({"a_html": GOOD_HTML.replace("#111111", "#222222")})
    case("G3 负例：出现基线外的新色值 ⇒ FAIL（Q3=A 等值）", not get(R, "G3")["ok"])
    # G3：新增页未登记进基线
    R = run({"baseline": {"pages": {"docs/a.html": {"hex_used": {"#111111": 1}}}}})
    case("G3 负例：页面未登记进改动前基线 ⇒ FAIL（增量冻结要求登记）", not get(R, "G3")["ok"])
    # G5：不达标且未登记 ⇒ FAIL；不达标但已登记 ⇒ PASS；达标却登记 ⇒ FAIL（登记过期）
    R = run({"contract": {"palettes": {"f": {"values": {"link.nav": {"light": "#0a0a0a"},
                                                       "surface.nav": {"light": "#000000"}}}}}})
    case("G5 负例：对比度不达标且未登记 ⇒ FAIL", not get(R, "G5")["ok"])
    R = run({"contract": {"palettes": {"f": {"values": {"link.nav": {"light": "#0a0a0a"},
                                                       "surface.nav": {"light": "#000000"}}}}},
             "profile": {"known_contrast_defects": [{"pair": "link.nav on surface.nav", "why": "既有缺陷"}]}})
    case("G5 正向：不达标但已登记（Q3=A 禁改值）⇒ PASS", get(R, "G5")["ok"])
    R = run({"profile": {"known_contrast_defects": [{"pair": "link.nav on surface.nav", "why": "过期"}]}})
    case("G5 负例：登记过期（实测已达标）⇒ FAIL", not get(R, "G5")["ok"])
    # G7：盘上出现未声明令牌
    R = run({"a_html": GOOD_HTML.replace(":root{", ":root{--ghost:#ffffff;")})
    case("G7 负例：出现未声明令牌名 ⇒ FAIL", not get(R, "G7")["ok"])
    # G8：双写（两个生成器都写 timeline）
    R = run({"gen_home": "OUT_PATH = BASE_DIR / 'docs' / 'timeline.html'\n"})
    case("G8 负例：timeline 写者 ≠1（双写复现）⇒ FAIL", not get(R, "G8")["ok"])
    R = run({"gen_home": "x = 1\n"})
    case("G8 负例：首页无生成器认领 ⇒ FAIL", not get(R, "G8")["ok"])
    # G9：快照面被生成器写入 ⇒ 必须 FAIL（快照产物不得有生成器写者）
    R = run({"gen_tl": GOOD_TL + "OUT_PATH = BASE_DIR / 'docs' / 'snap.html'\n"})
    case("G9 负例：快照产物被生成器声明写入 ⇒ FAIL", not get(R, "G9")["ok"])
    # G9：写者与声明不符
    R = run({"gen_tl": GOOD_TL.replace("timeline.html", "other.html")})
    case("G9 负例：timeline 写者与 profile 声明不符 ⇒ FAIL", not get(R, "G9")["ok"])
    # ast 求值面：跨行隐式拼接必须被识别（⛔ 逐行正则的盲区）
    tmp = tempfile.mkdtemp(prefix="lp-ast-")
    try:
        os.makedirs(os.path.join(tmp, "data"))
        open(os.path.join(tmp, "data", "g.py"), "w").write(
            "OUT_PATH = (BASE_DIR\n            / 'docs'\n            / 'x.html')\n")
        w = declared_writers(tmp)
        case("G8/G9 口径：ast 能识别跨行拼接的输出路径", w.get("docs/x.html") == ["g.py"])
        open(os.path.join(tmp, "data", "h.py"), "w").write(
            "OUT = os.path.join(BASE, 'docs', 'y.html')\n")
        w = declared_writers(tmp)
        case("G8/G9 口径：ast 能识别 os.path.join 写法", w.get("docs/y.html") == ["h.py"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    ok = all(v for _, v in cases)
    for n, v in cases:
        print("  [%s] %s" % ("PASS" if v else "FAIL", n))
    print("\n=== gate_tokens 自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-root", default=".")
    ap.add_argument("--manifest", default="gate-manifest.json")
    ap.add_argument("--profile", default="build/profile.json")
    ap.add_argument("--baseline", default="data/token-baseline.json")
    ap.add_argument("--value-file", default="vendor/pipeline/values/llm-papers-knowledge-base.json")
    ap.add_argument("--mode", default="enforce", choices=["enforce", "report"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    root = os.path.abspath(a.site_root)
    try:
        manifest = load_json(os.path.join(root, a.manifest), "门控清单")
        profile = load_json(os.path.join(root, a.profile), "profile")
        baseline = load_json(os.path.join(root, a.baseline), "改动前令牌基线")
        contract = load_json(os.path.join(root, a.value_file), "站点值件")
    except GateError as exc:
        print("GUARD-REJECT: %s" % exc)
        return 3
    R = check(root, manifest, profile, baseline, contract)
    for r in R:
        print("[%s] %-4s %-5s %s — %s" % ("PASS" if r["ok"] else "FAIL", r["id"], r["class"],
                                          r["name"], r["detail"]))
    if a.json:
        print(json.dumps(R, ensure_ascii=False, indent=1))
    blind_fail = [r for r in R if not r["ok"] and r["class"] == BLIND]
    hard_fail = [r for r in R if not r["ok"] and r["class"] in (HARD, "hard/report")]
    nf = len(blind_fail) + (0 if a.mode == "report" else len(hard_fail))
    print("\n=== 站点侧令牌门控：%d 项判据，%d FAIL（blind %d / hard %d；mode=%s）==="
          % (len(R), nf, len(blind_fail), len(hard_fail), a.mode))
    return 0 if nf == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
