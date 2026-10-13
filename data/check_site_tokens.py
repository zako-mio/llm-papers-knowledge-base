#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_site_tokens.py — 站点管线内的**站点契约门控入口**（薄适配器）。

★ 方案 §5.1 点名的三条站点侧门控之一（`data/check_site_tokens.py`）。判据实现在**仓根**
  `gate_tokens.py`（G1–G10：角色/值件/派生一致性/对比度/零引用/未声明令牌…）
  ⇒ 本件只是管线内的调用入口，⛔ 不复制判据实现。

★ 与 AUD 侧 `pipeline/check_site_tokens.py`（C1–C12）的分工：那件需要改动前克隆与
  `~/opencode/projects/fe-starter-kit`，**在 CI 上必然 FAIL（环境不成立）**，故只留在 AUD 侧跑。

用法与退出码与 `gate_tokens.py` 完全一致：
    python3 data/check_site_tokens.py --selftest
    python3 data/check_site_tokens.py --site-root . --mode enforce
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.argv = [os.path.join(REPO, "gate_tokens.py")] + sys.argv[1:]
runpy.run_path(os.path.join(REPO, "gate_tokens.py"), run_name="__main__")
