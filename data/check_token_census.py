#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_token_census.py — 站点管线内的**令牌普查门控入口**（薄适配器）。

★ 方案 §5.1 点名的三条站点侧门控之一（`data/check_token_census.py`）。判据实现在**仓根**
  `gate_census.py`（§4.1：门控放仓根）⇒ 本件只是管线内的调用入口，⛔ 不复制判据实现。

用法与退出码与 `gate_census.py` 完全一致：
    python3 data/check_token_census.py --selftest
    python3 data/check_token_census.py
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.argv = [os.path.join(REPO, "gate_census.py")] + sys.argv[1:]
runpy.run_path(os.path.join(REPO, "gate_census.py"), run_name="__main__")
