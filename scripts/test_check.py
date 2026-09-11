#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水文地质科研环境自检脚本
================================================================
用途：
    1. 逐项体检 Python 依赖是否安装、版本是否达标
    2. 对缺失的关键包给出「可直接复制执行」的修复命令
    3. 执行不依赖第三方库的数值冒烟测试，确认计算链路可用
       （水量平衡闭合 / Mann-Kendall 趋势检验 / NDVI 计算）

用法：
    python scripts/test_check.py            # 人类可读报告
    python scripts/test_check.py --json     # 机器可读（供 CI / Agent 解析）
    python scripts/test_check.py --no-smoke # 只查依赖，不跑数值测试

退出码：
    0  核心依赖齐备 且 冒烟测试全通过
    1  有核心依赖缺失 或 冒烟测试失败  -> 环境未就绪，不要开始写业务代码

设计原则：
    本脚本只依赖 Python 标准库。即使 numpy 一个都没装，
    它也必须能跑起来并把「缺什么、怎么修」说清楚 —— 否则环境诊断工具
    自己就成了第一个跑不通的东西。
================================================================
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import platform
import sys
from typing import Any

# ============================================================
# 依赖清单：(import 名, 版本属性, 是否核心, 修复提示)
# ============================================================
DEPENDENCIES: list[dict[str, Any]] = [
    # ---- 科学计算底座 ----
    {"import": "numpy", "attr": "__version__", "core": True,
     "fix": "pip install 'numpy>=1.26,<3'"},
    {"import": "pandas", "attr": "__version__", "core": True,
     "fix": "pip install 'pandas>=2.2'"},
    {"import": "scipy", "attr": "__version__", "core": True,
     "fix": "pip install 'scipy>=1.13'"},
    {"import": "xarray", "attr": "__version__", "core": True,
     "fix": "pip install 'xarray>=2024.6'"},
    # ---- 栅格 / 遥感 ----
    {"import": "rasterio", "attr": "__version__", "core": True,
     "fix": "conda install -c conda-forge rasterio  (pip 需先装系统 libgdal-dev)"},
    {"import": "osgeo.gdal", "attr": "__version__", "core": False,
     "fix": "conda install -c conda-forge gdal  或 apt install libgdal-dev"},
    {"import": "rioxarray", "attr": "__version__", "core": False,
     "fix": "pip install 'rioxarray>=0.15'"},
    {"import": "rasterstats", "attr": "__version__", "core": False,
     "fix": "pip install 'rasterstats>=0.19'"},
    # ---- 矢量 / 坐标 ----
    {"import": "geopandas", "attr": "__version__", "core": True,
     "fix": "conda install -c conda-forge geopandas  (pip 亦可用)"},
    {"import": "shapely", "attr": "__version__", "core": True,
     "fix": "pip install 'shapely>=2.0'"},
    {"import": "pyproj", "attr": "__version__", "core": True,
     "fix": "conda install -c conda-forge pyproj  或 pip install 'pyproj>=3.6'"},
    {"import": "fiona", "attr": "__version__", "core": False,
     "fix": "conda install -c conda-forge fiona"},
    # ---- 格点数据 ----
    {"import": "netCDF4", "attr": "__version__", "core": True,
     "fix": "conda install -c conda-forge netcdf4  或 pip install 'netCDF4>=1.6.5'"},
    {"import": "h5py", "attr": "__version__", "core": False,
     "fix": "pip install 'h5py>=3.11'"},
    # ---- 地下水数值模拟 ----
    {"import": "flopy", "attr": "__version__", "core": True,
     "fix": "pip install 'flopy>=3.6.0'"},
    # ---- 地形 / 水文分析 ----
    {"import": "pysheds", "attr": "__version__", "core": True,
     "fix": "pip install 'pysheds>=0.3.5'"},
    {"import": "richdem", "attr": "__version__", "core": False,
     "fix": "pip install richdem   (Windows 需编译工具链，可选)"},
    # ---- 模型评价 / 时序 ----
    {"import": "hydroeval", "attr": "__version__", "core": False,
     "fix": "pip install 'hydroeval>=0.0.1'"},
    {"import": "pymannkendall", "attr": "__version__", "core": False,
     "fix": "pip install 'pymannkendall>=1.4.3'"},
    {"import": "statsmodels", "attr": "__version__", "core": False,
     "fix": "pip install 'statsmodels>=0.14'"},
    {"import": "sklearn", "attr": "__version__", "core": False,
     "fix": "pip install 'scikit-learn>=1.5'"},
    # ---- 制图 ----
    {"import": "matplotlib", "attr": "__version__", "core": True,
     "fix": "pip install 'matplotlib>=3.8'"},
    {"import": "seaborn", "attr": "__version__", "core": False,
     "fix": "pip install 'seaborn>=0.13'"},
    {"import": "contextily", "attr": "__version__", "core": False,
     "fix": "pip install 'contextily>=1.6'"},
    # ---- 工程化 ----
    {"import": "yaml", "attr": "__version__", "core": False,
     "fix": "pip install 'pyyaml>=6.0'"},
    {"import": "loguru", "attr": "__version__", "core": False,
     "fix": "pip install 'loguru>=0.7'"},
    {"import": "tqdm", "attr": "__version__", "core": False,
     "fix": "pip install 'tqdm>=4.66'"},
    {"import": "pytest", "attr": "__version__", "core": False,
     "fix": "pip install 'pytest>=8.2'"},
    {"import": "openpyxl", "attr": "__version__", "core": False,
     "fix": "pip install 'openpyxl>=3.1'"},
    # ---- 领域增强：水土评价 / 环境经济评价（可选但推荐） ----
    {"import": "pastas", "attr": "__version__", "core": False,
     "fix": "pip install 'pastas>=1.14'   # 地下水头响应时序建模"},
    {"import": "gstools", "attr": "__version__", "core": False,
     "fix": "pip install 'gstools>=1.6'   # 地统计/变异函数/克里金"},
    {"import": "pykrige", "attr": "__version__", "core": False,
     "fix": "pip install 'pykrige'   # 克里金插值"},
    {"import": "pyemu", "attr": "__version__", "core": False,
     "fix": "pip install 'pyemu>=1.5'   # PEST 不确定性/数据价值"},
    {"import": "spotpy", "attr": "__version__", "core": False,
     "fix": "pip install 'SPOTpy>=1.6'   # GLUE/DREAM 参数优化"},
    {"import": "pyet", "attr": "__version__", "core": False,
     "fix": "pip install 'pyet'   # FAO-56 蒸散发"},
    {"import": "skcriteria", "attr": "__version__", "core": False,
     "fix": "pip install 'scikit-criteria>=0.8'   # MCDA 土地适宜性"},
    {"import": "numpy_financial", "attr": "__version__", "core": False,
     "fix": "pip install 'numpy-financial>=1.0'   # NPV/IRR 成本效益"},
    {"import": "hydrofunctions", "attr": "__version__", "core": False,
     "fix": "pip install 'hydrofunctions'   # USGS NWIS 取径流/水位"},
    {"import": "dataretrieval", "attr": "__version__", "core": False,
     "fix": "pip install 'dataretrieval'   # USGS 多类型水文数据拉取"},
    {"import": "cartopy", "attr": "__version__", "core": False,
     "fix": "conda install -c conda-forge cartopy  或 pip install cartopy"},
    {"import": "xskillscore", "attr": "__version__", "core": False,
     "fix": "pip install 'xskillscore'   # 网格/预报技能评分"},
    {"import": "phydrus", "attr": "__version__", "core": False,
     "fix": "pip install 'phydrus'   # HYDRUS-1D 包气带"},
    {"import": "timml", "attr": "__version__", "core": False,
     "fix": "pip install 'timml'   # 多层解析元模型"},
    {"import": "leafmap", "attr": "__version__", "core": False,
     "fix": "pip install 'leafmap'   # 交互式地图"},
]


# ============================================================
# 探针：导入模块并取版本
# ============================================================
def probe(import_name: str, attr: str | None) -> tuple[str | None, str | None]:
    """返回 (版本字符串, 错误信息)。成功时错误信息为 None。"""
    try:
        mod = importlib.import_module(import_name)
    except Exception as exc:  # noqa: BLE001 - 任何导入失败都要被捕获并报告
        return None, f"{type(exc).__name__}: {exc}"

    if attr:
        obj: Any = mod
        for part in attr.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                break
        if obj is not None:
            return str(obj), None
    return getattr(mod, "__version__", "unknown（无法读取版本）"), None


# ============================================================
# 冒烟测试 1：流域水量平衡闭合
#   P = ET + Q + ΔS  （降水 = 蒸散 + 径流 + 蓄变）
#   构造一组已知解算的数据，检验残差是否在阈值内
# ============================================================
def smoke_water_balance() -> dict[str, Any]:
    # 年尺度流域水量平衡，单位 mm/yr
    precipitation = 820.0     # 降水
    evapotranspiration = 415.0
    runoff = 305.0
    delta_storage = 100.0     # 蓄变量（地下水位上升）

    residual = precipitation - (evapotranspiration + runoff + delta_storage)
    tol = 1e-6
    return {
        "name": "水量平衡闭合校验",
        "pass": abs(residual) < tol,
        "detail": f"残差 {residual:.6f} mm/yr (阈值 {tol:g})",
    }


# ============================================================
# 冒烟测试 2：Mann-Kendall 趋势检验（纯标准库实现）
#   构造严格单调上升序列，期望得到显著上升趋势
# ============================================================
def _mk_test(series: list[float]) -> tuple[float, float]:
    """返回 (Z 统计量, 双侧 p 值)。不处理结值（ties）校正。"""
    n = len(series)
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = series[j] - series[i]
            if diff > 0:
                s += 1
            elif diff < 0:
                s -= 1

    var_s = n * (n - 1) * (2 * n + 5) / 18.0
    if var_s <= 0:
        return 0.0, 1.0

    if s > 0:
        z = (s - 1) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / math.sqrt(var_s)
    else:
        z = 0.0

    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return z, p


def smoke_mann_kendall() -> dict[str, Any]:
    # 10 年地下水位埋深观测：逐年上升（水位下降趋势）
    groundwater_depth = [3.1, 3.4, 3.6, 4.0, 4.3, 4.6, 5.0, 5.4, 5.7, 6.2]
    z, p = _mk_test(groundwater_depth)
    passed = z > 0 and p < 0.05
    return {
        "name": "Mann-Kendall 趋势检验",
        "pass": passed,
        "detail": f"Z={z:.2f}, p={p:.4f} -> " + ("显著上升趋势" if passed else "未检出显著趋势"),
    }


# ============================================================
# 冒烟测试 3：NDVI 遥感指数计算与值域校验
# ============================================================
def smoke_ndvi() -> dict[str, Any]:
    # 合成像元对：水体 / 裸土 / 稀疏植被 / 茂密植被
    pixels = [
        (0.02, 0.03),   # 水体：NIR 略高于 RED，NDVI 接近 0
        (0.25, 0.30),   # 裸土
        (0.18, 0.42),   # 稀疏植被
        (0.08, 0.55),   # 茂密植被
    ]
    ndvi_values = []
    for red, nir in pixels:
        denom = nir + red
        ndvi_values.append((nir - red) / denom if denom != 0 else 0.0)

    in_range = all(-1.0 <= v <= 1.0 for v in ndvi_values)
    monotonic = ndvi_values[3] > ndvi_values[2] > ndvi_values[1]
    passed = in_range and monotonic
    return {
        "name": "NDVI 计算与值域校验",
        "pass": passed,
        "detail": "NDVI=" + ", ".join(f"{v:+.3f}" for v in ndvi_values)
                  + (" (值域合规且植被梯度合理)" if passed else " (值域或梯度异常)"),
    }


SMOKE_TESTS = [smoke_water_balance, smoke_mann_kendall, smoke_ndvi]


# ============================================================
# 报告输出
# ============================================================
def build_report(run_smoke: bool) -> dict[str, Any]:
    deps: list[dict[str, Any]] = []
    for spec in DEPENDENCIES:
        version, error = probe(spec["import"], spec.get("attr"))
        deps.append({
            "import": spec["import"],
            "core": spec["core"],
            "installed": error is None,
            "version": version,
            "error": error,
            "fix": spec["fix"] if error else None,
        })

    smokes: list[dict[str, Any]] = []
    if run_smoke:
        for fn in SMOKE_TESTS:
            try:
                smokes.append(fn())
            except Exception as exc:  # noqa: BLE001
                smokes.append({
                    "name": fn.__name__,
                    "pass": False,
                    "detail": f"执行异常 {type(exc).__name__}: {exc}",
                })

    core_total = sum(1 for d in deps if d["core"])
    core_ok = sum(1 for d in deps if d["core"] and d["installed"])
    core_missing = [d for d in deps if d["core"] and not d["installed"]]
    smoke_failed = [s for s in smokes if not s["pass"]]

    ready = not core_missing and not smoke_failed
    return {
        "python": sys.version.split()[0],
        "platform": platform.system().lower(),
        "dependencies": deps,
        "smoke_tests": smokes,
        "summary": {
            "core_ok": core_ok,
            "core_total": core_total,
            "optional_installed": sum(1 for d in deps if not d["core"] and d["installed"]),
            "optional_total": sum(1 for d in deps if not d["core"]),
            "ready": ready,
        },
    }


def render_text(report: dict[str, Any], run_smoke: bool) -> None:
    line = "=" * 72
    print(line)
    print(" 水文地质科研环境自检  (hydro-research-env)")
    print(f" Python {report['python']}  |  平台 {report['platform']}")
    print(line)

    # 标签用 ASCII 定宽，避免中文标签在等宽终端里错位
    width = max(len(d["import"]) for d in report["dependencies"])
    for dep in report["dependencies"]:
        if dep["installed"]:
            tag = "[ OK  ]"
        else:
            tag = "[MISS ]" if dep["core"] else "[OPT  ]"
        ver = dep["version"] if dep["installed"] else "-"
        role = "核心" if dep["core"] else "可选"
        print(f" {tag} {dep['import']:<{width}}  {ver:<26} [{role}]")

    missing_core = [d for d in report["dependencies"] if d["core"] and not d["installed"]]
    if missing_core:
        print("-" * 72)
        print(" 核心依赖缺失 —— 复制以下命令修复：")
        for dep in missing_core:
            print(f"   {dep['import']:<{width}} ->  {dep['fix']}")

    if run_smoke:
        print("-" * 72)
        print(" 数值冒烟测试：")
        for smoke in report["smoke_tests"]:
            flag = "[PASS]" if smoke["pass"] else "[FAIL]"
            print(f" {flag} {smoke['name']}: {smoke['detail']}")

    summary = report["summary"]
    print(line)
    verdict = "环境就绪" if summary["ready"] else "环境未就绪，请先修复后再开始写业务代码"
    print(f" 结论：核心依赖 {summary['core_ok']}/{summary['core_total']} 就绪"
          f" | 可选依赖 {summary['optional_installed']}/{summary['optional_total']}"
          f" -> {verdict}")
    print(line)
    print(" 提醒：本脚本只保证「环境跑得通」，不保证「方法选得对」。")
    print("       实验数据正确性与科研结论须人工核验。")
    print(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="水文地质科研环境自检")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出（供 CI / Agent 解析）")
    parser.add_argument("--no-smoke", action="store_true", help="跳过数值冒烟测试")
    args = parser.parse_args()

    run_smoke = not args.no_smoke
    report = build_report(run_smoke)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        render_text(report, run_smoke)

    return 0 if report["summary"]["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
