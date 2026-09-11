#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
示例：流域水量平衡与地下水位趋势分析
================================================================
这个脚本有两个作用：
    1. 作为 Agent 的「可运行参考实现」——告诉它本仓库的代码风格、
       日志规范、输出约定是什么样
    2. 作为环境验证的可执行样本——装完环境后能真跑出结果

方法说明：
    (1) 水量平衡：P = ET + Q + ΔS
        P   降水量
        ET  实际蒸散发
        Q   地表径流 + 地下水排泄量
        ΔS  流域蓄变量（含土壤水、地下水）
    (2) Mann-Kendall 非参数趋势检验
        优点：不要求数据服从正态分布，对异常值稳健，水文序列分析标准方法
    (3) Sen's slope 斜率估计（Theil-Sen 中位数斜率）
        优点：同样抗异常值，与 MK 检验配套使用

用法：
    python scripts/water_balance.py
    python scripts/water_balance.py --years 2005 2024
================================================================
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Sequence


# ------------------------------------------------------------
# 核心算法（纯标准库实现，保证在任何环境都能跑）
# ------------------------------------------------------------
def water_balance_residual(
    precipitation: float,
    evapotranspiration: float,
    runoff: float,
    delta_storage: float,
) -> tuple[float, float]:
    """计算水量平衡残差与相对闭合误差(%)。"""
    residual = precipitation - (evapotranspiration + runoff + delta_storage)
    relative = abs(residual) / precipitation * 100.0 if precipitation else float("nan")
    return residual, relative


def mann_kendall(series: Sequence[float]) -> dict[str, float]:
    """Mann-Kendall 趋势检验，返回 Z 统计量与双侧 p 值。"""
    data = list(series)
    n = len(data)
    if n < 4:
        return {"Z": 0.0, "p": 1.0, "n": n, "trend": "样本过少"}

    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = data[j] - data[i]
            if diff > 0:
                s += 1
            elif diff < 0:
                s -= 1

    var_s = n * (n - 1) * (2 * n + 5) / 18.0
    if var_s <= 0:
        return {"Z": 0.0, "p": 1.0, "n": n, "trend": "方差为零"}

    if s > 0:
        z = (s - 1) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / math.sqrt(var_s)
    else:
        z = 0.0

    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))

    if p >= 0.05:
        trend = "无显著趋势"
    elif z > 0:
        trend = "显著上升趋势 (p<0.05)"
    else:
        trend = "显著下降趋势 (p<0.05)"

    return {"Z": z, "p": p, "n": n, "trend": trend}


def sens_slope(series: Sequence[float], time_step: float = 1.0) -> float:
    """Sen's slope：所有点对斜率的中位数，单位 = 序列值单位 / time_step。"""
    data = list(series)
    n = len(data)
    slopes = [
        (data[j] - data[i]) / (j - i) / time_step
        for i in range(n - 1)
        for j in range(i + 1, n)
    ]
    if not slopes:
        return float("nan")
    slopes.sort()
    mid = len(slopes) // 2
    if len(slopes) % 2 == 1:
        return slopes[mid]
    return (slopes[mid - 1] + slopes[mid]) / 2.0


# ------------------------------------------------------------
# 演示数据（真实项目请替换为 data/raw/ 下的观测序列）
# ------------------------------------------------------------
DEMO_PRECIPITATION = 820.0        # mm/yr
DEMO_ET = 415.0
DEMO_RUNOFF = 305.0
DEMO_DELTA_STORAGE = 100.0

# 2005-2024 年地下水位埋深（m），逐年增大 = 水位持续下降
DEMO_GROUNDWATER_DEPTH = [
    3.10, 3.42, 3.61, 3.98, 4.31, 4.58, 5.02, 5.37, 5.66, 6.19,
    6.44, 6.80, 7.15, 7.42, 7.88, 8.10, 8.55, 8.91, 9.24, 9.60,
]


def main() -> int:
    parser = argparse.ArgumentParser(description="流域水量平衡与地下水位趋势分析")
    parser.add_argument("--years", nargs=2, type=int, default=[2005, 2024],
                        help="观测年份起止，默认 2005 2024")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args()

    start_year, end_year = args.years
    years = list(range(start_year, end_year + 1))
    depth = DEMO_GROUNDWATER_DEPTH[: len(years)]

    residual, relative = water_balance_residual(
        DEMO_PRECIPITATION, DEMO_ET, DEMO_RUNOFF, DEMO_DELTA_STORAGE
    )
    mk = mann_kendall(depth)
    slope = sens_slope(depth, time_step=1.0)   # 单位 m/yr

    # 方向语义：埋深与水位方向相反，必须显式换算，避免结论被误读
    if slope > 0:
        physical_meaning = "水位持续下降（埋深增大）"
    elif slope < 0:
        physical_meaning = "水位持续回升（埋深减小）"
    else:
        physical_meaning = "水位基本稳定"

    result = {
        "研究区": "示例流域（请替换为实际研究区）",
        "时段": f"{start_year}-{end_year}",
        "水量平衡": {
            "降水_mm": DEMO_PRECIPITATION,
            "蒸散发_mm": DEMO_ET,
            "径流_mm": DEMO_RUNOFF,
            "蓄变量_mm": DEMO_DELTA_STORAGE,
            "残差_mm": round(residual, 6),
            "相对闭合误差_%": round(relative, 6),
        },
        "地下水位埋深趋势": {
            "MK_Z": round(mk["Z"], 4),
            "MK_p": round(mk["p"], 6),
            "埋深趋势": mk["trend"],
            "Sen斜率_m_per_yr": round(slope, 4),
            "累计埋深增量_m": round(slope * (len(years) - 1), 3),
            "物理含义": physical_meaning,
            "方向说明": "埋深上升 = 水位下降，二者符号相反",
        },
        "数据点数": len(depth),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    line = "=" * 66
    print(line)
    print(" 流域水量平衡与地下水位趋势分析")
    print(line)
    print(f" 研究区：{result['研究区']}")
    print(f" 时段  ：{result['时段']}（共 {len(depth)} 年）")
    print("-" * 66)
    print(" 【水量平衡】 P = ET + Q + dS")
    print(f"   降水 P        {DEMO_PRECIPITATION:>8.1f} mm/yr")
    print(f"   蒸散发 ET     {DEMO_ET:>8.1f} mm/yr")
    print(f"   径流 Q        {DEMO_RUNOFF:>8.1f} mm/yr")
    print(f"   蓄变 dS       {DEMO_DELTA_STORAGE:>8.1f} mm/yr")
    print(f"   残差          {residual:>8.6f} mm/yr")
    print(f"   相对闭合误差  {relative:>8.6f} %")
    print("-" * 66)
    print(" 【地下水位埋深趋势】 Mann-Kendall + Sen's slope")
    print(f"   MK 统计量 Z   {mk['Z']:>8.4f}")
    print(f"   p 值          {mk['p']:>8.6f}")
    print(f"   埋深趋势      {mk['trend']}")
    print(f"   Sen 斜率      {slope:>8.4f} m/yr  （年际埋深增量）")
    print(f"   累计增量      {slope * (len(years) - 1):>8.3f} m（{start_year}-{end_year}）")
    print("-" * 66)
    print(f"   物理含义      {physical_meaning}")
    print("   注意：埋深上升 = 水位下降，二者符号相反。报告中必须写清是")
    print("         埋深还是水位高程，否则结论方向会被误读。")
    print(line)
    print(" 注：以上为演示数据。真实分析请接入 data/raw/ 下的实测序列，")
    print("     并核验观测井编号、水位基准面、观测频次与缺测插补方法。")
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
