#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_home.py — 首页 `docs/index.html` 的**生成器**（Q1=B 裁定：新建生成器并纳入管线）。

★ 裁定原文（`evidence/i/decisions.json` → `Q1_index_provenance`，ruling=B）：
  「为 `docs/index.html` 新建生成器并纳入管线（理想档动作提前到本轮）。★ 该文件**不在仓库树里、
   无版本历史**，故必须先做成**可重跑的生成器**再谈任何改动——⛔ 不得就地手改。」
  ★ 同一条的 `premise_correction` 已**实测更正**该前提：`git cat-file -e HEAD:docs/index.html`
  成立、工作树 blob 与 `HEAD:docs/index.html` 逐字相同 ⇒ **它在 HEAD 提交树内、有版本历史**；
  真正成立的只有后半句「**无生成器认领**」。⇒ 裁定**维持 B**（动机那一半仍成立），
  而「改坏不可逆」这半句风险理由被推翻（风险低于上游表述）。

★ 本件的等价性义务（Q1 的 `impl_note`）：生成器产出的首页必须与**现行**首页等价。
  做法：`--cta legacy` 产出与 `git show HEAD:docs/index.html` **逐字节相同**的那一版
  （证据由 `data/build_all.py --equivalence` 与报告件给出）；默认 `--cta report` 即 Q5=A
  裁定的那一处改动。⇒ 首页的全部改动＝**且仅＝** Q5 的那一条 href。

★ 数值一律**派生**（⛔ 不写死）：133 / P3×38 / P2×81 / P1×14 / 9 条技术线分别取自
  `data/papers_master.json` 与 `data/papers_lanes.json`；只有编辑性文案（标题、副标题、
  卡片说明）是模板常量 —— 它们是内容，不是数据。

用法：
    python3 data/gen_home.py                 # 写 docs/index.html（Q5=A 后的形态）
    python3 data/gen_home.py --cta legacy    # 写与 HEAD 逐字节相同的历史形态（等价性证据用）
    python3 data/gen_home.py --check         # 只对账（把盘上文件反注解后与生成结果比）
    python3 data/gen_home.py --stdout        # 打到标准输出，不写盘
    python3 data/gen_home.py --selftest      # 负向夹具 6 例
退出码：0 成功/一致 · 1 有漂移或有 FAIL · 2 输入错误 · 3 护栏拒写
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
# ★ 产物归属声明（方案 C2-N6 / Q1=B）：本件**认领** docs/index.html。
#   机器可核：gate_tokens.py 的 G8/G9 用 **ast 求值面**扫 `OUT_PATH` 赋值（⛔ 不靠正则）。
OUT_PATH = os.path.join(REPO, "docs", "index.html")

TAGLINE_HEAD = "从《Attention Is All You Need》(2017) 到 GLM-5.3-Flash / DeepSeek-V4 / Kimi K3 (2026)"
TAGLINE_TAIL = "关键节点论文全集 + 全量深度解读 + 多技术线泳道图"

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>现代大语言模型发展史 · 知识库</title>
<style>
*{{box-sizing:border-box}}body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#0f1420;color:#e6e9f0;margin:0;line-height:1.7}}
.wrap{{max-width:1000px;margin:0 auto;padding:56px 22px 90px}}
h1{{font-size:32px;margin:0;background:linear-gradient(90deg,#7cb3ff,#c084fc);-webkit-background-clip:text;background-clip:text;color:transparent}}
.sub{{color:#8fa0b8;font-size:15px;margin-top:10px}}
.badges{{margin-top:22px}} .badge{{display:inline-block;background:#161d2e;border:1px solid #2a3650;border-radius:20px;padding:5px 14px;font-size:13px;margin:3px 7px 3px 0;color:#aeb9cc}}
.badge b{{color:#e6e9f0}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px;margin-top:34px}}
.card{{background:#161d2e;border:1px solid #24304a;border-radius:14px;padding:22px;text-decoration:none;color:inherit;transition:transform .15s,border-color .15s}}
.card:hover{{transform:translateY(-3px);border-color:#3b5a8a}}
.card .ic{{font-size:26px}} .card h2{{font-size:19px;margin:12px 0 6px;color:#7cb3ff}} .card p{{font-size:13px;color:#8fa0b8;margin:0;line-height:1.6}}
.note{{background:#1a2233;border-radius:12px;padding:16px 20px;font-size:13px;color:#aeb9cc;margin-top:36px}}
.note b{{color:#e6e9f0}}
a{{color:#7cb3ff}}
</style></head><body><div class="wrap">
<h1>现代大语言模型发展史 · 知识库</h1>
<p class="sub">{tagline_head} —— {tagline_tail}</p>
<div class="badges">
<span class="badge"><b>{total}</b> 个关键节点</span>
<span class="badge">P3×{p3} / P2×{p2} / P1×{p1}</span>
<span class="badge">{lanes} 条技术线</span>
<span class="badge">五时代 · 六层解读</span>
</div>
<div class="cards">
<a class="card" href="timeline.html"><div class="ic">🛤️</div><h2>多技术线泳道图</h2><p>横向泳道式展示 <b>{lanes} 条技术线</b>（架构/预训练/对齐/推理/长上下文/多模态/Agent/工程/开源）并行发展，节点按时间轴排列，P3 高亮，交叉节点标多线，悬停/点击/关系连线高亮交互。**展示发展史主线的主视图。**</p></a>
<a class="card" href="list.html"><div class="ic">📋</div><h2>卡片列表视图</h2><p>按时代分组的逐篇卡片，可筛选时代/优先级，查看完整标题/机构/贡献/背景档案，与泳道图一键互切，便于逐篇检索。</p></a>
<a class="card" href="analysis/index.html"><div class="ic">📚</div><h2>深度解读总览</h2><p>{total} 篇六层深度解读（问题定位→概念内核→方法拆解→证据链→批判→启示），点击进入各篇 HTML 阅读版</p></a>
<a class="card" href="{cta_href}"><div class="ic">📁</div><h2>论文库 README</h2><p>全量索引（{total} 篇论文表 + 五时代综述 + 技术线说明 + 信源口径）、命名规则、Git LFS 克隆与数据获取说明</p></a>
</div>
<div class="note"><b>克隆说明：</b>本仓库论文 PDF 使用 <b>Git LFS</b> 托管，克隆需先安装 <code>git-lfs</code> 并执行 <code>git lfs pull</code> 才能拉取 PDF。<b>在线下载：</b>在泳道图/列表图或任意深度解读页的「PDF下载」链接（media.githubusercontent.com 直链）可直接获取完整论文；纯解读与索引文件（HTML/MD）无需 LFS，可直接浏览本 Pages 站点。</div>
</div></body></html>
"""

CTA = {"legacy": "../README.md", "report": "report.html"}


class GuardError(Exception):
    """护栏拒写（exit 3）。"""


def load_json(path, label):
    if not os.path.isfile(path):
        raise GuardError("%s 不存在：%s" % (label, path))
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        raise GuardError("%s 非法 JSON：%s" % (label, exc))


def home_facts(repo):
    """首页的派生量：全部来自仓内数据件，⛔ 不写死。"""
    master = load_json(os.path.join(repo, "data", "papers_master.json"), "papers_master.json")
    lanes_data = load_json(os.path.join(repo, "data", "papers_lanes.json"), "papers_lanes.json")
    papers = master.get("papers") or []
    if not papers:
        raise GuardError("papers_master.json 无 papers ⇒ 拒跑（空集守卫）")
    pri = master.get("priority") or {}
    lane_keys = {r.get("line") for r in (lanes_data.get("lanes") or []) if r.get("line")}
    if not lane_keys:
        raise GuardError("papers_lanes.json 无 line 字段 ⇒ 拒跑（空集守卫）")
    return {"total": master.get("total") or len(papers),
            "p3": pri.get("P3", 0), "p2": pri.get("P2", 0), "p1": pri.get("P1", 0),
            "lanes": len(lane_keys)}


def generate(repo, cta="report"):
    if cta not in CTA:
        raise GuardError("未知的 --cta 取值：%r（可选 %s）" % (cta, sorted(CTA)))
    f = home_facts(repo)
    return TEMPLATE.format(tagline_head=TAGLINE_HEAD, tagline_tail=TAGLINE_TAIL,
                           cta_href=CTA[cta], **f), f


def deannotate(text):
    """把后处理器（`data/annotate_products.py`）的写入面**可逆地**还原。

    ★ 为什么需要：构建顺序是 `gen_home.py → annotate_products.py`，盘上文件必然带注解
      （令牌标记区 + `var()` 替换）。要让首页生成器能自证「我产出的就是盘上那一份」，
      必须能在**不读盘上生成物作为模板**的前提下做逆向对账。
    可逆性前提：值注册表（`data/token-baseline.json#palette`）+ 值件 site_token_names 都在仓内。
    """
    import re
    base = load_json(os.path.join(HERE, "token-baseline.json"), "改动前令牌基线")
    val = load_json(os.path.join(REPO, "vendor", "pipeline", "values",
                                 "llm-papers-knowledge-base.json"), "站点值件")
    name2val = {n: v for v, n in (base.get("palette") or {}).items()}
    fams = list((val.get("palettes") or {}).values())
    if fams:
        vals = fams[0].get("values") or {}
        for role, tok in ((val.get("binding") or {}).get("site_token_names") or {}).items():
            if role in vals:
                v = vals[role]
                name2val.setdefault(tok, v.get("light") if isinstance(v, dict) else v)
    out = re.sub(r"/\* LP:TOKENS:BEGIN \*/.*?/\* LP:TOKENS:END \*/", "", text, flags=re.S)
    out = re.sub(r"/\* LP:NAVCSS:BEGIN \*/.*?/\* LP:NAVCSS:END \*/", "", out, flags=re.S)
    out = re.sub(r"<!-- LP:NAV:BEGIN -->.*?<!-- LP:NAV:END -->", "", out, flags=re.S)
    out = re.sub(r":root\s*\{\s*\}", "", out)
    def back(m):
        return name2val.get(m.group(1), m.group(0))
    out = re.sub(r"var\(\s*(--[A-Za-z0-9_-]+)\s*\)", back, out)
    return out


def selftest():
    cases = []

    def case(name, ok):
        cases.append((name, bool(ok)))

    repo = REPO
    body, f = generate(repo, "report")
    case("派生量非空（total/P3/P2/P1/技术线）",
         f["total"] > 0 and f["p3"] > 0 and f["p2"] > 0 and f["p1"] > 0 and f["lanes"] > 0)
    case("派生量自洽：P3+P2+P1 == total", f["p3"] + f["p2"] + f["p1"] == f["total"])
    case("Q5=A：默认 CTA 指向 report.html（⛔ 不是 ../README.md）",
         'href="report.html"' in body and "../README.md" not in body)
    legacy, _ = generate(repo, "legacy")
    case("等价性入口：--cta legacy 保留 ../README.md（供与 HEAD 逐字节比对）",
         'href="../README.md"' in legacy)
    case("两版仅差 1 处（Q5 的那条 href）",
         legacy.replace('href="../README.md"', 'href="report.html"') == body)
    # 负例：未知 cta 必须护栏拒跑，⛔ 不静默回落
    try:
        generate(repo, "nope")
        case("负例·护栏：未知 --cta 必须拒跑", False)
    except GuardError:
        case("负例·护栏：未知 --cta 必须拒跑", True)
    # 负例：空集守卫（数据件缺 papers）
    import tempfile, shutil
    tmp = tempfile.mkdtemp(prefix="lp-home-")
    try:
        os.makedirs(os.path.join(tmp, "data"))
        json.dump({"total": 0, "papers": []}, open(os.path.join(tmp, "data", "papers_master.json"), "w"))
        json.dump({"lanes": []}, open(os.path.join(tmp, "data", "papers_lanes.json"), "w"))
        try:
            generate(tmp, "report")
            case("负例·空集：papers 为空必须拒跑", False)
        except GuardError:
            case("负例·空集：papers 为空必须拒跑", True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    ok = all(v for _, v in cases)
    for n, v in cases:
        print("  [%s] %s" % ("PASS" if v else "FAIL", n))
    print("\n=== gen_home 自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--cta", default="report", choices=sorted(CTA))
    ap.add_argument("--out", default=None)
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    try:
        body, facts = generate(a.repo, a.cta)
    except GuardError as exc:
        print("GUARD-REJECT: %s" % exc)
        return 3
    if a.stdout:
        sys.stdout.write(body)
        return 0
    out = a.out or (OUT_PATH if os.path.abspath(a.repo) == REPO
                    else os.path.join(a.repo, "docs", "index.html"))
    if a.check:
        if not os.path.isfile(out):
            print("GUARD-REJECT: 盘上首页不存在：%s" % out)
            return 3
        cur = deannotate(open(out, encoding="utf-8").read())
        same = cur == body
        print("check: %s" % ("一致（反注解后与生成结果逐字节相同）" if same else "漂移"))
        if not same:
            import difflib
            for line in list(difflib.unified_diff(cur.split("\n"), body.split("\n"),
                                                  "on-disk(deannotated)", "generated", lineterm=""))[:40]:
                print(line)
        return 0 if same else 1
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(body)
    print("首页已生成：%s（%d B；%d 个节点 / P3×%d P2×%d P1×%d / %d 条技术线；cta=%s）"
          % (out, len(body.encode("utf-8")), facts["total"], facts["p3"], facts["p2"],
             facts["p1"], facts["lanes"], a.cta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
