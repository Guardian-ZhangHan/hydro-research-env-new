---
name: water-quality-index
description: 水质指数与灌溉水质评价技能。覆盖 WQI 加权计算、灌溉水化学指标（SAR/Na%/EC/RSC/Kelly）、USSL 与 Wilcox 分级、地下水化学类型（Piper 三线图）。当用户要做饮用水/灌溉水适用性评价、盐渍化风险、地下水化学特征分析时使用。
---

# 水质指数与灌溉水质评价

## 一、饮用水/地表水 WQI（加权平均法）
1. 选参：pH、溶解氧、高锰酸盐指数、氨氮、硝酸盐、总硬度、砷、氟…（按评价标准）
2. 每个参数按国标/WHO 映射到**分指数 Qi**（0–100，100 最优）
3. 加权综合：
   ```
   WQI = Σ(wi · Qi) / Σ(wi)
   ```
   wi 可用等权或专家权重（权重来源须可追溯）
4. 分级：优(>90) / 良(70–90) / 中(50–70) / 差(25–50) / 极差(<25)

## 二、灌溉水质关键指标（盐渍化预警）
```python
import numpy as np
# 离子浓度单位 mmolc/L（当量浓度）
Na, Ca, Mg = na_mmolc, ca_mmolc, mg_mmolc
SAR   = Na / np.sqrt((Ca + Mg) / 2)        # 钠吸附比，越高越易置换钙镁 -> 土壤分散
Na_pct = Na / (Ca + Mg + Na + K) * 100      # 钠百分比
EC    = ec_dS_m                             # 电导率，盐度
RSC   = (CO3 + HCO3) - (Ca + Mg)           # 残余碳酸钠，>2.5 风险
Kelly = Na / (Ca + Mg)                      # Kelly 比，>1 不良
```
### 分级（标准对照）
- **USSL 图**（EC × SAR）：低钠(C1/C2/C3)、中钠(S1/S2/S3)
- **Wilcox 分级**（EC × SAR/Na%）：优良/好/中/差/极劣灌溉水
- 经验判据：SAR<6 安全；6–9 中等；9–18 需注意；>18 危害大

## 三、地下水化学类型（Piper 三线图）
- 阴离子（Cl/SO4/HCO3）与阳离子（Ca/Mg/Na+K）各自归一为百分比
- 投到 Piper 三角 + 菱形区，判别水化学类型（如 HCO3-Ca 型、Cl-Na 型）
- 作图：`matplotlib` 画三线图，或用 `pymdwaves`/`phreeqc` 辅助
- 水化学演化（地下水径流/蒸发浓缩/混合）要在结论里解释，不只给类型名

## 四、与水土评价的衔接
灌溉水 SAR/EC 是 `land-suitability-eval` 的**限制因子**；
高 EC/SAR 区土地适宜性直接下调，并在报告中提示次生盐渍化风险。

## 验收标准
- [ ] 离子浓度已统一到 mmolc/L 再算 SAR/Na%
- [ ] EC 单位（dS/m 与 µS/cm）换算无误
- [ ] 分级引用了具体标准（USSL/Wilcox/国标）
- [ ] Piper 图阳离子与阴离子百分比各自和为 100%
- [ ] 盐渍化风险给了明确文字结论，不只报数
