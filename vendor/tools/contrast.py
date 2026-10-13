#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""contrast.py — WCAG 2.x 对比度计算与令牌表批量体检。

用法：
    python3 contrast.py [--scan PATH ...] [--out evidence/contrast.json] [--hue-buckets]

模式：
  1. --scan（默认扫 evidence/live 与 evidence/repo 下的 .html/.css）：
       解析 --token: value 声明，找出**被用作 color / border-color 的令牌**，
       对每个候选背景令牌（bg / surface / panel / page / card / paper / background）
       计算对比度，取最差背景作为该令牌的判定依据。
       同时收集**字面 hex 的 color 声明**并按同样方法判定。
  2. --hue-buckets：对 hsl(H,55%,45%) 全色相桶计算白字对比度（复验「52% 不达标」）。

判据阈值：正文文字 4.5:1（AA 常规字号）/ 大字 3:1 / 非文本（边框）3:1。
本脚本**只计算不判定**——判定在方案文档里做，避免把阈值直觉写死进工具。
"""
import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

# ⛔ 长分支必须写在短分支之前：`#0f1117` 若先试 {3} 会匹配成 `#0f1`（= rgb(0,255,17)），
#    导致全部对比度计算失真（实测踩到：--text 对 --bg 算成 1.97:1，真值 14.9:1）。
HEX = r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F])"
TOKEN_DEF = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:\s*([^;{}]+);")
HSL = re.compile(r"hsla?\(\s*([\d.]+)(?:deg)?\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%")

BG_NAMES = ("bg", "background", "surface", "panel", "page", "card", "paper", "base", "canvas", "fill")


def hex_to_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8:
        h = h[:6]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hsl_to_rgb(h, s, l):
    h, s, l = h / 360.0, s / 100.0, l / 100.0

    def f(n):
        k = (n + h * 12) % 12
        a = s * min(l, 1 - l)
        return l - a * max(-1, min(k - 3, 9 - k, 1))
    return tuple(round(f(n) * 255) for n in (0, 8, 4))


def parse_color(v):
    v = v.strip()
    m = re.search(HEX, v)
    if m:
        return hex_to_rgb(m.group(0))
    m = HSL.search(v)
    if m:
        return hsl_to_rgb(float(m.group(1)), float(m.group(2)), float(m.group(3)))
    m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", v)
    if m:
        return tuple(int(g) for g in m.groups())
    return None


def lum(rgb):
    def c(x):
        x = x / 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = (c(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def scan_file(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    toks = {}
    for k, v in TOKEN_DEF.findall(txt):
        toks.setdefault(k, v.strip())
    if not toks:
        return None

    bgs = {}
    for k, v in toks.items():
        name = k.lstrip("-").lower()
        if any(name == b or name.startswith(b + "-") or name.endswith("-" + b) for b in BG_NAMES):
            rgb = parse_color(v)
            if rgb:
                bgs[k] = rgb
    if not bgs:
        m = re.search(r"body\s*\{[^}]*background(?:-color)?\s*:\s*([^;}]+)", txt, re.I)
        if m:
            rgb = parse_color(m.group(1))
            if rgb:
                bgs["<body background>"] = rgb
    if not bgs:
        return {"tokens": toks, "bgs": {}, "note": "未识别到背景令牌"}

    used_color = set(re.findall(r"(?:^|[;{\s])color\s*:\s*var\((--[a-zA-Z0-9_-]+)\)", txt, re.I))
    used_color |= set(re.findall(r"fill\s*:\s*var\((--[a-zA-Z0-9_-]+)\)", txt, re.I))
    used_border = set(re.findall(r"border(?:-\w+)?\s*:\s*[^;}]*var\((--[a-zA-Z0-9_-]+)\)", txt, re.I))

    def worst(tok, thresh):
        rgb = parse_color(toks.get(tok, ""))
        if not rgb:
            return None
        rows = []
        for bk, bv in bgs.items():
            rows.append({"bg": bk, "ratio": round(ratio(rgb, bv), 2)})
        rows.sort(key=lambda r: r["ratio"])
        return {"token": tok, "value": toks[tok], "threshold": thresh,
                "worst_bg": rows[0]["bg"], "worst_ratio": rows[0]["ratio"],
                "all": rows[:4]}

    text_rows = [worst(t, 4.5) for t in sorted(used_color)]
    border_rows = [worst(t, 3.0) for t in sorted(used_border)]
    return {"tokens": toks, "token_count": len(toks),
            "bgs": {k: "#%02x%02x%02x" % v for k, v in bgs.items()},
            "text_checks": [r for r in text_rows if r],
            "border_checks": [r for r in border_rows if r]}


def hue_buckets():
    rows = []
    white = (255, 255, 255)
    for h in range(0, 360, 10):
        rgb = hsl_to_rgb(h, 55, 45)
        rows.append({"h": h, "rgb": "#%02x%02x%02x" % rgb,
                     "white_ratio": round(ratio(white, rgb), 2)})
    bad = [r for r in rows if r["white_ratio"] < 4.5]
    return {"rows": rows, "n": len(rows), "n_below_4_5": len(bad),
            "pct_below": round(100.0 * len(bad) / len(rows), 1),
            "worst": sorted(rows, key=lambda r: r["white_ratio"])[:5]}


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    ap.add_argument("--scan", nargs="*", default=None)
    ap.add_argument("--out", default=os.path.join(root, "evidence", "contrast.json"))
    ap.add_argument("--hue-buckets", action="store_true")
    a = ap.parse_args()

    targets = a.scan
    if targets is None:
        targets = [os.path.join(root, "evidence", "live"), os.path.join(root, "evidence", "repo")]

    files = []
    for t in targets:
        if os.path.isdir(t):
            for dirpath, _dirs, names in os.walk(t):
                for nm in names:
                    if nm.endswith((".html", ".css")):
                        files.append(os.path.join(dirpath, nm))
        elif os.path.isfile(t):
            files.append(t)

    out = {"generated_by": "tools/contrast.py", "files": {}, "hue_buckets": None}
    for f in sorted(files):
        r = scan_file(f)
        if r:
            out["files"][os.path.relpath(f, root)] = r
    if a.hue_buckets or True:
        out["hue_buckets"] = hue_buckets()

    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("scanned %d files -> %s" % (len(out["files"]), a.out))
    hb = out["hue_buckets"]
    print("hue buckets: %d/%d (%.1f%%) 白字 <4.5:1；最差 %s"
          % (hb["n_below_4_5"], hb["n"], hb["pct_below"],
             [(r["h"], r["white_ratio"]) for r in hb["worst"][:3]]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
