#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""write_site_tokens.py — 把派生产物（令牌块）**就地写入**站点目标的写入器（批 D 共通件）。

用法：
    python3 write_site_tokens.py --profile P --payloads D --site-root R --apply
    python3 write_site_tokens.py --profile P --payloads D --site-root R --check
    python3 write_site_tokens.py --profile P --payloads D --site-root R --dry-run
    python3 write_site_tokens.py --selftest          # 负向夹具自检（判据非恒真）

三种写入模式（由 profile.targets[*].mode 声明，⛔ 不由脚本猜）：
    whole-file     整文件写出（形态 1 的专用外链产物；该文件**只含令牌**，不承载布局规则）
    root-block     只重写首个 `:root{...}` 块，**其余字节逐字节保留**
    marker-region  只重写 `/* TOKENS:BEGIN */` … `/* TOKENS:END */` 之间，标记本身保留

fail-closed 护栏（任一不满足即拒写、**零写入**、非零退出 3）：
  B1 目标必须可定位且**唯一**：root-block 必须恰有一个 `:root{...}`；marker-region 的
     起止标记必须各恰一次、且不嵌套（缺任一即拒写，⛔ 不做半途写入）
  B2 纯函数：无运行时钟、无随机、不联网；同输入两次运行零变化（幂等）
  B3 `--check` 逐字节对账（剥离尾部空白），漂移 → exit 1
  B4 ★ 非目标段 sha256 前后不变（证明「只动令牌块」）——这是本站最贵的一类事故的判据
  B5 目标路径必须落在 --site-root 内（拒绝绝对路径与 `..` 越界）

退出码：0 成功 / 1 对账漂移 / 2 输入错误 / 3 护栏拒写
"""
import argparse
import hashlib
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import derive_site_tokens as D  # noqa: E402  复用同一套归一化/块定位实现（⛔ 不造第二套）

BEGIN = "/* TOKENS:BEGIN */"
END = "/* TOKENS:END */"
SENTINEL = "\x00NON-TARGET-REGION\x00"


# ★ 与派生器共用同一个 GuardError 类：调用方（契约门控 / 验收总闸）可以只捕一个类型。
GuardError = D.GuardError


def safe_join(site_root, rel):
    if os.path.isabs(rel) or ".." in rel.split("/"):
        raise GuardError("B5 目标路径越界或为绝对路径：%s" % rel)
    root = os.path.abspath(site_root)
    full = os.path.abspath(os.path.join(root, rel))
    if not (full == root or full.startswith(root + os.sep)):
        raise GuardError("B5 目标路径越界：%s" % rel)
    return full


def locate(text, mode):
    """返回 (start, end, kind)：将被子载荷替换的字节区间。B1 全在此实现。"""
    if mode == "root-block":
        ms = list(re.finditer(r":root\s*\{[^{}]*\}", text, re.S))
        if len(ms) != 1:
            raise GuardError("B1 root-block 模式要求恰有 1 个 :root{...}，实测 %d 个" % len(ms))
        return ms[0].start(), ms[0].end(), "block"
    if mode == "marker-region":
        nb, ne = text.count(BEGIN), text.count(END)
        if nb != 1 or ne != 1:
            raise GuardError("B1 marker 必须各恰一次（BEGIN=%d END=%d）" % (nb, ne))
        s = text.index(BEGIN) + len(BEGIN)
        e = text.index(END)
        if e < s:
            raise GuardError("B1 marker 嵌套或顺序颠倒（END 在 BEGIN 之前）")
        if BEGIN in text[s:e] or END in text[s:e]:
            raise GuardError("B1 marker 嵌套")
        return s, e, "inner"
    raise GuardError("B1 未知写入模式：%r" % mode)


def non_target_digest(text, span):
    s, e, _ = span
    return hashlib.sha256((text[:s] + SENTINEL + text[e:]).encode("utf-8")).hexdigest()


def splice(text, span, payload):
    s, e, _ = span
    return text[:s] + payload + text[e:]


def plan_target(profile, payloads_dir, site_root, target, apply=False):
    path = target["path"]
    full = safe_join(site_root, path)
    fam = target["family"]
    pl = os.path.join(payloads_dir, "%s.css" % fam)
    if not os.path.isfile(pl):
        raise GuardError("B1 缺少族 %s 的派生产物：%s" % (fam, pl))
    payload = open(pl, encoding="utf-8").read().strip()

    mode = target["mode"]
    exists = os.path.isfile(full)
    rec = {"path": path, "mode": mode, "family": fam, "exists": exists}

    if mode == "whole-file":
        old = open(full, encoding="utf-8").read() if exists else None
        rec.update({"guard": "N/A（整文件模式：该产物**只含令牌**，不承载布局规则）",
                    "changed": (old is None or D.normalize(old) != D.normalize(payload))})
        return full, payload + "\n", rec

    if not exists:
        raise GuardError("B1 目标不存在：%s" % path)
    old = open(full, encoding="utf-8").read()
    span = locate(old, mode)
    new = splice(old, span, payload)
    d_old = non_target_digest(old, span)
    span_new = (span[0], span[0] + len(payload), span[2])
    d_new = non_target_digest(new, span_new)
    if d_old != d_new:
        raise GuardError("B4 非目标段 sha256 被改动（只应改令牌块）：%s" % path)
    rec.update({"guard": "B4 非目标段 sha256 不变（%s…）" % d_old[:12],
                "block_bytes": "%d → %d" % (span[1] - span[0], len(payload)),
                "changed": D.normalize(old) != D.normalize(new)})
    return full, new, rec


def run(profile, payloads_dir, site_root, mode, show=False):
    results = []
    for t in profile["targets"]:
        full, new, rec = plan_target(profile, payloads_dir, site_root, t)
        if mode == "check":
            if not os.path.isfile(full):
                rec["verdict"] = "DRIFT（目标缺失）"
                results.append((full, None, rec))
                continue
            disk = open(full, encoding="utf-8").read().rstrip()
            rec["verdict"] = "OK" if D.normalize(disk) == D.normalize(new) else "DRIFT"
            results.append((full, None, rec))
        elif mode == "apply":
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(new)
            rec["verdict"] = "WROTE" if rec["changed"] else "NOOP（幂等）"
            results.append((full, None, rec))
        else:
            if show:
                print("----- %s (%s) -----" % (full, t["mode"]))
                print(new)
            rec["verdict"] = "WOULD-WRITE" if rec["changed"] else "NOOP（幂等）"
            results.append((full, None, rec))
    return results


def report(results, mode):
    for full, _new, rec in results:
        print("  [%-11s] %-46s %s" % (rec["verdict"], rec["path"], rec["guard"]))
        if "block_bytes" in rec:
            print("                %s 块字节：%s" % (rec["mode"], rec["block_bytes"]))
    bad = [r for r in results if r[2]["verdict"] == "DRIFT"]
    return 1 if bad else 0


# ----------------------------------------------------------------------------- selftest
def selftest():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="wst-")
    pay = os.path.join(tmp, "payloads")
    os.makedirs(pay)
    open(os.path.join(pay, "default.css"), "w", encoding="utf-8").write(":root{--a:2;--b:#fff;}")
    site = os.path.join(tmp, "site")
    os.makedirs(os.path.join(site, "sub"))
    base = "body{color:red}\n"
    open(os.path.join(site, "rb.html"), "w", encoding="utf-8").write(":root{--a:1;}\n" + base)
    open(os.path.join(site, "mk.html"), "w", encoding="utf-8").write(
        "h1{x:1}\n%s\n:root{--a:1;}\n%s\np{y:2}\n" % (BEGIN, END))
    open(os.path.join(site, "no_root.html"), "w", encoding="utf-8").write(base)
    open(os.path.join(site, "dup.html"), "w", encoding="utf-8").write(
        ":root{--a:1;}:root{--b:2;}\n" + base)
    open(os.path.join(site, "nest.html"), "w", encoding="utf-8").write(
        "%s%s%s%s\n" % (BEGIN, BEGIN, END, END))
    open(os.path.join(site, "rev.html"), "w", encoding="utf-8").write(
        "%s\n%s\n" % (END, BEGIN))
    open(os.path.join(site, "wf.css"), "w", encoding="utf-8").write(":root{--old:1;}")

    def prof(targets):
        return {"site": "t", "form": "x", "publish_dir": ".", "value_file": "v.json",
                "targets": targets, "gates": {"manifest": "m", "hard_blocking": ["contrast"],
                                              "commands": ["x"]}}

    def T(path, mode, fam="default", **kw):
        d = {"path": path, "mode": mode, "family": fam}
        d.update(kw)
        return d

    cases = []

    def case(name, fn, expect_ok=True):
        try:
            fn()
            cases.append((name, expect_ok))
        except GuardError:
            cases.append((name, not expect_ok))
        except Exception:  # noqa: BLE001
            cases.append((name, False))

    # B1 负例
    case("B1a root-block 目标无 :root", lambda: plan_target(
        prof([]), pay, site, T("no_root.html", "root-block"), True), expect_ok=False)
    case("B1b root-block 有 2 个 :root（不唯一）", lambda: plan_target(
        prof([]), pay, site, T("dup.html", "root-block"), True), expect_ok=False)
    case("B1c marker 缺 END", lambda: plan_target(
        prof([]), pay, site, T("rb.html", "marker-region"), True), expect_ok=False)
    case("B1d marker 重复/嵌套（各 2 次）", lambda: plan_target(
        prof([]), pay, site, T("nest.html", "marker-region"), True), expect_ok=False)
    case("B1d2 marker 顺序颠倒（END 在 BEGIN 之前）", lambda: plan_target(
        prof([]), pay, site, T("rev.html", "marker-region"), True), expect_ok=False)
    case("B1e 族缺派生产物", lambda: plan_target(
        prof([]), pay, site, T("rb.html", "root-block", fam="ghost"), True), expect_ok=False)
    case("B1f 目标不存在", lambda: plan_target(
        prof([]), pay, site, T("nope.html", "root-block"), True), expect_ok=False)
    case("B5a 越界路径 ..", lambda: safe_join(site, "../evil"), expect_ok=False)
    case("B5b 绝对路径", lambda: safe_join(site, "/etc/passwd"), expect_ok=False)

    # B4 负例：注入「越出目标区间」的替换 → 非目标段摘要必不相等 → 必须被 GuardError 拦住
    def b4_neg():
        orig_splice = splice
        globals()["splice"] = lambda text, span, payload: (
            text[:span[0]] + payload + "EXTRA-BYTES" + text[span[1]:])
        try:
            plan_target(prof([]), pay, site, T("rb.html", "root-block"), True)
        finally:
            globals()["splice"] = orig_splice
    case("B4 负例（越界替换必被拦）", b4_neg, expect_ok=False)

    # B4 敏感性：摘要对区间敏感（错误区间与正确区间必不同）
    def b4_sense():
        text = open(os.path.join(site, "rb.html"), encoding="utf-8").read()
        span_wrong = (0, len(base), "block")
        span_right = locate(text, "root-block")
        if non_target_digest(text, span_wrong) == non_target_digest(text, span_right):
            raise GuardError("B4 摘要对区间不敏感（判据恒真）")
    case("B4 敏感性（摘要对区间敏感，非恒真）", b4_sense)

    # 正向：root-block 写入后 B4 成立
    def b4_pos():
        text = open(os.path.join(site, "rb.html"), encoding="utf-8").read()
        span = locate(text, "root-block")
        pl = ":root{--a:9;}"
        new = splice(text, span, pl)
        if non_target_digest(text, span) != non_target_digest(new, (span[0], span[0] + len(pl), "block")):
            raise GuardError("B4 正例失败")
    case("P-正例 B4 非目标段 sha256 不变", b4_pos)

    # 正向：幂等 + --check
    def idem():
        p = prof([T("rb.html", "root-block")])
        run(p, pay, site, "apply")
        first = open(os.path.join(site, "rb.html"), encoding="utf-8").read()
        res = run(p, pay, site, "apply")
        second = open(os.path.join(site, "rb.html"), encoding="utf-8").read()
        if first != second or res[0][2]["verdict"] != "NOOP（幂等）":
            raise GuardError("B2 幂等失败")
        if run(p, pay, site, "check")[0][2]["verdict"] != "OK":
            raise GuardError("B3 --check 失败")
    case("B2/B3 幂等：二次 apply 零变化且 --check OK", idem)

    # 正向：marker-region 只改标记之间
    def marker_ok():
        before = open(os.path.join(site, "mk.html"), encoding="utf-8").read()
        run(prof([T("mk.html", "marker-region")]), pay, site, "apply")
        after = open(os.path.join(site, "mk.html"), encoding="utf-8").read()
        if "h1{x:1}" not in after or "p{y:2}" not in after or BEGIN not in after or END not in after:
            raise GuardError("标记区外内容被破坏")
        if before.count(BEGIN) != after.count(BEGIN):
            raise GuardError("标记本身被吞")
    case("P-正例 marker-region 标记保留、区外不变", marker_ok)

    # 正向：whole-file 新建 + 幂等
    def whole_ok():
        run(prof([T("wf.css", "whole-file")]), pay, site, "apply")
        r1 = run(prof([T("wf.css", "whole-file")]), pay, site, "apply")
        if r1[0][2]["verdict"] != "NOOP（幂等）":
            raise GuardError("whole-file 非幂等")
        if run(prof([T("wf.css", "whole-file")]), pay, site, "check")[0][2]["verdict"] != "OK":
            raise GuardError("whole-file --check 失败")
    case("P-正例 whole-file 新建 + 幂等 + --check", whole_ok)

    # B3 负例：篡改后 --check 必须报 DRIFT
    def drift():
        open(os.path.join(site, "wf.css"), "a", encoding="utf-8").write("/*x*/")
        v = run(prof([T("wf.css", "whole-file")]), pay, site, "check")[0][2]["verdict"]
        if v != "DRIFT":
            raise GuardError("篡改未被检出")
    case("B3 负例（篡改后必报 DRIFT）", drift, expect_ok=False)

    ok = all(v for _, v in cases)
    for name, res in cases:
        print("  [%s] %s" % ("PASS" if res else "FAIL", name))
    print("\n=== 写入器自检：%d 项，%d FAIL ===" % (len(cases), sum(1 for _, v in cases if not v)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile")
    ap.add_argument("--payloads")
    ap.add_argument("--site-root")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--print", dest="show", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.profile and a.payloads and a.site_root):
        print("用法错误：需 --profile / --payloads / --site-root")
        return 2
    try:
        profile = D.load_json(a.profile, "profile")
        mode = "apply" if a.apply else ("check" if a.check else "dry-run")
        results = run(profile, a.payloads, a.site_root, mode, a.show)
    except GuardError as exc:
        print("GUARD-REJECT: %s" % exc)
        return 3
    rc = report(results, mode)
    print("\n=== %s：%d 目标，%d FAIL ===" % (mode, len(results), 1 if rc else 0))
    return rc


if __name__ == "__main__":
    sys.exit(main())
