---
name: sci-figure-standard
description: 科研论文制图规范。当任务需要绘制空间分布图、观测-模拟散点对比图、时间序列图、趋势与突变图、方法流程图等论文插图时使用，含中文字体、色标、指北针比例尺、分辨率与导出格式要求。
---

# 科研论文制图规范（Scientific Figure Standard）

## 何时使用

- 为论文/报告出图（空间分布、散点对比、时间序列、趋势突变、流程示意）
- 需要中文字体、指北针、比例尺、统一色标
- 需要确定分辨率、导出格式、排版尺寸

## 通用硬性要求

### 1. 中文字体必须显式设置（否则全是方框）

```python
import matplotlib.pyplot as plt
import matplotlib as mpl

# Windows / Linux 通用方案：优先用系统已装中文字体，逐个回退
CJK_CANDIDATES = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
                  "Source Han Sans SC", "WenQuanYi Zen Hei", "Arial Unicode MS"]
mpl.rcParams["font.sans-serif"] = CJK_CANDIDATES + ["DejaVu Sans"]
mpl.rcParams["axes.unicode_minus"] = False      # 负号正常显示，必加
mpl.rcParams["font.size"] = 9                    # 论文正文 9-10.5pt
mpl.rcParams["axes.linewidth"] = 0.8
mpl.rcParams["savefig.dpi"] = 300
```

出图后**必须目视检查一次**中文字符是否正常渲染，不能只看脚本没报错。

### 2. 分辨率与格式

| 用途 | DPI | 格式 |
|---|---|---|
| 期刊投稿（位图） | ≥ 300，线条图建议 600 | TIFF / PNG |
| 矢量优先 | — | PDF / EPS / SVG |
| 汇报 PPT | 150 | PNG |

```python
fig.savefig("figures/fig_01_study_area.png", dpi=300, bbox_inches="tight")
fig.savefig("figures/fig_01_study_area.pdf", bbox_inches="tight")   # 矢量版
```

**线条图、流程图上矢量格式**，栅格底图用位图，二者在投稿时按期刊要求提供。

### 3. 单栏 / 双栏尺寸（投稿前按目标期刊调整）

```python
# 常见单栏宽度
SINGLE_COL = 3.35   # inch，约 8.5 cm
DOUBLE_COL = 7.0    # inch，约 17.8 cm
fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.6))
```

## 分类型规范

### 空间分布图（地图）

**必含四要素**：指北针、比例尺、经纬网/坐标网格、图例（含色标与单位）

```python
import matplotlib.pyplot as plt
import contextily as cx
import geopandas as gpd

fig, ax = plt.subplots(figsize=(7.0, 5.5))

# 栅格底图：统一色标，务必标注值域与单位
im = ax.imshow(ndvi, extent=extent, cmap="RdYlGn", vmin=-1, vmax=1)
cbar = fig.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
cbar.set_label("NDVI（无量纲）")

# 矢量叠加
basin = gpd.read_file("data/interim/basin_boundary.shp")
basin.boundary.plot(ax=ax, edgecolor="black", linewidth=1.0, zorder=3)

# 指北针 + 比例尺
# 建议用 matplotlib-scalebar；或手绘简洁箭头+线段
from matplotlib_scalebar.scalebar import ScaleBar
ax.add_artist(ScaleBar(1, units="m", location="lower right",
                       box_alpha=0, color="black"))

# 经纬网
ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
ax.set_xlabel("经度 (°E)")
ax.set_ylabel("纬度 (°N)")

fig.savefig("figures/fig_02_distribution.png", dpi=300, bbox_inches="tight")
```

**地图合规**：涉及中国国界的底图，必须使用自然资源部标准地图或经审核的边界数据，
不得使用来源不明的国界线数据（OneMap/GADM 的国界线在涉及中国时可能不合规）。
涉及中国香港/中国台湾/中国澳门时，标注与配色须符合国家标准地图表达。

### 观测-模拟散点对比图

**必含**：1:1 线、回归线、R²、RMSE、NSE、样本量 n

```python
import numpy as np
from scipy import stats

def plot_obs_vs_sim(obs, sim, out_path, label="地下水位埋深 (m)"):
    obs, sim = np.asarray(obs), np.asarray(sim)
    mask = np.isfinite(obs) & np.isfinite(sim)
    obs, sim = obs[mask], sim[mask]

    slope, intercept, r, p, _ = stats.linregress(obs, sim)
    r2 = r ** 2
    rmse = float(np.sqrt(np.mean((obs - sim) ** 2)))
    nse = 1 - np.sum((obs - sim) ** 2) / np.sum((obs - obs.mean()) ** 2)

    fig, ax = plt.subplots(figsize=(3.35, 3.35))
    ax.scatter(obs, sim, s=22, c="#2b6cb0", edgecolor="white",
               linewidth=0.5, alpha=0.85, label="观测井", zorder=3)

    lim = [min(obs.min(), sim.min()), max(obs.max(), sim.max())]
    ax.plot(lim, lim, "k--", linewidth=1.0, zorder=2, label="1:1 线")
    xline = np.array(lim)
    ax.plot(xline, intercept + slope * xline, color="#c53030",
            linewidth=1.2, zorder=2, label="回归线")

    ax.text(0.05, 0.95,
            f"$R^2$ = {r2:.3f}\nRMSE = {rmse:.3f} m\nNSE = {nse:.3f}\nn = {len(obs)}",
            transform=ax.transAxes, va="top", ha="left", fontsize=8,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="0.7", alpha=0.9))

    ax.set_xlabel(f"观测{label}")
    ax.set_ylabel(f"模拟{label}")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_aspect("equal")
    ax.legend(loc="lower right", fontsize=7, frameon=False)
    ax.grid(True, linestyle=":", linewidth=0.4, alpha=0.5)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
```

### 时间序列图

- 观测与模拟用不同线型（实线/虚线），不能只靠颜色区分（黑白打印可辨）
- 加图例、轴标签含单位
- 校核期与验证期用背景色带或竖线分隔，并标注
- 多要素共图时用 twinx，但**最多两条 y 轴**，且颜色与标签对应

```python
ax.axvspan(calib_start, calib_end, color="#ebf8ff", alpha=0.6, zorder=0, label="校核期")
ax.axvspan(valid_start, valid_end, color="#fffaf0", alpha=0.6, zorder=0, label="验证期")
```

### 趋势与突变图

三件套（趋势分析的标准展示）：
1. 序列 + 趋势线 + Sen 斜率标注
2. 累积距平曲线（标突变点）
3. 滑动统计量或检验结果

### 方法流程图

- 用 `matplotlib.patches` 或 `graphviz` 绘制
- 箭头方向统一（自上而下或自左而右），不混用
- 每个方框文字 ≤ 12 字，过长拆分为多个框

## 色标选择

| 数据性质 | 推荐色标 | 说明 |
|---|---|---|
| 连续单向（降水、埋深） | `viridis` / `YlGnBu` | 色盲友好 |
| 双向偏离（距平、残差） | `RdBu_r` / `coolwarm` | 零点居中，`TwoSlopeNorm` |
| 植被 | `RdYlGn` | 符合领域认知 |
| 分类数据 | `tab10` / `Set2` | 定性色板 |

```python
# 距平类数据零点必须居中
from matplotlib.colors import TwoSlopeNorm
norm = TwoSlopeNorm(vmin=-5, vcenter=0, vmax=5)
```

**中国金融/水文惯例**：涨/增加用红色、跌/减少用绿色（与欧美相反），
若图表用于中文语境，需遵循该约定。

## 输出规范

1. 每个图都要有独立的生成脚本，放在 `scripts/figures/` 下，命名 `fig_01_xxx.py`
2. 图件存 `figures/` 且入库（图片本身小），数据大文件不入库
3. 脚本顶部注释写清：数据来源、图件用途、对应论文章节
4. 生成后**目视检查**：中文渲染、色标可读、图例完整、有无裁切

## 常见错误清单

- ❌ 忘记 `axes.unicode_minus = False`，负号变方框
- ❌ 中文字体未设，全文方框
- ❌ 只靠颜色区分类别，黑白打印无法分辨
- ❌ 散点图不画 1:1 线，无法判断偏差方向
- ❌ 色标不写单位与值域
- ❌ 地图缺指北针/比例尺/坐标网格
- ❌ 使用不合规的国界线数据
- ❌ dpi 不足 300 用于投稿
- ❌ 线条图导出位图而非矢量

## 验收标准

- [ ] 中文正常渲染（已目视确认）
- [ ] 分辨率 ≥ 300 dpi，线条图有矢量版本
- [ ] 轴标签含单位
- [ ] 散点图含 1:1 线 + R² + RMSE + n
- [ ] 地图含指北针 + 比例尺 + 坐标网格
- [ ] 国界数据合规
- [ ] 有独立可复现的出图脚本
