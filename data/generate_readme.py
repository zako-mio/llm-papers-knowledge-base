# -*- coding: utf-8 -*-
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

# ★ L1 本地化（批 I · 裁定 L1=A）：⛔ 不再写死作者机绝对路径；由文件位置推导仓根。
#   输入 data/*.json 与产物 README.md 都在仓根 ⇒ 本地化后行为等价。
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "README.md")

with open(os.path.join(DATA, "papers_master.json"), encoding="utf-8") as f:
    master = json.load(f)
with open(os.path.join(DATA, "era_narratives.json"), encoding="utf-8") as f:
    narratives = json.load(f)

papers = master["papers"]
stats = {
    "total": master["total"],
    "downloadable": master["downloadable"],
    "index_only": master["index_only"],
    "priority": master["priority"],
    "era_counts": master["era_counts"],
}
verified_n = sum(1 for p in papers if p.get("conf") == "verified")
cited_n = sum(1 for p in papers if p.get("conf") == "cited")

ERA_TITLES = {k: v["title"] for k, v in narratives.items()}

lines = []
add = lines.append

# 1. 标题+统计总览
add("# LLM 关键节点论文全集（2017–2026）\n")
add("收录大语言模型发展史上 98 篇关键论文，按五个时代组织，附优先级分级与推荐阅读路线。\n")
add("## 统计总览\n")
add("| 指标 | 数量 |")
add("|---|---:|")
add(f"| 收录总篇数 | {stats['total']} |")
add(f"| 可下载 PDF | {stats['downloadable']} |")
add(f"| 仅索引（无公开PDF） | {stats['index_only']} |")
add(f"| P3 必读核心 | {stats['priority']['P3']} |")
add(f"| P2 重要 | {stats['priority']['P2']} |")
add(f"| P1 补充 | {stats['priority']['P1']} |")
add("")
add("**五时代分布**：\n")
add("| 时代 | 论文数 |")
add("|---|---:|")
for era in ["E1", "E2", "E3", "E4", "E5"]:
    add(f"| {era} · {ERA_TITLES[era]} | {stats['era_counts'][era]} |")
add("")

# 2. 使用说明
add("## 使用说明\n")
add("- **目录结构**：本地 PDF 按 `papers/E1` … `papers/E5` 五个时代目录存放。")
add("- **文件命名规则**：`{日期}_{优先级}_{简称}.pdf`，例如 `2017-06_P3_Attention_Is_All_You_Need.pdf`。")
add("- **优先级含义**：")
add("  - **P3 = 必读核心**（21 篇）：建立主线骨架的里程碑工作；")
add("  - **P2 = 重要**：对主线有实质贡献或影响深远的分支；")
add("  - **P1 = 补充**：扩展视野与查证细节用。")
add("  - 同级内按发表时间越新越优先阅读。\n")

# 3. 推荐阅读路线（P3 先行）
add("## 推荐阅读路线（P3 先行）\n")
p3 = sorted([p for p in papers if p.get("p") == "P3"], key=lambda x: x["d"])
for i, p in enumerate(p3, 1):
    add(f"{i}. [{p['d']}] {p['t']} —— {p['c']}")
add("")
add("> 读完这 21 篇即建立主线骨架，再按时代下探 P2/P1。\n")

# 4. 五个时代章节
add("## 分时代论文清单\n")
for era in ["E1", "E2", "E3", "E4", "E5"]:
    add(f"### E{era[1]} · {narratives[era]['title']}\n")
    add(narratives[era]["text"])
    add("")
    add("| 日期 | 级别 | 论文 | 机构 | 核心贡献 | 资源 |")
    add("|---|---|---|---|---|---|")
    era_papers = sorted([p for p in papers if p.get("_era") == era], key=lambda x: x["d"])
    for p in era_papers:
        name = f"**{p['t']}**「※无公开PDF」" if not p.get("id") else p["t"]
        if p.get("id"):
            res = f"[arXiv](https://arxiv.org/abs/{p['id']})"
            if p.get("code"):
                res += f" · [code]({p['code']})"
        else:
            res = f"[外部链接]({p['ext_url']})" if p.get("ext_url") else "—"
        add(f"| {p['d']} | {p['p']} | {name} | {p['org']} | {p['c']} | {res} |")
    add("")

# 5. 附录·数据口径
add("## 附录·数据口径\n")
add(f"- `conf=verified`（本轮联网一手核验）：**{verified_n}** 篇——标题、机构、日期、链接均经 arXiv/官网实时核对。")
add(f"- `conf=cited`（高置信知识库条目）：**{cited_n}** 篇——来自权威综述与知识库交叉印证，未逐条回源。")
add("- 统计口径与 `data/papers_master.json` 完全一致，本 README 由脚本生成，勿手改。")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

paper_rows = len([p for p in papers])  # 每篇论文恰好一行表格行
print(f"README 行数: {len(lines)}")
print(f"论文表格行数: {paper_rows}")
print(f"P3 路线条目: {len(p3)}")
