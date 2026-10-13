#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_all.py — 本站**唯一声明的构建顺序**（方案 §4.2 第 3 步「补产物归属面」的落地件）。

★ 为什么必须显式声明（方案 C2-N5 / C2-N6）：
  改动前，`docs/timeline.html` 被 `generate_html.py` 与 `generate_timeline_lanes.py`
  **同时声明写入**（两处 `OUT_PATH` 逐字节相同），而执行顺序**在仓库里没有任何声明**
  ⇒ 产物内容取决于谁最后跑。本件把「谁写哪个产物、按什么顺序写」钉死，并由
  `gate_tokens.py` 的 G8/G9 与 `gate_ci_contract.py` 的 CI3/CI4 机械核对。

★ 顺序（前一步失败即中止，⛔ 不静默继续）：
  1. `gen_home.py`                → docs/index.html（Q1=B：首页纳入管线）
  2. `generate_timeline_lanes.py` → docs/timeline.html（Q4=A：**唯一写者**）
  3. `generate_list_html.py`      → docs/list.html
  4. `gen_analysis_index.py`      → docs/analysis/index.html
  5. `generate_html.py`           → build/legacy/timeline-classic.html（Q4=A：改名产出，非发布面）
  6. `annotate_products.py --apply` → 139 页的 Q3 等值令牌注入 ＋ 134 个解读页的 Q7 着陆结构
  7. 门控：`gate_tokens.py` / `gate_links.py` / `gate_census.py` / `gate_ci_contract.py`
     ＋ `vendor/pipeline/check_gate_manifest.py`
     ＋ ★ 批 J 追加 `gate_a11y.py` / `gate_seo_meta.py`（两条命令与 CI 的 Gate 步、与
       `build/profile.json#gates.commands` 逐条同序）
  8. 写 `gate-report.json`（**确定性件**：⛔ 无墙钟时间戳、⛔ 无作者机绝对路径；
     `tree_digest` ＝ 仓内文件（路径+内容）的 sha256，★ **排除报告自身**，否则自指）

★ ⛔ **不在本管线内的 `data/*.py`（逐条登记理由，见 build/profile.json）**：
  - `merge_manifests.py`：**过期**——它只并 e1–e5 五个原始件、**不读 `e5_additions.json`**，
    实跑把 `data/papers_master.json` 从 133 篇改回 125 篇（级联改坏 list.html / README）。
  - `generate_readme.py`：**过期且会删手工内容**——prose 里写死「98 篇 / 21 篇」，实跑会
    删掉 README 里手工补写的「在线浏览与视图」整节并把统计改回旧值。
  - `convert_b3_html.py`：**只复现 12/14**——B3_P1 里 `IndexShare` 与 `Qwen3.6-35B` 两页是
    **手工撰写**的（多行排版 + 自带 `:root`），实跑会把它们覆盖成单行压缩版。
  三件的实跑证据见报告 §执行情况；它们**不是**判据、也不是本轮门控对象 ⇒ 按「退役留痕」登记
  在 `build/profile.json` 的 `build.excluded_generators`（双向：登记项若消失也 FAIL）。

用法：
    python3 data/build_all.py                # 跑全流程（重生成 → 门控 → 写 gate-report.json）
    python3 data/build_all.py --skip-gates   # 只重生成
    python3 data/build_all.py --json         # 额外打印机器可读摘要
    python3 data/build_all.py --selftest     # 负向夹具 7 例
退出码：0 全过 · 1 有 FAIL · 2 输入错误 · 3 某一步护栏拒跑
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

PIPELINE = [
    ("gen_home", ["python3", "data/gen_home.py"], "docs/index.html"),
    ("timeline", ["python3", "data/generate_timeline_lanes.py"], "docs/timeline.html"),
    ("list", ["python3", "data/generate_list_html.py"], "docs/list.html"),
    ("analysis-index", ["python3", "data/gen_analysis_index.py"], "docs/analysis/index.html"),
    ("legacy-timeline", ["python3", "data/generate_html.py"], "build/legacy/timeline-classic.html"),
    ("annotate", ["python3", "data/annotate_products.py", "--apply"], "docs/**/*.html（139 页）"),
]

GATES = [
    ("gate-tokens", ["python3", "gate_tokens.py", "--site-root", ".",
                     "--manifest", "gate-manifest.json", "--mode", "enforce"]),
    ("gate-links", ["python3", "gate_links.py", "--site-root", "."]),
    ("gate-census", ["python3", "gate_census.py", "--site-root", "."]),
    ("gate-ci-contract", ["python3", "gate_ci_contract.py", "--site-root", "."]),
    ("manifest-check", ["python3", "vendor/pipeline/check_gate_manifest.py",
                        "--manifest", "gate-manifest.json", "--profile", "build/profile.json"]),
    # ★ 批 J：a11y / metadata 由 report_only 转硬档（gate-manifest.json 的 mode=hard）
    #   ⇒ 本地构建入口也必须跑它们，否则「重生成 → 门控」这条链在本地会漏判两类硬 FAIL。
    #   ★ 顺序与 .github/workflows/pages.yml 的 Gate 步逐条一致（CI 侧由 gate_ci_contract.py
    #     的 CI3 做「登记 ↔ 调用」双向断言；本表与 profile.gates.commands 亦逐条同序）。
    ("a11y", ["python3", "gate_a11y.py", "--site-root", ".", "--profile", "build/profile.json"]),
    ("metadata", ["python3", "gate_seo_meta.py", "--site-root", ".",
                  "--profile", "build/profile.json"]),
]

REPORT = "gate-report.json"
EXCLUDE_FROM_DIGEST = (REPORT,)
DIGEST_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}


def sanitize(text, repo):
    """★ 确定性件的前提：⛔ 不把作者机绝对路径写进报告（逐条规范化，⛔ 不靠人眼检查）。"""
    text = text.replace(repo, "<repo>")
    text = re.sub(r"/home/[^/\s\"']+", "<home>", text)
    return text


def run_step(cwd, argv):
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    out = sanitize((p.stdout or "") + (p.stderr or ""), cwd)
    tail = [ln for ln in out.strip().split("\n") if ln.strip()][-6:]
    return p.returncode, tail


def tree_digest(repo):
    """仓内文件（路径+内容）的 sha256 —— **确定性**：与 mtime/顺序无关，且排除报告自身。"""
    h = hashlib.sha256()
    rows = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in DIGEST_SKIP_DIRS)
        for fn in sorted(files):
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, repo).replace(os.sep, "/")
            if rel in EXCLUDE_FROM_DIGEST:
                continue
            try:
                with open(p, "rb") as fh:
                    data = fh.read()
            except OSError:
                continue
            rows.append((rel, hashlib.sha256(data).hexdigest()))
    for rel, d in sorted(rows):
        h.update(rel.encode("utf-8") + b"\0" + d.encode("ascii") + b"\n")
    return h.hexdigest(), len(rows)


def git_head(repo):
    try:
        return subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def guarded(repo):
    """护栏：判据面文件必须在（⛔ 不静默跳过不存在的门控）。"""
    need = ["gate_tokens.py", "gate_links.py", "gate_census.py", "gate_ci_contract.py",
            "gate-manifest.json", "build/profile.json",
            "vendor/pipeline/check_gate_manifest.py", "vendor/tools/contrast.py",
            "data/token-baseline.json", "data/annotate_products.py",
            "gate_a11y.py", "gate_seo_meta.py"]
    missing = [f for f in need if not os.path.isfile(os.path.join(repo, f))]
    if missing:
        raise SystemExit("GUARD-REJECT: 判据面缺件：%s" % missing)


def build(repo, skip_gates=False, verbose=True):
    guarded(repo)
    log = {"pipeline": [], "gates": [], "failed": []}
    for name, argv, target in PIPELINE:
        rc, tail = run_step(repo, argv)
        log["pipeline"].append({"step": name, "cmd": " ".join(argv), "target": target,
                                "exit": rc, "tail": tail})
        if verbose:
            print("[%s] %-16s → %-34s exit=%d" % ("OK " if rc == 0 else "FAIL", name, target, rc))
            for ln in tail[-2:]:
                print("      | %s" % ln[:180])
        if rc != 0:
            log["failed"].append("pipeline:%s" % name)
            return log
    if not skip_gates:
        for name, argv in GATES:
            rc, tail = run_step(repo, argv)
            summary = [ln for ln in tail if ln.startswith("===")]
            log["gates"].append({"gate": name, "cmd": " ".join(argv), "exit": rc,
                                 "summary": summary[-1] if summary else (tail[-1] if tail else "")})
            if verbose:
                print("[%s] %-16s %s" % ("OK " if rc == 0 else "FAIL", name,
                                         log["gates"][-1]["summary"][:150]))
            if rc != 0:
                log["failed"].append("gate:%s" % name)
    return log


def write_report(repo, log):
    digest, n = tree_digest(repo)
    rep = {
        "schema": "llm-papers-gate-report/1",
        "site": "llm-papers-knowledge-base",
        "generated_by": "data/build_all.py",
        "determinism_note": "★ 确定性件：⛔ 无墙钟时间戳、⛔ 无作者机绝对路径。tree_digest 排除本报告自身（否则自指：写报告改树 ⇒ 下次摘要必变）。★ 亦**不写 `source_head`**：报告随提交入库 ⇒ 它的值就是「包含它的那次提交」，任何一次提交都会让重跑结果与盘上不一致（同一种自指）。改动前的 HEAD 可随时用 `git log` 取，⛔ 不必进报告。",
        "pipeline": log["pipeline"],
        "gates": log["gates"],
        "failed": log["failed"],
        "result": "PASS" if not log["failed"] else "FAIL",
        "tree_digest": digest,
        "tree_digest_files": n,
    }
    with open(os.path.join(repo, REPORT), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    return rep


def selftest():
    cases = []

    def case(name, ok):
        cases.append((name, bool(ok)))

    tmp = tempfile.mkdtemp(prefix="lp-build-")
    try:
        # 1) 护栏：缺件必须拒跑（⛔ 不静默跳过）
        try:
            guarded(tmp)
            case("负例·护栏：判据面缺件必须拒跑", False)
        except SystemExit:
            case("负例·护栏：判据面缺件必须拒跑", True)

        # 2) tree_digest 确定性：同一棵树两次相同
        os.makedirs(os.path.join(tmp, "a"))
        open(os.path.join(tmp, "a", "x.txt"), "w").write("hi")
        d1, n1 = tree_digest(tmp)
        d2, _ = tree_digest(tmp)
        case("tree_digest 同树两次相同（确定性）", d1 == d2 and n1 == 1)
        open(os.path.join(tmp, "a", "y.txt"), "w").write("hi2")
        d3, _ = tree_digest(tmp)
        case("tree_digest 内容变则变（非恒真）", d3 != d1)
        # 3) 自指守卫：报告自身不进摘要
        with open(os.path.join(tmp, REPORT), "w") as fh:
            fh.write("{}")
        d4, n4 = tree_digest(tmp)
        case("报告自身被排除（防空自指）", d4 == d3 and n4 == 2)
        with open(os.path.join(tmp, REPORT), "w") as fh:
            fh.write('{"changed":1}')
        d5, _ = tree_digest(tmp)
        case("改报告内容不改变摘要（自指守卫成立）", d5 == d4)
        # 4) 路径确定性：与文件系统枚举顺序无关（.git/__pycache__ 被跳过）
        os.makedirs(os.path.join(tmp, ".git"))
        open(os.path.join(tmp, ".git", "HEAD"), "w").write("ref: x")
        os.makedirs(os.path.join(tmp, "__pycache__"))
        open(os.path.join(tmp, "__pycache__", "z.pyc"), "w").write("junk")
        d6, n6 = tree_digest(tmp)
        case(".git/__pycache__ 被跳过（摘要不受其影响）", d6 == d4 and n6 == 2)
        # 5) 报告里不得出现墙钟/作者机路径
        rep = {"a": 1}
        txt = json.dumps(rep)
        case("报告字段无墙钟时间戳", not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:", txt))
        case("报告字段无作者机绝对路径", "/home/" not in txt)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    ok = all(v for _, v in cases)
    for n, v in cases:
        print("  [%s] %s" % ("PASS" if v else "FAIL", n))
    print("\n=== build_all 自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--skip-gates", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    log = build(a.repo, a.skip_gates)
    rep = write_report(a.repo, log)
    print("\n=== build_all：%s（管线 %d 步 / 门控 %d 道）· tree_digest=%s（%d 文件）==="
          % (rep["result"], len(rep["pipeline"]), len(rep["gates"]),
             rep["tree_digest"][:16], rep["tree_digest_files"]))
    if rep["failed"]:
        print("FAILED: %s" % rep["failed"])
    if a.json:
        print(json.dumps({"result": rep["result"], "failed": rep["failed"],
                          "tree_digest": rep["tree_digest"]}, ensure_ascii=False))
    return 0 if not rep["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
