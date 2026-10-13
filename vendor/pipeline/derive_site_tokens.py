#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""derive_site_tokens.py — 「站点独立值件 → 本站令牌块」的派生器（批 D 共通件）。

用法：
    python3 derive_site_tokens.py --contract V --profile P [--family F] --out O --apply
    python3 derive_site_tokens.py --contract V --profile P [--family F] --out O --check
    python3 derive_site_tokens.py --contract V --profile P [--family F] --print
    python3 derive_site_tokens.py --selftest        # 负向夹具自检（判据非恒真）

★ 三级覆盖的落地顺序（SH1 §4.5.3「族默认 → 站点覆盖 → 页面族覆盖」）：
    ① 族默认：palettes[*].values[role][form] 给出角色基值；
    ② 站点覆盖：binding.site_token_names 把角色映射为本站令牌名；
    ③ 页面族覆盖：families[F].overrides **覆盖或追加**令牌（同名覆盖、新名追加）。
  再叠加 passthrough_tokens 的非角色令牌（字体栈/间距/圆角等，逐字节沿用）。
  ⇒ 同名令牌在**不同族**取不同值是被允许且须逐族登记的（这是页面族覆盖存在的成因）。

fail-closed 护栏（任一不满足即拒写、零写入、非零退出 3）：
  P1 值件与 profile 必须是合法 JSON 且必需段齐备
  P2 每个角色的 tier 必须指向值件内已声明的用途档（防悬挂）
  P3 值件声明的每个相关角色都必须在 binding.site_token_names 里有令牌名，且绑定表无未声明角色
  P4 profile.targets 与值件 families[*].targets 必须逐族一致（防两处各自漂移）
  P5 passthrough 令牌名不得与角色绑定名撞名（防静默覆盖）
  P6 值件声明的每个 form 都必须在该 palette 的每个角色下有取值
  P7 空集守卫：渲染结果为空、或某族一个令牌都没有 ⇒ 拒写（⛔ 不得静默产出空文件）

退出码：0 成功 / 1 对账漂移 / 2 输入错误 / 3 护栏拒写
"""
import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

REQUIRED_CONTRACT_SECTIONS = ("meta", "scope", "usage_tiers", "roles", "palettes",
                              "binding", "families", "derivation")
REQUIRED_PROFILE_KEYS = ("site", "form", "targets", "value_file", "publish_dir")

COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
ROOT_BLOCK_RE = re.compile(r":root\s*\{[^{}]*\}", re.S)


class GuardError(Exception):
    """护栏拒写（exit 3）。"""


def load_json(path, label):
    if not os.path.isfile(path):
        raise GuardError("P1 %s 不存在：%s" % (label, path))
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        raise GuardError("P1 %s 非法 JSON：%s" % (label, exc))


def check_contract(doc):
    """P1 + P2 + P3：值件结构与角色/档位引用完整性。"""
    if not isinstance(doc, dict):
        raise GuardError("P1 值件顶层不是对象")
    missing = [k for k in REQUIRED_CONTRACT_SECTIONS if k not in doc]
    if missing:
        raise GuardError("P1 值件缺段：%s" % ",".join(missing))
    for key in ("roles", "palettes", "binding", "families", "usage_tiers"):
        if not isinstance(doc[key], dict) or not doc[key]:
            raise GuardError("P1 值件段 %s 必须是非空对象" % key)
    if not (doc["binding"].get("site_token_names") or {}):
        raise GuardError("P3 角色无令牌名绑定：binding.site_token_names 为空")
    tiers = doc["usage_tiers"]
    for role, spec in doc["roles"].items():
        if spec.get("tier") not in tiers:
            raise GuardError("P2 角色 %s 的 tier=%r 未在 usage_tiers 内（档位悬挂）"
                             % (role, spec.get("tier")))
    names = doc["binding"].get("site_token_names") or {}
    for role in doc["roles"]:
        if role not in names:
            raise GuardError("P3 角色 %s 没有令牌名绑定（防漏派）" % role)
    for role in names:
        if role not in doc["roles"]:
            raise GuardError("P3 绑定表出现未声明角色 %s" % role)
    return True


def check_profile(profile):
    missing = [k for k in REQUIRED_PROFILE_KEYS if k not in profile]
    if missing:
        raise GuardError("P1 profile 缺键：%s" % ",".join(missing))
    if not profile["targets"]:
        raise GuardError("P7 空集守卫：profile.targets 为空")
    return True


def resolve_family(profile, contract, family):
    """P4：profile.targets 与 families[*].targets 逐族一致；返回 (family_id, tokens_for_that_family)。"""
    fams = contract["families"]
    fid = family or next(iter(fams))
    if fid not in fams:
        raise GuardError("P4 值件未声明页面族 %r（已声明：%s）" % (fid, ",".join(fams)))
    by_fam = {}
    for t in profile["targets"]:
        by_fam.setdefault(t["family"], []).append(t["path"])
    for k, spec in fams.items():
        if sorted(spec.get("targets") or []) != sorted(by_fam.get(k, [])):
            raise GuardError(
                "P4 页面族 %s 的 targets 两处不一致：值件=%s / profile=%s"
                % (k, sorted(spec.get("targets") or []), sorted(by_fam.get(k, []))))
    for k in by_fam:
        if k not in fams:
            raise GuardError("P4 profile 使用了值件未声明的页面族 %r" % k)
    return fid


def build_tokens(contract, profile, family=None):
    """三级覆盖 → 有序令牌表（dict 保序，Python 3.7+）。"""
    check_contract(contract)
    check_profile(profile)
    fid = resolve_family(profile, contract, family)

    scope = contract["scope"]
    forms = scope["declared_forms"]
    primary = forms[0]
    palette_id = next(iter(contract["palettes"]))
    palette = contract["palettes"][palette_id]
    values = palette["values"]

    names = contract["binding"]["site_token_names"]
    tokens = {}
    for role, token in names.items():
        if role not in values:
            raise GuardError("P6 角色 %s 在 palette %s 下无取值" % (role, palette_id))
        for form in forms:
            if form not in values[role]:
                raise GuardError("P6 角色 %s 缺 %s 档取值" % (role, form))
        tokens[token] = values[role].get(primary)

    fam_over = (contract["families"][fid].get("overrides") or {})
    for k, v in fam_over.items():
        tokens[k] = v  # 同名覆盖（保位置）/ 新名追加

    passed = contract["binding"].get("passthrough_tokens") or {}
    for group, kv in passed.items():
        if not isinstance(kv, dict):
            continue
        for k, v in kv.items():
            if not str(k).startswith("--"):
                continue      # ★ 组内的 `_note` 一类是**注解**，不是令牌（防把它当令牌写进产物）
            if k in names.values():
                raise GuardError("P5 passthrough 令牌 %s 与角色绑定名撞名（防静默覆盖）" % k)
            tokens.setdefault(k, v)

    if not tokens:
        raise GuardError("P7 空集守卫：渲染结果为空（一个令牌都没有）")
    return fid, tokens


def render(tokens):
    """确定性渲染：:root{--a:v;--b:v;}（无空格、无时钟、无随机）。"""
    return ":root{" + "".join("%s:%s;" % (k, v) for k, v in tokens.items()) + "}"


def normalize(text):
    """判据归一化：剥离注释与全部空白（SH1 §4.5.3 的对账口径）。"""
    text = COMMENT_RE.sub("", text)
    return re.sub(r"\s+", "", text)


def extract_block(text):
    """定位首个 :root{...} 块；找不到返回 None。"""
    m = ROOT_BLOCK_RE.search(text)
    return m.group(0) if m else None


def parse_tokens(block):
    body = re.sub(r"^:root\s*\{|\}$", "", block.strip(), flags=re.S)
    out = {}
    for name, val in re.findall(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;]+)", body):
        out[name] = val.strip()
    return out


# ----------------------------------------------------------------------------- selftest
FIXTURE_CONTRACT = {
    "meta": {"id": "t", "contract_version": "0", "frozen_at": "2026-10-13", "title": "t"},
    "scope": {"site": "t", "upstream_repo_head": "0" * 40, "declared_forms": ["dark"]},
    "usage_tiers": {"body": {"allowed_use": "x", "min_contrast": {"dark": 4.5}, "gate": "hard"},
                    "non-body": {"allowed_use": "x", "min_contrast": {"dark": 4.5}, "gate": "report-only"},
                    "non-text": {"allowed_use": "x", "min_contrast": {"dark": 3.0}, "gate": "hard"}},
    "roles": {"text.primary": {"tier": "body", "kind": "text", "purpose": "p", "site_source": "s"}},
    "palettes": {"p": {"family": "f", "provenance": "x",
                       "values": {"text.primary": {"dark": "#ffffff"}}}},
    "binding": {"site_token_names": {"text.primary": "--text"}, "note": "n",
                "passthrough_tokens": {"layout": {"--w-max": "1120px"}}},
    "families": {"default": {"targets": ["a.html"], "overrides": {}}},
    "derivation": {"state": "s", "direction": "d", "generator_ref": "g", "rule": "r"},
}
FIXTURE_PROFILE = {
    "site": "t", "form": "inline-single-source", "publish_dir": ".",
    "value_file": "v.json", "targets": [{"path": "a.html", "mode": "root-block", "family": "default"}],
    "gates": {"manifest": "m.json", "hard_blocking": ["contrast"], "commands": ["x"]},
}


def _clone(o):
    return json.loads(json.dumps(o))


def selftest():
    cases = []

    def case(name, mutate, expect_guard=True):
        c = _clone(FIXTURE_CONTRACT)
        p = _clone(FIXTURE_PROFILE)
        try:
            mutate(c, p)
            out = build_tokens(c, p)
            if render(out[1]) == "":
                raise AssertionError("渲染为空")
            cases.append((name, not expect_guard))
        except GuardError:
            cases.append((name, expect_guard))
        except Exception:  # noqa: BLE001
            cases.append((name, False))

    def _mk(contract=None, profile=None, drop_roles=(), drop_names=()):
        c = _clone(contract or FIXTURE_CONTRACT)
        p = _clone(profile or FIXTURE_PROFILE)
        for r in drop_roles:
            c["roles"].pop(r, None)
        for n in drop_names:
            c["binding"]["site_token_names"].pop(n, None)
        return c, p

    case("N1a 值件缺段（删 users_tiers… 即 usage_tiers）",
         lambda c, p: c.pop("usage_tiers"))
    case("N1b profile 缺 targets", lambda c, p: p.pop("targets"))
    case("N2 角色 tier 悬挂", lambda c, p: c["roles"]["text.primary"].__setitem__("tier", "nope"))
    case("N3a 角色无令牌名绑定", lambda c, p: c["binding"]["site_token_names"].clear())
    case("N3b 绑定表出现未声明角色",
         lambda c, p: c["binding"]["site_token_names"].__setitem__("ghost", "--ghost"))
    case("N4a profile 使用了值件未声明的族",
         lambda c, p: p["targets"][0].__setitem__("family", "ghost"))
    case("N4b 值的 targets 与 profile 不一致",
         lambda c, p: c["families"]["default"].__setitem__("targets", ["other.html"]))
    case("N5 passthrough 与角色绑定名撞名",
         lambda c, p: c["binding"]["passthrough_tokens"].__setitem__("x", {"--text": "#000"}))
    case("N6 角色缺该档取值",
         lambda c, p: c["palettes"]["p"]["values"]["text.primary"].pop("dark"))
    case("N7 空集守卫（一个令牌都没有）",
         lambda c, p: (c["binding"]["passthrough_tokens"].clear(),
                       c["binding"]["site_token_names"].clear()))
    case("N8 非法 JSON（结构被破坏成非 dict 段）", lambda c, p: c.__setitem__("roles", []))

    # 确定性（正向）：同输入两次渲染必须逐字节相同
    _, t1 = build_tokens(_clone(FIXTURE_CONTRACT), _clone(FIXTURE_PROFILE))
    _, t2 = build_tokens(_clone(FIXTURE_CONTRACT), _clone(FIXTURE_PROFILE))
    cases.append(("P-正例 确定性（两次渲染逐字节相同）", render(t1) == render(t2)))
    cases.append(("P-正例 覆盖顺序（family 覆盖角色值）",
                  render(build_tokens(
                      {**_clone(FIXTURE_CONTRACT),
                       "families": {"default": {"targets": ["a.html"],
                                                "overrides": {"--text": "#000000"}}}},
                      _clone(FIXTURE_PROFILE))[1]) == ":root{--text:#000000;--w-max:1120px;}"))

    ok = all(v for _, v in cases)
    for name, res in cases:
        print("  [%s] %s" % ("PASS" if res else "FAIL", name))
    print("\n=== 派生器自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract")
    ap.add_argument("--profile")
    ap.add_argument("--family")
    ap.add_argument("--out")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--print", dest="show", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    try:
        contract = load_json(a.contract, "值件")
        profile = load_json(a.profile, "profile")
        fid, tokens = build_tokens(contract, profile, a.family)
    except GuardError as exc:
        print("GUARD-REJECT: %s" % exc)
        return 3

    block = render(tokens)
    if a.show:
        print(block)
        return 0
    if a.check:
        if not a.out or not os.path.isfile(a.out):
            print("GUARD-REJECT: --check 需 --out 已存在的派生产物")
            return 2
        disk = normalize(open(a.out, encoding="utf-8").read())
        if disk != normalize(block):
            print("DRIFT: 派生产物与值件不一致：%s" % a.out)
            return 1
        print("OK: 派生产物与值件一致（family=%s，%d 令牌）" % (fid, len(tokens)))
        return 0
    if a.json:
        print(json.dumps({"family": fid, "count": len(tokens), "tokens": tokens},
                         ensure_ascii=False, indent=2))
        return 0
    if not a.out:
        print(block)
        return 0
    if a.apply:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(block + "\n")
        print("已写派生产物：%s（family=%s，%d 令牌）" % (a.out, fid, len(tokens)))
        return 0
    print(block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
