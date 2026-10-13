#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_workflow_contract.py — ADR-003 三 job 模板的**渲染器 + 静态契约门控**（批 D 共通件）。

用法：
    python3 check_workflow_contract.py --render --profile P --out O            # 按 profile 展开实例
    python3 check_workflow_contract.py --check O [--json]                      # 静态契约判据
    python3 check_workflow_contract.py --render --profile P | --check -       # 渲染并直接判
    python3 check_workflow_contract.py --selftest

判据（全部来自 ADR-003 的成文条款，⛔ 不由本件自创）：
  W1 YAML 可解析
  W2 job 集合**恰为** {build, gate, deploy}（条款五）
  W3 `deploy.needs` 指向 gate，⛔ 不得只依赖 build（条款五 ①）
  W4 `gate.needs` 指向 build（条款五：gate 只对**刚构建出的**发布目录跑）
  W5 `upload-pages-artifact` 恰出现 1 次，且在 deploy 内；门控（gate job）必须先于部署（条款五 ②）
  W6 `.nojekyll` 由 **build** job 产出（条款四）
  W7 ⛔ deploy/gate 无写回仓通道：全文无 `contents: write`、无 `git push`、无 `git commit`（条款五 ③）
  W8 最小权限：顶层只 `contents: read`；pages/id-token 写权限**只在** deploy（条款五 ③）
  W9 渲染后无残留占位符 `__…__`；发布目录来自参数（条款三），且不得是仓外绝对路径（条款六）

★ 判据强度上限（如实声明）：本件是**静态**判据，**不证**三 job 在真实 GitHub Actions 上跑得通
 （本机无 actionlint，亦不触网跑 Actions）。该未覆盖面须在清单里声明。
退出码：0 全过 / 1 有 FAIL / 2 输入错误
"""
import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import derive_site_tokens as D  # noqa: E402

TEMPLATE = os.path.join(HERE, "workflow-3job.template.yml")
PLACEHOLDER = re.compile(r"__[A-Z_]+__")


def render(profile, template_path=TEMPLATE):
    """按 profile 展开模板；多行命令占位符按出现列缩进。"""
    tpl = open(template_path, encoding="utf-8").read()
    cmds = {
        "__GENERATOR_COMMANDS__": profile.get("generator_commands") or ["echo '无生成器（手工站）'"],
        "__GATE_COMMANDS__": profile["gates"]["commands"],
    }
    for key, lines in cmds.items():
        ind = None
        for line in tpl.splitlines():
            if key in line:
                ind = " " * line.index(key)
                break
        if ind is None:
            raise D.GuardError("W9 模板缺少占位符 %s" % key)
        body = "\n".join(ind + str(x) for x in lines)
        tpl = tpl.replace(ind + key, body)
    simple = {
        "__SITE__": re.sub(r"[^a-zA-Z0-9._-]", "-", profile["site"]),
        "__DEFAULT_BRANCH__": profile.get("default_branch") or "main",
        "__PYTHON__": profile.get("python_version") or "3.11",
        "__BUILD_CWD__": profile.get("build_cwd") or ".",
        "__PUBLISH_DIR__": profile.get("publish_dir") or ".",
    }
    for k, v in simple.items():
        tpl = tpl.replace(k, str(v))
    left = sorted(set(PLACEHOLDER.findall(tpl)))
    if left:
        raise D.GuardError("W9 渲染后仍残留占位符：%s" % left)
    return tpl


def check(text):
    R = []

    def add(cid, name, ok, detail):
        R.append((cid, name, ok, detail))

    try:
        import yaml
    except ImportError:
        add("W1", "YAML 可解析", False, "pyyaml 不可用（⛔ 不得静默跳过）")
        return R
    try:
        doc = yaml.safe_load(text)
    except Exception as exc:  # noqa: BLE001
        add("W1", "YAML 可解析", False, str(exc)[:160])
        return R
    add("W1", "YAML 可解析", isinstance(doc, dict), "解析为对象" if isinstance(doc, dict) else "非对象")
    if not isinstance(doc, dict):
        return R

    jobs = doc.get("jobs") or {}
    add("W2", "job 集合恰为 {build, gate, deploy}", set(jobs) == {"build", "gate", "deploy"},
        "实测：%s" % sorted(jobs))

    dep = (jobs.get("deploy") or {}).get("needs")
    dep_needs = dep if isinstance(dep, list) else ([dep] if dep else [])
    add("W3", "deploy.needs 指向 gate（⛔ 不得只依赖 build）", dep_needs == ["gate"],
        "deploy.needs=%s" % dep_needs)

    gneeds = (jobs.get("gate") or {}).get("needs")
    gneeds = gneeds if isinstance(gneeds, list) else ([gneeds] if gneeds else [])
    add("W4", "gate.needs 指向 build", gneeds == ["build"], "gate.needs=%s" % gneeds)

    def uses_list(job):
        return [s.get("uses", "") for s in (jobs.get(job) or {}).get("steps", []) or []]

    up = [u for u in uses_list("deploy") if "upload-pages-artifact" in u]
    up_all = [u for j in jobs for u in uses_list(j) if "upload-pages-artifact" in u]
    dep_up = [u for u in uses_list("gate") if "upload-pages-artifact" in u]
    ok5 = len(up_all) == 1 and len(up) == 1 and not dep_up and jobs.get("deploy", {}).get("needs") == "gate"
    add("W5", "upload-pages-artifact 恰 1 次且在 deploy 内（门控先于部署）", ok5,
        "全文件 %d 次 / deploy %d 次 / gate %d 次" % (len(up_all), len(up), len(dep_up)))

    def runs(job):
        return " ".join(str(s.get("run", "")) + " " + str(s.get("working-directory", "")) +
                        " " + str(s.get("name", ""))
                        for s in (jobs.get(job) or {}).get("steps", []) or [])

    add("W6", ".nojekyll 由 build 产出（条款四）", ".nojekyll" in runs("build"),
        "build 步骤是否含 .nojekyll：%s" % (".nojekyll" in runs("build")))

    # ★ 只扫**有效 YAML**：注释行里出现这些字样（模板自己的说明）不算写回通道（SH5 §4.0 第 1 条：
    #   判据对象是「流水线里有没有写回动作」，不是「文本里有没有这个字符串」）。
    code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
    low = code.lower()
    wb = [k for k in ("contents: write", "git push", "git commit") if k in low]
    add("W7", "⛔ 无写回仓通道（contents: write / git push / git commit）", not wb,
        "命中：%s" % wb if wb else "无写回通道")

    top = doc.get("permissions") or {}
    dj = (jobs.get("deploy") or {}).get("permissions") or {}
    ok8 = (set(top) == {"contents"} and top.get("contents") == "read"
           and dj.get("pages") == "write" and dj.get("id-token") == "write")
    add("W8", "最小权限（顶层仅 contents:read；pages/id-token 只在 deploy）", ok8,
        "top=%s deploy=%s" % (top, dj))

    left = sorted(set(PLACEHOLDER.findall(text)))
    pd = re.search(r'path:\s*([^\s]+)', text)
    abs_out = bool(re.search(r"touch\s+\"/", text)) or bool(re.search(r"path:\s*/(?:home|Users|mnt)/", text))
    add("W9", "无残留占位符 + 发布目录为参数且非仓外绝对路径（条款三/六）",
        not left and not abs_out, "残留=%s 仓外绝对路径=%s" % (left, abs_out))

    return R


def selftest():
    base = render({
        "site": "demo-site", "default_branch": "master", "publish_dir": "docs",
        "build_cwd": "07-checkpoint", "generator_commands": ["python3 gen.py"],
        "gates": {"commands": ["python3 check_site_tokens.py --all"]},
    })
    cases = []

    def case(name, mutate, cid, expect_fail=True):
        t = mutate(base)
        R = check(t)
        got = {r[0]: r[2] for r in R}
        cases.append((name, (got.get(cid, False) is False) if expect_fail else bool(got.get(cid))))

    case("正向夹具（渲染实例）应 0 FAIL", lambda t: t, "W1", expect_fail=False)
    R = check(base)
    cases.append(("正向夹具全过", all(r[2] for r in R)))
    case("W1 负例：YAML 语法错误", lambda t: t + "\n  bad: [", "W1")
    case("W2 负例：多了一个 job", lambda t: t.replace("  deploy:", "  extra:\n    runs-on: ubuntu-latest\n  deploy:"), "W2")
    case("W3 负例：deploy.needs 改成 build", lambda t: t.replace("    needs: gate", "    needs: build"), "W3")
    case("W5 负例：把 Pages 上传挪到 gate", lambda t: t.replace(
        "      - name: 门控（硬阻断集；任一 FAIL 即让本 job 失败）",
        "      - uses: actions/upload-pages-artifact@v3\n        with:\n          path: docs\n"
        "      - name: 门控（硬阻断集；任一 FAIL 即让本 job 失败）"), "W5")
    case("W7 负例：出现写回通道（git push）",
         lambda t: t.replace("        run: touch \"docs/.nojekyll\"",
                             "        run: touch \"docs/.nojekyll\" && git push"), "W7")
    case("W7 负例：顶层 permissions 含 contents: write",
         lambda t: t.replace("  contents: read", "  contents: write"), "W7")
    case("W8 负例：deploy 缺 id-token", lambda t: t.replace("      id-token: write\n", ""), "W8")
    case("W9 负例：残留占位符", lambda t: t + "\n# __OOPS__\n", "W9")

    # 渲染器负例：缺占位符的模板
    def bad_tpl():
        p = os.path.join(HERE, "_tmp_bad_tpl.yml")
        open(p, "w", encoding="utf-8").write("jobs:\n  build:\n    steps:\n      - run: |\n")
        try:
            render({"site": "x", "publish_dir": ".", "gates": {"commands": ["x"]}}, p)
        finally:
            os.remove(p)
    try:
        bad_tpl()
        cases.append(("渲染器负例（缺占位符模板应拒渲染）", False))
    except D.GuardError:
        cases.append(("渲染器负例（缺占位符模板应拒渲染）", True))

    ok = all(v for _, v in cases)
    for name, res in cases:
        print("  [%s] %s" % ("PASS" if res else "FAIL", name))
    print("\n=== 三 job 模板静态契约自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--profile")
    ap.add_argument("--out")
    ap.add_argument("--check")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    text = None
    if a.render:
        try:
            profile = D.load_json(a.profile, "profile")
            text = render(profile)
        except D.GuardError as exc:
            print("GUARD-REJECT: %s" % exc)
            return 3
        if a.out:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write(text)
            print("已渲染：%s（%d B）" % (a.out, len(text.encode())))
    if a.check and a.check != "-":
        text = open(a.check, encoding="utf-8").read()
    if text is None:
        print("用法错误：需 --render 或 --check")
        return 2
    R = check(text)
    for cid, name, ok, detail in R:
        print("[%s] %s %s — %s" % ("PASS" if ok else "FAIL", cid, name, detail))
    if a.json:
        print(json.dumps([{"id": c, "name": n, "ok": o, "detail": d} for c, n, o, d in R],
                         ensure_ascii=False, indent=1))
    nf = sum(1 for r in R if not r[2])
    print("\n=== 三 job 静态契约：%d 项判据，%d FAIL ===" % (len(R), nf))
    return 0 if nf == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
