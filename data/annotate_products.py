#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""annotate_products.py — 本站产物的**唯一后处理生成器**：Q3 等值令牌注入 ＋ Q7 返回链接/面包屑。

★ 它为什么存在（三份裁定的交集）：
  - **Q3=A**「令牌只注入**等值**（观感零变化，只换取可门控性）」⇒ 注入的 `:root` 令牌，
    取值必须逐字等于**该页原本就在用的字面 hex**，并把规则里的字面值换成 `var(--同名)`：
    计算值不变 ⇒ 观感零变化；同时令牌变成**真被引用**（⛔ 不是零引用死令牌）。
  - **Q2=A**「先增量冻结再按页面族分批」⇒ ⛔ 不做一次全量归一。本件**只做等价改名**：
    不合并同族差异、不重写 76 套 `<style>`、不改任何取值。
  - **Q7=A**「134 页统一『返回深度解读总览』＋面包屑」⇒ 给 134 个解读页插同一套着陆结构。

★ 幂等机理（判据 `SH5 §4.0` 第 3 条：前置条件必须校验；第 5 条：负向夹具）：
  所有写入面都在**成对标记**内（`/* LP:TOKENS:BEGIN */…/* LP:TOKENS:END */`、
  `/* LP:NAVCSS:BEGIN */…/* LP:NAVCSS:END */`、`<!-- LP:NAV:BEGIN -->…<!-- LP:NAV:END -->`）。
  重跑时**先剥标记区再重算**，故第 N 次与第 1 次逐字节相同（`--selftest` 的幂等夹具实测）。

★ 判据对象 == 断言对象（`SH5 §4.0` 第 4 条）：
  令牌只注入到页面**首个** `<style>` 块；字面值替换覆盖该页**全部** `<style>` 块（⛔ 不碰
  正文、⛔ 不碰 HTML 属性里的 `#…`）。`:root` 块自身的文本**不参与**字面值收集（否则令牌
  定义会被当成「用法」，产生自指）。

★ 已知边界（如实登记，⛔ 不得读作「没问题」）：
  1. 本件是**产物 → 产物**的转换器：134 个解读页的正文来源（上游 0825 语料）**不在本仓**
     ⇒ 这批页面的「可复现」只到「重跑本件逐字节相同」这一层，⛔ 不是「从源语料可重建」。
     这是本站 C2-N6（产物归属契约缺失）的如实形态，不是本件引入的。
  2. 命名是**值注册表**式（`--lp-bg-001` 一类，全站同值同名），语义命名归后续按族收敛轮
     （Q2=A 明确把语义收敛推到「按页面族分批」）。
  3. 页面若在**第二个及以后**的 `<style>` 块里定义同名令牌并与首个块冲突，本件不处理
     （实测 139 页中 `style_blocks > 1` 的页数见 `--report`；为 0 时不适用）。

用法：
    python3 data/annotate_products.py --apply            # 就地改写（默认仓根 = 本文件上一级）
    python3 data/annotate_products.py --check            # 只对账：有漂移则 exit 1
    python3 data/annotate_products.py --report           # 打印统计（不改盘）
    python3 data/annotate_products.py --selftest         # 负向夹具 9 例
退出码：0 成功/一致 · 1 有漂移或有 FAIL · 2 输入错误 · 3 护栏拒写（零写入）
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

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "vendor", "tools"))
import contrast as C  # noqa: E402  ★ 项目唯一对比度实现（HEX 正则亦从此取，⛔ 不造第二套）

TB, TE = "/* LP:TOKENS:BEGIN */", "/* LP:TOKENS:END */"
NCB, NCE = "/* LP:NAVCSS:BEGIN */", "/* LP:NAVCSS:END */"
NB, NE = "<!-- LP:NAV:BEGIN -->", "<!-- LP:NAV:END -->"

STYLE_RE = re.compile(r"(<style[^>]*>)(.*?)(</style>)", re.S | re.I)
BODY_RE = re.compile(r"<body[^>]*>", re.I)
ROOT_RE = re.compile(r":root\s*\{([^{}]*)\}")
TOKEN_DEF = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+)")
VAR_USE_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
WHOLE_ROOT_TOKENS_RE = re.compile(r":root\s*\{\s*" + re.escape(TB) + r".*?" + re.escape(TE) + r"\s*\}", re.S)
TOKENS_RE = re.compile(re.escape(TB) + r".*?" + re.escape(TE), re.S)
NAVCSS_RE = re.compile(re.escape(NCB) + r".*?" + re.escape(NCE), re.S)
NAV_RE = re.compile(re.escape(NB) + r".*?" + re.escape(NE), re.S)


class GuardError(Exception):
    """护栏拒写（exit 3）——输入不满足前置条件，⛔ 不静默跳过。"""


def norm_hex(lit):
    if not re.fullmatch(C.HEX, lit):
        return None
    return "#%02x%02x%02x" % C.hex_to_rgb(lit)


def load_json(path, label):
    if not os.path.isfile(path):
        raise GuardError("%s 不存在：%s" % (label, path))
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        raise GuardError("%s 非法 JSON：%s" % (label, exc))


# --------------------------------------------------------------------------- Q3
def inject_tokens(style_text, palette, page_label, extra_tokens=None):
    """在首个 `<style>` 块里注入**等值**令牌并把规则里的字面值换成 `var()`。

    `extra_tokens`＝本页要一并声明的**站点级角色令牌**（导航条那 4 枚，值来自值件
    `vendor/pipeline/values/llm-papers-knowledge-base.json`，⛔ 不由本件自造色值）：
    只给会用到它们的页面（解读页）注入，其余页不注入 —— 否则会凭空造出零引用死令牌。

    返回 (新 style 文本, 统计)。纯函数：无时钟、无随机、无网络、幂等。
    """
    txt = WHOLE_ROOT_TOKENS_RE.sub("", style_text)
    txt = TOKENS_RE.sub("", txt)

    root_m = ROOT_RE.search(txt)
    root_inner = root_m.group(1) if root_m else ""
    existing = {}
    for k, v in TOKEN_DEF.findall(root_inner):
        existing[k.strip()] = v.strip()
    value_to_name = {}
    for k, v in existing.items():
        n = norm_hex(v)
        if n and n not in value_to_name:
            value_to_name[n] = k
    name_to_value = {}
    for k, v in existing.items():
        n = norm_hex(v)
        if n:
            name_to_value[k] = n
    for n, k in palette.items():
        name_to_value.setdefault(k, n)
    for k, v in (extra_tokens or {}).items():
        n = norm_hex(v)
        if n:
            name_to_value.setdefault(k, n)

    # 收集字面值（跳过首个 :root 块自身的文本）
    spans = []
    if root_m:
        spans.append((root_m.start(1), root_m.end(1)))
    def outside_root(pos):
        return not any(s <= pos < e for s, e in spans)

    order, count = [], {}
    # ★ 幂等的关键：第二次跑时规则里的字面 hex **已经被换成 var(--名)**，若只数 hex 就会
    #   「数出 0 个用法 ⇒ 不注入 ⇒ 令牌块被抹掉」。故把可解析的 `var(--名)` 也当作「该值在用」。
    occ = []
    for m in re.finditer(C.HEX, txt):
        if not outside_root(m.start()):
            continue
        n = norm_hex(m.group(0))
        if n:
            occ.append((m.start(), n))
    for m in re.finditer(VAR_USE_RE, txt):
        if not outside_root(m.start()):
            continue
        n = name_to_value.get(m.group(1))
        if n:
            occ.append((m.start(), n))
    for _pos, n in sorted(occ):
        if n not in count:
            order.append(n)
        count[n] = count.get(n, 0) + 1

    injected, undeclared = [], []
    extra_values = {norm_hex(v) for v in (extra_tokens or {}).values()}
    for k, v in (extra_tokens or {}).items():
        if k not in existing:
            injected.append((k, v))
    for n in order:
        if n in extra_values:
            continue          # ★ 已由站点级角色令牌覆盖（同名不同名空间），⛔ 不重复注入、不报未声明
        name = value_to_name.get(n)
        if name is None:
            name = palette.get(n)
        if name is None:
            undeclared.append(n)
            continue
        if name in existing:
            if norm_hex(existing[name]) != n:
                undeclared.append(n)   # 名字冲突且值不同 ⇒ 不注入（⛔ 不改观感）
                continue
        elif name not in [x[0] for x in injected]:
            injected.append((name, n))

    def repl(m):
        if not outside_root(m.start()):
            return m.group(0)
        n = norm_hex(m.group(0))
        if n is None:
            return m.group(0)
        name = value_to_name.get(n) or palette.get(n)
        if name is None:
            return m.group(0)
        if name in existing and norm_hex(existing[name]) != n:
            return m.group(0)
        return "var(%s)" % name

    txt = re.sub(C.HEX, repl, txt)

    if injected:
        decls = TB + "".join("%s:%s;" % (k, v) for k, v in injected) + TE
        if root_m:
            # 重新定位（替换后 span 变了）
            root_m2 = ROOT_RE.search(txt)
            if not root_m2:
                raise GuardError("%s：替换后丢失 :root（解析口径自检失败）" % page_label)
            s, e = root_m2.start(1), root_m2.end(1)
            inner = txt[s:e]
            sep = "" if inner.rstrip().endswith(";") or not inner.strip() else ";"
            txt = txt[:s] + inner.rstrip() + sep + decls + txt[e:]
        else:
            txt = ":root{" + decls + "}" + txt
    return txt, {"injected": len(injected), "literals": sum(count.values()),
                 "undeclared": undeclared,
                 "reused_existing": len([n for n in order if value_to_name.get(n)])}


def apply_tokens(raw, palette, page_label, extra_tokens=None):
    blocks = list(STYLE_RE.finditer(raw))
    if not blocks:
        raise GuardError("%s：无 <style> 块 ⇒ 拒写（形态 2 的判据对象不存在）" % page_label)
    stats = {"injected": 0, "literals": 0, "undeclared": [], "reused_existing": 0}
    out, last = [], 0
    for i, m in enumerate(blocks):
        new_txt, st = inject_tokens(m.group(2), palette, page_label, extra_tokens) if i == 0 \
            else (TOKENS_RE.sub("", m.group(2)), {})
        if i == 0:
            stats = st
        out.append(raw[last:m.start(2)])
        out.append(new_txt)
        last = m.end(2)
    out.append(raw[last:])
    return "".join(out), stats


# --------------------------------------------------------------------------- Q7
NAVCSS_TMPL = (NCB + """
.lp-crumb{font:13px/1.5 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;color:var(--lp-nav-ink);
  background:var(--lp-nav-bg);border:1px solid var(--lp-nav-line);border-radius:8px;
  padding:8px 12px;margin:0 0 18px;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.lp-crumb a{color:var(--lp-nav-accent);text-decoration:none}
.lp-crumb a:hover{text-decoration:underline}
.lp-crumb a:focus-visible{outline:2px solid var(--lp-nav-accent);outline-offset:2px}
.lp-crumb .lp-sep{color:var(--lp-nav-line)}
.lp-back{display:inline-block;margin:0 0 18px;font:13px/1.5 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
  color:var(--lp-nav-accent);text-decoration:none;border-bottom:1px solid var(--lp-nav-line)}
.lp-back:hover{text-decoration:underline}
.lp-back:focus-visible{outline:2px solid var(--lp-nav-accent);outline-offset:2px}
""" + NCE)


def add_navcss(raw):
    m = STYLE_RE.search(raw)
    if not m:
        raise GuardError("加导航样式失败：无 <style> 块")
    txt = NAVCSS_RE.sub("", m.group(2)).rstrip() + "\n" + NAVCSS_TMPL + "\n"
    return raw[:m.start(2)] + txt + raw[m.end(2):]


def nav_markup(rel, labels):
    parts = rel.split("/")
    batch = parts[2]
    slug = parts[3]
    label = labels.get(batch, batch)
    return (NB + "\n"
            '<nav class="lp-crumb" aria-label="面包屑导航">'
            '<a href="../../index.html">深度解读总览</a>'
            '<span class="lp-sep" aria-hidden="true">›</span><span>%s</span>'
            '<span class="lp-sep" aria-hidden="true">›</span><span>%s</span></nav>\n'
            '<a class="lp-back" href="../../index.html">← 返回深度解读总览</a>\n'
            % (label, slug) + NE)


def apply_nav(raw, rel, labels):
    frag = nav_markup(rel, labels)
    if NAV_RE.search(raw):
        return NAV_RE.sub(lambda _m: frag, raw, count=1)
    m = BODY_RE.search(raw)
    if not m:
        raise GuardError("%s：无 <body> ⇒ 无法插着陆结构" % rel)
    return raw[:m.end()] + "\n" + frag + raw[m.end():]


# --------------------------------------------------------------------------- 主流程
DEEP_DEFAULT = "docs/analysis/*/*/*.html"
VALUE_FILE_DEFAULT = "vendor/pipeline/values/llm-papers-knowledge-base.json"


def default_labels():
    return {"B1_P3": "P3 · 必读核心", "B2_P2": "P2 · 重要",
            "B3_P1": "P1 · 基础补充", "_rejected": "未采纳"}


def load_site_tokens(repo, value_file):
    """从**值件**取「站点级角色令牌 → 值」（导航条那 4 枚）。⛔ 不在本件里写死任何色值。"""
    c = load_json(os.path.join(repo, value_file), "站点值件")
    names = (c.get("binding") or {}).get("site_token_names") or {}
    fams = c.get("palettes") or {}
    if not fams:
        raise GuardError("值件无 palettes ⇒ 拒跑")
    vals = list(fams.values())[0].get("values") or {}
    out = {}
    for role, tok in names.items():
        if role in vals:
            v = vals[role]
            v = v.get("light") if isinstance(v, dict) else v
            out[tok] = v
    if not out:
        raise GuardError("值件未给出任何「角色 → 站点令牌名 → 值」⇒ 拒跑（空集守卫）")
    return out


def transform(raw, rel, palette, labels, deep_globs, site_tokens=None):
    is_deep = any(glob.fnmatch.fnmatch(rel, g) for g in deep_globs)
    # ★ 顺序是幂等性的一部分：导航样式必须在**字面值扫描之前**落进首个 <style> 块，
    #   否则第一次跑时导航的 var() 引用还不存在，第二次跑才被算作「在用」⇒ 令牌块漂移。
    if is_deep:
        raw = add_navcss(raw)
    out, stats = apply_tokens(raw, palette, rel, site_tokens if is_deep else None)
    stats["nav"] = False
    if is_deep:
        out = apply_nav(out, rel, labels)
        stats["nav"] = True
    return out, stats


def scan_products(repo):
    return sorted(os.path.relpath(p, repo).replace(os.sep, "/")
                  for p in glob.glob(os.path.join(repo, "docs", "**", "*.html"), recursive=True))


def run(repo, mode, deep_globs, labels, value_file=VALUE_FILE_DEFAULT):
    baseline = load_json(os.path.join(HERE, "token-baseline.json"), "改动前令牌基线")
    palette = baseline.get("palette") or {}
    if not palette:
        raise GuardError("令牌基线里 palette 为空 ⇒ 拒跑（空集守卫）")
    site_tokens = load_site_tokens(repo, value_file)
    pages = scan_products(repo)
    if not pages:
        raise GuardError("docs/**/*.html 扫到 0 页 ⇒ 拒跑（空集守卫）")

    changed, rows, errs = [], [], []
    for rel in pages:
        p = os.path.join(repo, rel)
        raw = open(p, encoding="utf-8", errors="replace").read()
        try:
            new, stats = transform(raw, rel, palette, labels, deep_globs, site_tokens)
        except GuardError as exc:
            errs.append("%s: %s" % (rel, exc))
            continue
        rows.append((rel, stats))
        if new != raw:
            changed.append(rel)
            if mode == "apply":
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(new)
    return {"pages": len(pages), "changed": changed, "rows": rows, "errors": errs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    deep = [DEEP_DEFAULT]
    labels = default_labels()
    try:
        r = run(a.repo, "apply" if a.apply else "check", deep, labels)
    except GuardError as exc:
        print("GUARD-REJECT: %s" % exc)
        return 3 if "拒写" in str(exc) else 2

    inj = sum(s["injected"] for _r, s in r["rows"])
    nav = sum(1 for _r, s in r["rows"] if s["nav"])
    und = sorted({u for _r, s in r["rows"] for u in s["undeclared"]})
    print("扫描 %d 页 · 本次变更 %d 页 · 注入令牌 %d 枚 · 加着陆结构 %d 页 · 未声明值 %d 个"
          % (r["pages"], len(r["changed"]), inj, nav, len(und)))
    if und:
        print("  未声明值（不在改动前 palette 内，保持字面值不改）：%s%s"
              % (und[:10], " …" if len(und) > 10 else ""))
    for e in r["errors"]:
        print("  [FAIL] %s" % e)
    if a.report or a.json:
        for rel, s in r["rows"]:
            print("  %-58s inj=%-3d reuse=%-3d nav=%s" %
                  (rel, s["injected"], s.get("reused_existing", 0), s["nav"]))
    if r["errors"]:
        print("\n=== annotate_products：%d 页有护栏 FAIL ===" % len(r["errors"]))
        return 1
    if a.check:
        print("\n=== annotate_products --check：%d 页有漂移 ===" % len(r["changed"]))
        return 1 if r["changed"] else 0
    print("\n=== annotate_products：OK ===")
    return 0


# --------------------------------------------------------------------------- 自检
FIX = {
    "plain.html": '<!DOCTYPE html><html><head><style>'
                  'body{background:#0f1420;color:#e6e9f0}'
                  '.a{border:1px solid #2a3650}</style></head><body><p>x</p></body></html>',
    "rootonly.html": '<!DOCTYPE html><html><head><style>'
                     ':root{--bg:#0f1420}</style></head><body><p>x</p></body></html>',
    "reuse.html": '<!DOCTYPE html><html><head><style>'
                  ':root{--bd:#24304a}body{background:#24304a}</style></head><body><p>x</p></body></html>',
    "attr.html": '<!DOCTYPE html><html><head><style>:root{--bg:#111111}'
                 'body{background:#111111}</style></head>'
                 '<body><a href="#0f1420">#0f1420 不是颜色用法</a></body></html>',
    "nostyle.html": '<!DOCTYPE html><html><head></head><body><p>x</p></body></html>',
    "deep/B1_P3/Slug_X/03-深度解读报告.html":
        '<!DOCTYPE html><html lang="zh-CN"><head><style>'
        'body{background:#eef3fa;color:#1f2430}</style></head><body><div class="wrap">t</div></body></html>',
}


def selftest():
    cases = []

    def case(name, ok):
        cases.append((name, bool(ok)))

    tmp = tempfile.mkdtemp(prefix="lp-annot-")
    try:
        repo = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(repo, "docs", "analysis", "B1_P3", "Slug_X"), exist_ok=True)
        here = os.path.dirname(os.path.abspath(__file__))
        shutil.copy(os.path.join(here, "token-baseline.json"), os.path.join(tmp, "token-baseline.json"))
        palette = json.load(open(os.path.join(tmp, "token-baseline.json"), encoding="utf-8"))["palette"]
        labels = default_labels()
        deep = [DEEP_DEFAULT]
        site_tokens = {"--lp-nav-bg": "#eef1f5", "--lp-nav-line": "#cbd5e1",
                       "--lp-nav-ink": "#14304f", "--lp-nav-accent": "#2b6cb0"}

        # 夹具：写真实文件再读（⛔ 不做「先截断后读」——批 H 的 12-factor 自检脚本体裁在此）
        paths = {}
        for name, body in FIX.items():
            p = os.path.join(repo, "docs", *name.split("/")) if name.startswith("deep/") \
                else os.path.join(repo, "docs", name)
            if name.startswith("deep/"):
                p = os.path.join(repo, "docs", "analysis", "B1_P3", "Slug_X", "03-深度解读报告.html")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(body)
            paths[name] = p

        def tf(name):
            rel = ("docs/analysis/B1_P3/Slug_X/03-深度解读报告.html" if name.startswith("deep/")
                   else "docs/" + name)
            raw = open(paths[name], encoding="utf-8").read()
            return transform(raw, rel, palette, labels, deep, site_tokens)

        # 1) 等值注入：字面值 → var()，且 :root 里的值与字面值逐字相等
        out, st = tf("plain.html")
        case("等值注入：body 背景被换成 var()", "background:var(--lp-bg-" in out)
        case("等值注入：注入数 == 该页不同字面值数（3）", st["injected"] == 3)
        case("等值注入：值未被改动（#0f1420 原样出现在 :root）", "#0f1420" in out)

        # 2) 只定义不使用的 :root ⇒ 不得凭空注入（0 注入）
        _o2, s2 = tf("rootonly.html")
        case("负例·假阳：只有 :root 定义、无用法 ⇒ 注入 0（⛔ 不把定义当用法）", s2["injected"] == 0)

        # 3) 复用既有令牌名（值相同）⇒ 用 --bd 而不是新造 --lp-*
        o3, _s3 = tf("reuse.html")
        case("复用：同名同值复用既有 --bd", "background:var(--bd)" in o3 and "--lp-" not in o3)

        # 4) HTML 属性里的 #hex 不得被令牌化
        o4, _s4 = tf("attr.html")
        case("负例·假阳：href=\"#0f1420\" 保持字面（只在 <style> 内替换）",
             'href="#0f1420"' in o4)

        # 5) 无 <style> ⇒ 护栏 FAIL，⛔ 不静默跳过
        try:
            tf("nostyle.html")
            case("负例·空集：无 <style> 必须抛护栏", False)
        except GuardError:
            case("负例·空集：无 <style> 必须抛护栏", True)

        # 6) 幂等：同一输入跑两次逐字节相同
        o6a, _ = transform(FIX["plain.html"], "docs/plain.html", palette, labels, deep, site_tokens)
        o6b, _ = transform(o6a, "docs/plain.html", palette, labels, deep, site_tokens)
        case("幂等：二次转换逐字节相同", o6a == o6b)
        d6a, _ = transform(FIX["deep/B1_P3/Slug_X/03-深度解读报告.html"],
                           "docs/analysis/B1_P3/Slug_X/03-深度解读报告.html", palette, labels, deep, site_tokens)
        d6b, _ = transform(d6a, "docs/analysis/B1_P3/Slug_X/03-深度解读报告.html",
                           palette, labels, deep, site_tokens)
        case("幂等：解读页二次转换逐字节相同（含导航与站点级令牌）", d6a == d6b)

        # 7) 深页加导航＋面包屑，且重复转换不叠加
        o7, s7 = tf("deep/B1_P3/Slug_X/03-深度解读报告.html")
        case("Q7：解读页插了面包屑与返回链接", "lp-crumb" in o7 and "返回深度解读总览" in o7)
        case("Q7：导航只插一次（重复转换不叠加）",
             transform(o7, "docs/analysis/B1_P3/Slug_X/03-深度解读报告.html", palette, labels, deep,
                       site_tokens)[0].count("lp-back") == o7.count("lp-back"))
        case("Q7：返回目标为 ../../index.html", 'href="../../index.html"' in o7)
        case("Q3/Q7：解读页声明了站点级导航令牌", "--lp-nav-ink:#14304f" in o7)

        # 8) 非解读页不得加导航
        o8, s8 = tf("plain.html")
        case("Q7 边界：顶层页不加面包屑", "lp-crumb" not in o8 and s8["nav"] is False)
        case("Q7 边界：顶层页不注入站点级导航令牌（防空造零引用）", "--lp-nav-" not in o8)

        # 9) 导航令牌与值注册表名字空间不冲突（值件 role 名 vs palette 值注册表名）
        case("命名空间：--lp-nav-* 不出现在值注册表里（⛔ 两套名字不混）",
             all(k not in palette.values() for k in site_tokens))
        case("命名空间：palette 名一律 --lp-{bg|ink|line|mix}-NNN",
             all(re.fullmatch(r"--lp-(bg|ink|line|mix)-\d{3}", v) for v in palette.values()))

        ok = all(v for _, v in cases)
        for n, v in cases:
            print("  [%s] %s" % ("PASS" if v else "FAIL", n))
        print("\n=== annotate_products 自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
