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
import html
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
# ★ 批 J（无障碍 / 元数据面）的三处新写入面，同样**成对标记 + 先剥后写** ⇒ 幂等：
AB, AE = "/* LP:A11Y:BEGIN */", "/* LP:A11Y:END */"
HB, HE = "<!-- LP:HEAD:BEGIN -->", "<!-- LP:HEAD:END -->"
SB, SE = "<!-- LP:SKIP:BEGIN -->", "<!-- LP:SKIP:END -->"

STYLE_RE = re.compile(r"(<style[^>]*>)(.*?)(</style>)", re.S | re.I)
BODY_RE = re.compile(r"<body[^>]*>", re.I)
END_HEAD_RE = re.compile(r"</head>", re.I)
END_BODY_RE = re.compile(r"</body>", re.I)
ROOT_RE = re.compile(r":root\s*\{([^{}]*)\}")
TOKEN_DEF = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+)")
VAR_USE_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
WHOLE_ROOT_TOKENS_RE = re.compile(r":root\s*\{\s*" + re.escape(TB) + r".*?" + re.escape(TE) + r"\s*\}", re.S)
TOKENS_RE = re.compile(re.escape(TB) + r".*?" + re.escape(TE), re.S)
NAVCSS_RE = re.compile(re.escape(NCB) + r".*?" + re.escape(NCE), re.S)
A11YCSS_RE = re.compile(re.escape(AB) + r".*?" + re.escape(AE), re.S)
# ★ 尾部 `\n?` 是**幂等的关键**：写入时固定为「frag + "\n"」，剥离时连这个换行一起吃掉，
#   否则每跑一次就地多出一行空行（第 N 次 ≠ 第 1 次）。
NAV_RE = re.compile(r"\n*" + re.escape(NB) + r".*?" + re.escape(NE) + r"\n*", re.S)
HEAD_RE = re.compile(re.escape(HB) + r".*?" + re.escape(HE) + r"\n?", re.S)
SKIP_RE = re.compile(r"\n*" + re.escape(SB) + r".*?" + re.escape(SE) + r"\n*", re.S)

# ---------------------------------------------------------------- 站点常量（批 J）
# ★ 值来源：站点 brief §1「规范 URL 基址」/「站点名」；⛔ 不含墙钟时间、⛔ 不含作者机路径。
REPO_NAME = "llm-papers-knowledge-base"
SITE_NAME = "LLM 论文知识库"
PUBLISH_DIR = "docs"          # ★ 与 build/profile.json#publish_dir 一致（canonical 拼接用）
BASE_URL = "https://zako-mio.github.io/%s/" % REPO_NAME
OG_IMAGE = BASE_URL + "og.png"


def favicon_href(rel):
    """发布根 `favicon.svg` 的**逐页相对路径**。

    ★ 为什么⛔ 不用 `COMMON.md §2.1` 建议的根绝对形式 `/{REPO}/favicon.svg`：本站既有的
      **hard 门控 `gate_links.py`（LK2）把 `<link href>` 也纳入「站内锚可达」判据**，而 LK2 的
      解析口径是 `os.path.normpath(os.path.join(页目录, href))` —— 以 `/` 开头的 href 会被
      `join` 当成**宿主文件系统绝对路径**，在任何仓内布局下都必然判「断链」（LK2/LK5 双红）。
      该门控属本轮「⛔ 不要动」的四道既有门控之一 ⇒ 判据不改，改用**真的可达**的相对路径。
      ★ `gate_seo_meta.py` 的 S7 只要求「页内有 `<link rel="icon">`」或「发布根有 favicon 文件」，
      与 href 形式无关 ⇒ 两套判据同时成立，且部署后都指向同一个 `/REPO/favicon.svg`。
    """
    r = rel[len(PUBLISH_DIR) + 1:] if rel.startswith(PUBLISH_DIR + "/") else rel
    return "../" * r.count("/") + "favicon.svg"


FAVICON_HREF = "favicon.svg"          # 发布根页（docs/*.html）用的相对形式

# ★ 生成器拥有面（`build/profile.json#generator_owned_products`）：这 4 页的**外壳**由各自的
#   生成器产出（本轮同批改为自带 head/骨架/无障碍样式）⇒ 本件**只做** Q3 令牌注入，
#   ⛔ 不重复写它们的 head / skip link / `<main>`（否则两套写法会漂移）。
GENERATOR_OWNED = ("docs/index.html", "docs/timeline.html", "docs/list.html",
                   "docs/analysis/index.html")

# ---------------------------------------------------------------- 批 J：无障碍/元数据
# ★ 为什么这条 CSS **一个色值字面量都不写**（形态与 `COMMON.md §2.3` 的建议式不同）：
#   本站门控 `gate_tokens.py` 的 G3（Q3=A 等值注入）**硬判**「页面 CSS 语料里不得出现
#   改动前基线之外的新色值」⇒ 写入 `#4f8cff` / `#fff` 一类字面量会当场把 G3 判红。
#   故改用 `currentColor` 与系统色 `Canvas` / `CanvasText`：既拿到「键盘焦点可见」与
#   「skip link 与底色成对可读」，又**不引入任何新色值**（G3 与 G7 同时保持 0 FAIL）。
A11YCSS_TMPL = (AB + """
:focus-visible{outline:2px solid currentColor;outline-offset:2px}
.skip-link{position:absolute;left:-9999px;top:0;z-index:100;padding:0.5rem 1rem;
  background:Canvas;color:CanvasText;border:1px solid CanvasText;border-radius:0 0 6px 0}
.skip-link:focus{left:0}
""" + AE)

EMPTY_TAG_RE = re.compile(r"<[^>]+>")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
SCRIPT_RE = re.compile(r"<script\b.*?</script>", re.S | re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S | re.I)
P_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
SUB_RE = re.compile(r'<div[^>]*\bclass\s*=\s*"[^"]*(?:\bsub\b|\ben\b)[^"]*"[^>]*>(.*?)</div>',
                    re.S | re.I)
MAIN_RE = re.compile(r"<main\b[^>]*>", re.I)
ID_ATTR_RE = re.compile(r"\bid\s*=", re.I)
DIV_TOKEN_RE = re.compile(r"<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>|</?div\b[^>]*>",
                          re.S | re.I)
DIV_OPEN_RE = re.compile(r'<div\b[^>]*\bclass\s*=\s*"([^"]*)"[^>]*>', re.I)
# ★ `<main>` 的落点候选**按类名逐 token 精确匹配**（⛔ 不用 `\bpage\b` 这类子串口径：
#   那会把 `class="page-head"` 也当成命中）。优先序：内容容器 → 兜底 hero。
CONTAINER_CLASSES = (("wrap", "page", "container"), ("hero",))


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


def add_css_regions(raw, with_a11y, with_nav):
    """把**本件管理的两个 CSS 区**（A11Y ＋ NAVCSS）规范化写入首个 `<style>` 块。

    ★ 为什么两者必须由**同一个函数**一次写完（而不是各写各的）：两个区都追加在块尾，
      各自「先剥自己、再追加」时，被剥掉的位置会留下空行，而另一个区又在其后 ⇒ 空行
      逐次累积（实测：第 2 次就多出 2 行空行）。统一「先把两个区都剥掉、`rstrip()` 归一化
      块尾、再按固定序追加」之后，第 N 次与第 1 次逐字节相同。
    """
    if not (with_a11y or with_nav):
        return raw
    m = STYLE_RE.search(raw)
    if not m:
        raise GuardError("加无障碍/导航样式失败：无 <style> 块")
    txt = NAVCSS_RE.sub("", A11YCSS_RE.sub("", m.group(2)))
    txt = txt.rstrip() + "\n"
    if with_a11y:
        txt += A11YCSS_TMPL + "\n"
    if with_nav:
        txt += NAVCSS_TMPL + "\n"
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


def skip_markup():
    """skip link（`gate_a11y.py` A3 三条同时满足）：

    ① `href="#main"` 命中前缀口径；② 目标 `#id` **在同一页里真的存在**（由 `ensure_main`
    保证每页恰有 1 个 `<main id="main">`）；③ 锚文本含 skip 信号 ＋ class 含 `skip`。
    """
    return SB + '\n<a class="skip-link" href="#main">跳到主要内容</a>\n' + SE


def apply_landing(raw, rel, labels, is_deep):
    """着陆结构统一落位：**先剥两区、再按固定序写入**（SKIP 恒在 NAV 之前）。

    ★ 为什么必须「先剥后写、顺序写死」：`apply_nav` 旧实现是「有标记就就地替换、没有就插在
      `<body>` 后」，一旦插入面从一个变两个（SKIP ＋ NAV），就地替换会让两者的相对次序随
      历史状态漂移 ⇒ 第 N 次 ≠ 第 1 次。这里改成幂等的不动点写法。
    ★ 归一化（`\\n*` 剥离 ＋ 插入侧 `lstrip("\\n")`）是幂等性的第二个必要条件：`<body>` 之后
      原本可能已有换行/缩进，若只「追加」不归一，第一次写入会把原有换行挤到区之后，
      第二次剥离时又多吃掉一个 ⇒ 每跑一次漂一格（实测踩到过）。⛔ 这里只归并**换行**，
      不吞缩进空格（那属于页面自有排版）。
    """
    raw = SKIP_RE.sub("", raw)
    raw = NAV_RE.sub("", raw)
    frag = skip_markup()
    if is_deep:
        frag = frag + "\n" + nav_markup(rel, labels)
    m = BODY_RE.search(raw)
    if not m:
        raise GuardError("%s：无 <body> ⇒ 无法插着陆结构" % rel)
    return raw[:m.end()] + "\n" + frag + "\n" + raw[m.end():].lstrip("\n")


# --------------------------------------------------------------------------- 批 J · A2
def _div_close(raw, start):
    """返回与 `start` 处 `<div …>` 配对的 `</div>` 的 (start, end)；解析不到返回 (None, None)。

    ★ 口径：整段扫描里 `<script…>…</script>` / `<style…>…</style>` / `<!-- … -->` 先被当成
      **单个不可分记号**吃掉（否则脚本字符串里的 `</div>` 会把深度数带偏 ⇒ 配错闭合位）。
    """
    depth = 0
    for m in DIV_TOKEN_RE.finditer(raw, start):
        tok = m.group(0)
        low = tok[:8].lower()
        if tok.startswith("<!--") or low.startswith("<script") or low.startswith("<style"):
            continue
        if tok.startswith("</"):
            depth -= 1
            if depth == 0:
                return m.start(), m.end()
        else:
            depth += 1
    return None, None


def _find_container(raw):
    """主内容容器：`<div>` 且 class 词表命中 `CONTAINER_CLASSES`（逐 token 精确匹配）。"""
    for tokens in CONTAINER_CLASSES:
        for m in DIV_OPEN_RE.finditer(raw):
            words = set((m.group(1) or "").split())
            if words & set(tokens):
                return m
    return None


def ensure_main(raw, rel):
    """每页**恰 1 个** `<main id="main">`（`gate_a11y.py` A2 ＋ A3 的目标存在性）。

    三条互斥路径（②③ 都只改**一处**容器，⛔ 不新增包裹层 ⇒ 不引入额外布局影响）：
      ① 已有 `<main>`：只补 `id="main"`（⛔ 不再套一层 —— COMMON.md §2.2 明令）；
      ② 无 `<main>` 但有内容容器（139 页里 128 页是这种形态，容器类名逐页实测）：
         把那**一个** `<div class="…">` 就地改名为 `<main id="main" class="…">`，
         并把与它配对的 `</div>` 改为 `</main>`（`_div_close` 逐层配平）；
      ③ 既无 `<main>` 又无容器（护栏兜底，例如自检夹具里的最小页）：把 `<body>` 内容整段
         包进 `<main id="main">…</main>`。
    """
    m = MAIN_RE.search(raw)
    if m:
        tag = m.group(0)
        if not ID_ATTR_RE.search(tag):
            tag = tag[:-1].rstrip() + ' id="main">'
            raw = raw[:m.start()] + tag + raw[m.end():]
        return raw, "existing"
    cm = _find_container(raw)
    if cm:
        attrs = cm.group(0)[len("<div"):-1]
        new_open = "<main id=\"main\"" + attrs + ">"
        cs, ce = _div_close(raw, cm.start())
        if cs is None:
            raise GuardError("%s：容器 <div> 闭合位解析失败 ⇒ 拒写（⛔ 不猜）" % rel)
        return raw[:cm.start()] + new_open + raw[cm.end():cs] + "</main>" + raw[ce:], "converted"
    bm = BODY_RE.search(raw)
    em = END_BODY_RE.search(raw)
    if not (bm and em and bm.end() <= em.start()):
        raise GuardError("%s：无 <body>…</body> ⇒ 无法建主地标" % rel)
    return (raw[:bm.end()] + '\n<main id="main">' + raw[bm.end():em.start()]
            + "</main>\n" + raw[em.start():]), "wrapped"


# --------------------------------------------------------------------------- 批 J · S2–S7
def _plain(s):
    s = EMPTY_TAG_RE.sub(" ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def page_texts(raw):
    """取该页**已有**的标题与首段（★ 逐页不同，⛔ 不用全站同一句模板文案）。"""
    work = HTML_COMMENT_RE.sub("", raw)
    work = SCRIPT_RE.sub("", work)
    work = STYLE_RE.sub("", work)
    tm = TITLE_RE.search(work)
    title = _plain(tm.group(1)) if tm else ""
    hm = H1_RE.search(work) or H2_RE.search(work)
    head = _plain(hm.group(1)) if hm else ""
    tail = work[hm.end():] if hm else work
    paras = [p for p in (_plain(x) for x in P_RE.findall(tail)) if p][:6]
    body = ""
    for p in paras:
        if len(p) >= 40:
            body = p
            break
    if not body and paras:
        body = max(paras, key=len)
    if not body:
        sm = SUB_RE.search(tail)
        if sm:
            body = _plain(sm.group(1))
    return title, head, body


def _clip_desc(s, limit=160):
    """把 description 截到 `limit` 以内（★ 按**转义后**的长度算）。

    ★ 为什么按转义后算：`content="…"` 里的 `&`/`"`/`<` 会膨胀成 `&amp;`/`&quot;`/`&lt;`
      （1 字变 4–6 字）⇒ 只按原文截会在盘上留下 >160 的 content 值（实测 20 页到 180）。
      判据（S10）虽只报告长度，但 `COMMON.md §2.1` 的「截 60–160 字」应按**落盘形态**成立。
    """
    if len(html.escape(s, quote=True)) <= limit:
        return s
    out = s
    while out and len(html.escape(out + "…", quote=True)) > limit:
        out = out[:-1]
    return out.rstrip() + "…"


def compose_desc(title, head, body):
    """description = 该页 h1/h2 ＋ 首个实质段落（截 160 字以内，非空）。"""
    parts = [x for x in (head, body) if x]
    s = "——".join(parts) if parts else (title or SITE_NAME)
    if len(s) < 60 and title and title not in s:
        s = (s + "——" + title) if s else title
    s = re.sub(r"\s+", " ", s).strip()
    return _clip_desc(s) or SITE_NAME


def page_url(rel):
    """产物相对路径 → 该页**自身**的规范 URL。

    ★ 口径必须与 `gate_seo_meta.py#page_url` 逐字一致，而两者的**入参基准不同**：
      门控的 `rel` 相对**发布根**（`docs/`），本件的 `rel` 相对**仓根**（`scan_products`
      产出 `docs/…`）⇒ 这里先剥掉发布根前缀再套同一条规则，否则 S6「canonical 自指」必红。
    """
    prefix = PUBLISH_DIR + "/"
    r = rel[len(prefix):] if rel.startswith(prefix) else rel
    if r == "index.html":
        return BASE_URL
    if r.endswith("/index.html"):
        return BASE_URL + r[:-len("index.html")]
    return BASE_URL + r


def head_block(rel, raw):
    title, head, body = page_texts(raw)
    desc = html.escape(compose_desc(title, head, body), quote=True)
    ogt = html.escape(title or head or SITE_NAME, quote=True)
    url = html.escape(page_url(rel), quote=True)
    icon = html.escape(favicon_href(rel), quote=True)
    return (HB + "\n"
            '<meta name="description" content="%s">\n'
            '<meta property="og:type" content="website">\n'
            '<meta property="og:title" content="%s">\n'
            '<meta property="og:description" content="%s">\n'
            '<meta property="og:url" content="%s">\n'
            '<meta property="og:image" content="%s">\n'
            '<link rel="canonical" href="%s">\n'
            '<link rel="icon" type="image/svg+xml" href="%s">\n'
            % (desc, ogt, desc, url, OG_IMAGE, url, icon) + HE)


def add_head(raw, rel):
    frag = head_block(rel, raw)
    raw = HEAD_RE.sub("", raw)
    m = END_HEAD_RE.search(raw)
    if not m:
        raise GuardError("%s：无 </head> ⇒ 无法注入元数据" % rel)
    return raw[:m.start()] + frag + "\n" + raw[m.start():]


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
    is_owned = rel in GENERATOR_OWNED
    # ★ 顺序是幂等性的一部分：导航样式必须在**字面值扫描之前**落进首个 <style> 块，
    #   否则第一次跑时导航的 var() 引用还不存在，第二次跑才被算作「在用」⇒ 令牌块漂移。
    #   批 J 的 A11YCSS 同理（它不含任何色值字面量，但顺序仍固定，便于逐次比对）。
    if not is_owned:
        raw = add_css_regions(raw, True, is_deep)
    elif is_deep:
        raw = add_css_regions(raw, False, True)
    out, stats = apply_tokens(raw, palette, rel, site_tokens if is_deep else None)
    stats["nav"] = False
    stats["main"] = ""
    if not is_owned:
        out, main_mode = ensure_main(out, rel)
        out = apply_landing(out, rel, labels, is_deep)
        out = add_head(out, rel)
        stats["nav"] = is_deep
        stats["main"] = main_mode
    return out, stats


def scan_products(repo):
    return sorted(os.path.relpath(p, repo).replace(os.sep, "/")
                  for p in glob.glob(os.path.join(repo, "docs", "**", "*.html"), recursive=True))


# ---------------------------------------------------------------- 批 J · S8（站点级两件）
SITEMAP_HEAD = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
ROBOTS = "User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n" % BASE_URL


def sitemap_xml(pages):
    """发布根下**全部**产物页（本件扫描面 == 139 页）逐页 `<loc>`。

    ★ `COMMON.md §1.6` 确定性要求：⛔ 不写 `<lastmod>`（墙钟时间戳会破坏「重跑逐字节相同」）。
    ★ 顺序 = `scan_products()` 的 sorted 顺序（与文件系统枚举顺序无关）。
    """
    out = [SITEMAP_HEAD]
    for rel in pages:
        out.append(" <url><loc>%s</loc></url>\n" % html.escape(page_url(rel), quote=True))
    out.append("</urlset>\n")
    return "".join(out)


def write_site_files(repo, pages):
    """在**发布根**（`profile.publish_dir = docs`）写 `sitemap.xml` 与 `robots.txt`。

    ★ 为什么放在本件收尾（而不是 build_all）：本件是唯一一个**已经遍历过全部 139 个产物页**
      的步骤（`scan_products`），产物清单天然与站点面一致；`build_all.PIPELINE` 与
      `profile.build.pipeline` 的表则被 `gate_ci_contract.py` 的 CI5 逐项双向断言，
      ⛔ 不宜为两件静态文件去动那张表。
    """
    docs = os.path.join(repo, "docs")
    if not os.path.isdir(docs):
        raise GuardError("发布根不存在：%s" % docs)
    with open(os.path.join(docs, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(sitemap_xml(pages))
    with open(os.path.join(docs, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(ROBOTS)


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
    site_changed = []
    if mode == "apply" and not errs:
        before = {}
        for fn in ("sitemap.xml", "robots.txt"):
            fp = os.path.join(repo, "docs", fn)
            before[fn] = open(fp, encoding="utf-8").read() if os.path.isfile(fp) else None
        write_site_files(repo, pages)
        for fn in ("sitemap.xml", "robots.txt"):
            fp = os.path.join(repo, "docs", fn)
            if open(fp, encoding="utf-8").read() != before[fn]:
                site_changed.append("docs/" + fn)
    return {"pages": len(pages), "changed": changed, "rows": rows, "errors": errs,
            "site_changed": site_changed}


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
    n_main = sum(1 for _r, s in r["rows"] if s.get("main"))
    und = sorted({u for _r, s in r["rows"] for u in s["undeclared"]})
    print("扫描 %d 页 · 本次变更 %d 页 · 注入令牌 %d 枚 · 加着陆结构 %d 页 · 主地标 %d 页 · 未声明值 %d 个"
          % (r["pages"], len(r["changed"]), inj, nav, n_main, len(und)))
    if r.get("site_changed"):
        print("  站点级两件已更新：%s" % r["site_changed"])
    if und:
        print("  未声明值（不在改动前 palette 内，保持字面值不改）：%s%s"
              % (und[:10], " …" if len(und) > 10 else ""))
    for e in r["errors"]:
        print("  [FAIL] %s" % e)
    if a.report or a.json:
        for rel, s in r["rows"]:
            print("  %-58s inj=%-3d reuse=%-3d nav=%-5s main=%s" %
                  (rel, s["injected"], s.get("reused_existing", 0), s["nav"], s.get("main") or "-"))
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
    # ★ 批 J 新增夹具：A2（主地标）与 S2–S7（元数据）的**正/负向**样本
    "mainid.html": '<!DOCTYPE html><html lang="zh-CN"><head><title>已有地标页</title>'
                   '<style>:root{--bg:#0f1420}body{background:#0f1420}</style></head><body>'
                   '<header class="hero">题</header>'
                   '<main class="content"><p>该页已经自带一个 main 元素，本轮只应补 id="main"，'
                   '绝不能在其外再套一层（否则 A2 的地标计数会变成 2）。</p></main>'
                   '</body></html>',
    "nest.html": '<!DOCTYPE html><html lang="zh-CN"><head><title>嵌套配平页</title>'
                 '<style>:root{--bg:#0f1420}body{background:#0f1420}</style></head><body>'
                 '<header class="hero">页眉</header>'
                 '<div class="wrap"><div class="inner">内层</div>'
                 '<script>var t="</div>";</script>'
                 '<p>外层容器里的实质段落，用来验证配对闭合位不会被脚本字符串里的假标签带偏，'
                 '同时给出足够长度的 description 取材。</p>'
                 '</div></body></html>',
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

        # ---------------------------------------------------------------- 批 J 新增判据
        def meta_of(out):
            m = re.search(r'<meta name="description" content="([^"]*)">', out)
            return m.group(1) if m else ""

        # 10) A2：已有 <main> 只补 id，⛔ 不叠第二层
        o10, s10 = tf("mainid.html")
        case("A2：已有 <main> 只补 id=\"main\"（⛔ 不再套一层）",
             s10["main"] == "existing" and o10.count("<main") == 1
             and '<main class="content" id="main">' in o10)

        # 11) A2：无 <main> ⇒ 把那**一个**容器就地改名（嵌套/脚本内假标签不误配）
        o11, s11 = tf("nest.html")
        case("A2：容器 <div class=\"wrap\"> 就地改名为 <main id=\"main\" class=\"wrap\">",
             s11["main"] == "converted" and '<main id="main" class="wrap">' in o11)
        case("A2：嵌套 + 脚本内 </div> 不误配（闭合位正确、div 计数恰减 1）",
             o11.count("<main") == 1 and o11.count("</main>") == 1
             and o11.count("</div>") == FIX["nest.html"].count("</div>") - 1
             and 'var t="</div>";' in o11)
        case("A2：⛔ 不为不同页新增包裹层（hero 页眉仍留在 main 之外）",
             '<header class="hero">页眉</header>' in o11
             and o11.index('<header class="hero">') < o11.index('<main id="main"'))

        # 12) A3：skip link 三条（href 前缀 / 目标 #id 同页存在 / skip 信号）
        case("A3：skip link 三条同时成立（href=#main ＋ id=main ＋ 信号文本）",
             'class="skip-link" href="#main"' in o11 and "跳到主要内容" in o11
             and '<main id="main"' in o11)

        # 13) A4：:focus-visible 落在**内联** CSS 语料里且不在注释/@media 内
        case("A4：:focus-visible 作为真规则写进首个 <style>",
             ":focus-visible{outline:2px solid currentColor" in o11)
        case("A4：条文不在 @media 里（键盘可见性不接受条件生效）",
             not re.search(r"@media[^{]*\{[^}]*:focus-visible", o11))
        blk11 = o11[o11.index(AB):o11.index(AE) + len(AE)]
        case("G3 前置：A11YCSS 不含任何色值字面量（否则 gate_tokens G3 必红）",
             not re.search(r"#[0-9a-fA-F]{3,8}\b", A11YCSS_TMPL)
             and not re.search(r"#[0-9a-fA-F]{3,8}\b", blk11))

        # 14) S2–S7：head 8 行齐备 ＋ canonical 绝对且**自指**
        for prop in ("og:title", "og:description", "og:type", "og:url", "og:image"):
            case("S5：%s 已注入" % prop, ('property="%s"' % prop) in o11)
        case("S6：canonical 等于该页自身 URL（绝对且自指）",
             ('<link rel="canonical" href="%s">' % page_url("docs/nest.html")) in o11)
        case("S7：link rel=icon 指向发布根 favicon.svg（type=image/svg+xml，相对路径可达）",
             '<link rel="icon" type="image/svg+xml" href="favicon.svg">' in o11
             and '<link rel="icon" type="image/svg+xml" href="../../../favicon.svg">'
             in tf("deep/B1_P3/Slug_X/03-深度解读报告.html")[0])
        case("S7/LK2 口径：favicon 相对路径逐页深度正确（⛔ 不用根绝对形式）",
             favicon_href("docs/index.html") == "favicon.svg"
             and favicon_href("docs/analysis/index.html") == "../favicon.svg"
             and favicon_href("docs/analysis/B1_P3/S/03-深度解读报告.html")
             == "../../../favicon.svg")
        case("S4：description 非空且**逐页不同**（⛔ 不是全站同一句）",
             bool(meta_of(o11)) and bool(meta_of(o10)) and meta_of(o11) != meta_of(o10))
        case("S4：description 非空且 ≤160 字（长文截断为单行、按**转义后**长度算）",
             0 < len(meta_of(o11)) <= 160 and "\n" not in meta_of(o11))
        case("S4：含 & / \" 的段落截断后仍 ≤160（⛔ 不因转义膨胀越界）",
             len(html.escape(_clip_desc("A&B" * 60), quote=True)) <= 160
             and _clip_desc("A&B" * 60).endswith("…"))

        # 15) 幂等：新增写入面（head / skip / main / a11ycss）二次转换逐字节相同
        case("幂等：新增面二次转换逐字节相同（nest）",
             transform(o11, "docs/nest.html", palette, labels, deep, site_tokens)[0] == o11)
        case("幂等：新增面二次转换逐字节相同（已有地标页）",
             transform(o10, "docs/mainid.html", palette, labels, deep, site_tokens)[0] == o10)
        case("幂等：解读页（SKIP＋NAV 同页）二次转换逐字节相同",
             transform(o7, "docs/analysis/B1_P3/Slug_X/03-深度解读报告.html", palette, labels,
                       deep, site_tokens)[0] == o7)

        # 16) S8：sitemap 逐页 loc 覆盖且**无 lastmod**（确定性）
        sm = sitemap_xml(["docs/index.html", "docs/analysis/index.html", "docs/a.html"])
        case("S8：sitemap 覆盖传入的每一页且 X/index.html → X/",
             sm.count("<loc>") == 3 and ("<loc>%s</loc>" % BASE_URL) in sm
             and ("<loc>%sanalysis/</loc>" % BASE_URL) in sm
             and ("<loc>%sa.html</loc>" % BASE_URL) in sm)
        case("S8：sitemap ⛔ 不含 <lastmod>（墙钟时间戳会破坏幂等）", "lastmod" not in sm)
        case("S8：robots.txt 声明 Sitemap 指向发布根 sitemap.xml",
             ROBOTS.count("Sitemap: %ssitemap.xml" % BASE_URL) == 1)

        # 17) 发布根相对路径口径：docs/X/index.html → …/X/（⛔ 不把 docs/ 拼进 URL）
        case("S6 口径：仓根相对路径先剥发布根前缀再拼 URL",
             page_url("docs/index.html") == BASE_URL
             and page_url("docs/analysis/index.html") == BASE_URL + "analysis/"
             and page_url("docs/analysis/B1_P3/S/03-深度解读报告.html")
             == BASE_URL + "analysis/B1_P3/S/03-深度解读报告.html"
             and "docs/" not in page_url("docs/x.html"))

        ok = all(v for _, v in cases)
        for n, v in cases:
            print("  [%s] %s" % ("PASS" if v else "FAIL", n))
        print("\n=== annotate_products 自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
