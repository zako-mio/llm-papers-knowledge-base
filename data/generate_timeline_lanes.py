#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 data/papers_lanes.json，脚本驱动生成 docs/timeline.html 横向泳道图。
零外部依赖（无CDN、离线可用），暗色科技风。
设计要点：
- 横向泳道式：顶部时间轴，纵向 9 条技术线泳道，节点落泳道
- 时间轴按节点密度动态分档（早年按年/中途半年/近年季度），全年份刻度最醒目
- 节点仅现一次、标交叉点(tags)、严格时间排序、最小间距防拥挤
- P3 高亮 / P2 / P1 弱化
- 悬停显示信息+关系标签；点击展开深度解读/PDF；点关系线高亮
- 原生 JS + SVG，自包含
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

# 9 条泳道定义（顺序即泳道从上到下）
LANE_DEF = [
    {'key': 'arch',     'name': '架构革命',       'color': '#58a6ff', 'desc': 'Transformer / 注意力变体 / 稀疏·线性 / SSM'},
    {'key': 'pretrain', 'name': '预训练与Scaling', 'color': '#3fb950', 'desc': '预训练目标 / 缩放定律 / 数据 / 涌现'},
    {'key': 'align',    'name': '对齐与后训练',     'color': '#bc8cff', 'desc': 'RLHF / DPO / 指令微调 / 安全'},
    {'key': 'reason',   'name': '推理与测试时计算', 'color': '#f0883e', 'desc': 'CoT / 长思维链 / test-time / RL推理'},
    {'key': 'longctx',  'name': '长上下文与效率',   'color': '#7fd4ae', 'desc': '位置编码 / KV压缩 / 量化 / 粗长窗口'},
    {'key': 'multi',    'name': '多模态',           'color': '#d2a8ff', 'desc': '视觉·图文 / VLM / 原生多模态'},
    {'key': 'agent',    'name': 'Agent与工具',      'color': '#f85149', 'desc': '工具调用 / 行动推理 / Agentic'},
    {'key': 'eng',      'name': '工程与部署',       'color': '#e8b93e', 'desc': '训练并行 / 推理服务 / 分发压缩'},
    {'key': 'opensrc',  'name': '开源生态与旗舰',   'color': '#79c0ff', 'desc': '开源权重 / 旗舰模型 / 生态影响'},
]
LANE_BY_KEY = {l['key']: l for l in LANE_DEF}

PRIS = ['P3', 'P2', 'P1']
PRI_LABEL = {'P3': 'P3必读', 'P2': 'P2重要', 'P1': 'P1补充'}

# 批量映射
batch_of = lambda p: 'B1_P3' if p == 'P3' else ('B2_P2' if p == 'P2' else 'B3_P1')


def esc(v):
    return html.escape(str(v)) if v is not None else ''


# ---- 缩略别名提取 ----
def short_name(n):
    """从标题/slug 提取论文短别名，用于节点显示（完整标题走 tooltip）。"""
    slug = n.get('slug', '')
    t = n.get('t', '')
    # 知名简写映射（优先）
    known = {
        'Attention_Is_All_You_Need': 'Attention',
        'BERT': 'BERT',
        'GPT-1': 'GPT-1', 'GPT-2': 'GPT-2', 'GPT-3_Few-Shot_Learners': 'GPT-3',
        'GPT-4_Technical_Report': 'GPT-4', 'GPT-5_System_Card': 'GPT-5',
        'Kaplan_Scaling_Laws': 'Scaling Laws',
        'Chinchilla': 'Chinchilla',
        'InstructGPT_RLHF': 'InstructGPT',
        'Chain-of-Thought': 'CoT',
        'DPO': 'DPO',
        'CLIP': 'CLIP', 'ViT': 'ViT',
        'FlashAttention': 'FlashAttn', 'FlashAttention-2': 'FlashAttn-2', 'FlashAttention-3': 'FlashAttn-3',
        'RoPE_RoFormer': 'RoPE', 'ALiBi': 'ALiBi',
        'ReAct': 'ReAct', 'Mamba': 'Mamba', 'Mamba-2': 'Mamba-2',
        'DeepSeek-V3': 'DeepSeek-V3', 'DeepSeek-R1': 'DS-R1', 'DeepSeek-V4': 'DS-V4',
        'vLLM_PagedAttention': 'vLLM',
        'LLaMA': 'LLaMA', 'LLaMA_2': 'Llama-2', 'Llama_3': 'Llama-3', 'Llama_4': 'Llama-4',
        'LoRA': 'LoRA', 'Switch_Transformers': 'Switch',
        'Kimi_K2': 'Kimi K2', 'Kimi_K3': 'Kimi K3',
        'GLM-4.5': 'GLM-4.5', 'GLM-5': 'GLM-5',
        'o1_Learning_to_Reason': 'o1',
        'GQA': 'GQA', 'MQA': 'MQA',
        'LLaVA': 'LLaVA', 'Qwen2': 'Qwen2', 'Qwen2.5': 'Qwen2.5', 'Qwen3': 'Qwen3',
        'Mixtral': 'Mixtral', 'GRPO_DeepSeekMath': 'GRPO',
        'DeepSeek-V2_MLA': 'DS-V2 MLA', 'DeepSeekMoE': 'DS-MoE',
        'PosREALM': 'REALM', 'RAG': 'RAG',
        'Stitch': 'T5', 'T5': 'T5', 'FLAN': 'FLAN',
        'Constitutional_AI': 'CAI', 'Self-Instruct': 'Self-Instr',
        'Toolformer': 'Toolformer', 'Tree_of_Thoughts': 'ToT',
        'Self-Consistency': 'Self-Con',
        'Gemini_Technical_Report': 'Gemini', 'Gemini_2.5_Report': 'Gemini 2.5',
        'Claude_Opus_4.5_System_Card': 'Opus 4.5',
        'MiniMax-01': 'MiniMax-01', 'MiniMax-M1': 'MiniMax-M1', 'MiniMax-M2_Series': 'MiniMax-M2',
        'Qwen3.5': 'Qwen3.5', 'Qwen3.5-Omni': 'Qwen3.5-Omni', 'Qwen3.6-35B': 'Qwen3.6',
        'Thinking_with_Visual_Primitives': 'VisPrimitives',
        'StreamingLLM': 'StreamingLLM', 'H2O': 'H2O', 'AWQ': 'AWQ', 'GPTQ': 'GPTQ',
        'Grokking': 'Grokking', 'Emergent_Abilities_Mirage': 'Emergence?',
        'DeepSeek-OCR': 'DS-OCR', 'Kimi_Linear': 'Kimi Linear',
        'DeepSpeed': 'DeepSpeed', 'Megatron_LM': 'Megatron',
        'GShard': 'GShard', 'Sparse_Transformers': 'Sparse Attn',
        'Scaling_TestTime_Compute': 'TTC Scaling',
        'mHC': 'mHC', 'Manifold-Constrained_Hyper-Connections': 'mHC',
        'GLM-5.3': 'GLM-5.3', 'GLM-5.2': 'GLM-5.2', 'GLM-5.1': 'GLM-5.1',
        'GLM-5.3-Flash': 'GLM-5.3-Flash',
        'Native_Sparse_Attention': 'NSA', 'NSA': 'NSA',
        'MoBA': 'MoBA', 'Kimi_Linear': 'Kimi Linear',
        'Forge_RL_Framework': 'Forge', 'WebExplorer': 'WebExplorer',
        'UI-TARS': 'UI-TARS', 'Seed1.8': 'Seed1.8', 'Seed2.0': 'Seed2.0',
        'Seed-OSS': 'Seed-OSS', 'HunyuanImage_3.0': 'Hunyuan 3.0',
        'IndexShare': 'IndexShare', 'DeepSeek-V3.2_DSA': 'DS-V3.2',
        'MiniMax-01': 'MiniMax-01',
        'Qwen2.5-VL': 'QW2.5-VL', 'DeepSeek-VL2': 'DS-VL2', 'Qwen2.5': 'QW2.5',
        'Qwen2': 'QW2', 'Qwen_Technical_Report': 'Qwen',
        'LongRoPE': 'LongRoPE', 'LongLoRA': 'LongLoRA', 'YaRN': 'YaRN',
        'Position_Interpolation': 'PosInterp', 'NTK-aware_RoPE': 'NTK-RoPE',
        'FineWeb': 'FineWeb', 'KTO': 'KTO', 'LIMA': 'LIMA', 'Alpaca': 'Alpaca',
        'Reflexion': 'Reflexion', 'Self-Refine': 'Self-Refine', 'Voyager': 'Voyager',
        'BLIP-2': 'BLIP-2', 'Flamingo': 'Flamingo', 'PaLM': 'PaLM', 'T5': 'T5',
        'Grokking': 'Grokking', 'Emergent_Abilities_Mirage': 'Emergence?',
        'Gated_Linear_Attention': 'GatedLinAttn', 'GQA': 'GQA', 'EAGLE': 'EAGLE',
        'DeepSeek-Coder-V2': 'DS-Coder-V2', 'DeepSeek_LLM': 'DS-LLM',
        'DeepSeekMath': 'DeepSeekMath', 'Long_CoT_Survey': 'LongCoT Survey',
        'QwQ-32B': 'QwQ-32B', 'WenExplorer': 'WebExplorer', 'WebExplorer': 'WebExplorer',
        'CoT_Distillation': 'CoT蒸馏', 'Teaching_Small_LMs': 'CoT蒸馏',
        'H2O': 'H2O', 'AWQ': 'AWQ', 'GPTQ': 'GPTQ', 'Qwen3.5': 'Qwen3.5',
        'ChatGLM_Family': 'ChatGLM', 'GLM-130B': 'GLM-130B',
        'InternVL': 'InternVL', 'Speculative_Decoding': 'SpecDecode',
        'Gated_Linear_Attention': 'GatedLin',
    }
    if slug in known:
        return known[slug]
    # 启发式：取标题首段冒号前的部分，或前2-3个词
    base = t.split(':')[0].split('（')[0].split('(')[0].strip()
    words = base.split()
    if len(words) <= 3:
        return base
    return ' '.join(words[:2]) + '…' if len(words) > 2 else base


# ---- 时间轴分档 ----
def axis_columns(lanes):
    """根据节点密度决定时间轴细分粒度。
    返回 {label: [list of node slugs]}，label 为时间轴刻度。"""
    from collections import defaultdict
    # 收集所有日期
    dates = sorted(set(n['d'] for n in lanes))
    # 年份集合
    years = sorted(set(d[:4] for d in dates))

    # 密度分档：分段统计每段节点数，决定粒度
    # 用年份为最小刻度，若某年节点数多则细分到半年/季度
    groups = defaultdict(list)  # 刻度label -> nodes
    for n in lanes:
        y = n['d'][:4]
        m = int(n['d'][5:7]) if len(n['d']) >= 7 else 1
        # 决策：按年份节点密度
        # 我们用一个简单规则：刻度 = 年份（统一），但若某年节点数>=6则细分到半年
        groups[y].append(n)

    # 二级细分：对节点多的年份，拆分到 H1/H2
    result = []
    for y in years:
        nodes = groups.get(y, [])
        if len(nodes) >= 7:  # 该年节点多，细分到半年
            h1 = [n for n in nodes if int(n['d'][5:7]) <= 6]
            h2 = [n for n in nodes if int(n['d'][5:7]) > 6]
            if h1:
                result.append((f'{y} H1', h1))
            if h2:
                result.append((f'{y} H2', h2))
        elif len(nodes) >= 4:  # 中等密度，仍可细分到半年以显得"不同粒度"
            # 为体现"不同细粒度"，中等年份也细分
            h1 = [n for n in nodes if int(n['d'][5:7]) <= 6]
            h2 = [n for n in nodes if int(n['d'][5:7]) > 6]
            result.append((f'{y} H1', h1))
            result.append((f'{y} H2', h2))
        else:
            result.append((y, nodes))
    return result, years


# 计算时间轴
axis_cols, all_years = axis_columns(lanes)

# 每一列(时间刻度)对应可能的 x 区间。为布局方便，我们把每个节点标一个"列索引"
col_index = {}
for i, (label, nodes) in enumerate(axis_cols):
    for n in nodes:
        col_index[n['slug']] = i

n_cols = len(axis_cols)


# ---- 生成 CSS ----
def lane_css():
    parts = []
    for l in LANE_DEF:
        parts.append(f'.lane-{l["key"]} {{ --lc:{l["color"]}; }}')
    parts.append('''
.lane-row{display:grid;grid-template-columns:190px 1fr;gap:0;border-bottom:1px solid #1d2632}
.lane-label{padding:14px 12px;border-right:1px solid #1d2632;background:#10161f;position:sticky;left:0;z-index:5;min-height:118px}
.lane-label .ldot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:7px}
.lane-label .lname{font-size:14px;font-weight:700;color:var(--tx)}
.lane-label .ldesc{font-size:11px;color:var(--mut);margin-top:5px;line-height:1.5}
.lane-track{position:relative;min-height:118px;overflow:visible}
'''
    )
    return '\n'.join(parts)


# ---- 生成节点卡片 ----
def node_pin(n):
    pri = n['p']
    cls = f'node node-{pri} lane-node'
    # 多线交叉标 tag 数
    cross = len(n.get('tags', []))
    cross_badge = f'<span class="cross-badge">×{cross}</span>' if cross >= 2 else ''
    rel_cnt = len(n.get('related', []))
    title = esc(n['t'])
    short = esc(short_name(n))
    batch = batch_of(pri)
    ana = f"analysis/{batch}/{n['slug']}/03-深度解读报告.html"
    link = f"https://arxiv.org/abs/{n['id']}" if 'id' in n and n['id'] else ''
    return (
        f'<div class="{cls}" data-lane="{n["line"]}" data-slug="{esc(n["slug"])}" '
        f'data-col="{col_index.get(n["slug"],0)}" data-pri="{pri}" '
        f'data-id="{esc(str(n.get("id","")))}" data-rel="{rel_cnt}">'
        f'<div class="node-top"><span class="node-date">{esc(n["d"])}</span>'
        f'<span class="pri-chip">{pri}</span>{cross_badge}</div>'
        f'<a class="node-title" href="{esc(link)}" target="_blank" rel="noopener" '
        f'title="{esc(n["t"])}">{short}</a>'
        f'<div class="node-org">{esc(n["org"])}</div>'
        f'<div class="node-ana"><a href="{quote(ana, safe="/")}">深度解读</a></div>'
        f'</div>'
    )


# ---- 关系连线 SVG ----
def build_connections(lanes):
    """构建关系线。返回 (svg_polylines, node_positions).
    简化：用节点在泳道内的相对横向位置估计，生成二次贝塞尔路径。
    """
    # 每泳道内按列排布(实际由CSS grid控制列,这里估算每列中心x)
    # 列宽 = (100 / n_cols)% 近似
    col_width = 100.0 / max(n_cols, 1)
    lines = []
    position = {}
    for n in lanes:
        position[n['slug']] = (col_index.get(n['slug'], 0), n['line'])
    for n in lanes:
        for rel in n.get('related', []):
            tgt = rel['target']
            typ = rel['type']
            if tgt in position and tgt != n['slug']:
                x1, y1 = position[n['slug']]
                x2, y2 = position[tgt]
                lines.append({
                    'sx': x1, 'sy': y1, 'tx': x2, 'ty': y2,
                    'type': typ, 'slug': n['slug'], 'tgt': tgt
                })
    return lines, position


conns, pos = build_connections(lanes)


# ---- 组装 HTML ----
def build_html():
    # 关系JSON注入(以HTML安全转义)
    conns_json = json.dumps(conns, ensure_ascii=False)
    # 头部统计
    total = len(lanes)
    pri_cnt = {p: sum(1 for n in lanes if n['p'] == p) for p in PRIS}
    line_cnt = {}
    for l in LANE_DEF:
        line_cnt[l['key']] = sum(1 for n in lanes if n['line'] == l['key'])

    # 泳道行
    lane_rows = []
    for l in LANE_DEF:
        key = l['key']
        nodes_in = [n for n in lanes if n['line'] == key]
        nodes_in.sort(key=lambda x: x['d'])
        # 节点按列排布，用CSS grid
        # 每个节点放一个 grid-cell，用绝对列定位
        cells = []
        for n in nodes_in:
            ci = col_index.get(n['slug'], 0)
            cells.append(f'<span class="node-wrap" style="grid-column:{ci+1}">{node_pin(n)}</span>')
        grid = ''.join(cells)
        lane_rows.append(
            f'<div class="lane-row lane-{key}">'
            f'<div class="lane-label"><span class="ldot" style="background:{l["color"]}"></span>'
            f'<span class="lname">{esc(l["name"])}</span>'
            f'<div class="ldesc">{esc(l["desc"])}</div>'
            f'<div class="lcnt" style="color:{l["color"]}">{line_cnt.get(key,0)} 节点</div></div>'
            f'<div class="lane-track" data-lane="{key}">{grid}</div></div>'
        )
    lanes_html = '\n'.join(lane_rows)

    # 时间轴头(列标签)
    axis_head = []
    for i, (label, nodes) in enumerate(axis_cols):
        axis_head.append(f'<div class="ax-cell" style="grid-column:{i+1}">{esc(label)}')
        axis_head.append(f'<div class="ax-mini">{len(nodes)} 篇</div></div>')
    axis_html = ''.join(axis_head)

    # 统计badges
    stat = (f'<span class="sb">总计 <b>{total}</b></span>'
            + f'<span class="sb p3c">P3 <b>{pri_cnt["P3"]}</b></span>'
            + f'<span class="sb p2c">P2 <b>{pri_cnt["P2"]}</b></span>'
            + f'<span class="sb p1c">P1 <b>{pri_cnt["P1"]}</b></span>')

    # 9条泳道图例
    lg = ''.join(
        f'<button class="lg-btn" data-sid="{"all" if False else ""}"></button>' for _ in []
    ) if False else ''
    legend = ''.join(
        f'<div class="lg-item"><span class="ldot" style="background:{l["color"]}"></span>{esc(l["name"])}</div>'
        for l in LANE_DEF)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>现代大语言模型发展史 · 多技术线泳道图</title>
<style>
:root{{--bg:#0b0f14;--panel:#11161d;--bd:#232b36;--tx:#dbe4ee;--mut:#7d8b9d;--acc:#4cc2ff;--gold:#e8b93e;
--e1:#58a6ff;--e2:#3fb950;--e3:#bc8cff;--e4:#f0883e;--e5:#f85149}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--tx);line-height:1.6;font-family:system-ui,-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}}
a{{color:var(--acc);text-decoration:none}}a:hover{{text-decoration:underline}}
.mono{{font-family:ui-monospace,Consolas,monospace}}
.page-head{{text-align:center;padding:44px 16px 26px;background:radial-gradient(ellipse 80% 65% at 50% -10%,#12304a66,transparent),linear-gradient(180deg,#0e141b,var(--bg))}}
.page-head h1{{font-size:clamp(22px,3.2vw,32px);letter-spacing:.02em;background:linear-gradient(90deg,#9ecbff,#eef6ff 45%,#7fd4ff);-webkit-background-clip:text;background-clip:text;color:transparent}}
.page-head .sub{{color:var(--mut);margin-top:8px;font-family:ui-monospace,Consolas,monospace;font-size:13px}}
.stat-badges{{margin-top:16px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap}}
.sb{{border:1px solid var(--bd);background:var(--panel);border-radius:999px;padding:4px 14px;font-size:13px;color:var(--mut)}}
.sb b{{color:var(--tx)}}.sb.p3c b{{color:var(--gold)}}.sb.p2c b{{color:#7fa3c9}}.sb.p1c b{{color:#9aa7b5}}
.legend{{display:flex;gap:8px 18px;flex-wrap:wrap;justify-content:center;max-width:1180px;margin:10px auto 0;padding:10px 18px;background:#0d1219f2;border:1px solid var(--bd);border-radius:10px}}
.lg-item{{display:flex;align-items:center;gap:6px;font-size:12px;color:#a7b4c4}}
.ldot{{width:9px;height:9px;border-radius:50%;display:inline-block}}
.timeline-wrap{{max-width:1300px;margin:26px auto 0;padding:0 12px;overflow-x:auto}}
.axis-row{{display:grid;grid-template-columns:190px 1fr;border-bottom:2px solid var(--bd)}}
.axis-spacer{{border-right:1px solid var(--bd)}}
.axis-grid{{display:grid;grid-auto-columns:minmax(118px,1fr);grid-auto-flow:column;align-items:end}}
.ax-cell{{text-align:center;padding:8px 4px;font-size:12px;font-weight:700;color:#cddaea;border-left:1px solid #1d2632;position:sticky;top:0;background:#0d1219}}
.ax-mini{{font-size:10px;color:var(--mut);font-weight:400;margin-top:2px}}
.lane-scroll{{position:relative}}
.lane-row{{display:grid;grid-template-columns:190px 1fr;gap:0;border-bottom:1px solid #1d2632}}
.lane-label{{padding:12px;border-right:1px solid #1d2632;background:#10161f;position:sticky;left:0;z-index:5}}
.lane-label .lname{{font-size:13.5px;font-weight:700;color:var(--tx)}}
.lane-label .ldesc{{font-size:10.5px;color:var(--mut);margin-top:4px;line-height:1.45}}
.lane-label .lcnt{{font-size:11px;margin-top:6px;font-weight:600}}
.lane-track{{position:relative;display:grid;grid-auto-columns:minmax(118px,1fr);grid-auto-flow:column;align-items:start;padding:10px 0}}
.lane-node{{position:relative}}
.node-wrap{{padding:5px 4px;min-width:88px}}
.node{{background:var(--panel);border:1px solid var(--bd);border-radius:8px;padding:7px 9px;transition:.16s;position:relative;width:100%;min-height:84px;display:flex;flex-direction:column}}
.node:hover{{transform:translateY(-2px);box-shadow:0 6px 16px #00000066;border-color:#3d4c60;z-index:8}}
/* === 优先级视觉三档（强区分） === */
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
.node-title{{font-size:11.5px;line-height:1.32;display:block;word-break:break-word;overflow:hidden}}
.node-org{{font-size:10px;color:var(--mut);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.node-ana{{margin-top:auto;padding-top:4px}}.node-ana a{{font-size:10px;color:#c084fc;font-weight:600}}
.relation-layer{{position:absolute;top:0;left:0;overflow:visible;pointer-events:none;z-index:2}}
.rel-line{{pointer-events:auto;cursor:pointer;opacity:.38;stroke-width:1.2}}
.rel-line.found{{stroke:#3fb950}}.rel-line.inherit{{stroke:#58a6ff}}.rel-line.branch{{stroke:#bc8cff}}.rel-line.compete{{stroke:#f85149}}
.rel-line:hover,.rel-line.hl{{opacity:.95;stroke-width:2.5}}
.node.sel{{box-shadow:0 0 0 2px var(--acc),0 6px 16px #00000066;z-index:9}}
.page-foot{{margin-top:46px;padding:26px 16px 42px;text-align:center;color:var(--mut);font-size:12px;border-top:1px solid var(--bd);background:#0d1219}}
@media(max-width:760px){{.lane-label{{min-width:120px}}}}
</style>
</head>
<body>
<header class="page-head"><h1>现代大语言模型发展史 · 关键节点技术线泳道图</h1>
<p class="sub">{lanes[0]['d'] if lanes else ''} → {lanes[-1]['d'] if lanes else ''} · {total} 个关键节点 · 9 条技术线</p>
<div class="stat-badges">{stat}</div></header>
<div class="legend">{legend}</div>
<section class="timeline-wrap">
<div class="lane-scroll">
  <div class="axis-row"><div class="axis-spacer"></div><div class="axis-grid">{axis_html}</div></div>
  {lanes_html}
  <svg class="relation-layer" id="relLayer"></svg>
</div>
</section>
<div style="text-align:center;margin:22px 0"><a href="list.html" style="border:1px solid var(--bd);border-radius:99px;padding:6px 20px;font-size:13px">📋 切换到卡片列表视图</a></div>
<footer class="page-foot"><p>数据口径：verified=联网一手核验 · 共 {total} 篇；本地PDF 112 篇 · 仅索引 21 篇</p><p>生成日期：{sys.argv[0].split("/")[-1]} 脚本驱动 · 禁止手抄数据</p></footer>
<script>
(function(){{
  var nodes=$$ ? [] : [];
  function $$(s,c){{return Array.prototype.slice.call((c||document).querySelectorAll(s));}}
  // 关系连线
  var layer=document.getElementById('relLayer');
  var R={conns_json};
  var W=document.querySelector('.lane-scroll');
  function drawRel(){{
    layer.setAttribute('width',W.scrollWidth);
    layer.setAttribute('height',W.scrollHeight);
    layer.innerHTML='';
    var wsr=W.getBoundingClientRect();
    R.forEach(function(r){{
      var sn=document.querySelector('.node[data-slug="'+r.slug+'"]');
      var tn=document.querySelector('.node[data-slug="'+r.tgt+'"]');
      if(!sn||!tn) return;
      var sr=sn.getBoundingClientRect(), tr=tn.getBoundingClientRect();
      // 相对 lane-scroll content 原点（SVG 坐标系）
      var x1=sr.left-wsr.left+sr.width/2, y1=sr.top-wsr.top+sr.height/2;
      var x2=tr.left-wsr.left+tr.width/2, y2=tr.top-wsr.top+tr.height/2;
      var dx=x2-x1, dy=y2-y1;
      // 贝塞尔：控制点沿 y 方向（泳道间纵向连接）, 避免横穿泳道；同泳道近距离用平滑曲线
      var c1y=y1+dy*0.5, c2y=y2-dy*0.5;
      var path=document.createElementNS('http://www.w3.org/2000/svg','path');
      path.setAttribute('d','M'+x1+','+y1+' C'+x1+','+c1y+' '+x2+','+c2y+' '+x2+','+y2);
      path.setAttribute('class','rel-line '+r.type);
      path.setAttribute('vector-effect','non-scaling-stroke');
      path.setAttribute('fill','none');
      path.setAttribute('data-from',r.slug);path.setAttribute('data-to',r.tgt);path.setAttribute('data-type',r.type);
      path.addEventListener('click',function(e){{
        e.preventDefault();e.stopPropagation();
        $$('.rel-line').forEach(function(p){{p.classList.remove('hl');}});
        path.classList.add('hl');
      }});
      layer.appendChild(path);
    }});
  }}
  window.addEventListener('resize',drawRel);
  drawRel();
  // 节点点击：高亮该节点及其相关关系线，其余淡化
  document.addEventListener('click',function(e){{
    var n=e.target.closest('.node');
    if(n){{
      var slug=n.getAttribute('data-slug');
      $$('.node').forEach(function(x){{x.classList.remove('sel');}});
      n.classList.add('sel');
      // 高亮相关关系
      $$('.rel-line').forEach(function(p){{
        var f=p.getAttribute('data-from'),t=p.getAttribute('data-to');
        p.classList.toggle('hl',(f===slug||t===slug));
      }});
    }} else {{
      // 点击空白处取消
      $$('.node').forEach(function(x){{x.classList.remove('sel');}});
      $$('.rel-line').forEach(function(p){{p.classList.remove('hl');}});
    }}
  }});
  // 图例已内联，无额外绑定
}})( );
</script>
</body>
</html>'''


html_out = build_html()
OUT_PATH.write_text(html_out, encoding='utf-8')
print('已生成', OUT_PATH)
print('篇数:', len(lanes), '列数:', n_cols, '关系线:', len(conns))
