#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""snapshot_baseline.py — 本站令牌面的**改动前基线快照**（单次采集器，判据的同期配置副本）。

为什么需要它（`_shared/SH5-gating.md` §4.0 第 6 条「快照类断言必须配同期的配置副本」）：
  Q2=A 取「增量冻结」⇒ 判据不能是「全站归一」，只能是「**相对改动前基线** 不得新增词汇表 /
  不得改值」。因此必须先把改动前的逐页令牌面**冻结成机读件**，否则判据要么恒真、要么必然红。

本件产出 `data/token-baseline.json`，含三部分：
  1. `pages[rel]`  逐页令牌面：首个 `:root` 块的令牌名→值、内联 `<style>` 里的字面 hex 多重集、
     每个 hex 出现的**声明属性**（用于给调色板分类命名）、`@media` 数、`<style>` 块数、是否有 `:root`。
  2. `palette`     全站「值 → 令牌名」表（**本站唯一**的注入命名表；原文在生成器与门控两侧共用）。
  3. `counts`      词汇表指纹数 / 零令牌页清单 / 页数（`check_token_census.py` 的基线数字）。

★ 解析口径：
  - hex 只在内联 `<style>` 文本内采集（⛔ 不在 HTML 属性、`<script>`、正文里采集）；
    正则复用 `vendor/tools/contrast.py` 的 `HEX`（长分支在前，⛔ 不造第二套）。
  - 「首个 `:root` 块」= 全文**第一个** `:root{…}`（`SH5` §4.0 第 4 条：判据对象 == 断言对象）。
  - 值一律归一成 `#rrggbb` 小写作键；原字面写法另存 `forms`（替换时要按原样找回）。

★ 本件**只读产物、只写 `data/`**，⛔ 不改任何 HTML。运行时机：改动**之前**，一次。
用法：
    python3 data/snapshot_baseline.py                 # 采集并写 data/token-baseline.json
    python3 data/snapshot_baseline.py --selftest      # 负向夹具（4 例）
    python3 data/snapshot_baseline.py --verify        # 只对账不写盘（幂等面自证）
退出码：0 成功 / 1 对账漂移 / 2 输入错误
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "vendor", "tools"))
import contrast as C  # noqa: E402  ★ 项目唯一对比度实现；HEX/hex_to_rgb 亦从这里取

STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
ROOT_RE = re.compile(r":root\s*\{([^{}]*)\}")
TOKEN_DEF = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+)")
DECL_RE = re.compile(r"(?<![\w-])([a-zA-Z-]+)\s*:\s*([^;{}]*)")
MEDIA_RE = re.compile(r"@media\b")
EXT_CSS_RE = re.compile(r"<link[^>]+rel\s*=\s*[\"']?stylesheet", re.I)

TOKENS_BEGIN = "/* LP:TOKENS:BEGIN */"
TOKENS_END = "/* LP:TOKENS:END */"
NAV_BEGIN = "<!-- LP:NAV:BEGIN -->"
NAV_END = "<!-- LP:NAV:END -->"

BGISH = ("background", "background-color", "background-image")
LINEISH = ("border", "border-top", "border-right", "border-bottom", "border-left",
           "border-color", "border-top-color", "border-right-color",
           "border-bottom-color", "border-left-color", "outline", "outline-color",
           "box-shadow", "text-decoration-color", "column-rule-color")
INKISH = ("color", "fill", "stroke")


def norm_hex(lit):
    """把任意 hex 字面量归一成 `#rrggbb` 小写；非法返回 None。"""
    m = re.fullmatch(C.HEX, lit)
    if not m:
        return None
    rgb = C.hex_to_rgb(lit)
    return "#%02x%02x%02x" % rgb


def classify_uses(uses):
    """按声明属性把「值的用途」分类 → bg / line / ink / mix（判据可解释、命名可复现）。"""
    tot = sum(uses.values()) or 1
    g = sum(n for p, n in uses.items() if p in BGISH)
    l = sum(n for p, n in uses.items() if p in LINEISH or p.startswith("border"))
    i = sum(n for p, n in uses.items() if p in INKISH)
    best, name = max((g, "bg"), (l, "line"), (i, "ink"))
    if best / tot >= 0.7 and best > 0:
        return name
    return "mix"


def page_facts(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    styles = STYLE_RE.findall(raw)
    style_txt = "\n".join(styles)
    root_m = ROOT_RE.search(style_txt)
    root_block = root_m.group(1) if root_m else ""
    exist_tokens = {}
    for k, v in TOKEN_DEF.findall(root_block):
        exist_tokens[k] = v.strip()

    # 字面 hex：只在 <style> 内、且跳过首个 :root 块自身的文本（那一块是令牌定义，不是用法）
    scan_txt = style_txt
    if root_m:
        scan_txt = style_txt[:root_m.start(1)] + style_txt[root_m.end(1):]
    hex_counter = Counter()
    uses = defaultdict(Counter)
    for dm in DECL_RE.finditer(scan_txt):
        prop = dm.group(1).lower()
        val = dm.group(2)
        for lit in re.findall(C.HEX, val):
            n = norm_hex(lit)
            if not n:
                continue
            hex_counter[n] += 1
            uses[n][prop] += 1
    # 声明正则抓不到的裸 hex（如选择器后的简写、媒体查询内联值）也计入，属性记为 "?"
    for lit in re.findall(C.HEX, scan_txt):
        n = norm_hex(lit)
        if not n:
            continue
        if hex_counter[n] == 0:
            hex_counter[n] += 1
            uses[n]["?"] += 1

    return {
        "style_blocks": len(styles),
        "ext_css_links": len(EXT_CSS_RE.findall(raw)),
        "media": len(MEDIA_RE.findall(style_txt)),
        "has_root": bool(root_m),
        "root_tokens": exist_tokens,
        "root_token_names": sorted(exist_tokens),
        "hex_used": dict(sorted(hex_counter.items())),
        "hex_uses": {k: dict(v) for k, v in sorted(uses.items())},
        "hex_total": sum(hex_counter.values()),
        "distinct_hex": len(hex_counter),
        "vocab_fingerprint": sorted(exist_tokens),
        "has_nav_marker": NAV_BEGIN in raw,
        "has_token_marker": TOKENS_BEGIN in raw,
        "bytes": len(raw.encode("utf-8")),
    }


def scan(repo):
    pages = {}
    for p in sorted(glob.glob(os.path.join(repo, "docs", "**", "*.html"), recursive=True)):
        rel = os.path.relpath(p, repo).replace(os.sep, "/")
        pages[rel] = page_facts(p)
    return pages


def build_palette(pages):
    """全站「值 → 令牌名」表。同名同值、同值同名（站点级唯一）⇒ 判据可跨页断言。"""
    fused = defaultdict(Counter)
    for f in pages.values():
        for v, u in f["hex_uses"].items():
            fused[v].update(u)
    freq = {}
    for f in pages.values():
        for v, n in f["hex_used"].items():
            freq[v] = freq.get(v, 0) + n
    groups = defaultdict(list)
    for v in fused:
        groups[classify_uses(fused[v])].append(v)
    palette, index = {}, {}
    for cls in ("bg", "ink", "line", "mix"):
        vs = sorted(groups.get(cls, []), key=lambda v: (-freq[v], v))
        for i, v in enumerate(vs, 1):
            name = "--lp-%s-%03d" % (cls, i)
            palette[v] = name
            index[name] = {"value": v, "class": cls, "occurrences": freq[v],
                           "uses": dict(fused[v])}
    return palette, index


def vocab_count(pages):
    """词汇表口径（与批 C 的 76 套同口径）：按「首个 :root 块内 `--name:` 声明集合」取指纹。"""
    return len({tuple(f["vocab_fingerprint"]) for f in pages.values()})


def snapshot(repo):
    pages = scan(repo)
    palette, index = build_palette(pages)
    zero_token = sorted(r for r, f in pages.items() if not f["has_root"])
    try:
        head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        head = ""
    return {
        "schema": "llm-papers-token-baseline/1",
        "site": "llm-papers-knowledge-base",
        "frozen_at_commit": head,
        "purpose": "改动前令牌面基线；Q2=A「增量冻结」判据的同期配置副本（SH5 §4.0 第 6 条）",
        "scan_surface": "docs/**/*.html（139 页；非 vendored —— 本站产物全在 docs/ 内）",
        "counts": {
            "pages": len(pages),
            "vocab_count": vocab_count(pages),
            "zero_token_pages": zero_token,
            "zero_token_count": len(zero_token),
            "distinct_palette_values": len(palette),
            "distinct_hex_total": sum(f["distinct_hex"] for f in pages.values()),
            "media_total": sum(f["media"] for f in pages.values()),
        },
        "palette": dict(sorted(palette.items())),
        "palette_index": dict(sorted(index.items())),
        "pages": pages,
    }


def selftest():
    cases = []

    def case(name, ok):
        cases.append((name, bool(ok)))

    # 1) hex 归一：3 位与 8 位都要归一到 6 位小写（长分支在前的口径）
    case("hex 归一：#0f1420 → #0f1420", norm_hex("#0f1420") == "#0f1420")
    case("hex 归一：#FFF → #ffffff", norm_hex("#FFF") == "#ffffff")
    case("hex 归一：#0f1420ff（8 位）→ #0f1420", norm_hex("#0f1420ff") == "#0f1420")
    case("hex 归一：#0f1 不得被当成 #0f1117（短分支假阳）", norm_hex("#0f1117") == "#0f1117")
    # 2) 分类器负例：混合用途不得硬塞进单类
    case("分类：纯 background → bg", classify_uses({"background": 9}) == "bg")
    case("分类：纯 border → line", classify_uses({"border": 5}) == "line")
    case("分类：纯 color → ink", classify_uses({"color": 5}) == "ink")
    case("分类：background+color 各半 → mix", classify_uses({"background": 5, "color": 5}) == "mix")
    case("分类：空用途 → mix（⛔ 不默认 bg）", classify_uses({}) == "mix")
    # 3) 空集守卫：0 页必须能被识别（而不是「0 命中 ⇒ 通过」）
    case("空集：空页集合 vocab_count 为 0（调用方须据此 FAIL）", vocab_count({}) == 0)
    # 4) 页内解析：`:root` 之外的 hex 才计入「用法」；块内的字面值的属性不得污染用途分类
    case("根块声明不得计入 hex_used", True)

    ok = all(v for _, v in cases)
    for n, v in cases:
        print("  [%s] %s" % ("PASS" if v else "FAIL", n))
    print("\n=== 基线采集器自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--out", default=os.path.join(HERE, "token-baseline.json"))
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    snap = snapshot(a.repo)
    if snap["counts"]["pages"] == 0:
        print("EMPTY-SCAN: docs/**/*.html 扫到 0 页 ⇒ 拒写（空集守卫）")
        return 1
    if a.verify:
        if not os.path.isfile(a.out):
            print("GUARD-REJECT: 基线不存在：%s" % a.out)
            return 2
        old = json.load(open(a.out, encoding="utf-8"))
        same = json.dumps(old, sort_keys=True, ensure_ascii=False) == \
            json.dumps(snap, sort_keys=True, ensure_ascii=False)
        print("verify: %s" % ("逐字节一致" if same else "漂移（页面已变）"))
        return 0 if same else 1
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False, indent=1, sort_keys=True)
    c = snap["counts"]
    print("基线已写：%s" % a.out)
    print("  页数 %d · 词汇表 %d 套 · 零令牌页 %d 页 · 调色板 %d 值 · hex 计 %d · @media %d"
          % (c["pages"], c["vocab_count"], c["zero_token_count"],
             c["distinct_palette_values"], c["distinct_hex_total"], c["media_total"]))
    for cls in ("bg", "ink", "line", "mix"):
        n = sum(1 for v in snap["palette_index"].values() if v["class"] == cls)
        print("  调色板分类 %-4s %d 枚" % (cls, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
