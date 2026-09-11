---
name: hydro-trend-analysis
description: 水文气象序列的趋势、突变与周期分析规范。当任务涉及 Mann-Kendall 趋势检验、Sen 斜率、Pettitt/累积距平突变点识别、小波分析、去季节化、相关性与滞后分析时使用。
---

# 水文序列趋势与突变分析（Trend & Change-Point Analysis）

## 何时使用

- 判断地下水位、径流、降水是否存在显著趋势
- 识别序列的突变年份（人类活动/气候变化影响分界）
- 计算趋势速率（mm/yr、m/yr）
- 分析要素间的相关性与滞后关系

## 方法选择决策树

```
数据是否近似正态、无异常值？
├── 是 -> 可考虑线性回归 / t 检验（但要报告残差诊断）
└── 否 -> Mann-Kendall（非参数，稳健）  ← 水文序列默认选它

序列是否含明显季节循环？
├── 是 -> 先做去季节化（月度距平 / STL 分解），再检验
└── 否 -> 直接检验

要估计趋势速率？
└── Sen's slope（Theil-Sen 中位数斜率），与 MK 配套

要找突变点？
├── 单突变点 -> Pettitt 检验 / 累积距平
└── 多突变点 -> 滑动 t 检验 / Buishand 检验，并交叉验证
```

## Mann-Kendall 检验要点

### 标准公式

```
S = ΣΣ sgn(x_j - x_i)          i < j
Var(S) = [n(n-1)(2n+5) - Σt(t-1)(2t+5)] / 18     ← 第二项是结值(ties)校正
Z = (S-1)/√Var(S)  if S > 0
Z = (S+1)/√Var(S)  if S < 0
Z = 0              if S = 0
```

### 三个必查项

**1. 结值校正不能忘**

水文数据常有结值（如水位取整、降水为零）。n 大时结值影响显著：

```python
from collections import Counter
import math

def mk_with_ties(series):
    data = list(series)
    n = len(data)
    s = sum(
        1 if data[j] > data[i] else (-1 if data[j] < data[i] else 0)
        for i in range(n - 1) for j in range(i + 1, n)
    )
    # 结值校正项
    tie_term = sum(t * (t - 1) * (2 * t + 5) for t in Counter(data).values() if t > 1)
    var_s = (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0
    z = 0.0
    if var_s > 0:
        z = (s - 1) / math.sqrt(var_s) if s > 0 else ((s + 1) / math.sqrt(var_s) if s < 0 else 0.0)
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return z, p
```

**2. 自相关校正（重要且常被忽略）**

水位、径流具有强自相关，直接用原始 MK 会**高估显著性**（假阳性）：
- 序列存在显著自相关（ACF(1) 显著）时，应使用 **预白化（pre-whitening）** 或
  **修正 MK（Hamed & Rao 1998）**
- 报告时必须说明是否做了自相关处理

```python
import numpy as np

def lag1_autocorr(x):
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    denom = np.sum(x * x)
    return float(np.sum(x[:-1] * x[1:]) / denom) if denom else 0.0
```

**3. 显著 ≠ 重要**

p < 0.05 只说明趋势非随机，**不说明趋势幅度有物理意义**。必须同时报告 Sen 斜率
与相对变化率（如「年均下降 0.32 m，20 年累计下降 6.4 m，占初始埋深的 206%」）。

## 突变点识别

### 累积距平法（直观，适合初步判断）

```python
import numpy as np

def cumulative_anomaly(series):
    x = np.asarray(series, dtype=float)
    return np.cumsum(x - x.mean())
```

距平曲线由上升转下降的拐点即为突变年份候选。

### Pettitt 检验（给出统计显著性）

零假设为「序列无突变点」。返回突变位置与 p 值。

### 多方法交叉验证（必做）

**单一方法的突变点结论不可信。** 至少用两种方法交叉验证：
- 累积距平 + Pettitt 一致 → 结论可信
- 不一致 → 报告两个候选年份，说明不确定性，不要挑一个顺眼的

且突变点必须与**物理事件**对应（水库建成、大规模开采开始、降水量级改变）。
找不到物理对应的事件，结论要打问号。

## 去季节化与 STL 分解

```python
from statsmodels.tsa.seasonal import STL

# period=12 对应月度数据；日数据用 365
stl = STL(monthly_series, period=12, robust=True).fit()
trend_component = stl.trend          # 趋势项：用于趋势检验
seasonal_component = stl.seasonal    # 季节项
resid = stl.resid                    # 残差：用于异常检测
```

- 用 `robust=True` 抵御异常值
- 去季节化后再做 MK，避免季节循环被误判为趋势
- 数据长度 < 2 个完整周期时不要做 STL

## 相关性与滞后分析

```python
import numpy as np

def cross_correlation(a, b, max_lag=12):
    """互相关，返回 (滞后阶数, 相关系数) 列表。正滞后表示 b 滞后于 a。"""
    a = np.asarray(a, dtype=float) - np.mean(a)
    b = np.asarray(b, dtype=float) - np.mean(b)
    out = []
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            x, y = a[: len(a) - lag], b[lag:]
        else:
            x, y = a[-lag:], b[: len(b) + lag]
        if len(x) > 3:
            r = float(np.corrcoef(x, y)[0, 1])
            out.append((lag, r))
    return out
```

**相关不等于因果。** 报告相关性时必须：
1. 给出样本量 n 与显著性 p 值
2. 说明是否为伪相关（共同趋势导致的虚假相关）
3. 对存在共同趋势的序列，先差分/去趋势再算相关

## 输出规范

每次趋势分析必须同时给出：

| 项目 | 必填内容 |
|---|---|
| 数据 | 序列长度、时段、缺测处理方式、是否去季节化 |
| 方法 | MK（是否结值校正、是否自相关校正）|
| 统计量 | Z、p、Sen 斜率、置信区间 |
| 物理量 | 绝对变化量 + 相对变化率 |
| 突变 | 突变年份 + 交叉验证方法 + 物理事件对应 |
| 局限 | 未处理的问题（数据长度不足、自相关未校正等）|

## 常见错误清单

- ❌ 只报 p 值不报 Sen 斜率（读者无法判断幅度）
- ❌ 不做结值校正
- ❌ 对强自相关序列直接用原始 MK，显著性虚高
- ❌ 用单一方法定突变点
- ❌ 突变年份找不到物理对应事件却直接下结论
- ❌ 对含季节循环的序列直接 MK
- ❌ 用相关分析暗示因果关系
- ❌ 数据长度不足（n < 10）仍然强做趋势检验

## 验收标准

- [ ] 方法选择有理由（正态性/自相关/季节性已检查）
- [ ] MK 做结值校正，必要时做自相关修正
- [ ] 同时报告 Z、p、Sen 斜率与置信区间
- [ ] 报告绝对变化量与相对变化率
- [ ] 突变点至少两种方法交叉验证并有物理事件对应
- [ ] 局限性明确写出
