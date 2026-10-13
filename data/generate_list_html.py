#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 data/papers_master.json + era_narratives.json，生成 docs/list.html 卡片列表视图。
与 timeline.html（泳道图）互切，供逐篇检索细节。零外部依赖，暗色科技风。
"""
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).resolve().parent
BASE_DIR = DATA_DIR.parent
OUT_PATH = BASE_DIR / 'docs' / 'list.html'

# ★ 批 J：站点级常量 ＋ 无障碍样式。⛔ 下列 CSS 一个色值字面量都没有——本站
#   gate_tokens.py 的 G3（Q3=A 等值注入）硬判「不得出现改动前基线之外的新色值」，
#   故用 currentColor ＋ 系统色 Canvas/CanvasText（可见焦点环 ＋ 可读 skip link）。
REPO_NAME = 'llm-papers-knowledge-base'
BASE_URL = 'https://zako-mio.github.io/%s/' % REPO_NAME
A11Y_CSS = '''
:focus-visible{outline:2px solid currentColor;outline-offset:2px}
.skip-link{position:absolute;left:-9999px;top:0;z-index:100;padding:0.5rem 1rem;
  background:Canvas;color:CanvasText;border:1px solid CanvasText;border-radius:0 0 6px 0}
.skip-link:focus{left:0}
'''

master = json.loads((DATA_DIR / 'papers_master.json').read_text(encoding='utf-8'))
narratives = json.loads((DATA_DIR / 'era_narratives.json').read_text(encoding='utf-8'))
papers = master['papers']
ERAS = ['E1', 'E2', 'E3', 'E4', 'E5']
PRIS = ['P3', 'P2', 'P1']

era_dirs = {}
for d in (BASE_DIR / 'papers').iterdir():
    m = re.match(r'^(E\d)_', d.name)
    if d.is_dir() and m:
        era_dirs[m.group(1)] = d.name


def esc(v):
    return html.escape(str(v)) if v is not None else ''


def pdf_github_url(x):
    name = f"{x['d']}_{x['p']}_{x['slug']}.pdf"
    repo = 'zako-mio/llm-papers-knowledge-base'
    path = quote(f"papers/{era_dirs[x['_era']]}/{name}", safe='/')
    return f"https://media.githubusercontent.com/media/{repo}/main/{path}"


def analysis_html(x):
    batch = {'P3': 'B1_P3', 'P2': 'B2_P2', 'P1': 'B3_P1'}[x['p']]
    rel = f"analysis/{batch}/{x['slug']}/03-深度解读报告.html"
    if (BASE_DIR / 'docs' / 'analysis' / batch / x['slug'] / '03-深度解读报告.html').exists():
        return rel
    return None


def anchor(x):
    return 'paper-' + (x['id'] if x.get('id') else x['slug'])


def res_html(x):
    parts = []
    parts.append(f'<a class="res-link pdf" href="{pdf_github_url(x)}" target="_blank" rel="noopener">PDF下载</a>')
    if x.get('code'):
        parts.append(f'<a class="res-link code" href="{esc(x["code"])}" target="_blank" rel="noopener">官方代码</a>')
    an = analysis_html(x)
    if an:
        parts.append(f'<a class="res-link analysis" href="{quote(an, safe="/")}">深度解读</a>')
    # 技术线徽章
    line = x.get('line', '')
    lanename = {'arch': '架构', 'pretrain': '预训练', 'align': '对齐', 'reason': '推理',
                'longctx': '长上下文', 'multi': '多模态', 'agent': 'Agent', 'eng': '工程',
                'opensrc': '开源'}.get(line, '')
    if lanename:
        parts.append(f'<span class="res-link lane-chip">{lanename}</span>')
    return '<div class="res">' + ' <span class="sep">|</span> '.join(parts) + '</div>'


def card_html(x):
    pri = x['p']
    t = esc(x['t'])
    link = f"https://arxiv.org/abs/{x['id']}" if x.get('id') else (x.get('ext_url') or '')
    title_html = f'<a href="{esc(link)}" target="_blank" rel="noopener">{t}</a>' if link else t
    rows = ''.join(
        f'<tr><th>{lab}</th><td>{esc(x[k])}</td></tr>'
        for lab, k in (('当时主流', 'prev'), ('痛点', 'need'), ('为何胜出', 'win'), ('后续影响', 'imp')))
    return (
        f'<article class="paper-card pri-{pri}" id="{anchor(x)}" data-era="{x["_era"]}" data-pri="{pri}">'
        f'<div class="card-top"><span class="date-badge">{esc(x["d"])}</span>'
        f'<span class="pri-badge">{pri}</span>'
        f'</div><h3 class="ptitle">{title_html}</h3>'
        f'<div class="org">{esc(x["org"])}</div>'
        f'<p class="contrib"><b>贡献：</b>{esc(x["c"])}</p>'
        f'<details><summary>展开背景档案</summary><div class="det-body">'
        f'<table class="archive">{rows}</table>{res_html(x)}</div></details></article>')


dates = sorted(x['d'] for x in papers)
total = len(papers)
pc = {p: sum(1 for x in papers if x['p'] == p) for p in PRIS}
dl = sum(1 for x in papers if (BASE_DIR / 'papers' / era_dirs[x['_era']] / f"{x['d']}_{x['p']}_{x['slug']}.pdf").exists())

header_html = (
    '<header class="page-head"><h1>现代大语言模型发展史 · 关键节点论文列表</h1>'
    f'<p class="sub">{dates[0]} → {dates[-1]} · {total} 个关键节点</p>'
    '<div class="stat-badges">'
    f'<span class="sb">总计 <b>{total}</b></span><span class="sb">本地PDF <b>{dl}</b></span>'
    f'<span class="sb p3c">P3 <b>{pc["P3"]}</b></span><span class="sb p2c">P2 <b>{pc["P2"]}</b></span>'
    f'<span class="sb p1c">P1 <b>{pc["P1"]}</b></span>'
    '</div></header>')

# 视图切换按钮
view_switch = ('<div class="view-switch"><a href="timeline.html">🛤️ 泳道图视图</a>'
               '<span class="cur">📋 当前：卡片列表视图</span></div>')

# 筛选栏
short = {e: narratives[e]['title'].split('：')[0] for e in ERAS}
era_btns = '<button class="fbtn on" data-era="all">全部</button>' + ''.join(
    f'<button class="fbtn" data-era="{e}">{esc(short[e])}</button>' for e in ERAS)
pri_btns = '<button class="fbtn on" data-pri="all">全部</button>' + ''.join(
    f'<button class="fbtn" data-pri="{p}">{p}</button>' for p in PRIS)
nav_html = (f'<nav class="toolbar"><div class="fgroup" id="fEra"><span class="flabel">时代</span>{era_btns}</div>'
            f'<div class="fgroup" id="fPri"><span class="flabel">优先级</span>{pri_btns}</div></nav>')

# P3 先行路线
p3 = sorted((x for x in papers if x['p'] == 'P3'), key=lambda x: x['d'])
route_lis = ''.join(
    f'<li><a href="#{anchor(x)}"><span class="num">{i:02d}</span>'
    f'<span class="rd">{esc(x["d"])}</span><span class="rt">{esc(x["t"])}</span></a></li>'
    for i, x in enumerate(p3, 1))
route_html = (f'<section class="route-card"><div class="route-head"><h2>P3 先行 · {len(p3)} 篇主线故事</h2>'
              f'<p>按时间升序通读即掌握领域主干，点击跳转</p></div>'
              f'<ol class="route-list">{route_lis}</ol></section>')

# 五时代区块
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

nv = sum(1 for x in papers if x.get('conf') == 'verified')
nc = sum(1 for x in papers if x.get('conf') == 'cited')
footer_html = (
    f'<footer class="page-foot"><p>数据口径：verified=联网一手核验 {nv} 篇 · cited=高置信知识库 {nc} 篇（共 {total} 篇）；'
    f'本地PDF {dl} 篇 · 仅索引 {total - dl} 篇。</p>'
    f'<p>生成日期：由 data/generate_list_html.py 驱动 · 与时序图 timeline.html 互切</p></footer>')

CSS = '''
:root{--bg:#0b0f14;--panel:#11161d;--bd:#232b36;--tx:#dbe4ee;--mut:#7d8b9d;--acc:#4cc2ff;
--gold:#e8b93e;--bg1:#7fa3c9;--e1:#58a6ff;--e2:#3fb950;--e3:#bc8cff;--e4:#f0883e;--e5:#f85149}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);line-height:1.65;
font-family:system-ui,-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.page-head{text-align:center;padding:42px 16px 24px;
background:radial-gradient(ellipse 80% 65% at 50% -10%,#12304a66,transparent),linear-gradient(180deg,#0e141b,var(--bg))}
.page-head h1{font-size:clamp(22px,3.2vw,32px);letter-spacing:.02em;
background:linear-gradient(90deg,#9ecbff,#eef6ff 45%,#7fd4ff);-webkit-background-clip:text;background-clip:text;color:transparent}
.page-head .sub{color:var(--mut);margin-top:8px;font-family:ui-monospace,Consolas,monospace;font-size:13px}
.stat-badges{margin-top:14px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.sb{border:1px solid var(--bd);background:var(--panel);border-radius:999px;padding:4px 14px;font-size:13px;color:var(--mut)}
.sb b{color:var(--tx)}.sb.p3c b{color:var(--gold)}.sb.p2c b{color:var(--bg1)}.sb.p1c b{color:#9aa7b5}
.view-switch{max-width:1180px;margin:18px auto 0;padding:0 20px;display:flex;gap:12px;align-items:center;justify-content:center;flex-wrap:wrap}
.view-switch a{border:1px solid var(--acc);color:var(--acc);border-radius:99px;padding:6px 20px;font-size:13px;font-weight:600;background:var(--acc)14}
.view-switch .cur{color:var(--mut);font-size:12.5px;border:1px dashed var(--bd);border-radius:99px;padding:6px 16px}
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
.era-num{font-size:42px;font-weight:800;line-height:1;color:var(--ec);opacity:.9;
font-family:ui-monospace,Consolas,monospace;flex:none}
.era-txt h2{font-size:19px}.era-txt p{margin-top:8px;color:#a7b4c4;font-size:14px;text-align:justify}
.card-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:16px}
@media(max-width:880px){.card-grid{grid-template-columns:1fr}.era-num{font-size:30px}}
.paper-card{background:var(--panel);border:1px solid var(--bd);border-radius:12px;padding:14px 16px;
transition:border-color .15s,transform .15s,box-shadow .15s}
.paper-card:hover{border-color:#3d4c60;transform:translateY(-2px);box-shadow:0 6px 18px #00000055}
.hidden{display:none!important}
.card-top{display:flex;gap:8px;align-items:center;margin-bottom:8px}
.date-badge{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#cddaea;background:#2c3a4d;border-radius:6px;padding:1px 8px;font-weight:600}
.pri-badge{font-size:11.5px;font-weight:700;border-radius:6px;padding:1px 8px;border:1px solid}
.pri-P3 .pri-badge{color:var(--gold);border-color:var(--gold);background:#e8b93e14;box-shadow:0 0 8px #e8b93e33}
.pri-P2 .pri-badge{color:var(--bg1);border-color:#3d5a78;background:#7fa3c914}
.pri-P1 .pri-badge{color:#8b98a8;border-color:#37424f;background:#8b98a80f}
.ptitle{font-size:15px;line-height:1.45}.ptitle a{color:#eaf2fb}.ptitle a:hover{color:var(--acc)}
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
.res-link.code{color:#9db8e8;border-color:#2c3a52}
.res-link.analysis{color:#c084fc;border-color:#4a2f6b;font-weight:600}
.res-link.lane-chip{color:#79c0ff;border-color:#2c3a52;background:#0f1a24}
.res-link:hover{text-decoration:none;filter:brightness(1.25)}
.page-foot{margin-top:46px;padding:26px 16px 42px;text-align:center;color:var(--mut);font-size:12px;
border-top:1px solid var(--bd);background:#0d1219}
.page-foot p{margin:3px 0}
''' + A11Y_CSS

DESC = ('现代大语言模型发展史 · 关键节点论文列表视图：{total} 个关键节点按五个时代分组、'
        '逐篇卡片呈现标题/机构/贡献/背景档案，可按时代与优先级筛选，与泳道图一键互切。'
        .format(total=total))

html_out = (
    f'<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
    f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    f'<title>现代大语言模型发展史 · 关键节点论文列表</title>\n'
    f'<meta name="description" content="{DESC}">\n'
    f'<meta property="og:type" content="website">\n'
    f'<meta property="og:title" content="现代大语言模型发展史 · 关键节点论文列表">\n'
    f'<meta property="og:description" content="{DESC}">\n'
    f'<meta property="og:url" content="{BASE_URL}list.html">\n'
    f'<meta property="og:image" content="{BASE_URL}og.png">\n'
    f'<link rel="canonical" href="{BASE_URL}list.html">\n'
    f'<link rel="icon" type="image/svg+xml" href="favicon.svg">\n'
    f'<style>{CSS}</style>\n</head>\n<body>\n'
    f'<a class="skip-link" href="#main">跳到主要内容</a>\n'
    f'{header_html}\n{view_switch}\n{nav_html}\n'
    f'<main id="main">\n{route_html}\n{main_html}\n</main>\n{footer_html}\n'
    '<script>\n'
    'function $$(s,c){return Array.prototype.slice.call((c||document).querySelectorAll(s));}\n'
    'var curEra="all",curPri="all";\n'
    'function syncBtns(){$$("#fEra .fbtn").forEach(function(b){b.classList.toggle("on",b.dataset.era===curEra);});'
    '$$("#fPri .fbtn").forEach(function(b){b.classList.toggle("on",b.dataset.pri===curPri);});}\n'
    'function applyF(){$$(".paper-card").forEach(function(c){var ok=(curEra==="all"||c.dataset.era===curEra)&&(curPri==="all"||c.dataset.pri===curPri);c.classList.toggle("hidden",!ok);});'
    '$$(".era-block").forEach(function(sec){var vis=$$(".paper-card",sec).some(function(c){return !c.classList.contains("hidden");});sec.style.display=vis?"":"none";});}\n'
    '$$("#fEra .fbtn").forEach(function(b){b.addEventListener("click",function(){curEra=b.dataset.era;syncBtns();applyF();});});\n'
    '$$("#fPri .fbtn").forEach(function(b){b.addEventListener("click",function(){curPri=b.dataset.pri;syncBtns();applyF();});});\n'
    '</script>\n</body>\n</html>\n'
)

OUT_PATH.write_text(html_out, encoding='utf-8')
print('已生成', OUT_PATH)
print('篇数:', total, '| P3:', pc["P3"], 'P2:', pc["P2"], 'P1:', pc["P1"])
