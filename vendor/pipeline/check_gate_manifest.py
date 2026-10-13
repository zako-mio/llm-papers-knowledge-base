#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_gate_manifest.py — 声明式门控清单的双向 fail-closed 校验（批 D 共通件）。

范式来源：hub 的 `scripts/check_ci_manifest.py`（批 A 的 SH5 §2.2 N1 认定它是「本项目判据设计
最成熟的范式」）。本件把它的五条设计要点照搬为通用件：

  M1 **登记 ⇒ 必须被调用**：清单里每一项的脚本，必须在 profile.gates.commands 里真实出现
  M2 **被调用 ⇒ 必须登记**：命令里出现的 `*.py` 门控脚本，必须在清单里登记
  M3 **非空守卫**：清单项数与命令数都不得为 0（防空跑绿灯）
  M4 ⛔ **不设豁免白名单**：清单不得含 waivers / exempt / allow / skip 一类逃逸字段
  M5 **每项须声明 reads（判据对象）与 selftest=true（负向夹具义务）**
  M6 **声明未覆盖面**：`not_covered` 必须存在且非空（照 SH5 §4.0 第 10 条）

★ 判据蕴含关系声明（SH5 §4.0 第 8 条）：M3 ⊂ M1（空集时 M1 恒真，故必须单列）。
★ 本件只证「登记与调用一致」；⛔ 不证「门控真的跑过」「门控判据不是恒真」——后者归各门控自身的 --selftest。

用法：
    python3 check_gate_manifest.py --manifest M.json --profile P.json [--json]
    python3 check_gate_manifest.py --selftest
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

ESCAPE_KEYS = ("waivers", "waiver", "exempt", "exemptions", "allow", "allowlist",
               "whitelist", "skip", "skips", "ignore")


def invoked_scripts(profile):
    """从 profile.gates.commands 里抽取被调用的 .py 脚本 basename。"""
    out = set()
    for cmd in profile.get("gates", {}).get("commands", []) or []:
        for m in re.finditer(r"[A-Za-z0-9_./-]+\.py", cmd):
            out.add(os.path.basename(m.group(0)))
    return out


def check(manifest, profile):
    R = []

    def add(cid, name, ok, detail):
        R.append((cid, name, ok, detail))

    if not isinstance(manifest, dict):
        add("M0", "清单必须是对象", False, "顶层不是对象")
        return R
    gates = manifest.get("gates")
    if not isinstance(gates, list):
        add("M0", "清单必须有 gates 数组", False, "缺 gates 或类型错误")
        return R

    registered = {os.path.basename(g.get("script", "")): g for g in gates}
    invoked = invoked_scripts(profile)

    missing_call = sorted(k for k in registered if k and k not in invoked)
    add("M1", "登记 ⇒ 必须被调用", not missing_call,
        "未进 CI/命令的登记项：%s" % missing_call if missing_call else
        "登记 %d 项全部被命令调用" % len(registered))

    unregistered = sorted(s for s in invoked if s not in registered)
    add("M2", "被调用 ⇒ 必须登记", not unregistered,
        "命令里出现但未登记的脚本：%s" % unregistered if unregistered else
        "命令调用的 %d 个脚本全部已登记" % len(invoked))

    add("M3", "非空守卫（清单项数与命令数均 > 0）",
        bool(gates) and bool(invoked),
        "清单 %d 项 / 命令调用 %d 个脚本" % (len(gates), len(invoked)))

    escape = []
    for k in manifest:
        if any(e == k.lower() or e in k.lower() for e in ESCAPE_KEYS):
            escape.append(k)
    for g in gates:
        for k in g:
            if any(e == k.lower() or e in k.lower() for e in ESCAPE_KEYS):
                escape.append("gates[].%s" % k)
    add("M4", "⛔ 不设豁免白名单（豁免即逃逸门）", not escape,
        "发现逃逸字段：%s" % escape if escape else "无豁免/白名单字段")

    weak = [g.get("id", "?") for g in gates if not g.get("reads") or g.get("selftest") is not True]
    add("M5", "每项声明 reads（判据对象）与 selftest=true（负向夹具义务）", not weak,
        "缺 reads 或未声明 selftest 的项：%s" % weak if weak else
        "%d 项全部声明 reads 与 selftest" % len(gates))

    nc = manifest.get("not_covered")
    add("M6", "声明未覆盖面（须非空）", bool(nc) and isinstance(nc, list),
        "not_covered 缺或为空" if not (nc and isinstance(nc, list)) else
        "已声明 %d 条未覆盖面" % len(nc))

    return R


GOOD_MANIFEST = {
    "site": "t",
    "gates": [
        {"id": "token-consistency", "script": "check_site_tokens.py",
         "reads": ["语义角色 → 值 映射"], "selftest": True, "mode": "hard"},
        {"id": "contrast", "script": "gate_contrast.py",
         "reads": ["令牌产物的真实色值"], "selftest": True, "mode": "hard"},
    ],
    "not_covered": ["三 job 契约未在真实 Actions 上跑过", "像素层视觉回归未测"],
}
GOOD_PROFILE = {"gates": {"commands": ["python3 check_site_tokens.py --all",
                                       "python3 gate_contrast.py"]}}


def selftest():
    cases = []

    def case(name, mutate, cid, expect_fail=True):
        m = json.loads(json.dumps(GOOD_MANIFEST))
        p = json.loads(json.dumps(GOOD_PROFILE))
        try:
            mutate(m, p)
        except Exception:  # noqa: BLE001
            pass
        try:
            R = check(m, p)
        except Exception:  # noqa: BLE001
            R = [("M0", "x", False, "异常")]
        got = {r[0]: r[2] for r in R}
        cases.append((name, (got.get(cid, False) is False) if expect_fail else bool(got.get(cid))))

    # 正向
    R = check(json.loads(json.dumps(GOOD_MANIFEST)), json.loads(json.dumps(GOOD_PROFILE)))
    cases.append(("正向夹具应 0 FAIL", all(r[2] for r in R)))

    case("M1 负例：登记了但没被调用",
         lambda m, p: m["gates"].append({"id": "x", "script": "ghost.py", "reads": ["r"],
                                         "selftest": True}), "M1")
    case("M2 负例：被调用但没登记",
         lambda m, p: p["gates"]["commands"].append("python3 ghost_extra.py"), "M2")
    case("M3 负例：清单为空", lambda m, p: m.__setitem__("gates", []), "M3")
    case("M3 负例：命令为空", lambda m, p: p["gates"].__setitem__("commands", []), "M3")
    case("M4 负例：出现豁免白名单", lambda m, p: m.__setitem__("waivers", ["x"]), "M4")
    case("M4 负例：gate 项里出现 allowlist",
         lambda m, p: m["gates"][0].__setitem__("allowlist", ["y"]), "M4")
    case("M5 负例：项缺 reads",
         lambda m, p: m["gates"][0].pop("reads"), "M5")
    case("M5 负例：项未声明 selftest",
         lambda m, p: m["gates"][0].__setitem__("selftest", False), "M5")
    case("M6 负例：未声明未覆盖面",
         lambda m, p: m.pop("not_covered"), "M6")

    ok = all(v for _, v in cases)
    for name, res in cases:
        print("  [%s] %s" % ("PASS" if res else "FAIL", name))
    print("\n=== 清单双向校验自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest")
    ap.add_argument("--profile")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    try:
        m = D.load_json(a.manifest, "门控清单")
        p = D.load_json(a.profile, "profile")
    except D.GuardError as exc:
        print("GUARD-REJECT: %s" % exc)
        return 2
    R = check(m, p)
    for cid, name, ok, detail in R:
        print("[%s] %s %s — %s" % ("PASS" if ok else "FAIL", cid, name, detail))
    if a.json:
        print(json.dumps([{"id": c, "name": n, "ok": o, "detail": d} for c, n, o, d in R],
                         ensure_ascii=False, indent=1))
    nf = sum(1 for r in R if not r[2])
    print("\n=== 门控清单双向校验：%d 项判据，%d FAIL ===" % (len(R), nf))
    return 0 if nf == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
