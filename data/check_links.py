#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_links.py — 站点管线内的**链路门控入口**（薄适配器）。

★ 方案 §5.1 点名的三条站点侧门控之一（`data/check_links.py`）。★ 判据实现在**仓根**
  `gate_links.py` 里（§4.1 的落点硬约束：门控放仓根，⛔ 不散落在生成器目录）
  ⇒ 本件只做「站点管线内的调用入口」，⛔ **不复制第二套判据实现**（那会立刻产生两套口径）。

用法与退出码与 `gate_links.py` 完全一致：
    python3 data/check_links.py --selftest
    python3 data/check_links.py
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.argv = [os.path.join(REPO, "gate_links.py")] + sys.argv[1:]
runpy.run_path(os.path.join(REPO, "gate_links.py"), run_name="__main__")
