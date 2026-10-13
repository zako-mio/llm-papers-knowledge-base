#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_ci_contract.py — **CI 步骤序 + 管线/登记表双向一致性**门控（Q1/Q4/Q6 与 §4.1 落点的机检）。

★ 本件存在的理由（`CONTINUE-PROMPT-G.md` §4.1 的**位置硬约束**）：
  门控必须落在「**重生成之后 / 回写 master 之前**」。放在重生成**之前**＝判的是上一版产物；
  放在回写**之后**＝坏产物已经进 master。★ 本站的 `pages.yml` **没有回写 master 的步骤**
  （ADR-003 的发布形态未被收敛，产物不入库、CI 只上传 artifact）⇒ 「回写」的等价物是
  **发布步**（`upload-pages-artifact` / `deploy-pages`）。本件**显式声明这个 N/A**，
  ⛔ 不新建回写步（那会改发布形态，属常设排除项）。

判据（7 条）：
  CI1 [blind] 空集守卫：workflow 存在且解析出 ≥1 step；CI4 的登记面非空
  CI2 [hard]  步骤序 **Rebuild < Gate < Publish**（Publish 口径见上；顺序按**有效 YAML**求，
              ⛔ 不把注释里的字样当写回通道）
  CI3 [hard]  登记 ↔ 调用**双向**：gate-manifest 的每个脚本必须在 CI 的 Gate 步里被调用；
              CI Gate 步里出现的 `*.py` 必须已在清单登记
  CI4 [hard]  `data/*.py` **三分登记双向**：每个生成器/巡检件必须恰在
              `build.pipeline` ∪ `build.inspectors` ∪ `build.excluded_generators` 之一；
              登记项必须真的存在（防登记过期）
  CI5 [hard]  Rebuild 步必须**真的调用**构建入口（`data/build_all.py`）且列出的生成器与
              `build.pipeline` 声明一致
  CI6 [hard]  CI 的 Gate 步必须调用 `vendor/pipeline/check_gate_manifest.py`（清单守门人也在 CI 里跑）
  CI7 [report] CI 变更面（仅报告）：workflow 文件 sha256、step 清单

用法：
    python3 gate_ci_contract.py --site-root .
    python3 gate_ci_contract.py --site-root . --json
    python3 gate_ci_contract.py --selftest
退出码：0 全过 · 1 有 FAIL · 2 输入错误 · 3 护栏拒读
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

WORKFLOW = ".github/workflows/pages.yml"
PY_RE = re.compile(r"[A-Za-z0-9_./-]+\.py")
BLIND, HARD, REPORT = "blind", "hard", "report"


class GateError(Exception):
    pass


def load_json(path, label):
    if not os.path.isfile(path):
        raise GateError("%s 不存在：%s" % (label, path))
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        raise GateError("%s 非法 JSON：%s" % (label, exc))


def steps_of(text):
    """取**有效 YAML** 的 job→steps 列表（`SH5 §4.0` 第 1 条：⛔ 不把注释里的字样当写回通道）。

    ★ 口径只有一种：**真 YAML 解析**。无 pyyaml 时**护栏拒读**（exit 3），
      ⛔ 不退回「手写块解析」——手写解析把 `with:` 子键与 job 边界读错，
      会产出**看起来跑得通、实际判错序**的假绿（本件在开发中实测到过，故不保留该退化路径）。
      CI 侧由 workflow 的 Gate 步显式 `pip install pyyaml` 保证可用。
    """
    try:
        import yaml  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        raise GateError("需要 pyyaml（有效 YAML 口径）：%s" % exc)
    doc = yaml.safe_load(text)
    out = []
    for job, spec in (doc.get("jobs") or {}).items():
        for st in (spec or {}).get("steps") or []:
            name = st.get("name") or st.get("uses") or ""
            run = st.get("run") or st.get("uses") or ""
            out.append((job, name, run))
    return out, "pyyaml", "有效 YAML（注释与块标量按语法求值；⛔ 无降级解析路径）"


def build_all_pipeline(root):
    """★ 从 `data/build_all.py` 的 **ast** 求值面取构建顺序（⛔ 不靠正则读字符串）。"""
    import ast  # noqa: PLC0415
    p = os.path.join(root, "data", "build_all.py")
    if not os.path.isfile(p):
        return None
    try:
        tree = ast.parse(open(p, encoding="utf-8").read())
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "PIPELINE" for t in node.targets):
            if isinstance(node.value, ast.List):
                out = []
                for el in node.value.elts:
                    if isinstance(el, ast.Tuple) and len(el.elts) >= 2:
                        cmd = el.elts[1]
                        if isinstance(cmd, ast.List):
                            strs = [x.value for x in cmd.elts
                                    if isinstance(x, ast.Constant) and isinstance(x.value, str)]
                            out.append(" ".join(strs))
                return out
    return None


def check(root, manifest, profile):
    R = []

    def add(cid, name, cls, ok, detail):
        R.append({"id": cid, "name": name, "class": cls, "ok": bool(ok), "detail": detail})

    wf_path = os.path.join(root, WORKFLOW)
    if not os.path.isfile(wf_path):
        raise GateError("workflow 不存在：%s" % WORKFLOW)
    text = open(wf_path, encoding="utf-8").read()
    steps, parser, note = steps_of(text)
    pipeline = profile.get("build", {}).get("pipeline") or []
    inspectors = profile.get("build", {}).get("inspectors") or []
    excluded = profile.get("build", {}).get("excluded_generators") or []

    add("CI1", "空集守卫（steps ≥1 且构建登记面非空）", BLIND,
        bool(steps) and bool(pipeline),
        "steps %d（口径 %s）· pipeline %d 项 · inspectors %d 项 · excluded %d 项"
        % (len(steps), parser, len(pipeline), len(inspectors), len(excluded)))

    def idx(pred):
        for i, (_j, n, r) in enumerate(steps):
            if pred((n or "") + " " + (r or "")):
                return i
        return None

    i_re = idx(lambda s: re.search(r"build_all\.py", s))
    i_gate = idx(lambda s: re.search(r"gate_tokens\.py", s))
    i_pub = idx(lambda s: re.search(r"upload-pages-artifact|deploy-pages", s))
    ok2 = None not in (i_re, i_gate, i_pub) and i_re < i_gate < i_pub
    add("CI2", "步骤序 Rebuild < Gate < Publish（「回写 master」在本站 N/A，见件头）", HARD, ok2,
        "Rebuild@%s < Gate@%s < Publish@%s" % (i_re, i_gate, i_pub) if ok2
        else "顺序不满足：Rebuild=%s Gate=%s Publish=%s（steps=%s）"
        % (i_re, i_gate, i_pub, [n for _j, n, _r in steps]))

    # ★ 「Gate 步」的识别必须**以调用为准**：Rebuild 步的 `--skip-gates` 里也有 "gate" 字样，
    #   若按子串匹配就会把 Rebuild 步误当成 Gate 步（实测踩到 ⇒ 假 FAIL）。
    def is_gate_step(n, r):
        return bool(re.search(r"gate_tokens\.py", r or "")) or (n or "").strip().startswith("Gate")

    gate_step = " ".join((n or "") + " " + (r or "") for _j, n, r in steps if is_gate_step(n, r))
    registered = {os.path.basename(g.get("script", "")) for g in manifest.get("gates") or []}
    in_ci = {os.path.basename(m) for m in PY_RE.findall(gate_step)}
    miss = sorted(registered - in_ci)
    extra = sorted(in_ci - registered)
    add("CI3", "登记 ↔ CI 调用双向（清单项必须在 CI Gate 步被调用；CI 调用的必须登记）", HARD,
        not miss and not extra,
        ("清单登记但 CI 未调用：%s；" % miss if miss else "")
        + ("CI 调用但未登记：%s" % extra if extra else "")
        if (miss or extra) else "清单 %d 项与 CI Gate 步 %d 个脚本一一对应"
        % (len(registered), len(in_ci)))

    data_py = sorted(os.path.basename(p) for p in glob.glob(os.path.join(root, "data", "*.py")))
    reg = {}
    entry = os.path.basename(profile.get("build", {}).get("entry") or "")
    if entry:
        reg.setdefault(entry, []).append("entry")
    for group, items in (("pipeline", pipeline), ("inspectors", inspectors),
                         ("excluded_generators", excluded)):
        for it in items:
            reg.setdefault(os.path.basename(it if isinstance(it, str) else it.get("path", "")), []).append(group)
    unregistered = [f for f in data_py if f not in reg]
    multi = sorted(f for f, g in reg.items() if len(g) > 1)
    gone = sorted(f for f in reg if f not in data_py)
    add("CI4", "data/*.py 四分登记双向（entry ∪ pipeline ∪ inspectors ∪ excluded，恰属一类）", HARD,
        not unregistered and not multi and not gone,
        ("未登记：%s；" % unregistered if unregistered else "")
        + ("重复登记：%s；" % multi if multi else "")
        + ("登记过期（文件已不在）：%s" % gone if gone else "")
        if (unregistered or multi or gone)
        else "%d 个 data/*.py 全部恰属一类（entry 1 / pipeline %d / inspectors %d / excluded %d）"
        % (len(data_py), len(pipeline), len(inspectors), len(excluded)))

    reb = " ".join((n or "") + " " + (r or "") for _j, n, r in steps
                   if re.search(r"[Rr]ebuild|重新生成|构建", (n or "") + (r or "")))
    declared = [os.path.basename(x if isinstance(x, str) else x.get("path", "")) for x in pipeline]
    impl = build_all_pipeline(root)
    impl_base = [os.path.basename(PY_RE.findall(c)[0]) for c in (impl or []) if PY_RE.findall(c)]
    ok5 = (bool(re.search(r"build_all\.py", reb)) and impl is not None
           and impl_base == declared)
    add("CI5", "Rebuild 步调用 build_all.py 且其 ast 求值面 == build.pipeline 声明（双向）", HARD, ok5,
        "Rebuild 调 build_all.py=%s；build_all.PIPELINE=%s；profile.build.pipeline=%s"
        % (bool(re.search(r"build_all\.py", reb)), impl_base, declared))

    ok6 = "check_gate_manifest.py" in gate_step
    add("CI6", "CI Gate 步调用清单守门人 check_gate_manifest.py", HARD, ok6,
        "已调用" if ok6 else "缺失：CI 的 Gate 步未调用 vendor/pipeline/check_gate_manifest.py")

    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    # ★ CI8：vendor 薄副本的**逐文件 sha256 双向核对**（pipeline/README.md §四 的纪律：
    #   「各站副本的 sha256 应被该站清单登记」）——盘上未登记 ⇒ FAIL；登记漂移/过期 ⇒ FAIL。
    man_path = os.path.join(root, "vendor", "pipeline", "VENDOR-MANIFEST.json")
    vendor_files = sorted(
        os.path.relpath(p, root).replace(os.sep, "/")
        for pat in ("vendor/pipeline/**", "vendor/tools/**")
        for p in glob.glob(os.path.join(root, pat), recursive=True)
        if os.path.isfile(p) and "__pycache__" not in p
        and not p.endswith("VENDOR-MANIFEST.json"))
    bad8 = []
    if not os.path.isfile(man_path):
        bad8.append("VENDOR-MANIFEST.json 不存在")
    else:
        vm = json.load(open(man_path, encoding="utf-8"))
        reg8 = vm.get("files") or {}
        if not reg8:
            bad8.append("VENDOR-MANIFEST.json 的 files 为空（空集守卫）")
        missing = [f for f in vendor_files if f not in reg8]
        stale = [f for f in reg8 if f not in vendor_files]
        drift = [f for f in vendor_files if f in reg8
                 and hashlib.sha256(open(os.path.join(root, f), "rb").read()).hexdigest()
                 != reg8[f].get("sha256")]
        if missing:
            bad8.append("未登记：%s" % missing)
        if stale:
            bad8.append("登记过期：%s" % stale)
        if drift:
            bad8.append("sha256 漂移：%s" % drift)
        ok8 = not bad8
        detail8 = ("；".join(bad8) if bad8 else
                   "%d 个薄副本逐文件 sha256 与清单一致（其中 %d 项与 AUD 侧源逐字节相同）"
                   % (len(vendor_files),
                      sum(1 for f in vendor_files if reg8.get(f, {}).get("byte_identical"))))
    add("CI8", "vendor 薄副本 sha256 双向登记（盘上 ⊆ 清单 · 清单 ⊆ 盘上 · 逐文件一致）", HARD,
        not bad8, detail8 if not bad8 else "；".join(bad8))
    add("CI7", "CI 变更面（仅报告）", REPORT, True,
        "%s sha256=%s · steps=%s · vendor 薄副本 %d 个"
        % (WORKFLOW, sha[:16], [n for _j, n, _r in steps], len(vendor_files)))
    return R, note


GOOD_WF = """
name: Deploy GitHub Pages
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Rebuild
        run: python3 data/build_all.py --skip-gates
      - name: Gate
        run: |
          python3 gate_tokens.py --site-root . --manifest gate-manifest.json --mode enforce
          python3 vendor/pipeline/check_gate_manifest.py --manifest gate-manifest.json --profile build/profile.json
      - uses: actions/upload-pages-artifact@v3
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/deploy-pages@v4
"""


def selftest():
    cases = []

    def case(name, ok):
        cases.append((name, bool(ok)))

    PROF = {"build": {"entry": "data/build_all.py", "pipeline": ["gen_home.py"],
                      "inspectors": [], "excluded_generators": []}}
    MAN = {"gates": [{"script": "gate_tokens.py"}, {"script": "check_gate_manifest.py"}]}

    def run(wf, prof=None, man=None, extra_files=None):
        tmp = tempfile.mkdtemp(prefix="lp-ci-")
        try:
            p = os.path.join(tmp, WORKFLOW)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").write(wf)
            files = extra_files if extra_files is not None else {
                "data/gen_home.py": "# stub\n",
                "data/build_all.py": 'PIPELINE = [("gen_home", ["python3", "data/gen_home.py"], "docs/index.html")]\n',
                "vendor/pipeline/derive_site_tokens.py": "# stub\n",
                "vendor/pipeline/VENDOR-MANIFEST.json": json.dumps(
                    {"files": {"vendor/pipeline/derive_site_tokens.py":
                               {"sha256": hashlib.sha256(b"# stub\n").hexdigest()}}}, indent=1),
            }
            for f, body in files.items():
                q = os.path.join(tmp, f)
                os.makedirs(os.path.dirname(q), exist_ok=True)
                open(q, "w").write(body)
            return check(tmp, man or MAN, prof or PROF)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def get(R, cid):
        for r in R:
            if r["id"] == cid:
                return r
        return {"ok": False, "detail": "缺判据"}

    R, _ = run(GOOD_WF)
    case("正向夹具 0 FAIL", all(r["ok"] for r in R))
    # 顺序负例：门控放在重生成之前
    BAD = GOOD_WF.replace("""      - name: Rebuild
        run: python3 data/build_all.py --skip-gates
      - name: Gate
        run: |
          python3 gate_tokens.py --site-root . --manifest gate-manifest.json --mode enforce
          python3 vendor/pipeline/check_gate_manifest.py --manifest gate-manifest.json --profile build/profile.json
""", """      - name: Gate
        run: |
          python3 gate_tokens.py --site-root . --manifest gate-manifest.json --mode enforce
          python3 vendor/pipeline/check_gate_manifest.py --manifest gate-manifest.json --profile build/profile.json
      - name: Rebuild
        run: python3 data/build_all.py --skip-gates
""")
    R, _ = run(BAD)
    case("CI2 负例：Gate 在 Rebuild 之前 ⇒ FAIL", not get(R, "CI2")["ok"])
    # 顺序负例：门控放在发布之后
    BAD2 = GOOD_WF.replace("      - uses: actions/upload-pages-artifact@v3\n", "")
    BAD2 = BAD2 + ""
    BAD2 = GOOD_WF.replace("""      - name: Gate
        run: |
          python3 gate_tokens.py --site-root . --manifest gate-manifest.json --mode enforce
          python3 vendor/pipeline/check_gate_manifest.py --manifest gate-manifest.json --profile build/profile.json
      - uses: actions/upload-pages-artifact@v3""", """      - uses: actions/upload-pages-artifact@v3
      - name: Gate
        run: |
          python3 gate_tokens.py --site-root . --manifest gate-manifest.json --mode enforce
          python3 vendor/pipeline/check_gate_manifest.py --manifest gate-manifest.json --profile build/profile.json""")
    R, _ = run(BAD2)
    case("CI2 负例：Gate 在发布之后 ⇒ FAIL", not get(R, "CI2")["ok"])
    # CI3：清单登记但 CI 未调用
    R, _ = run(GOOD_WF, man={"gates": [{"script": "gate_tokens.py"}, {"script": "check_gate_manifest.py"},
                                       {"script": "gate_ghost.py"}]})
    case("CI3 负例：清单登记但 CI 未调用 ⇒ FAIL", not get(R, "CI3")["ok"])
    # CI3：CI 调用但未登记
    R, _ = run(GOOD_WF.replace("python3 gate_tokens.py", "python3 gate_extra.py"))
    case("CI3 负例：CI 调用但清单未登记 ⇒ FAIL", not get(R, "CI3")["ok"])
    # CI4：data/*.py 未登记
    R, _ = run(GOOD_WF, extra_files={
        "data/gen_home.py": "# stub\n",
        "data/build_all.py": 'PIPELINE = [("gen_home", ["python3", "data/gen_home.py"], "docs/index.html")]\n',
        "data/orphan.py": "# stub\n",
        "vendor/pipeline/VENDOR-MANIFEST.json": '{"files": {}}'})
    case("CI4 负例：data/ 下出现未登记脚本 ⇒ FAIL", not get(R, "CI4")["ok"])
    # CI8：vendor 薄副本未登记
    R, _ = run(GOOD_WF, extra_files={
        "data/gen_home.py": "# stub\n",
        "data/build_all.py": 'PIPELINE = [("gen_home", ["python3", "data/gen_home.py"], "docs/index.html")]\n',
        "vendor/pipeline/derive_site_tokens.py": "# stub\n",
        "vendor/pipeline/VENDOR-MANIFEST.json": '{"files": {}}'})
    case("CI8 负例：vendor 薄副本未登记（空集守卫）⇒ FAIL", not get(R, "CI8")["ok"])
    # CI8：sha256 漂移
    R, _ = run(GOOD_WF, extra_files={
        "data/gen_home.py": "# stub\n",
        "data/build_all.py": 'PIPELINE = [("gen_home", ["python3", "data/gen_home.py"], "docs/index.html")]\n',
        "vendor/pipeline/derive_site_tokens.py": "# stub\n",
        "vendor/pipeline/VENDOR-MANIFEST.json": json.dumps(
            {"files": {"vendor/pipeline/derive_site_tokens.py": {"sha256": "0" * 64}}})})
    case("CI8 负例：薄副本 sha256 漂移 ⇒ FAIL", not get(R, "CI8")["ok"])
    # CI4：登记过期
    R, _ = run(GOOD_WF, prof={"build": {"entry": "data/build_all.py",
                                        "pipeline": ["gen_home.py", "gone.py"],
                                        "inspectors": [], "excluded_generators": []}})
    case("CI4 负例：登记项已不存在 ⇒ FAIL（登记过期）", not get(R, "CI4")["ok"])
    # CI5：build_all.py 的 PIPELINE 与 profile 声明不一致
    R, _ = run(GOOD_WF, extra_files={
        "data/gen_home.py": "# stub\n",
        "data/build_all.py": 'PIPELINE = [("other", ["python3", "data/other.py"], "x")]\n'})
    case("CI5 负例：build_all.PIPELINE 与 profile.build.pipeline 不一致 ⇒ FAIL",
         not get(R, "CI5")["ok"])
    # CI6：Gate 步缺清单守门人
    R, _ = run(GOOD_WF.replace("          python3 vendor/pipeline/check_gate_manifest.py --manifest gate-manifest.json --profile build/profile.json\n", ""))
    case("CI6 负例：Gate 步未调用清单守门人 ⇒ FAIL", not get(R, "CI6")["ok"])
    # 口径：无 pyyaml 必须**护栏拒读**，⛔ 不退化成手写解析（假绿来源）
    here = os.path.dirname(os.path.abspath(__file__))
    wf = os.path.join(here, WORKFLOW)
    if os.path.isfile(wf):
        import builtins
        real_import = builtins.__import__

        def fake(name, *a, **k):
            if name == "yaml":
                raise ImportError("blocked for selftest")
            return real_import(name, *a, **k)
        builtins.__import__ = fake
        try:
            try:
                steps_of(open(wf, encoding="utf-8").read())
                case("负例·口径：无 pyyaml 时必须抛护栏（⛔ 不静默降级）", False)
            except GateError:
                case("负例·口径：无 pyyaml 时必须抛护栏（⛔ 不静默降级）", True)
        finally:
            builtins.__import__ = real_import
        s1, p1, _ = steps_of(open(wf, encoding="utf-8").read())
        case("正向·口径：真实 workflow 用有效 YAML 解析出 ≥3 步（%s）" % p1, len(s1) >= 3)
    else:
        case("真实 workflow 不存在 ⇒ 无法对照（如实登记，非 PASS 语义）", False)

    ok = all(v for _, v in cases)
    for n, v in cases:
        print("  [%s] %s" % ("PASS" if v else "FAIL", n))
    print("\n=== gate_ci_contract 自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-root", default=".")
    ap.add_argument("--manifest", default="gate-manifest.json")
    ap.add_argument("--profile", default="build/profile.json")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    root = os.path.abspath(a.site_root)
    try:
        manifest = load_json(os.path.join(root, a.manifest), "门控清单")
        profile = load_json(os.path.join(root, a.profile), "profile")
    except GateError as exc:
        print("GUARD-REJECT: %s" % exc)
        return 3
    R, note = check(root, manifest, profile)
    print("# 解析口径：%s" % note)
    for r in R:
        print("[%s] %-4s %-5s %s — %s" % ("PASS" if r["ok"] else "FAIL", r["id"], r["class"],
                                          r["name"], r["detail"]))
    if a.json:
        print(json.dumps(R, ensure_ascii=False, indent=1))
    nf = sum(1 for r in R if not r["ok"])
    print("\n=== CI 步骤序/管线登记门控：%d 项判据，%d FAIL ===" % (len(R), nf))
    return 0 if nf == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
