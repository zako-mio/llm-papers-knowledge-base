#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 data/papers_lanes.json，生成 docs/timeline.html 【转置泳道图】。
布局（相对原横向版做了 X/Y 转置）：
- 左侧固定列 = 自适应时间纵轴（按节点密度分段），sticky left
- 顶部固定行 = 9 条技术线横轴（泳道标签+图例），sticky top
- 左上角 = 十字双轴 sticky（left+top 固定）
- 中间 = 节点卡片 + 关系线画布，随 body 原生滚动（上下为主看时间）
- 图例即筛选器（多选）+ 图例点击联动高亮关系线（技术线+关系类型双图例）
- 节点保留全部交互（悬停完整信息 / 点击深度解读+高亮）
- 原生 JS + SVG，零外部依赖、自包含
"""
import html
import json
import sys
from pathlib import Path
from urllib.parse import quote

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).resolve().parent
BASE_DIR = DATA_DIR.parent
OUT_PATH = BASE_DIR / 'docs' / 'timeline.html'

DATA = json.loads((DATA_DIR / 'papers_lanes.json').read_text(encoding='utf-8'))
lanes = DATA['lanes']

# 9 条技术线（顺序即顶部横轴从左到右）
LANE_DEF = [
    {'key': 'arch',     'name': '架构革命',       'color': '#58a6ff', 'desc': 'Transformer/注意力变体/稀疏·线性/SSM'},
    {'key': 'pretrain', 'name': '预训练与Scaling', 'color': '#3fb950', 'desc': '预训练目标/缩放定律/数据/涌现'},
    {'key': 'align',    'name': '对齐与后训练',     'color': '#bc8cff', 'desc': 'RLHF/DPO/指令微调/安全'},
    {'key': 'reason',   'name': '推理与测试时计算', 'color': '#f0883e', 'desc': 'CoT/长思维链/test-time/RL推理'},
    {'key': 'longctx',  'name': '长上下文与效率',   'color': '#7fd4ae', 'desc': '位置编码/KV压缩/量化/长窗口'},
    {'key': 'multi',    'name': '多模态',           'color': '#d2a8ff', 'desc': '视觉·图文/VLM/原生多模态'},
    {'key': 'agent',    'name': 'Agent与工具',      'color': '#f85149', 'desc': '工具调用/行动推理/Agentic'},
    {'key': 'eng',      'name': '工程与部署',       'color': '#e8b93e', 'desc': '训练并行/推理服务/分发压缩'},
    {'key': 'opensrc',  'name': '开源生态与旗舰',   'color': '#79c0ff', 'desc': '开源权重/旗舰模型/生态影响'},
]
LANE_BY_KEY = {l['key']: l for l in LANE_DEF}
LANE_KEYS = [l['key'] for l in LANE_DEF]
# 关系类型
REL_DEF = [
    {'key': 'found',   'name': '奠基', 'color': '#3fb950'},
    {'key': 'inherit', 'name': '继承', 'color': '#58a6ff'},
    {'key': 'branch',  'name': '分支', 'color': '#bc8cff'},
    {'key': 'compete', 'name': '竞争', 'color': '#f85149'},
]

PRIS = ['P3', 'P2', 'P1']
batch_of = lambda p: 'B1_P3' if p == 'P3' else ('B2_P2' if p == 'P2' else 'B3_P1')


def esc(v):
    return html.escape(str(v)) if v is not None else ''


# ---- 缩略别名 ----
def short_name(n):
    slug = n.get('slug', '')
    t = n.get('t', '')
    known = {
        'Attention_Is_All_You_Need': 'Attention', 'BERT': 'BERT',
        'GPT-1': 'GPT-1', 'GPT-2': 'GPT-2', 'GPT-3_Few-Shot_Learners': 'GPT-3',
        'GPT-4_Technical_Report': 'GPT-4', 'GPT-5_System_Card': 'GPT-5',
        'Kaplan_Scaling_Laws': 'Scaling Laws', 'Chinchilla': 'Chinchilla',
        'InstructGPT_RLHF': 'InstructGPT', 'Chain-of-Thought': 'CoT', 'DPO': 'DPO',
        'CLIP': 'CLIP', 'ViT': 'ViT', 'FlashAttention': 'FlashAttn',
        'FlashAttention-2': 'FlashAttn-2', 'FlashAttention-3': 'FlashAttn-3',
        'RoPE_RoFormer': 'RoPE', 'ALiBi': 'ALiBi', 'ReAct': 'ReAct',
        'Mamba': 'Mamba', 'Mamba-2': 'Mamba-2', 'DeepSeek-V3': 'DS-V3',
        'DeepSeek-R1': 'DS-R1', 'DeepSeek-V4': 'DS-V4', 'vLLM_PagedAttention': 'vLLM',
        'LLaMA': 'LLaMA', 'LLaMA_2': 'Llama-2', 'Llama_3': 'Llama-3', 'Llama_4': 'Llama-4',
        'LoRA': 'LoRA', 'Switch_Transformers': 'Switch', 'Kimi_K2': 'Kimi K2',
        'Kimi_K3': 'Kimi K3', 'GLM-4.5': 'GLM-4.5', 'GLM-5': 'GLM-5',
        'o1_Learning_to_Reason': 'o1', 'GQA': 'GQA', 'MQA': 'MQA', 'LLaVA': 'LLaVA',
        'Qwen2': 'Qwen2', 'Qwen2.5': 'Qwen2.5', 'Qwen3': 'Qwen3', 'Mixtral': 'Mixtral',
        'GRPO_DeepSeekMath': 'GRPO', 'DeepSeek-V2_MLA': 'DS-V2 MLA', 'DeepSeekMoE': 'DS-MoE',
        'RAG': 'RAG', 'T5': 'T5', 'FLAN': 'FLAN', 'Constitutional_AI': 'CAI',
        'Self-Instruct': 'Self-Instr', 'Toolformer': 'Toolformer', 'Tree_of_Thoughts': 'ToT',
        'Self-Consistency': 'Self-Con', 'Gemini_Technical_Report': 'Gemini',
        'Gemini_2.5_Report': 'Gemini 2.5', 'Claude_Opus_4.5_System_Card': 'Opus 4.5',
        'MiniMax-01': 'MiniMax-01', 'MiniMax-M1': 'MiniMax-M1', 'MiniMax-M2_Series': 'MiniMax-M2',
        'Qwen3.5': 'Qwen3.5', 'Qwen3.5-Omni': 'Qwen3.5-Omni', 'Qwen3.6-35B': 'Qwen3.6',
        'Thinking_with_Visual_Primitives': 'VisPrimitives', 'StreamingLLM': 'StreamingLLM',
        'H2O': 'H2O', 'AWQ': 'AWQ', 'GPTQ': 'GPTQ', 'Grokking': 'Grokking',
        'DeepSeek-OCR': 'DS-OCR', 'Kimi_Linear': 'Kimi Linear', 'DeepSpeed': 'DeepSpeed',
        'Megatron_LM': 'Megatron', 'GShard': 'GShard', 'Sparse_Transformers': 'Sparse Attn',
        'Scaling_TestTime_Compute': 'TTC Scaling', 'mHC': 'mHC', 'GLM-5.3': 'GLM-5.3',
        'GLM-5.2': 'GLM-5.2', 'GLM-5.1': 'GLM-5.1', 'GLM-5.3-Flash': 'GLM-5.3-Flash',
        'NSA': 'NSA', 'MoBA': 'MoBA', 'Forge_RL_Framework': 'Forge',
        'WebExplorer': 'WebExplorer', 'UI-TARS': 'UI-TARS', 'Seed1.8': 'Seed1.8',
        'Seed2.0': 'Seed2.0', 'Seed-OSS': 'Seed-OSS', 'HunyuanImage_3.0': 'Hunyuan 3.0',
        'IndexShare': 'IndexShare', 'DeepSeek-V3.2_DSA': 'DS-V3.2',
        'Qwen2.5-VL': 'QW2.5-VL', 'DeepSeek-VL2': 'DS-VL2', 'Qwen_Technical_Report': 'Qwen',
        'LongRoPE': 'LongRoPE', 'LongLoRA': 'LongLoRA', 'YaRN': 'YaRN',
        'Position_Interpolation': 'PosInterp', 'NTK-aware_RoPE': 'NTK-RoPE',
        'FineWeb': 'FineWeb', 'KTO': 'KTO', 'LIMA': 'LIMA', 'Alpaca': 'Alpaca',
        'Reflexion': 'Reflexion', 'Self-Refine': 'Self-Refine', 'Voyager': 'Voyager',
        'BLIP-2': 'BLIP-2', 'Flamingo': 'Flamingo', 'PaLM': 'PaLM',
        'Gated_Linear_Attention': 'GatedLin', 'EAGLE': 'EAGLE',
        'DeepSeek-Coder-V2': 'DS-Coder-V2', 'DeepSeek_LLM': 'DS-LLM',
        'DeepSeekMath': 'DeepSeekMath', 'Long_CoT_Survey': 'LongCoT Survey',
        'QwQ-32B': 'QwQ-32B', 'CoT_Distillation': 'CoT蒸馏',
        'ChatGLM_Family': 'ChatGLM', 'GLM-130B': 'GLM-130B', 'InternVL': 'InternVL',
        'Speculative_Decoding': 'SpecDecode', 'Emergent_Abilities_Mirage': '涌现?',
    }
    if slug in known:
        return known[slug]
    base = t.split(':')[0].split('（')[0].split('(')[0].strip()
    words = base.split()
    if len(words) <= 3:
        return base
    return ' '.join(words[:2]) + '…'


# ---- 时间轴分档（转置后为纵轴分段） ----
def axis_rows(lanes):
    """按节点密度分段时间，返回 [(label, [nodes])]。转置后这些是纵轴的每个 segment。"""
    from collections import defaultdict
    dates = sorted(set(n['d'] for n in lanes))
    years = sorted(set(d[:4] for d in dates))
    groups = defaultdict(list)
    for n in lanes:
        groups[n['d'][:4]].append(n)
    result = []
    for y in years:
        nodes = groups.get(y, [])
        node_count = len(nodes)
        if node_count >= 7:
            h1 = [n for n in nodes if int(n['d'][5:7]) <= 6]
            h2 = [n for n in nodes if int(n['d'][5:7]) > 6]
            if h1: result.append((f'{y} H1', h1))
            if h2: result.append((f'{y} H2', h2))
        elif node_count >= 4:
            h1 = [n for n in nodes if int(n['d'][5:7]) <= 6]
            h2 = [n for n in nodes if int(n['d'][5:7]) > 6]
            result.append((f'{y} H1', h1))
            result.append((f'{y} H2', h2))
        else:
            result.append((y, nodes))
    return result, years


axis_segs, all_years = axis_rows(lanes)
# 每个节点的 segment 索引
seg_index = {}
for i, (label, nodes) in enumerate(axis_segs):
    for n in nodes:
        seg_index[n['slug']] = i
n_segs = len(axis_segs)


# ---- 生成节点卡片 ----
def node_pin(n):
    pri = n['p']
    cls = f"node node-{pri} lane-node"
    cross = len(n.get('tags', []))
    cross_badge = f'<span class="cross-badge">×{cross}</span>' if cross >= 2 else ''
    batch = batch_of(pri)
    ana = f"analysis/{batch}/{n['slug']}/03-深度解读报告.html"
    link = f"https://arxiv.org/abs/{n['id']}" if n.get('id') else ''
    return (
        f'<div class="{cls}" data-slug="{esc(n["slug"])}" data-lane="{n["line"]}" '
        f'data-seg="{seg_index.get(n["slug"],0)}" data-pri="{pri}" '
        f'data-rel="{len(n.get("related",[]))}">'
        f'<div class="node-top"><span class="node-date">{esc(n["d"])}</span>'
        f'<span class="pri-chip">{pri}</span>{cross_badge}</div>'
        f'<a class="node-title" href="{esc(link)}" target="_blank" rel="noopener" '
        f'title="{esc(n["t"])}">{esc(short_name(n))}</a>'
        f'<div class="node-org">{esc(n["org"])}</div>'
        f'<div class="node-ana"><a href="{quote(ana, safe="/")}">深度解读</a></div>'
        f'<div class="node-tip">'
        f'<div class="tip-title">{esc(n["t"])}</div>'
        f'<div class="tip-org">{esc(n["org"])}</div>'
        f'<div class="tip-contrib"><b>贡献：</b>{esc(n.get("c", ""))}</div>'
        f'<div class="tip-meta"><span>{esc(n["d"])}</span>·<span>{esc(short_name(n))}</span></div>'
        f'</div>'
        f'</div>'
    )


# ---- 关系连接（转置后坐标由 JS 计算，这里只提供数据） ----
def build_conns():
    conns = []
    for n in lanes:
        for rel in n.get('related', []):
            tgt = rel['target']
            typ = rel['type']
            if tgt in seg_index and tgt != n['slug']:
                conns.append({'slug': n['slug'], 'tgt': tgt, 'type': typ})
    return conns


conns = build_conns()


def build_html():
    total = len(lanes)
    pri_cnt = {p: sum(1 for n in lanes if n['p'] == p) for p in PRIS}
    line_cnt = {}
    for l in LANE_DEF:
        line_cnt[l['key']] = sum(1 for n in lanes if n['line'] == l['key'])

    conns_json = json.dumps(conns, ensure_ascii=False)
    lanes_json = json.dumps([{'slug': n['slug'], 'line': n['line'], 'seg': seg_index.get(n['slug'], 0), 'd': n['d']} for n in lanes], ensure_ascii=False)
    lane_keys_json = json.dumps(LANE_KEYS)
    rel_keys_json = json.dumps([r['key'] for r in REL_DEF])

    # 顶部技术线横轴标签（含图例筛选按钮）=> 放入 grid 第一行
    lane_head_cells = []
    for l in LANE_DEF:
        lane_head_cells.append(
            f'<div class="lane-head-cell" style="--lc:{l["color"]}">'
            f'<button class="lane-tab" data-lane="{l["key"]}"'
            f' title="点击筛选/高亮 {esc(l["name"])}">'
            f'<span class="ldot" style="background:{l["color"]}"></span>'
            f'<span class="lt-name">{esc(l["name"])}</span>'
            f'<span class="lt-cnt">{line_cnt[l["key"]]}</span>'
            f'</button></div>'
        )
    lane_head_cells_html = ''.join(lane_head_cells)

    # 关系类型图例
    rel_legend = ''
    for r in REL_DEF:
        rel_legend += (
            f'<button class="rel-tab" data-rel="{r["key"]}" style="--rc:{r["color"]}">'
            f'<span class="rline" style="background:{r["color"]}"></span>{esc(r["name"])}</button>'
        )

    # 左侧时间纵轴标签单元格（每 segment 一行，grid 列1）
    seg_cells = []
    for si in range(n_segs):
        label = axis_segs[si][0]
        nodes = axis_segs[si][1]
        seg_cells.append(
            f'<div class="seg-cell" style="grid-row:{si+2};grid-column:1" data-seg="{si}">'
            f'<span class="seg-y">{esc(label)}</span>'
            f'<span class="seg-n">{len(nodes)} 篇</span>'
            f'</div>'
        )
    seg_cells_html = ''.join(seg_cells)

    # 网格主体：行=时间segment，列=技术线。每行高度由该 segment 最多节点数决定
    # 用 grid-template-rows 定义高度（每行取该segment 各线节点的最大值）
    # 先算每 segment 每线的节点数
    seg_lines = {}  # (seg, lane) -> list of nodes
    for n in lanes:
        si = seg_index.get(n['slug'], 0)
        seg_lines.setdefault(si, {}).setdefault(n['line'], []).append(n)
    # 每行高度 = max(该 segment 内某条线的节点数) * 行内高
    row_heights = []
    for si in range(n_segs):
        mx = 1
        sl = seg_lines.get(si, {})
        for lane in LANE_KEYS:
            cnt = len(sl.get(lane, []))
            if cnt > mx: mx = cnt
        row_heights.append(mx * 102 + 14)
    # 用显式 grid-template-rows
    rows_vals = [str(h) + 'px' for h in row_heights]
    grid_template_rows = ' '.join(rows_vals)

    # 主体单元格：每个 (seg, lane) 一个格子，内含该线该segment的节点(纵向堆叠)
    cells = []
    for si in range(n_segs):
        for li, l in enumerate(LANE_KEYS):
            nodes_in = seg_lines.get(si, {}).get(l, [])
            nodes_in.sort(key=lambda x: x['d'])
            inner = ''.join(node_pin(n) for n in nodes_in)
            cells.append(
                f'<div class="cll lane-{l}" style="grid-row:{si+2};grid-column:{li+2}"'
                f' data-lane="{l}">{inner}</div>'
            )
    grid_html = ''.join(cells)

    # 图例（顶部技术线头部先放）
    stat = (f'<span class="sb">总计 <b>{total}</b></span>'
            + f'<span class="sb p3c">P3 <b>{pri_cnt["P3"]}</b></span>'
            + f'<span class="sb p2c">P2 <b>{pri_cnt["P2"]}</b></span>'
            + f'<span class="sb p1c">P1 <b>{pri_cnt["P1"]}</b></span>')

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>现代大语言模型发展史 · 多技术线泳道图（转置）</title>
<style>
:root{{--bg:#0b0f14;--panel:#11161d;--bd:#232b36;--tx:#dbe4ee;--mut:#7d8b9d;--acc:#4cc2ff;--gold:#e8b93e}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--tx);line-height:1.6;font-family:system-ui,-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}}
a{{color:var(--acc);text-decoration:none}}a:hover{{text-decoration:underline}}
.page-head{{text-align:center;padding:36px 16px 20px;background:radial-gradient(ellipse 80% 65% at 50% -10%,#12304a66,transparent),linear-gradient(180deg,#0e141b,var(--bg))}}
.page-head h1{{font-size:clamp(20px,3vw,30px);letter-spacing:.02em;background:linear-gradient(90deg,#9ecbff,#eef6ff 45%,#7fd4ff);-webkit-background-clip:text;background-clip:text;color:transparent}}
.page-head .sub{{color:var(--mut);margin-top:6px;font-family:ui-monospace,Consolas,monospace;font-size:12px}}
.stat-badges{{margin-top:12px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap}}
.sb{{border:1px solid var(--bd);background:var(--panel);border-radius:999px;padding:3px 12px;font-size:12px;color:var(--mut)}}
.sb b{{color:var(--tx)}}.sb.p3c b{{color:var(--gold)}}.sb.p2c b{{color:#7fa3c9}}.sb.p1c b{{color:#9aa7b5}}

/* ===== 转置布局：左=时间纵轴 sticky left，顶=技术线横轴 sticky top ===== */
.timeline-wrap{{position:relative;margin:20px auto 0;max-width:1700px;padding:0 14px 40px;overflow:visible}}
.tl-grid{{display:grid;grid-template-columns:120px repeat({len(LANE_KEYS)},minmax(150px,1fr));grid-template-rows:88px {grid_template_rows};min-width:max-content;position:relative}}
/* 左上角空白 + 技术线头部行 (sticky top) */
.corner{{grid-row:1;grid-column:1;background:#0d1219;position:sticky;top:0;left:0;z-index:20;border:1px solid var(--bd);display:flex;align-items:center;justify-content:center}}
.lane-head-cell{{grid-row:1;position:sticky;top:0;z-index:15;background:#0d1219;border:1px solid var(--bd);display:flex;align-items:center;justify-content:center;padding:6px}}
/* 技术线标签按钮（顶部横轴 + 图例筛选） */
.lane-tab{{display:flex;flex-direction:column;align-items:center;gap:3px;width:100%;height:100%;background:transparent;border:none;cursor:pointer;padding:6px 4px;transition:.15s;border-radius:8px}}
.lane-tab .ldot{{width:12px;height:12px;border-radius:50%}}
.lane-tab .lt-name{{font-size:13px;font-weight:700;color:var(--tx);line-height:1.2;text-align:center}}
.lane-tab .lt-cnt{{font-size:10.5px;color:var(--mut);font-family:ui-monospace,monospace}}
.lane-tab:hover{{background:#1a2431}}
.lane-tab.on{{background:#1c2f45;box-shadow:inset 0 0 0 2px var(--lc)}}
.lane-tab.dim{{opacity:.35}}
.lane-tab.off{{opacity:.3;filter:grayscale(1);text-decoration:line-through}}

/* 左侧时间纵轴 segment 标签 (sticky left) */
.seg-cell{{grid-column:1;position:sticky;left:0;z-index:10;background:#0d1219;border:1px solid var(--bd);padding:4px 8px;display:flex;flex-direction:column;justify-content:center;gap:2px}}
.seg-y{{font-family:ui-monospace,Consolas,monospace;font-size:12px;font-weight:700;color:#cddaea}}
.seg-n{{font-size:10px;color:var(--mut)}}

/* 内容单元格 */
.cll{{position:relative;border:1px solid #1a222d;padding:6px 4px;display:flex;flex-direction:column;gap:6px;align-items:center}}
.cll:nth-child(odd){{background:#0d1219}}

/* 节点卡片 */
.node{{position:relative;background:var(--panel);border:1px solid var(--bd);border-radius:8px;padding:6px 8px;width:100%;min-height:80px;display:flex;flex-direction:column;transition:.16s}}
.node:hover{{transform:translateY(-2px);box-shadow:0 6px 16px #00000066;border-color:#3d4c60;z-index:100}}
.node-P3{{border-color:var(--gold);border-width:2px;background:linear-gradient(180deg,#242012,#141019);box-shadow:0 0 14px #e8b93e44;z-index:4}}
.node-P3 .node-title{{color:var(--gold);font-weight:800}}
.node-P3 .pri-chip{{background:var(--gold);color:#14100a;font-weight:800}}
.node-P2{{border-color:#3d6ea0;border-width:1.5px;background:linear-gradient(180deg,#14202e,#11161d)}}
.node-P2 .node-title{{color:#cfe0f0}}
.node-P2 .pri-chip{{background:#3d5a78;color:#fff}}
.node-P1{{border-color:#333b45;border-width:1px;background:#0e1319;opacity:.72}}
.node-P1 .node-title{{color:#7d8b9d}}
.node-P1 .pri-chip{{background:#333b45;color:#9aa7b5}}
.pri-chip{{font-size:9px;font-weight:700;border-radius:4px;padding:0 5px;line-height:1.5}}
.node-top{{display:flex;gap:4px;align-items:center;margin-bottom:4px;flex-wrap:wrap}}
.node-date{{font-family:ui-monospace,Consolas,monospace;font-size:10px;color:var(--mut)}}
.cross-badge{{font-size:9px;background:#2c3a4d;color:#cddaea;border-radius:99px;padding:0 5px;font-weight:700}}
.node-title{{font-size:11.5px;line-height:1.32;display:block;word-break:break-word}}
.node-org{{font-size:10px;color:var(--mut);margin-top:3px;line-height:1.25;word-break:break-word;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.node-ana{{margin-top:auto;padding-top:4px}}.node-ana a{{font-size:10px;color:#c084fc;font-weight:600}}
.node.dim{{opacity:.18;pointer-events:none}}
.node.sel{{box-shadow:0 0 0 2px var(--acc),0 6px 16px #00000066;z-index:9}}

/* 悬停概要浮层 */
.node-tip{{position:absolute;left:50%;bottom:calc(100% + 10px);transform:translateX(-50%);width:230px;background:#131c2b;border:1px solid #33415a;border-radius:10px;padding:10px 12px;z-index:200;opacity:0;visibility:hidden;pointer-events:none;transition:opacity .15s,visibility .15s;text-align:left;box-shadow:0 10px 28px #00000088}}
.node:hover .node-tip{{opacity:1;visibility:visible;pointer-events:auto}}
.node-tip .tip-title{{font-size:12px;font-weight:700;color:#eaf2fb;line-height:1.35;word-break:break-word}}
.node-tip .tip-org{{font-size:10.5px;color:var(--mut);margin-top:4px}}
.node-tip .tip-contrib{{font-size:11px;color:#c3cedb;margin-top:6px;line-height:1.45;word-break:break-word}}
.node-tip .tip-contrib b{{color:var(--acc)}}

/* 关系线 SVG overlay */
.relation-layer{{position:absolute;top:0;left:0;overflow:visible;pointer-events:none;z-index:1}}
.rel-line{{pointer-events:auto;cursor:pointer;opacity:.32;stroke-width:1.2;fill:none}}
.rel-line.found{{stroke:#3fb950}} .rel-line.inherit{{stroke:#58a6ff}}
.rel-line.branch{{stroke:#bc8cff}} .rel-line.compete{{stroke:#f85149}}
.rel-line:hover,.rel-line.hl{{opacity:.95;stroke-width:2.5}}
.rel-line.dim{{opacity:.06;pointer-events:none}}
.rel-line.hide{{display:none}}

/* 关系类型图例 */
.legend{{display:flex;gap:10px 18px;flex-wrap:wrap;justify-content:center;max-width:1300px;margin:14px auto 0;padding:10px 16px;background:#0d1219f2;border:1px solid var(--bd);border-radius:10px}}
.rel-tab{{display:flex;align-items:center;gap:6px;background:transparent;border:1px solid var(--bd);border-radius:999px;padding:4px 12px;font-size:12px;color:var(--mut);cursor:pointer;transition:.15s}}
.rel-tab .rline{{width:18px;height:3px;border-radius:2px;display:inline-block}}
.rel-tab:hover{{color:var(--tx);border-color:#3b4757}}
.rel-tab.on{{background:#1c2f45;color:var(--tx);border-color:var(--rc);box-shadow:inset 0 0 0 1px var(--rc)}}
.rel-tab.dim{{opacity:.4}}

/* 视图切换 + 图例提示 */
.view-switch{{text-align:center;margin:18px 0 0}}
.view-switch a{{display:inline-block;border:1px solid var(--acc);color:var(--acc);border-radius:99px;padding:6px 20px;font-size:13px;font-weight:600;background:var(--acc)14}}
.hint{{text-align:center;color:var(--mut);font-size:11.5px;margin:12px auto 0}}
.page-foot{{margin-top:40px;padding:24px 16px 40px;text-align:center;color:var(--mut);font-size:12px;border-top:1px solid var(--bd);background:#0d1219}}
@media(max-width:760px){{
  .tl-grid{{grid-template-columns:88px repeat({len(LANE_KEYS)},minmax(120px,1fr))}}
  .node{{width:100%}}
  .node-tip{{width:200px}}
}}
</style>
</head>
<body>
<header class="page-head"><h1>现代大语言模型发展史 · 多技术线泳道图</h1>
<p class="sub">{lanes[0]['d'] if lanes else ''} → {lanes[-1]['d'] if lanes else ''} · {total} 个关键节点 · 9 条技术线 · 左=时间纵轴 / 顶=技术线横轴</p>
<div class="stat-badges">{stat}</div></header>
<div class="legend">
  <span style="color:var(--mut);font-size:12px;align-self:center">关系类型筛选：</span>
  {rel_legend}
  <span style="color:var(--mut);font-size:12px;align-self:center;margin-left:8px">技术线图例在顶部行，点击筛选/高亮</span>
</div>
<div class="hint">🖱️ 上下滚动浏览时间；图例点击高亮关系线/筛选技术线；节点悬停看详情</div>

<div class="timeline-wrap">
<div class="tl-grid" id="tlGrid">
  <div class="corner">⚡</div>
  {lane_head_cells_html}
  {seg_cells_html}
  {grid_html}
  <svg class="relation-layer" id="relLayer"></svg>
</div>
</div>

<div class="view-switch"><a href="list.html">📋 切换到卡片列表视图</a></div>
<footer class="page-foot"><p>数据口径：verified=联网一手核验 · 共 {total} 篇 · 9 条技术线 · 转置布局(左时间/顶技术线)</p><p>生成：data/generate_timeline_lanes.py 脚本驱动 · 禁止手抄数据</p></footer>

<script>
(function(){{
  function $$(s,c){{return Array.prototype.slice.call((c||document).querySelectorAll(s));}}
  var layer=document.getElementById('relLayer');
  var R={conns_json};
  var NODES={lanes_json};
  var W=document.querySelector('.tl-grid');
  var LANE_KEYS={lane_keys_json};
  var REL_KEYS={rel_keys_json};

  function drawRel(){{
    var gridRect=W.getBoundingClientRect();
    layer.setAttribute('width',W.scrollWidth);
    layer.setAttribute('height',W.scrollHeight);
    layer.innerHTML='';
    R.forEach(function(r){{
      var sn=document.querySelector('.node[data-slug="'+r.slug+'"]');
      var tn=document.querySelector('.node[data-slug="'+r.tgt+'"]');
      if(!sn||!tn) return;
      // 检查两端是否可见(筛选后)
      if(sn.closest('.cll').classList.contains('dim')||tn.closest('.cll').classList.contains('dim')) return;
      var sr=sn.getBoundingClientRect(), tr=tn.getBoundingClientRect();
      var x1=sr.left-gridRect.left+sr.width/2, y1=sr.top-gridRect.top+sr.height/2;
      var x2=tr.left-gridRect.left+tr.width/2, y2=tr.top-gridRect.top+tr.height/2;
      var path=document.createElementNS('http://www.w3.org/2000/svg','path');
      path.setAttribute('d','M'+x1+','+y1+' C'+x1+','+(y1+(y2-y1)*0.5)+' '+x2+','+(y2-(y2-y1)*0.5)+' '+x2+','+y2);
      path.setAttribute('class','rel-line '+r.type);
      path.setAttribute('vector-effect','non-scaling-stroke');
      path.setAttribute('data-from',r.slug);path.setAttribute('data-to',r.tgt);path.setAttribute('data-type',r.type);
      layer.appendChild(path);
    }});
  }}

  // 图例筛选状态
  function drawRel(){{
    var gridRect=W.getBoundingClientRect();
    layer.setAttribute('width',W.scrollWidth);
    layer.setAttribute('height',W.scrollHeight);
    layer.innerHTML='';
    R.forEach(function(r){{
      var sn=document.querySelector('.node[data-slug="'+r.slug+'"]');
      var tn=document.querySelector('.node[data-slug="'+r.tgt+'"]');
      if(!sn||!tn) return;
      // 两端技术线是否被筛选选中
      var laneA=sn.getAttribute('data-lane'), laneB=tn.getAttribute('data-lane');
      var bothOn = activeLanes[laneA] && activeLanes[laneB];
      var typeOn = activeRels[r.type]!==false;
      var sr=sn.getBoundingClientRect(), tr=tn.getBoundingClientRect();
      var x1=sr.left-gridRect.left+sr.width/2, y1=sr.top-gridRect.top+sr.height/2;
      var x2=tr.left-gridRect.left+tr.width/2, y2=tr.top-gridRect.top+tr.height/2;
      var path=document.createElementNS('http://www.w3.org/2000/svg','path');
      path.setAttribute('d','M'+x1+','+y1+' C'+x1+','+(y1+(y2-y1)*0.5)+' '+x2+','+(y2-(y2-y1)*0.5)+' '+x2+','+y2);
      path.setAttribute('class','rel-line '+r.type+(bothOn&&typeOn?'':' dim'));
      path.setAttribute('vector-effect','non-scaling-stroke');
      path.setAttribute('data-from',r.slug);path.setAttribute('data-to',r.tgt);path.setAttribute('data-type',r.type);
      layer.appendChild(path);
    }});
  }}

  // 筛选状态
  var activeLanes={{}};   // lane->true 全部默认true
  var activeRels={{}};    // rel->true
  var focusLane=null;     // 聚焦单线(点图例高亮)
  LANE_KEYS.forEach(function(k){{activeLanes[k]=true;}});
  REL_KEYS.forEach(function(k){{activeRels[k]=true;}});

  function applyState(){{
    var anyFocused = focusLane!==null;
    // 节点显隐
    $$('.node').forEach(function(nd){{
      var lane=nd.getAttribute('data-lane');
      var active=activeLanes[lane]!==false;
      var focused = anyFocused ? (lane===focusLane) : true;
      nd.classList.toggle('dim', !active || !focused);
    }});
    // 关系类型显隐由 drawRel 重建时处理(这里不再重复)
    // 顶部tab状态
    $$('.lane-tab').forEach(function(t){{
      var k=t.getAttribute('data-lane');
      t.classList.toggle('on', k===focusLane);
      t.classList.toggle('off', activeLanes[k]===false);
      t.classList.toggle('dim', anyFocused && k!==focusLane);
    }});
    $$('.rel-tab').forEach(function(t){{
      var k=t.getAttribute('data-rel');
      t.classList.toggle('on', activeRels[k]===true);
    }});
    drawRel();
  }}

  // 技术线图例点击：单选聚焦高亮 + 再次点击取消；用 Ctrl/Shift+点击=多选筛选toggle
  $$('.lane-tab').forEach(function(t){{
    t.addEventListener('click',function(e){{
      var k=t.getAttribute('data-lane');
      if(e.ctrlKey||e.metaKey||e.shiftKey){{
        // 多选筛选: toggle
        activeLanes[k]=!activeLanes[k];
        if(activeLanes[k]===false && focusLane===k) focusLane=null;
      }} else {{
        // 单选聚焦: 点击切换
        focusLane = (focusLane===k) ? null : k;
      }}
      applyState();
    }});
  }});

  // 关系类型图例点击
  $$('.rel-tab').forEach(function(t){{
    t.addEventListener('click',function(){{
      var k=t.getAttribute('data-rel');
      activeRels[k]=!activeRels[k];
      applyState();
    }});
  }});

  // 节点点击：高亮该节点相关关系线
  document.addEventListener('click',function(e){{
    var n=e.target.closest('.node');
    if(n){{
      var slug=n.getAttribute('data-slug');
      $$('.node').forEach(function(x){{x.classList.remove('sel');}});
      n.classList.add('sel');
      $$('.rel-line').forEach(function(p){{
        var f=p.getAttribute('data-from'),t=p.getAttribute('data-to');
        p.classList.toggle('hl',(f===slug||t===slug));
      }});
    }} else {{
      $$('.node').forEach(function(x){{x.classList.remove('sel');}});
      $$('.rel-line').forEach(function(p){{p.classList.remove('hl');}});
    }}
  }});

  window.addEventListener('resize',drawRel);
  applyState();
}})();
 </script>
 </body>
 </html>'''


html_out = build_html()
OUT_PATH.write_text(html_out, encoding='utf-8')
print('已生成', OUT_PATH)
print('篇数:', len(lanes), '| 时间分段:', n_segs, '| 技术线:', len(LANE_KEYS), '| 关系线:', len(conns))

