# -*- coding: utf-8 -*-
"""
水文地质科研环境 - pytest 冒烟用例
================================================================
运行：python -m pytest tests/ -v

这些用例只依赖标准库 + 本仓库脚本，保证「即使第三方库没装全，
核心算法逻辑也能被验证」。装了 numpy 之后可再补数值对拍用例
（见文件末尾被跳过的用例骨架）。
================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 允许直接 import scripts/ 下的模块
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from water_balance import (  # noqa: E402
    mann_kendall,
    sens_slope,
    water_balance_residual,
)


# ------------------------------------------------------------
# 水量平衡
# ------------------------------------------------------------
class TestWaterBalance:
    def test_closed_balance_returns_zero_residual(self) -> None:
        """完全闭合的水量平衡，残差应为 0。"""
        residual, relative = water_balance_residual(800.0, 400.0, 300.0, 100.0)
        assert residual == pytest.approx(0.0, abs=1e-9)
        assert relative == pytest.approx(0.0, abs=1e-9)

    def test_unclosed_balance_reports_positive_residual(self) -> None:
        """降水偏多 50mm，残差应为 +50。"""
        residual, relative = water_balance_residual(850.0, 400.0, 300.0, 100.0)
        assert residual == pytest.approx(50.0)
        assert relative == pytest.approx(50.0 / 850.0 * 100.0)

    def test_zero_precipitation_returns_nan_relative_error(self) -> None:
        """降水为 0 时相对误差无定义，应返回 NaN 而非抛异常。"""
        _, relative = water_balance_residual(0.0, 10.0, 5.0, -5.0)
        assert relative != relative  # NaN 判定


# ------------------------------------------------------------
# Mann-Kendall 趋势检验
# ------------------------------------------------------------
class TestMannKendall:
    def test_monotonic_increasing_is_significant(self) -> None:
        series = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        mk = mann_kendall(series)
        assert mk["Z"] > 0
        assert mk["p"] < 0.05
        assert "上升" in mk["trend"]

    def test_monotonic_decreasing_is_significant(self) -> None:
        series = list(range(10, 0, -1))
        mk = mann_kendall(series)
        assert mk["Z"] < 0
        assert mk["p"] < 0.05
        assert "下降" in mk["trend"]

    def test_constant_series_has_no_trend(self) -> None:
        series = [5.0] * 12
        mk = mann_kendall(series)
        assert mk["Z"] == 0.0
        assert mk["p"] == 1.0

    def test_short_series_is_guarded(self) -> None:
        """样本少于 4 个时不应报错，应返回提示。"""
        mk = mann_kendall([1.0, 2.0, 3.0])
        assert mk["trend"] == "样本过少"


# ------------------------------------------------------------
# Sen's slope
# ------------------------------------------------------------
class TestSensSlope:
    def test_linear_series_recovers_slope(self) -> None:
        """严格线性序列，Sen 斜率应精确等于步长。"""
        series = [2.0 * i for i in range(10)]
        assert sens_slope(series) == pytest.approx(2.0)

    def test_outlier_resistance(self) -> None:
        """加入一个异常值后，Sen 斜率应保持稳健（这是它相对最小二乘的优势）。"""
        clean = [1.0 * i for i in range(10)]
        polluted = list(clean)
        polluted[9] = 500.0     # 强异常值
        assert sens_slope(polluted) == pytest.approx(sens_slope(clean), abs=1.5)


# ------------------------------------------------------------
# 环境自检脚本自身可用性
# ------------------------------------------------------------
class TestEnvironmentCheck:
    def test_test_check_script_importable(self) -> None:
        """自检脚本必须能被导入且暴露 build_report。"""
        import test_check

        report = test_check.build_report(run_smoke=False)
        assert "dependencies" in report
        assert report["summary"]["core_total"] > 0

    def test_smoke_tests_all_pass_without_third_party_libs(self) -> None:
        """冒烟测试只用标准库，任何环境都应通过。"""
        import test_check

        for fn in test_check.SMOKE_TESTS:
            assert fn()["pass"] is True, f"冒烟测试失败: {fn.__name__}"


# ------------------------------------------------------------
# 装了 numpy 之后再补的数值对拍用例（现在自动跳过）
# ------------------------------------------------------------
@pytest.mark.skipif(True, reason="需要 numpy / pymannkendall，装好依赖后删除本 skip 标记")
class TestNumpyCrossValidation:
    """用 numpy / pymannkendall 对拍纯标准库实现，确保结果一致。"""

    def test_mk_against_pymannkendall(self) -> None:
        import numpy as np
        import pymannkendall as mk_ref

        series = np.array([3.1, 3.4, 3.6, 4.0, 4.3, 4.6, 5.0, 5.4, 5.7, 6.2])
        ours = mann_kendall(series.tolist())
        ref = mk_ref.original_test(series)
        assert ours["Z"] == pytest.approx(ref.z, abs=1e-6)
