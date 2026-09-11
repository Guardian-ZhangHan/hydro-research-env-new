---
name: modflow-groundwater
description: MODFLOW 地下水数值模拟建模与校核规范。当任务涉及用 flopy 搭建 MODFLOW-6/MODFLOW-2005 模型、定义网格与边界条件、参数分区、抽水井、运行求解、水位校核、水量均衡与敏感性分析时使用。
---

# MODFLOW 地下水数值模拟（Groundwater Modeling）

## 何时使用

- 用 flopy 构建/修改 MODFLOW 模型
- 定义分层、边界条件、抽水井、补给
- 模型运行、水位拟合校核、水量均衡分析
- 参数敏感性分析与不确定性评估

## 标准建模流程（不可跳步）

```
1. 概念模型   -> 水文地质概念模型文档（含水层结构、边界、源汇项）
2. 网格剖分   -> 确定网格尺寸、层数、垂向分层方式
3. 参数赋值   -> K、Ss/Sy、有效孔隙度，按分区赋值
4. 边界条件   -> 定水头/定流量/河流/排水/补给/蒸发
5. 初始条件   -> 初始水头（关键！收敛失败的首要原因）
6. 稳态标定   -> 先做稳态，率定 K 与补给
7. 非稳态标定 -> 再校核 Ss/Sy
8. 校核评估   -> 残差、RMSE、NSE、散点图
9. 预测模拟   -> 情景方案
```

**必须先稳态后非稳态。** 直接上非稳态且初始水头是猜的，模型不收敛只是时间问题。

## flopy 骨架（MODFLOW-6）

```python
import flopy

sim_name = "basin_gw"
workspace = "data/interim/modflow"

# ---- 1. 时间离散 ----
# 稳态期 + 非稳态期分离，稳态用于标定，非稳态用于预测
tdis = flopy.mf6.ModflowTdis(
    sim, time_units="DAYS", nper=2,
    perioddata=[
        (1.0, 1, 1.0),        # 稳态期
        (365.0, 365, 1.0),    # 1 年非稳态，日步长
    ],
)

# ---- 2. 网格 ----
# 网格尺寸需与水文地质条件空间变异性匹配，
# 剖分过粗会掩盖降落漏斗，过细则计算成本失控
dis = flopy.mf6.ModflowGwfdis(
    gwf, nlay=2, nrow=60, ncol=80,
    delr=200.0, delc=200.0,      # 单位与 time_units 一致（m）
    top=120.0, botm=[80.0, 40.0],
    xorigin=500000.0, yorigin=3200000.0,
)

# ---- 3. 初始水头：绝不允许默认 0 ----
ic = flopy.mf6.ModflowGwfic(gwf, strt=initial_head_array)

# ---- 4. 水力传导系数 ----
# K 按分区赋值，水平/垂向各向异性用 hk/kv 体现，kv 通常取 hk 的 1/10 ~ 1/1000
npf = flopy.mf6.ModflowGwfnpf(
    gwf, icelltype=1, k=hk_array, k33=kv_array,
    save_flows=True,
)

# ---- 5. 边界条件 ----
# 定水头边界要放在物理上合理的位置，不能为了收敛随便加
chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=chd_spd)

# 河流：用 RIV 而非 CHD，允许河流与含水层双向交换
riv = flopy.mf6.ModflowGwfriv(gwf, stress_period_data=riv_spd)

# 抽水井：注意符号约定 —— MODFLOW 中抽水为负值
wel_spd = [[(0, 25, 40), -1500.0]]     # 第 0 层井，抽水量 1500 m3/d
wel = flopy.mf6.ModflowGwfwel(gwf, stress_period_data={1: wel_spd})

# 补给：大气降水入渗，单位 m/d，需按土地利用分区折减
rch = flopy.mf6.ModflowGwfrcha(gwf, recharge={1: recharge_array})

# ---- 6. 求解器 ----
# 收敛失败先看 IMS 设置，再看初始水头与边界条件
ims = flopy.mf6.ModflowIms(
    sim, complexity="MODERATE",
    outer_dvclose=1e-4, inner_dvclose=1e-6,
    linear_acceleration="BICGSTAB",
)
```

## 水量均衡核对（必做）

模型跑完**必须**提取 `LIST` 文件的体积均衡，逐项核对：

```
累计入流 = 累计出流 + 蓄变量变化
```

残差相对误差 > 0.1% 说明模型有问题（时间步长过大、收敛容差过松、边界设置矛盾），
**不得直接使用结果**。

```python
# 读取并核对均衡
import numpy as np
budget = gwf.output.budget()
flows = flopy.utils.postprocessing.get_specific_discharge(...)
# 打印 IN/OUT 汇总，人工确认量级合理性
```

## 校核评估（必做，且必须出图）

| 指标 | 公式 | 合格阈值 |
|---|---|---|
| RMSE | `sqrt(mean((obs-sim)^2))` | 需 < 观测水头变幅的 10% |
| NSE | `1 - sum((obs-sim)^2)/sum((obs-mean(obs))^2)` | > 0.7（> 0.5 可接受） |
| 平均绝对残差 | `mean(\|obs-sim\|)` | — |
| 标准化残差 | `(obs-sim)/obs_std` | 应在 ±2 内，且残差与观测值无系统相关 |

**关键判据：残差分布不能有系统性偏差。** 若残差随水位升高单调变化，说明结构有问题
（分层、边界、参数分区），而不仅是数值精度不够。

必须产出三张图：
1. 观测 vs 模拟散点图（含 1:1 线）
2. 各观测井残差时间序列（看是否有系统漂移）
3. 校核期与验证期的水位过程线对比

## 敏感性分析

至少对以下参数做单因素敏感性：

| 参数 | 典型范围 | 说明 |
|---|---|---|
| 水平渗透系数 K | ±50% | 主导因素 |
| 垂向各向异性 K33/K | 1/10 ~ 1/1000 | 控制垂向越流 |
| 给水度 Sy | ±30% | 影响非稳态响应速度 |
| 储水率 Ss | ±50% | 影响弹性储量 |
| 入渗补给 | ±50% | 山区流域主导 |

结果用蜘蛛图或 Tornado 图呈现，说明模型对哪些参数最敏感。

## 常见错误清单

- ❌ 模型不收敛却强行使用结果（必须报错停下）
- ❌ 初始水头全填 0 或随意常数
- ❌ 抽水井流量符号写反（MODFLOW 中抽水为负）
- ❌ 单位不统一（时间用天，流量用 m³/s）
- ❌ 用 CHD 定水头边界代替河流，导致河流失去与含水层的交换能力
- ❌ 稳态不标定直接上非稳态预测
- ❌ 只报 RMSE 不出散点图与残差图
- ❌ 校核期与验证期使用同一段时间（数据泄漏）

## 验收标准

- [ ] 概念模型有文档，含水层结构、边界、源汇项可追溯
- [ ] 稳态先标定，非稳态后校核
- [ ] 水量均衡残差 < 0.1%
- [ ] RMSE / NSE 达标，残差无系统偏差
- [ ] 三张校核图齐备
- [ ] 敏感性分析完成
- [ ] 校核期与验证期时间不重叠
