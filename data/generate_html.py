#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 papers_master.json + era_narratives.json，脚本驱动生成单文件 timeline.html。
零外部依赖（无CDN、离线可用），暗色科技风，含筛选/阅读路线/五时代区块/自检门控。"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).resolve().parent
BASE_DIR = DATA_DIR.parent
OUT_PATH = BASE_DIR / 'timeline.html'

master = json.loads((DATA_DIR / 'papers_master.json').read_text(encoding='utf-8'))
narratives = json.loads((DATA_DIR / 'era_narratives.json').read_text(encoding='utf-8'))
papers = master['papers']
ERAS = ['E1', 'E2', 'E3', 'E4', 'E5']
PRIS = ['P3', 'P2', 'P1']
assert all(e in narratives for e in ERAS), 'era_narratives.json 缺少时代键'

# 扫描 papers/ 下真实时代目录名（含中文），以 E<n>_ 前缀映射
era_dirs = {}
for d in (BASE_DIR / 'papers').iterdir():
    m = re.match(r'^(E\d)_', d.name)
    if d.is_dir() and m:
        era_dirs[m.group(1)] = d.name
assert all(e in era_dirs for e in ERAS), f'papers/ 缺少时代目录: {[e for e in ERAS if e not in era_dirs]}'


def esc(v):
    return html.escape(str(v)) if v is not None else ''


def pdf_rel(x):
    """存在则返回相对路径字符串，否则 None"""
    name = f"{x['d']}_{x['p']}_{x['slug']}.pdf"
    if (BASE_DIR / 'papers' / era_dirs[x['_era']] / name).exists():
        return f"papers/{era_dirs[x['_era']]}/{name}"
    return None


def anchor(x):
    return 'paper-' + (x['id'] if x.get('id') else x['slug'])


def res_html(x):
    rel = pdf_rel(x)
    parts = []
    if rel:
        parts.append(f'<a class="res-link pdf" href="{quote(rel, safe="/")}">本地PDF</a>')
    elif x.get('ext_url'):
        parts.append(f'<a class="res-link ext" href="{esc(x["ext_url"])}" target="_blank" rel="noopener">※无公开PDF·外部链接</a>')
    else:
        parts.append('<span class="res-none">※无公开PDF</span>')
    if x.get('code'):
        parts.append(f'<a class="res-link code" href="{esc(x["code"])}" target="_blank" rel="noopener">官方代码</a>')
    return '<div class="res">' + ' <span class="sep">|</span> '.join(parts) + '</div>'


def card_html(x):
    pri = x['p']
    rel = pdf_rel(x)
    idx_only = rel is None
    t = esc(x['t'])
    link = f"https://arxiv.org/abs/{x['id']}" if x.get('id') else (x.get('ext_url') or '')
    title_html = f'<a href="{esc(link)}" target="_blank" rel="noopener">{t}</a>' if link else t
    rows = ''.join(
        f'<tr><th>{lab}</th><td>{esc(x[k])}</td></tr>'
        for lab, k in (('当时主流', 'prev'), ('痛点', 'need'), ('为何胜出', 'win'), ('后续影响', 'imp')))
    cls = f'paper-card pri-{pri}' + (' index-only' if idx_only else '')
    return (
        f'<article class="{cls}" id="{anchor(x)}" data-era="{x["_era"]}" data-pri="{pri}">'
        f'<div class="card-top"><span class="date-badge">{esc(x["d"])}</span>'
        f'<span class="pri-badge">{pri}</span>'
        + ('<span class="idx-tag">仅索引</span>' if idx_only else '') +
        f'</div><h3 class="ptitle">{title_html}</h3>'
        f'<div class="org">{esc(x["org"])}</div>'
        f'<p class="contrib"><b>贡献：</b>{esc(x["c"])}</p>'
        f'<details><summary>展开背景档案</summary><div class="det-body">'
        f'<table class="archive">{rows}</table>{res_html(x)}</div></details></article>')


# ---------- 页头 ----------
dates = sorted(x['d'] for x in papers)
total = len(papers)
dl = sum(1 for x in papers if pdf_rel(x))
pc = {p: sum(1 for x in papers if x['p'] == p) for p in PRIS}
meta_dl = master.get('downloadable')
if meta_dl is not None and meta_dl != dl:
    print(f'[WARN] meta.downloadable={meta_dl} 与实际本地PDF数 {dl} 不一致（以实测为准）')

header_html = (
    '<header class="page-head"><h1>现代大语言模型发展史 · 关键节点论文时间线</h1>'
    f'<p class="sub">{dates[0]} → {dates[-1]} · {total} 个关键节点</p>'
    '<div class="stat-badges">'
    f'<span class="sb">总计 <b>{total}</b> 篇</span>'
    f'<span class="sb">本地PDF <b>{dl}</b></span>'
    f'<span class="sb p3c">P3 <b>{pc["P3"]}</b></span>'
    f'<span class="sb p2c">P2 <b>{pc["P2"]}</b></span>'
    f'<span class="sb p1c">P1 <b>{pc["P1"]}</b></span>'
    '</div></header>')

# ---------- 筛选工具栏 ----------
short = {e: narratives[e]['title'].split('：')[0] for e in ERAS}
era_btns = '<button class="fbtn on" data-era="all">全部</button>' + ''.join(
    f'<button class="fbtn" data-era="{e}">{esc(short[e])}</button>' for e in ERAS)
pri_btns = '<button class="fbtn on" data-pri="all">全部</button>' + ''.join(
    f'<button class="fbtn" data-pri="{p}">{p}</button>' for p in PRIS)
nav_html = (f'<nav class="toolbar"><div class="fgroup" id="fEra"><span class="flabel">时代</span>{era_btns}</div>'
            f'<div class="fgroup" id="fPri"><span class="flabel">优先级</span>{pri_btns}</div></nav>')

# ---------- 阅读路线 ----------
p3 = sorted((x for x in papers if x['p'] == 'P3'), key=lambda x: x['d'])
route_lis = ''.join(
    f'<li><a href="#{anchor(x)}"><span class="num">{i:02d}</span>'
    f'<span class="rd">{esc(x["d"])}</span><span class="rt">{esc(x["t"])}</span></a></li>'
    for i, x in enumerate(p3, 1))
route_html = (f'<section class="route-card"><div class="route-head"><h2>P3 先行 · {len(p3)} 篇主线故事</h2>'
              f'<p>按时间升序通读即掌握领域主干，点击任意条目跳转对应论文卡</p></div>'
              f'<ol class="route-list">{route_lis}</ol></section>')

# ---------- 五个时代区块 ----------
era_secs = []
for ei, ek in enumerate(ERAS, 1):
    meta = narratives[ek]
    eps = sorted((x for x in papers if x['_era'] == ek), key=lambda x: x['d'])
    cards = ''.join(card_html(x) for x in eps)
    era_secs.append(
        f'<section class="eb era-block era-{ek}" id="era-{ek}">'
        f'<div class="era-head"><span class="era-num">{ei:02d}</span>'
        f'<div class="era-txt"><h2>{esc(meta["title"])}</h2><p>{esc(meta["text"])}</p></div></div>'
        f'<div class="card-grid">{cards}</div></section>')
main_html = '\n'.join(era_secs)

# ---------- 页脚 ----------
nv = sum(1 for x in papers if x.get('conf') == 'verified')
nc = sum(1 for x in papers if x.get('conf') == 'cited')
footer_html = (
    f'<footer class="page-foot"><p>数据口径：verified=联网一手核验 {nv} 篇 · cited=高置信知识库 {nc} 篇（共 {nv + nc} 篇）；'
    f'本地PDF {dl} 篇 · 仅索引 {total - dl} 篇（提供外部链接）。</p>'
    f'<p>生成日期：{date.today().isoformat()} · 由 data/generate_html.py 脚本驱动生成，禁止手抄数据</p></footer>')

CSS = '''
:root{--bg:#0b0f14;--panel:#11161d;--bd:#232b36;--tx:#dbe4ee;--mut:#7d8b9d;--acc:#4cc2ff;
--gold:#e8b93e;--bg1:#7fa3c9;--e1:#58a6ff;--e2:#3fb950;--e3:#bc8cff;--e4:#f0883e;--e5:#f85149}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--tx);line-height:1.65;
font-family:system-ui,-apple-system,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.mono{font-family:ui-monospace,Consolas,monospace}
.page-head{text-align:center;padding:48px 16px 30px;
background:radial-gradient(ellipse 80% 65% at 50% -10%,#12304a66,transparent),linear-gradient(180deg,#0e141b,var(--bg))}
.page-head h1{font-size:clamp(22px,3.4vw,34px);letter-spacing:.02em;
background:linear-gradient(90deg,#9ecbff,#eef6ff 45%,#7fd4ff);-webkit-background-clip:text;background-clip:text;color:transparent}
.page-head .sub{color:var(--mut);margin-top:8px;font-family:ui-monospace,Consolas,monospace;font-size:14px}
.stat-badges{margin-top:18px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.sb{border:1px solid var(--bd);background:var(--panel);border-radius:999px;padding:4px 14px;font-size:13px;color:var(--mut)}
.sb b{color:var(--tx)}.sb.p3c b{color:var(--gold)}.sb.p2c b{color:var(--bg1)}.sb.p1c b{color:#9aa7b5}
.toolbar{position:sticky;top:0;z-index:60;display:flex;gap:20px;flex-wrap:wrap;justify-content:center;align-items:center;
padding:10px 16px;background:#0d1219f2;backdrop-filter:blur(8px);border-bottom:1px solid var(--bd)}
.fgroup{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.flabel{font-size:12px;color:var(--mut);letter-spacing:.14em}
.fbtn{background:var(--panel);border:1px solid var(--bd);color:var(--mut);border-radius:999px;padding:4px 14px;font-size:13px;cursor:pointer;transition:.15s}
.fbtn:hover{color:var(--tx);border-color:#3b4757}
.fbtn.on{color:#0b0f14;background:var(--acc);border-color:var(--acc);font-weight:700}
.route-card{max-width:1180px;margin:26px auto 0;padding:18px 20px;
background:linear-gradient(135deg,#141c27,#101722);border:1px solid var(--bd);border-radius:14px}
.route-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:12px}
.route-head h2{font-size:17px;color:var(--gold)}.route-head p{font-size:12.5px;color:var(--mut)}
.route-list{list-style:none;display:flex;flex-wrap:wrap;gap:8px}
.route-list li a{display:inline-flex;gap:7px;align-items:center;border:1px solid #2a3542;background:#131b26;border-radius:999px;
padding:3px 12px 3px 5px;font-size:12.5px;color:#b9c6d6;max-width:340px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.route-list li a:hover{border-color:var(--gold);text-decoration:none;color:#fff}
.route-list .num{display:inline-flex;width:22px;height:22px;border-radius:50%;background:var(--gold);color:#14100a;
font-weight:700;align-items:center;justify-content:center;font-size:11px;flex:none}
.route-list .rd{font-family:ui-monospace,Consolas,monospace;color:var(--mut);flex:none}
.route-list .rt{overflow:hidden;text-overflow:ellipsis}
.eb{max-width:1180px;margin:36px auto 0;padding:0 20px}
.era-E1{--ec:var(--e1)}.era-E2{--ec:var(--e2)}.era-E3{--ec:var(--e3)}.era-E4{--ec:var(--e4)}.era-E5{--ec:var(--e5)}
.era-head{border-left:6px solid var(--ec,var(--acc));background:linear-gradient(90deg,#121823aa,transparent);
padding:16px 18px;border-radius:0 12px 12px 0;display:flex;gap:18px;align-items:flex-start}
.era-num{font-size:44px;font-weight:800;line-height:1;color:var(--ec);opacity:.9;
font-family:ui-monospace,Consolas,monospace;flex:none}
.era-txt h2{font-size:19px}.era-txt p{margin-top:8px;color:#a7b4c4;font-size:14px;text-align:justify}
.card-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:16px}
@media(max-width:880px){.card-grid{grid-template-columns:1fr}.era-num{font-size:32px}}
.paper-card{background:var(--panel);border:1px solid var(--bd);border-radius:12px;padding:14px 16px;
transition:border-color .15s,transform .15s,box-shadow .15s;scroll-margin-top:130px}
.paper-card:hover{border-color:#3d4c60;transform:translateY(-2px);box-shadow:0 6px 18px #00000055}
.paper-card.index-only{border-style:dashed;background:#10151c}
.hidden{display:none!important}
.card-top{display:flex;gap:8px;align-items:center;margin-bottom:8px}
.date-badge{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#cddaea;background:#2c3a4d;border-radius:6px;padding:1px 8px;font-weight:600}
.pri-badge{font-size:11.5px;font-weight:700;border-radius:6px;padding:1px 8px;border:1px solid}
.pri-P3 .pri-badge{color:var(--gold);border-color:var(--gold);background:#e8b93e14;box-shadow:0 0 8px #e8b93e33}
.pri-P2 .pri-badge{color:var(--bg1);border-color:#3d5a78;background:#7fa3c914}
.pri-P1 .pri-badge{color:#8b98a8;border-color:#37424f;background:#8b98a80f}
.idx-tag{margin-left:auto;font-size:11px;color:var(--mut);border:1px dashed #3a4553;border-radius:6px;padding:1px 7px}
.ptitle{font-size:15.5px;line-height:1.45}.ptitle a{color:#eaf2fb}.ptitle a:hover{color:var(--acc)}
.org{margin-top:4px;font-size:12.5px;color:var(--mut)}
.contrib{margin-top:8px;font-size:13.5px;color:#c3cedb}.contrib b{color:var(--acc)}
details{margin-top:10px;border-top:1px dashed var(--bd);padding-top:8px}
details summary{cursor:pointer;font-size:12.5px;color:var(--mut);user-select:none;list-style:none}
details summary::-webkit-details-marker{display:none}
details summary::before{content:"\\25B8 ";color:var(--acc)}
details[open] summary::before{content:"\\25BE "}
details summary:hover{color:var(--tx)}
.det-body{animation:detIn .22s ease}
@keyframes detIn{from{opacity:0;transform:translateY(-5px)}to{opacity:1;transform:none}}
table.archive{width:100%;border-collapse:collapse;margin-top:8px;font-size:12.5px}
table.archive th{width:74px;text-align:left;color:var(--mut);font-weight:600;vertical-align:top;padding:4px 8px 4px 0;white-space:nowrap}
table.archive td{color:#b6c2d0;padding:4px 0;border-bottom:1px solid #1a222d}
table.archive tr:last-child td{border-bottom:none}
.res{margin-top:9px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12.5px}
.res .sep{color:#33404f}
.res-link{border:1px solid var(--bd);border-radius:6px;padding:2px 10px;background:#151c26}
.res-link.pdf{color:#7fd4a6;border-color:#2b4636}
.res-link.ext{color:#f0b26a;border-color:#4d3c22}
.res-link.code{color:#9db8e8;border-color:#2c3a52}
.res-link:hover{text-decoration:none;filter:brightness(1.25)}
.res-none{color:var(--mut)}
.page-foot{margin-top:46px;padding:26px 16px 42px;text-align:center;color:var(--mut);font-size:12.5px;
border-top:1px solid var(--bd);background:#0d1219}
.page-foot p{margin:3px 0}
'''

JS = '''
(function(){
"use strict";
function $$(s,c){return Array.prototype.slice.call((c||document).querySelectorAll(s));}
var curEra="all",curPri="all";
function syncBtns(){
  $$("#fEra .fbtn").forEach(function(b){b.classList.toggle("on",b.dataset.era===curEra);});
  $$("#fPri .fbtn").forEach(function(b){b.classList.toggle("on",b.dataset.pri===curPri);});
}
function applyF(){
  $$(".paper-card").forEach(function(c){
    var ok=(curEra==="all"||c.dataset.era===curEra)&&(curPri==="all"||c.dataset.pri===curPri);
    c.classList.toggle("hidden",!ok);
  });
  $$(".eb").forEach(function(sec){
    var vis=$$(".paper-card",sec).some(function(c){return !c.classList.contains("hidden");});
    sec.classList.toggle("hidden",!vis);
  });
}
$$("#fEra .fbtn").forEach(function(b){b.addEventListener("click",function(){curEra=b.dataset.era;syncBtns();applyF();});});
$$("#fPri .fbtn").forEach(function(b){b.addEventListener("click",function(){curPri=b.dataset.pri;syncBtns();applyF();});});
$$(".route-list a").forEach(function(a){a.addEventListener("click",function(){
  if(curEra!=="all"||curPri!=="all"){curEra="all";curPri="all";syncBtns();applyF();}
});});
})();
'''

doc = (
    '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    '<title>现代大语言模型发展史 · 关键节点论文时间线</title>\n'
    f'<style>{CSS}</style>\n</head>\n<body>\n'
    + header_html + '\n' + nav_html + '\n' + route_html + '\n' + main_html
    + '\n' + footer_html + f'\n<script>{JS}</script>\n</body>\n</html>\n')

OUT_PATH.write_text(doc, encoding='utf-8')
print(f'[WRITE] {OUT_PATH}')

# ================= 自检门控 =================
raw = OUT_PATH.read_bytes()
text = raw.decode('utf-8')
results = []

r1 = '\ufffd' not in text
results.append(('utf-8 解码无 U+FFFD 替换字符', r1))

nd_open, nd_close = text.count('<div'), text.count('</div>')
results.append((f'div 平衡: <div>={nd_open} </div>={nd_close}', nd_open == nd_close and nd_open > 0))

n_card = text.count('paper-card')
results.append((f'"paper-card" 出现 {n_card} 次 (要求>=98)', n_card >= 98))
n_eb = text.count('era-block')
results.append((f'"era-block" 出现 {n_eb} 次 (要求==5)', n_eb == 5))
narr_ok = all(narratives[e]['text'].strip() and html.escape(narratives[e]['text']) in text for e in ERAS)
results.append(('五个时代 narrative 段落均非空且存在', narr_ok))

size_kb = len(raw) / 1024
results.append((f'文件大小 {size_kb:.1f} KB (上限 300KB)', len(raw) <= 300 * 1024))

all_pass = True
for name, ok in results:
    print(f'  [{"PASS" if ok else "FAIL"}] {name}')
    all_pass = all_pass and ok

print(f'  卡片数实测: {text.count(chr(34) + "paper-card") and n_card}, P3路线 {len(p3)} 条, '
      f'verified {nv} / cited {nc}')
print('[GATE] ' + ('ALL PASS' if all_pass else 'FAILED'))
sys.exit(0 if all_pass else 1)
