#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_site_tokens.py — 站点令牌契约门控（批 D 共通件）。

用法：
    python3 check_site_tokens.py --contract V --profile P --site-root R --orig-root O \
            --payloads D [--json] [--warn-only]
    python3 check_site_tokens.py --selftest        # 每条判据的负向夹具（判据非恒真）

角色定位：`fe-starter-kit/tools/check_starter.py` 管的是 **starter 仓**；本件是它在**站点侧**的
对应物。判据实现**复用** `pipeline/derive_site_tokens.py`（派生器）与 `tools/contrast.py`
（对比度），⛔ 不造第二套实现（SH5 §4.0 第 7 条）。

判据（★ 每条写明「判据对象」与「断言对象」是否一致 —— SH5 §4.0 第 1 条）：
  C1 值件与 profile 合法且必需段齐备（含 JSON Schema 校验，若 jsonschema 可用）
  C2 角色集非空、且与 binding.site_token_names 一一对应
  C3 每个角色的 tier 在 usage_tiers 内（防档位悬挂）
  C4 取值可解析：「解析出 0 条」报错，⛔ 不当成「0 条事实」
  C5 成对对比度：按 usage_tiers 的 min_contrast 与 gate 逐对断言（**逐族**跑，故页面族覆盖下的
     两个不同取值都要各自达标）；gate=report-only 的对只记 WARN，⛔ 不用它去硬判弱分隔线
  C6 border.line 极性：强分隔必须强于弱分隔（同族内）
  C7 覆盖完整性：角色令牌 ∪ 页面族 overrides ∪ 透传令牌 ⊇ **原始**目标的令牌名集合（防静默丢令牌）
  C8 写入幂等 + --check 零写入（在工作副本上复跑两次；非目标段不变由写入器 B4 承担）
  C9 ★ 形态归一化对账：先按 profile.form 归一化（剥注释与空白）再比对；形态 external-link
     额外交验外链可达（本地 http.server：200 + content-type: text/css）
  C10 ★ 三级覆盖可解释性：每个原始目标的令牌名必须能被「族默认 ∪ 该族 overrides ∪ 透传」解释；
     同一令牌名在不同族取不同值时，**每个值都必须在各自族里登记**
  C11 空集守卫：任一侧令牌缺失即 FAIL，⛔ 不静默跳过
  C12 零改动：克隆 HEAD 等于值件冻结值、工作树干净、starter 关键文件 sha256 未变

★ 判据强度上限（如实声明，⛔ 不声称它证明了更多）：
  * 本门控**只证**「值件、派生产物与目标文件满足上述机械判据」。
  * 它**不证**：① 色值在审美上可接受；② 逐像素视觉一致（本机 agent-browser 不在 PATH ⇒ 像素层未测）；
    ③ 真实用户可用性；④ 三 job 契约在真实 GitHub Actions 上跑得通（本机无 actionlint）。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import threading

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(AUD, "tools"))

import derive_site_tokens as D      # noqa: E402
import write_site_tokens as W       # noqa: E402
import contrast as C                # noqa: E402

STARTER = os.path.expanduser("~/opencode/projects/fe-starter-kit")
BASELINE = os.path.join(AUD, "evidence", "b1-zero-change-baseline.json")


def sha256_file(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_baseline():
    try:
        with open(BASELINE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return {}


def http_check(site_root, rel):
    """形态 1 的外部表可达性：本地静态服务上 200 且 content-type: text/css。"""
    import http.server
    import socketserver
    import urllib.request

    class Q(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=site_root, **kw)

        def log_message(self, *a):  # 静音
            pass

    with socketserver.TCPServer(("127.0.0.1", 0), Q) as srv:
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            url = "http://127.0.0.1:%d/%s" % (port, rel)
            with urllib.request.urlopen(url, timeout=10) as resp:
                return resp.status, resp.headers.get("content-type", ""), len(resp.read())
        finally:
            srv.shutdown()


def families_of(profile):
    out = {}
    for t in profile["targets"]:
        out.setdefault(t["family"], []).append(t)
    return out


def derive_all(contract, profile):
    blocks = {}
    for fid in contract["families"]:
        try:
            _, toks = D.build_tokens(contract, profile, fid)
        except D.GuardError as exc:
            return None, str(exc)
        blocks[fid] = (r"%s" % D.render(toks), toks)
    return blocks, None


def check(contract, profile, site_root, orig_root, payloads):
    """返回 [(id, name, ok, detail, severity)]。"""
    R = []

    def add(cid, name, ok, detail, sev="FAIL"):
        R.append((cid, name, ok, detail, sev))

    # ---- C1 schema / 结构
    detail = []
    try:
        import jsonschema
        for doc, sch, label in ((contract, "site-value-contract.schema.json", "值件"),
                                (profile, "site-profile.schema.json", "profile")):
            sp = os.path.join(HERE, sch)
            if os.path.isfile(sp):
                try:
                    jsonschema.validate(doc, json.load(open(sp, encoding="utf-8")))
                    detail.append("%s 过 %s" % (label, sch))
                except jsonschema.ValidationError as exc:
                    detail.append("%s 未过 %s：%s" % (label, sch, str(exc).split("\n")[0][:120]))
                    add("C1", "值件与 profile 合法且必需段齐备", False, "；".join(detail))
                    return R
        add("C1", "值件与 profile 合法且必需段齐备", True, "；".join(detail) or "结构齐备")
    except ImportError:
        try:
            D.check_contract(contract)
            D.check_profile(profile)
            add("C1", "值件与 profile 合法且必需段齐备", True, "结构齐备（jsonschema 不可用，退化为结构检查）")
        except D.GuardError as exc:
            add("C1", "值件与 profile 合法且必需段齐备", False, str(exc))
            return R

    # ---- C2 角色集
    roles = list(contract["roles"])
    names = contract["binding"]["site_token_names"]
    ok = bool(roles) and set(roles) == set(names)
    add("C2", "角色集非空且与令牌名绑定一一对应", ok,
        "角色 %d / 绑定 %d" % (len(roles), len(names)) if ok
        else "差集：%s" % sorted(set(roles) ^ set(names)))

    # ---- C3 tier
    bad = [r for r in roles if contract["roles"][r].get("tier") not in contract["usage_tiers"]]
    add("C3", "每个角色的 tier 在 usage_tiers 内", not bad, "悬挂：%s" % bad if bad else "无悬挂")

    # ---- C4 取值可解析
    forms = contract["scope"]["declared_forms"]
    forms = forms if isinstance(forms, list) else [forms]
    rid = next(iter(contract["palettes"]))
    vals = contract["palettes"][rid]["values"]
    unresolved, total = [], 0
    for role in roles:
        for f in forms:
            v = (vals.get(role) or {}).get(f)
            total += 1
            if v is None:
                unresolved.append("%s/%s 缺" % (role, f))
            elif isinstance(v, str) and v.startswith("#") and C.parse_color(v) is None:
                unresolved.append("%s/%s 不可解析(%r)" % (role, f, v))
    ok = bool(total) and not unresolved
    add("C4", "取值可解析（解析出 0 条即报错）", ok,
        "解析 %d 条，全部可解析" % total if ok else "未解析 %d/%d：%s" % (len(unresolved), total, unresolved[:4]))

    blocks, err = derive_all(contract, profile)
    if err:
        add("C11", "空集守卫（派生结果非空）", False, err)
        return R

    # ---- C5 成对对比度（逐族）
    tiers = contract["usage_tiers"]
    bad, warns = [], []
    surf = names.get("surface.page")
    for fid, (blk, toks) in blocks.items():
        if surf not in toks:
            bad.append("%s 缺表面令牌 %s（空集守卫）" % (fid, surf))
            continue
        for role, token in names.items():
            if contract["roles"][role].get("kind") == "dimension":
                continue          # ★ 尺寸类角色不是颜色对象（判据对象必须与断言对象一致）
            spec = tiers[contract["roles"][role]["tier"]]
            need = spec["min_contrast"].get(forms[0])
            if not need:
                continue
            if role.startswith("surface."):
                continue
            a, b = toks.get(token), toks.get(surf)
            if a is None or b is None:
                bad.append("%s %s/%s 令牌缺失（空集守卫）" % (fid, role, token))
                continue
            try:
                rr = C.ratio(C.parse_color(str(a)), C.parse_color(str(b)))
            except Exception:  # noqa: BLE001
                bad.append("%s %s 无法计算对比度（%r）" % (fid, role, a))
                continue
            if spec["gate"] == "hard":
                if rr is None or rr < need:
                    bad.append("%s %s=%s 对 %s=%s 仅 %s < %s" %
                               (fid, token, a, surf, b, "n/a" if rr is None else "%.2f" % rr, need))
            else:
                warns.append("%s %s=%.2f（report-only，档=%s）" %
                             (fid, token, rr if rr is not None else -1, need))
    add("C5", "成对对比度（逐族，按 usage_tiers 的 gate 分档）", not bad,
        "；".join(bad[:4]) if bad else "硬阻断对全部达标；report-only %d 条" % len(warns))

    # ---- C6 极性
    pol_bad = []
    for fid, (_b, toks) in blocks.items():
        ln, sub = toks.get(names.get("border.line")), toks.get(names.get("border.subtle"))
        if ln and sub:
            try:
                rl = C.ratio(C.parse_color(ln), C.parse_color(toks[surf]))
                rs = C.ratio(C.parse_color(sub), C.parse_color(toks[surf]))
                if rl is not None and rs is not None and rl <= rs:
                    pol_bad.append("%s border.line %.2f 不弱于 border.subtle %.2f（极性反转）" % (fid, rl, rs))
            except Exception:  # noqa: BLE001
                pol_bad.append("%s 极性无法计算" % fid)
    add("C6", "border.line 极性（强分隔强于弱分隔）", not pol_bad,
        "；".join(pol_bad) if pol_bad else "极性成立")

    # ---- C7 覆盖完整性（对**原始**目标）
    role_tokens = set(names.values())
    pass_tokens = set()
    for _g, kv in (contract["binding"].get("passthrough_tokens") or {}).items():
        if isinstance(kv, dict):
            pass_tokens |= set(kv)
    lost = []
    checked = 0
    for t in profile["targets"]:
        src = t.get("coverage_source") or t["path"]
        bank = orig_root or site_root
        p = os.path.join(bank, src)
        if not os.path.isfile(p):
            continue
        blk = D.extract_block(open(p, encoding="utf-8").read())
        if not blk:
            continue
        checked += 1
        orig = set(D.parse_tokens(blk))
        declared = role_tokens | pass_tokens | set((contract["families"][t["family"]].get("overrides") or {}))
        miss = orig - declared
        if miss:
            lost.append("%s 原始令牌未申报：%s" % (src, sorted(miss)))
    add("C7", "覆盖完整性（角色 ∪ 族覆盖 ∪ 透传 ⊇ 原始令牌集）", not lost,
        "；".join(lost) if lost else "核对 %d 个原始目标，无静默丢令牌" % checked)

    # ---- C9 形态归一化对账（+ 形态 1 外链可达）
    rec_bad, extra = [], []
    for t in profile["targets"]:
        fam = t["family"]
        exp = blocks[fam][0]
        p = os.path.join(site_root, t["path"])
        if not os.path.isfile(p):
            rec_bad.append("%s 不存在" % t["path"])
            continue
        disk = open(p, encoding="utf-8").read()
        got = disk if t["mode"] == "whole-file" else (D.extract_block(disk) or "")
        if D.normalize(got) != D.normalize(exp):
            rec_bad.append("%s 与族 %s 的值件派生结果不一致" % (t["path"], fam))
    if profile["form"] == "external-link":
        tgt = profile["targets"][0]["path"]
        try:
            st, ct, n = http_check(site_root, tgt)
            extra.append("外链 %s → %d / %s / %dB" % (tgt, st, ct, n))
            if st != 200 or "text/css" not in ct:
                rec_bad.append("外链不可达或类型不对：%d %s" % (st, ct))
        except Exception as exc:  # noqa: BLE001
            rec_bad.append("外链可达性检查失败（⛔ 不静默跳过）：%s" % exc)
    add("C9", "形态归一化对账（%s）" % profile["form"], not rec_bad,
        "；".join(rec_bad) if rec_bad else ("；".join(extra) or "全部目标与值件派生结果一致"))

    # ---- C8 写入幂等 + --check 零写入（★ 只在**工作副本**上复跑；克隆不动）
    idem_bad = []
    paydir = os.path.dirname(list(payloads.values())[0]) if payloads else None
    try:
        for fid, path in payloads.items():
            if not os.path.isfile(path):
                idem_bad.append("族 %s 缺派生产物" % fid)
        if not paydir:
            idem_bad.append("未提供任何派生产物目录")
        if not idem_bad:
            def snap():
                out = {}
                for t in profile["targets"]:
                    p2 = os.path.join(site_root, t["path"])
                    out[t["path"]] = sha256_file(p2) if os.path.isfile(p2) else None
                return out
            W.run(profile, paydir, site_root, "apply")
            a = snap()
            W.run(profile, paydir, site_root, "apply")
            b = snap()
            if a != b:
                idem_bad.append("二次 apply 发生了改动（非幂等）：%s" %
                                [k for k in a if a[k] != b[k]])
            W.run(profile, paydir, site_root, "check")
            if snap() != b:
                idem_bad.append("--check 竟然改了文件")
    except W.GuardError as exc:
        idem_bad.append("幂等复跑被护栏拒绝：%s" % exc)
    add("C8", "写入幂等 + --check 零写入（工作副本上复跑两次）", not idem_bad,
        "；".join(idem_bad) if idem_bad else "幂等成立、--check 零写入")

    # ---- C10 三级覆盖可解释性：每一处取值改动都必须可归因
    #   ★ 判据对象＝「原始目标的真实取值」，断言对象＝「派生后的取值」；两者之差必须能归因到
    #     「该族的页面族覆盖」或契约声明的 known_value_changes。⛔ 不允许静默改值。
    exp_bad, chg_checked, chg_reg = [], 0, 0
    bank = orig_root or site_root
    known = contract.get("known_value_changes") or {}
    for t in profile["targets"]:
        src = t.get("coverage_source") or t["path"]
        pp = os.path.join(bank, src)
        if not os.path.isfile(pp):
            continue
        blk = D.extract_block(open(pp, encoding="utf-8").read())
        if not blk:
            continue
        orig = D.parse_tokens(blk)
        fam = t["family"]
        der = blocks[fam][1]
        over = contract["families"][fam].get("overrides") or {}
        for nm, ov in orig.items():
            if nm not in der:
                exp_bad.append("族 %s 派生结果丢了原始令牌 %s（静默丢令牌）" % (fam, nm))
                continue
            if der[nm] == ov:
                continue
            chg_checked += 1
            if nm in over and over[nm] == der[nm]:
                continue
            kc = known.get(nm)
            if kc and kc.get("from") == ov and kc.get("to") == der[nm]:
                chg_reg += 1
                continue
            exp_bad.append("族 %s 的 %s 由 %s 改为 %s，但既不在该族 overrides 也无 known_value_changes 登记"
                           % (fam, nm, ov, der[nm]))
    # 跨族同名不同值：每一处都必须逐族登记（页面族覆盖的成因实例）
    fam_orig = {}
    for t in profile["targets"]:
        src = t.get("coverage_source") or t["path"]
        pp = os.path.join(bank, src)
        if os.path.isfile(pp):
            blk = D.extract_block(open(pp, encoding="utf-8").read())
            if blk:
                fam_orig.setdefault(t["family"], {}).update(D.parse_tokens(blk))
    for nm in sorted({k for m in fam_orig.values() for k in m}):
        vals = {f: m[nm] for f, m in fam_orig.items() if nm in m}
        if len(set(vals.values())) > 1:
            for f, v in vals.items():
                der = blocks[f][1]
                over = contract["families"][f].get("overrides") or {}
                if der.get(nm) == v:
                    continue
                kc = (contract.get("known_value_changes") or {}).get(nm)
                if nm in over or (kc and kc.get("from") == v and kc.get("to") == der.get(nm)):
                    continue
                exp_bad.append("跨族同名令牌 %s 在族 %s 取 %s，改动未登记" % (nm, f, v))
    add("C10", "三级覆盖可解释性（每处取值改动可归因）", not exp_bad,
        "；".join(exp_bad[:4]) if exp_bad else
        "核对改动 %d 处、其中 known_value_changes 归因 %d 处；跨族差异全部逐族登记" % (chg_checked, chg_reg))

    # ---- C11 空集守卫
    empty = [f for f, (_b, toks) in blocks.items() if not toks]
    no_target = [f for f in contract["families"] if not (contract["families"][f].get("targets"))]
    add("C11", "空集守卫（任一侧缺失即 FAIL，不静默跳过）", not empty and not no_target,
        "空族：%s；无目标族：%s" % (empty, no_target) if (empty or no_target) else "无空集")

    # ---- C12 零改动
    base = load_baseline()
    zc = []
    lc = contract["scope"].get("upstream_repo_head")
    if profile.get("local_clone") and os.path.isdir(os.path.join(profile["local_clone"], ".git")):
        import subprocess
        cl = profile["local_clone"]
        head = subprocess.run(["git", "-C", cl, "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", cl, "status", "--porcelain"],
                               capture_output=True, text=True).stdout.strip()
        if lc and head != lc:
            zc.append("克隆 HEAD %s ≠ 值件冻结 %s" % (head[:12], lc[:12]))
        if dirty:
            zc.append("克隆工作树不干净（%d）" % len(dirty.splitlines()))
    sf = base.get("starter_files") or {}
    for rel, want in sf.items():
        p = os.path.join(STARTER, rel)
        if not os.path.isfile(p):
            zc.append("starter 文件缺失 %s" % rel)
        elif sha256_file(p) != want:
            zc.append("starter 文件已变 %s" % rel)
    add("C12", "零改动（克隆 HEAD 与工作树 + starter 关键文件 sha256）", not zc,
        "；".join(zc) if zc else "克隆与 starter 共 %d 项未变" % len(sf))

    return R


# ----------------------------------------------------------------------------- selftest
FIX_CONTRACT = {
    "meta": {"id": "t", "contract_version": "0", "frozen_at": "2026-10-13", "title": "t"},
    "scope": {"site": "t", "upstream_repo_head": "0" * 40, "declared_forms": ["dark"]},
    "usage_tiers": {
        "body": {"allowed_use": "x", "min_contrast": {"dark": 4.5}, "gate": "hard"},
        "non-body": {"allowed_use": "x", "min_contrast": {"dark": 4.5}, "gate": "report-only"},
        "non-text": {"allowed_use": "x", "min_contrast": {"dark": 3.0}, "gate": "hard"},
        "non-text-decorative": {"allowed_use": "弱分隔：按定义应不可见，只报告不硬判",
                                "min_contrast": {"dark": 3.0}, "gate": "report-only"}},
    "roles": {
        "text.primary": {"tier": "body", "kind": "text", "purpose": "p", "site_source": "s"},
        "surface.page": {"tier": "non-text", "kind": "surface", "purpose": "p", "site_source": "s"},
        "surface.raised": {"tier": "non-text", "kind": "surface", "purpose": "p", "site_source": "s"},
        "border.line": {"tier": "non-text", "kind": "border", "purpose": "p", "site_source": "s"},
        "border.subtle": {"tier": "non-text-decorative", "kind": "border",
                          "purpose": "p", "site_source": "s"}},
    "palettes": {"p": {"family": "f", "provenance": "x", "values": {
        "text.primary": {"dark": "#e6e8ee"}, "surface.page": {"dark": "#0f1117"},
        "surface.raised": {"dark": "#161a22"}, "border.line": {"dark": "#6b7280"},
        "border.subtle": {"dark": "#2a2f3a"}}}},
    "binding": {"note": "n", "site_token_names": {
        "text.primary": "--text", "surface.page": "--bg", "surface.raised": "--panel",
        "border.line": "--line", "border.subtle": "--line-subtle"},
        "passthrough_tokens": {"layout": {"--w-max": "1120px"}}},
    "families": {
        "default": {"targets": ["a.html"], "overrides": {"--warn": "#e8933b"}},
        "fam2": {"targets": ["b.html"], "overrides": {"--warn": "#e8933b"}}},
    "derivation": {"state": "s", "direction": "d", "generator_ref": "g", "rule": "r"},
    "known_value_changes": {
        "--line": {"from": "#2a2f3a", "to": "#6b7280",
                   "reason": "原值对 --bg 仅 1.41，不达 non-text 的 3:1（门控驱动，非审美选择）"}},
}
FIX_PROFILE = {
    "site": "t", "form": "inline-single-source", "publish_dir": ".", "value_file": "v.json",
    "targets": [{"path": "a.html", "mode": "root-block", "family": "default"},
                {"path": "b.html", "mode": "root-block", "family": "fam2"}],
    "gates": {"manifest": "m.json", "hard_blocking": ["contrast"], "commands": ["x"]},
}
ORIG_A = (":root{--bg:#0f1117;--panel:#161a22;--text:#e6e8ee;--line:#2a2f3a;"
          "--line-subtle:#2a2f3a;--warn:#e8933b;}\nbody{color:red}\n")
ORIG_B = (":root{--bg:#0f1117;--panel:#161a22;--text:#e6e8ee;--line:#2a2f3a;"
          "--line-subtle:#2a2f3a;--warn:#e0c35e;}\nbody{color:red}\n")


def _mk_fixture(tmp):
    cl = os.path.join(tmp, "clone")
    site = os.path.join(tmp, "site")
    orig = os.path.join(tmp, "orig")
    pay = os.path.join(tmp, "payloads")
    for d in (site, orig, pay):
        os.makedirs(d, exist_ok=True)
    open(os.path.join(orig, "a.html"), "w", encoding="utf-8").write(ORIG_A)
    open(os.path.join(orig, "b.html"), "w", encoding="utf-8").write(ORIG_B)
    os.makedirs(cl, exist_ok=True)
    import subprocess
    subprocess.run(["git", "init", "-q", cl], check=True)
    open(os.path.join(cl, "seed.txt"), "w", encoding="utf-8").write("seed\n")

    def _head():
        # ★ 未诞生的分支上 `git rev-parse HEAD` 会把字面量 "HEAD" 打到 stdout（exit≠0），
        #   故必须按 40 位十六进制校验，⛔ 不能只判非空。
        h = subprocess.run(["git", "-C", cl, "rev-parse", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        return h if re.fullmatch(r"[0-9a-f]{40}", h) else ""

    if not _head():
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "-C", cl, "add", "-A"], check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "-C", cl, "commit", "-q", "-m", "seed"], check=True)
    head = _head()
    c = json.loads(json.dumps(FIX_CONTRACT))
    c["families"]["fam2"]["overrides"]["--warn"] = "#e0c35e"     # 逐族登记（正确）
    c["scope"]["upstream_repo_head"] = head
    p = json.loads(json.dumps(FIX_PROFILE))
    p["local_clone"] = cl
    return c, p, site, orig, pay


def _payloads_of(contract, paydir):
    return {fid: os.path.join(paydir, "%s.css" % fid) for fid in contract["families"]}


def selftest():
    import subprocess
    import tempfile
    tmp = tempfile.mkdtemp(prefix="cst-")
    cases = []

    def run_case(name, mutate, cid, expect_fail=True):
        c, p, site, orig, pay = _mk_fixture(tmp)
        # 基线：先派生 + 写入，使 C8/C9 有可对账的盘上状态
        ok = True
        for fid, spec in c["families"].items():
            try:
                _, toks = D.build_tokens(c, p, fid)
            except D.GuardError:
                ok = False
                break
            open(os.path.join(pay, "%s.css" % fid), "w", encoding="utf-8").write(D.render(toks))
        if ok:
            for t in p["targets"]:
                src = os.path.join(orig, t["path"])
                dst = os.path.join(site, t["path"])
                open(dst, "w", encoding="utf-8").write(open(src, encoding="utf-8").read())
            try:
                W.run(p, pay, site, "apply")
            except W.GuardError:
                ok = False
        try:
            mutate(c, p, site, orig, pay)
        except Exception:  # noqa: BLE001
            pass
        try:
            R = check(c, p, site, orig, pay and _payloads_of(c, pay))
        except D.GuardError as exc:
            R = [("C11", "空集守卫", False, str(exc), "FAIL")]
        got = {r[0]: r[2] for r in R}
        fired = got.get(cid, False) is False
        cases.append((name, fired if expect_fail else not fired))

    # 基线正例（无突变）：应全过
    c, p, site, orig, pay = _mk_fixture(tmp)
    for fid in c["families"]:
        _, toks = D.build_tokens(c, p, fid)
        open(os.path.join(pay, "%s.css" % fid), "w", encoding="utf-8").write(D.render(toks))
    for t in p["targets"]:
        open(os.path.join(site, t["path"]), "w", encoding="utf-8").write(
            open(os.path.join(orig, t["path"]), encoding="utf-8").read())
    W.run(p, pay, site, "apply")
    base_res = check(c, p, site, orig, _payloads_of(c, pay))
    fails = [r for r in base_res if r[2] is False and r[4] == "FAIL"]
    cases.append(("正向夹具（无突变）应 0 FAIL", not fails))
    for r in base_res:
        print("    [%s] %s — %s" % ("PASS" if r[2] else "FAIL", r[0], str(r[3])[:90]))

    # 逐判据负例
    run_case("C1 负例：值件缺段", lambda c, p, *_: c.pop("usage_tiers"), "C1")
    run_case("C2 负例：角色与绑定不等",
             lambda c, p, *_: c["binding"]["site_token_names"].pop("border.subtle"), "C2")
    run_case("C3 负例：tier 悬挂",
             lambda c, p, *_: c["roles"]["text.primary"].__setitem__("tier", "nope"), "C3")
    run_case("C4 负例：色值不可解析",
             lambda c, p, *_: c["palettes"]["p"]["values"]["text.primary"].__setitem__("dark", "#zzzzzz"), "C4")
    run_case("C5 负例：正文对比度不达标",
             lambda c, p, *_: c["palettes"]["p"]["values"]["text.primary"].__setitem__("dark", "#101010"), "C5")
    run_case("C6 负例：border.line 极性反转（取弱值）",
             lambda c, p, *_: c["palettes"]["p"]["values"]["border.line"].__setitem__("dark", "#111111"), "C6")
    run_case("C7 负例：原始令牌未申报（清空透传与族覆盖）",
             lambda c, p, *_: (c["binding"]["passthrough_tokens"].clear(),
                               c["families"]["default"]["overrides"].clear(),
                               c["families"]["fam2"]["overrides"].clear()), "C7")
    run_case("C8 负例：族派生产物缺失（幂等复跑被护栏拒绝）",
             lambda c, p, site, orig, pay: os.remove(os.path.join(pay, "fam2.css")), "C8")
    run_case("C9 负例：盘上块与值件派生不一致",
             lambda c, p, site, *_: open(os.path.join(site, "a.html"), "w", encoding="utf-8").write(
                 ":root{--text:#000000;}\n"), "C9")
    run_case("C10 负例：跨族不同值未逐族登记（页面族覆盖缺失）",
             lambda c, p, *_: c["families"]["fam2"]["overrides"].pop("--warn"), "C10")
    run_case("C10 负例：取值改动未登记 known_value_changes",
             lambda c, p, *_: c["known_value_changes"].pop("--line"), "C10")
    run_case("C11 负例：空族（family 无 overrides 且清空角色）",
             lambda c, p, *_: (c["binding"]["site_token_names"].clear(),
                               c["binding"]["passthrough_tokens"].clear(),
                               c["families"]["default"].__setitem__("overrides", {})), "C11")
    run_case("C12 负例：克隆 HEAD 与值件冻结值不符",
             lambda c, p, *_: c["scope"].__setitem__("upstream_repo_head", "1" * 40), "C12")
    run_case("C1 负例：profile 缺 gates",
             lambda c, p, *_: p.pop("gates"), "C1")

    ok = all(v for _, v in cases)
    for name, res in cases:
        print("  [%s] %s" % ("PASS" if res else "FAIL", name))
    print("\n=== 契约门控自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract")
    ap.add_argument("--profile")
    ap.add_argument("--site-root")
    ap.add_argument("--orig-root")
    ap.add_argument("--payloads")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--warn-only", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    try:
        contract = D.load_json(a.contract, "值件")
        profile = D.load_json(a.profile, "profile")
        payloads = {}
        for fid in contract.get("families", {}):
            fp = os.path.join(a.payloads, "%s.css" % fid)
            if os.path.isfile(fp):
                payloads[fid] = fp
        R = check(contract, profile, a.site_root, a.orig_root, payloads)
    except D.GuardError as exc:
        print("GUARD-REJECT: %s" % exc)
        return 3
    for cid, name, ok, detail, sev in R:
        print("[%s] %s %s — %s" % ("PASS" if ok else sev, cid, name, detail))
    nf = sum(1 for r in R if r[2] is False and r[4] == "FAIL")
    if a.json:
        print(json.dumps([{"id": c, "name": n, "ok": o, "detail": d, "severity": s}
                          for c, n, o, d, s in R], ensure_ascii=False, indent=1))
    print("\n=== 契约门控：%d 项判据，%d FAIL ===" % (len(R), nf))
    return 0 if nf == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
