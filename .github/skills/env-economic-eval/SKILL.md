---
name: env-economic-eval
description: 环境经济评价技能 —— 生态服务货币化与环境成本效益分析。覆盖 InVEST 生态服务估值（水源涵养/固碳/生境/土壤保持/休闲）、CBA（NPV/BCR/IRR via numpy-financial）、意愿调查法（CVM/WTP）、损害成本法。当用户要做生态补偿、绿色核算、治理工程经济可行性、环境效益量化时使用。
---

# 环境经济评价

## 适用范围
- 生态修复/治理工程的**成本效益分析（CBA）**
- 生态系统服务**货币化**（GEP/生态产品价值实现）
- 生态补偿标准、绿色 GDP 核算辅助
- 水土评价结论的**经济维度**衔接（`land-suitability-eval`）

## 一、InVEST 生态服务货币化（natcap.invest）
把空间模型产出转成物理量，再乘单价得价值量：

| 服务 | InVEST 模块 | 物理产出 | 常见货币化路径 |
|---|---|---|---|
| 水源涵养 | `annual_water_yield` | 涵养量 (mm·ha) | × 水资源费/供水成本 (元/m³) |
| 土壤保持 | `sediment_delivery_ratio` | 保土量 (t) | × 淤积损失/清淤成本 (元/t) |
| 固碳 | `carbon` | 碳储量/ sequestration (t C) | × 碳价 (元/t CO₂) |
| 生境质量 | `habitat_quality` | 生境指数 | × 替代成本法（谨慎使用） |
| 休闲游憩 | `recreation` | 访问量 | × 旅行费用/支付意愿 |

```bash
# 安装（重依赖，见 requirements-domain.txt）
pip install natcap.invest
python -m natcap.invest annual_water_yield --datastack water_yield.json
```

**单价红线**：所有货币化参数（水价、碳价、清淤单价）**必须注明来源与年份**，
不得凭空给数。优先用政府公布价、公开文献、地方核算规范。

## 二、成本效益分析 CBA（numpy-financial）
```python
import numpy_financial as npf
# 净现值：CF 为逐年净现金流（收益-成本），r 为社会折现率
npv = npf.npv(rate=0.05, values=[-init] + annual_net)
bcr = sum(benefit) / sum(cost)          # 效益成本比
irr = npf.irr([-init] + annual_net)     # 内部收益率
```
- 社会折现率按项目性质取（生态类常用 4%–8%，以现行规范为准）
- 收益/成本必须**分年度、可审计**，单独列敏感性（±折现率、±工程量）

## 三、意愿调查法 CVM / WTP（statsmodels）
对无市场价的生态效益，用条件价值评估：
```python
import statsmodels.formula.api as smf
# 双栏模型：是否支付(probit) + 支付多少(区间/截断回归)
smf.logit("pay ~ age + income + knowledge", data=df).fit()
smf.ols("amount | amount>0 ~ income + bid", data=df).fit()
```
- 问卷设计、样本量、无响应偏差都须在方法学里交代
- 结果作为**参考区间**，不替代市场价

## 四、损害成本法（快速折算）
对污染/超采的代价，用单位损害单价倒推：
`年损害 = 超采量(m³) × 水资源稀缺单价 + 土壤流失(t) × 清淤单价`。

## 验收标准
- [ ] 每一项货币化参数都有出处与年份
- [ ] NPV/BCR/IRR 的折现率与年限已声明
- [ ] 做了单价/折现率敏感性分析
- [ ] 无市场价部分用 CVM 时方法学透明、标注局限
- [ ] 结论区分"物理量"与"价值量"，不混用
