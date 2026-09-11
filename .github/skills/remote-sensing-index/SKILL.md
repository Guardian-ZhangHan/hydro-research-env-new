---
name: remote-sensing-index
description: 遥感指数计算与栅格处理规范。当任务涉及 NDVI/NDWI/MNDWI/NDMI/NDBI/地表温度等指数计算、云掩膜、影像时序合成、重投影、裁剪、栅格统计分区汇总时使用。
---

# 遥感指数计算与栅格处理（Remote Sensing Index）

## 何时使用

- 计算植被/水体/湿度/建筑指数用于水文地质分析
- 处理 Landsat / Sentinel-2 / MODIS 影像
- 需要云掩膜、时序合成、重投影、按流域裁剪
- 按含水层分区/流域边界做栅格统计

## 指数公式（务必区分传感器波段编号）

| 指数 | 公式 | 用途 | 值域 |
|---|---|---|---|
| NDVI | `(NIR - RED) / (NIR + RED)` | 植被覆盖度 | [-1, 1] |
| NDWI | `(GREEN - NIR) / (GREEN + NIR)` | 地表水体 (McFeeters) | [-1, 1] |
| MNDWI | `(GREEN - SWIR1) / (GREEN + SWIR1)` | 水体（抗建筑干扰） | [-1, 1] |
| NDMI | `(NIR - SWIR1) / (NIR + SWIR1)` | 植被/土壤水分 | [-1, 1] |
| NDBI | `(SWIR1 - NIR) / (SWIR1 + NIR)` | 建设用地 | [-1, 1] |

**波段编号因传感器而异，必须显式查表，禁止凭记忆写死：**

```python
BANDS = {
    "Landsat-8/9 OLI": {"RED": 4,  "NIR": 5, "SWIR1": 6, "GREEN": 3},
    "Landsat-5/7 TM":  {"RED": 3,  "NIR": 4, "SWIR1": 5, "GREEN": 2},
    "Sentinel-2 MSI":  {"RED": 4,  "NIR": 8, "SWIR1": 11, "GREEN": 3},
    "MODIS":           {"RED": 1,  "NIR": 2, "SWIR1": 6, "GREEN": 4},
}
```

> 参考 Landsat-8 与 Landsat-9 波段一致；Sentinel-2 的 8A 与 8 在窄/宽 NIR 上有差异，
> 做时序一致性分析时必须统一，否则会产生伪突变。

## 必做的四步防护

### 1. 除以零防护

```python
import numpy as np

def safe_normalized_difference(a, b, nodata=-9999.0):
    a = a.astype("float32")
    b = b.astype("float32")
    valid = (a != nodata) & (b != nodata) & np.isfinite(a) & np.isfinite(b)
    denom = a + b
    out = np.full(a.shape, np.nan, dtype="float32")
    usable = valid & (denom != 0)
    out[usable] = (a[usable] - b[usable]) / denom[usable]
    out[~valid] = np.nan
    return out
```

**禁止**裸写 `(nir - red) / (nir + red)`，水体像元极易触发除零与 Inf。

### 2. 值域校验

```python
valid = ndvi[np.isfinite(ndvi)]
assert valid.min() >= -1.0001 and valid.max() <= 1.0001, "NDVI 超出物理值域"
```

超值域通常意味着：① 波段选错 ② 反射率缩放系数未应用 ③ 整数反射率未除 10000。

### 3. 缩放系数（高频事故点）

```python
# Landsat Collection 2 L2：反射率需乘以 0.0000275 再减 0.2
reflectance = dn * 0.0000275 - 0.2
# Sentinel-2 L2A：整数反射率需除以 10000
reflectance = dn / 10000.0
```

**不做缩放直接算指数，NDVI 值域会完全错乱**——这是遥感里 CI 最难发现的一类错误，
因为它不会报错，只会给出错的数。

### 4. 云掩膜

```python
# Sentinel-2 L2A 的 SCL 分类：3=云影, 8=中概率云, 9=高概率云, 10=卷云, 11=雪
MASK_CLASSES = {3, 8, 9, 10, 11}
valid = ~np.isin(scl, list(MASK_CLASSES))
```

云掩膜要在**指数计算之前**作用于所有输入波段，且掩膜后必须报告有效像元占比。
有效像元 < 30% 的影像应剔除，不得进入时序合成。

## 时序合成规范

```python
# 时序合成推荐：中位数合成（抗云、抗异常值）
composite = xr.concat(stacked, dim="time").median(dim="time", skipna=True)
# 不要用 mean —— 少量残云会显著拉低均值，造成假下降趋势
```

合成前必须做的检查：
1. 影像间几何对齐（同一 CRS、同一像元网格、同一分辨率）
2. 辐射一致性（不同传感器/不同时相需做相对辐射归一化）
3. 有效像元占比统计

## 重投影与裁剪

```python
import rioxarray

# 重投影必须显式指定重采样方法
raster = raster.rio.reproject("EPSG:4326", resampling=rasterio.enums.Resampling.bilinear)
# 分类数据（土地覆盖、SCL）必须用 nearest，不能用 bilinear
```

**连续数据用 bilinear / cubic，分类数据必须用 nearest。** 对分类栅格做双线性插值
会创造出物理上不存在的类别值。

## 分区统计

```python
from rasterstats import zonal_stats

stats = zonal_stats(
    "data/interim/basin_boundary.shp",
    "data/interim/ndvi_composite.tif",
    stats=["mean", "median", "std", "count", "percentile_25", "percentile_75"],
    nodata=np.nan,
    all_touched=False,     # 汇流/面积统计建议 False，避免边界像元重复计入
)
```

必须在报告中说明 `all_touched` 取值及其面积影响。

## 输出规范

1. 每个指数图层附带元数据：传感器、日期范围、波段映射、缩放系数、云掩膜规则
2. 出图附色标、值域说明、有效像元占比
3. 时序分析前，先出一张各期有效像元占比曲线，暴露数据空洞

## 常见错误清单

- ❌ 波段编号按记忆写死，不查传感器表
- ❌ 忘记乘缩放系数（Landsat C2 会给出 -0.2 偏移的错误结果）
- ❌ 未做除零防护，水体像元产生 Inf 污染整个统计
- ❌ 对分类栅格用 bilinear 重采样
- ❌ 时序合成用 mean 而非 median，残留云导致假趋势
- ❌ 用不同传感器影像拼时序却不做辐射归一化

## 验收标准

- [ ] 波段映射来源可查（传感器 + 产品级别）
- [ ] 缩放系数已应用并有单像元手算验证
- [ ] 值域校验通过
- [ ] 云掩膜后报告有效像元占比
- [ ] 重采样方法与数据类型匹配
