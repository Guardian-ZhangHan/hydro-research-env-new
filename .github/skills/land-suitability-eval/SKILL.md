---
name: land-suitability-eval
description: 水土评价核心技能 —— 土地适宜性评价与灌溉水质约束。覆盖 FAO 土地评价框架、MCDA（AHP/TOPSIS）、评价单元栅格叠加、灌溉水质（SAR/EC/钠吸附比）。当用户要做农用地/建设用地/生态用地适宜性分级、水土资源承载力评价时使用。
---

# 土地适宜性评价（水土评价）

## 适用范围
- 耕地/园地/建设用地/生态用地的适宜性分级（S1/S2/S3/N）
- 水土资源承载力、土地整治潜力评价
- 与地下水脆弱性评价（`gw-vulnerability`）联合做"水土一体"评价

## 一、FAO 土地评价框架（分级逻辑）
1. 明确**土地利用类型**（如雨养玉米、灌溉菜地、建设用地）
2. 列出该利用方式的**土地质量要求**（土质、排水、盐分、有效土层、坡度…）
3. 对每个评价单元，将实际土地特性与要求比对 → 初判适宜类：
   - **S1** 高度适宜（无重大限制）
   - **S2** 中等适宜（有限制，减产但仍经济）
   - **S3** 临界适宜（强限制，边际经济）
   - **N** 不适宜（当前技术经济下不可行）
4. 限定因素法：只要有一项"否决因子"超限（如地下水位埋深过浅、盐渍化），直接降等。

## 二、MCDA 多准则综合评分（scikit-criteria）
因子多、难以纯经验分级时，用 MCDA 把多因子合成综合适宜度。

```python
import skcriteria as skc
from skcriteria.madm import closeness, similarity  # TOPSIS / WPM 等

# 行=评价单元，列=因子；min/max 说明因子方向（越大越适宜 or 越小越适宜）
dm = skc.Data(
    mtx=[[0.82, 12.0, 1.1, 35.0], ...],   # 示例：[有机质, 坡度°, 盐渍化指数, 有效土层cm]
    criteria=[max, min, min, max],
    weights=[0.30, 0.20, 0.30, 0.20],     # AHP 得出，须可追溯
    anames=[f"单元{i}" for i in range(n)],
    cnames=["有机质","坡度","盐渍化","有效土层"],
)
# AHP 定权（成对比较矩阵 -> 权重 + 一致性比 CR<0.1）
# TOPSIS 综合排序
dec = closeness.TOPSIS().decide(dm)
```

- **权重必须可追溯**：用 AHP 成对比较矩阵导出，并在报告中给出 CR（一致性比 < 0.1 方可用）。
- **敏感性分析**：扰动权重 ±20%，看排序是否稳定，写进局限。

## 三、评价单元与因子栅格叠加
- 矢量边界/单元：`geopandas`；栅格因子：`rasterio`
- 单元统计：`rasterstats.zonal_stats` 取均值/众数
- 叠加合成：把各因子重采样到统一 `grid_resolution_m`（见 project.example.yaml 的 analysis_crs）

## 四、灌溉水质约束（与 water-quality-index 联动）
灌溉用水若 SAR 高 / EC 高，土地会**次生盐渍化**，适宜性直接降级。
评价时把灌溉水质的钠危害分级作为限定因子之一（见 `water-quality-index` 的 SAR/EC/USSL 分级）。

## 验收标准
- [ ] 评价单元空间边界与 CRS 已声明
- [ ] 权重来源（AHP 矩阵/文献）可追溯，CR 已报
- [ ] 做了权重敏感性分析
- [ ] 限制/否决因子已显式建模（不是只靠综合分）
- [ ] 所有单价/阈值注明出处，未编造
