# 水文地质学科研环境（Hydrogeology Research Env）

> 一个面向 **GitHub Copilot Coding Agent** 的水文地质 / 遥感 / GeoAI 科研仓库脚手架。
> 目标：让 AI Agent 在动手改代码之前，先在一个**可复现的真实环境**里跑通依赖与测试，
> 从源头压掉「AI 生成的代码跑不通」「环境幻觉」「依赖缺失」三类高频事故。

配套方法论对照（对应参考图的五个阶段）：

| 阶段 | 参考图内容 | 本仓库落地位置 |
|---|---|---|
| 阶段 1 | 开通订阅、开启 Coding Agent 总开关、配置仓库权限 | 见下方「阶段 1 操作清单」（GitHub 网页设置，不在仓库内） |
| 阶段 2 | `.github/copilot-setup-steps.yml` 项目环境配置 | [`.github/copilot-setup-steps.yml`](.github/copilot-setup-steps.yml) + `requirements.txt` + `environment.yml` |
| 阶段 3 | 加载科研技能包（`.github/skills/`）与自定义 Agent | [`.github/skills/`](.github/skills) + [`.github/agents/`](.github/agents) |
| 阶段 4 | 三种使用入口（网页 Agent 面板 / Issue 驱动 / VS Code Chat） | 见下方「阶段 4 三种入口」 |
| 阶段 5 | 权限与安全（沙箱、copilot/* 分支、Actions 分钟计费） | 见下方「阶段 5 权限与安全」 |

---

## 一、这个仓库解决什么问题

水文地质科研的典型技术栈横跨 GIS（GDAL/GEOS/PROJ 原生库）、遥感栅格、时序统计、
地下水数值模拟（MODFLOW）四套体系，`pip install` 顺序稍错就会触发
`GDAL 找不到` / `proj 数据库版本不匹配` / `netCDF4 编译失败` 等经典泥潭。

AI Coding Agent 在沙箱里最需要的不是「你告诉它怎么写」，而是**一份可执行的环境配方**——
这就是 `copilot-setup-steps.yml` 的作用：Agent 每次启动任务，先按这份配方装环境、跑校验，
校验不过就重试修依赖，而不是硬写一段跑不通的代码交给你。

## 二、目录结构

```
hydro-research-env/
├── .github/
│   ├── copilot-setup-steps.yml        # 阶段 2：Agent 沙箱环境配方（AI 必读）
│   ├── agents/                        # 阶段 3：自定义科研 Agent 角色
│   │   ├── hydro-research.agent.md    #   水位/水质/地下水建模主控
│   │   └── remote-sensing-analyst.agent.md
│   └── skills/                        # 阶段 3：科研技能包（Agent 自动按需加载）
│       ├── hydro-data-qc/SKILL.md
│       ├── remote-sensing-index/SKILL.md
│       ├── modflow-groundwater/SKILL.md
│       ├── hydro-trend-analysis/SKILL.md
│       ├── sci-figure-standard/SKILL.md
│       ├── land-suitability-eval/SKILL.md   # 水土/土地适宜性评价（FAO S1-S3/N + MCDA）
│       ├── env-economic-eval/SKILL.md        # 环境经济评价（InVEST 估值 + CBA 成本效益）
│       ├── water-quality-index/SKILL.md      # 水质指数（WQI / SAR / Na% / USSL / Piper）
│       ├── gw-vulnerability/SKILL.md         # 地下水脆弱性（DRASTIC / GOD）
│       └── soil-classification/SKILL.md      # 土壤分类（USDA 质地三角 + 中国土系对照）
├── requirements.txt                   # pip 路线依赖（Linux 沙箱 / 有 GDAL 预编译轮子时）
├── environment.yml                    # conda/mamba 路线（GDAL 最稳，推荐本地用）
├── scripts/
│   ├── test_check.py                  # 环境自检：依赖 + 版本 + 数值冒烟测试
│   └── water_balance.py               # 示例：流域水量平衡计算（可独立运行验证）
├── data/
│   └── README.md                      # 数据目录规范（原始/中间/成果三层，禁止入库大文件）
├── configs/
│   └── project.example.yaml           # 研究区参数模板（投影、水位基准、时间范围）
└── tests/
    └── test_smoke.py                  # pytest 冒烟用例
```

## 三、快速开始（本地）

**路线 A：conda / mamba（推荐，GDAL 体系最省心）**

```bash
mamba env create -f environment.yml
mamba activate hydro-research
python scripts/test_check.py
```

**路线 B：纯 pip（Linux 服务器 / CI 常用）**

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/test_check.py
```

`test_check.py` 会输出一张依赖体检表，并对缺失的关键包给出**具体修复命令**：

```
$ python scripts/test_check.py
========================================================================
 水文地质科研环境自检  (hydro-research-env)
 Python 3.11.x  |  平台 linux  |  GDAL 3.8.4
========================================================================
 [OK]   numpy            1.26.4
 [OK]   pandas           2.2.2
 [OK]   rasterio         1.3.10
 [MISS] flopy            ->  conda install -c conda-forge flopy  或  pip install flopy
 ...
------------------------------------------------------------------------
 数值冒烟测试：水量平衡闭合校验 / Mann-Kendall 趋势检验 / NDVI 计算
 [PASS] 水量平衡残差 0.000000 (阈值 1e-6)
 [PASS] MK 检验 Z=4.21, p=0.0000  -> 显著上升趋势
------------------------------------------------------------------------
 结论：核心依赖 12/14 就绪，2 项缺失 -> 环境未就绪
```

退出码：全部核心依赖就绪 + 冒烟通过 → `0`；否则 → `1`（可直接被 CI 与 Agent 判断）。

## 四、核心依赖清单（为什么是这些）

> **可选重依赖**：`requirements-domain.txt` 收纳了体积大、依赖原生库、CI 中易失败的包
> （`imod` / `hydromt` / `natcap.invest` / `wflow` / `pyRecharge`）。本地按需 `pip install -r requirements-domain.txt`，
> CI 通过 `copilot-setup-steps.yml` 的 best-effort 步骤兜底，缺失不阻断环境。

| 领域 | 关键包 | 说明 |
|---|---|---|
| 科学计算底座 | numpy / pandas / scipy / xarray | 时序、网格、拉平维度 |
| 栅格与遥感 | rasterio / rioxarray / GDAL | GeoTIFF 读写、重投影、裁剪 |
| 矢量与坐标 | geopandas / shapely / pyproj / fiona | 流域边界、含水层分区、坐标系转换 |
| 气象水文时序 | netCDF4 / h5py | 再分析数据（ERA5、GLDAS）、格点产品 |
| 地下水数值模拟 | **flopy** | MODFLOW-6 / MODFLOW-2005 / MT3D 的 Python 驱动 |
| 水文地形分析 | pysheds / richdem | 洼地填平、流向、汇流累积、流域提取 |
| 模型评价 | hydroeval | NSE / KGE / PBIAS 等水文模型标准指标 |
| 趋势与突变 | pymannkendall / statsmodels | MK 检验、Sen 斜率、Pettitt 突变点 |
| 遥感云平台 | earthengine-api / geemap | GEE 取数、在线时序合成 |
| 制图 | matplotlib / seaborn / contextily | 论文级出图 + 底图 |
| 工程化 | pytest / loguru / pyyaml / tqdm | 校验、日志、配置、进度 |
| 时序响应 | **pastas** | 地下水位对降水/开采的时序响应（脉冲/阶跃）反演 |
| 地统计/插值 | **gstools** / **pykrige** | 变异函数拟合、普通/泛kriging 空间插值 |
| 参数估计 | **pyemu**（PEST）/ **spotpy**（GLUE/DREAM） | 模型自动校准、不确定性量化 |
| 蒸散发 | **pyet** | FAO-56 参考蒸散发与作物系数 |
| 多准则决策 | **scikit-criteria** / **numpy-financial** | 水土适宜性 AHP/TOPSIS；环境经济 NPV/IRR |
| 水资源取数 | hydrofunctions / dataretrieval | USGS 实时水位/流量 API 直取 |
| 生态估值 | natcap.invest（可选） | InVEST 生境/固碳/产水服务货币化 |
| 地图与可视化 | **leafmap** / cartopy / xskillscore | 交互地图、出图投影、技能评分 |

### 当前重点研究方向：水土评价 + 环境经济评价

本仓库按使用者的主要研究场景，预置了 5 个领域技能包，可让 Agent 在动手前先套用正确方法学：

| 方向 | 对应技能包 | 关键方法 / 输出 |
|---|---|---|
| **土地适宜性（水土评价）** | `land-suitability-eval` | FAO S1/S2/S3/N 分级、MCDA（AHP/TOPSIS，scikit-criteria）、栅格加权叠加、灌溉用水约束（SAR/EC） |
| **环境经济评价** | `env-economic-eval` | InVEST 生态系统服务货币化、成本效益分析 CBA（NPV/BCR/IRR，numpy-financial）、CVM/WTP 支付意愿、损害成本法 |
| **水质评价** | `water-quality-index` | 综合 WQI、SAR/Na%/RSC/Kelly、USSL/Wilcox 灌溉分级、Piper 三线图 |
| **地下水脆弱性** | `gw-vulnerability` | DRASTIC 七因子法、GOD 简化法、污染敏感指数 SI |
| **土壤分类** | `soil-classification` | USDA 质地三角（砂/粉/黏）、中国土壤分类与质地对照、纹理/含水量经验式 |

> 方法学正确性永远由研究者负责；技能包只规范用词、流程与输出格式，不替代专业判断。

## 五、阶段 1 操作清单（GitHub 网页端，5 分钟）

1. 登录 GitHub → 右上角头像下拉 → **Settings**
2. 左侧菜单进入 **Copilot**
3. 找到 **Coding agent** 板块
4. 打开 **Enable coding agent** 总开关
5. 配置 **Repository access**：
   - 选项 A `All repositories` —— 全部仓库（含私有），省事，**科研单用户推荐**
   - 选项 B `Only selected repositories` —— 只勾选本科研仓库（更安全）
6. **Model** 选择：按需开启模型开关；Pro+ 套餐才支持自由切换模型
7. 保存策略后，Agent 即获得：仓库读取、新建 `copilot/*` 分支、提交 commit、创建 Draft PR 的权限

> 天然安全边界：Agent **只能创建 `copilot/` 前缀分支**，无法直接推送 `main`/`master`。

## 六、阶段 4 三种入口

**入口 A：仓库网页端 Agent 面板（最常用）**
1. 进入本仓库页面 → 右上角 **Agents** 按钮
2. 选择模型（如 Claude Sonnet 4.5 / Codex）与自定义科研 Agent
3. 输入任务 prompt，例如：
   > 用 `pysheds` 重构 `scripts/delineate_basin.py` 的流域提取逻辑，处理 DEM 洼地填平，
   > 并补一个 pytest 用例，最后生成 Draft PR
4. Agent 后台在 GitHub Actions 沙箱中：克隆 → 读码 → 按 `copilot-setup-steps.yml` 装环境 →
   改文件 → 建 `copilot/xxx` 分支 → 提交 → 生成 Draft PR（附执行日志）
5. 你 review PR，人工校验数值/结论后合并到主分支

**入口 B：Issue 驱动工作流（科研迭代推荐）**
1. 新建 Issue，写清需求（数据范围、方法、验收标准）
2. 把 Issue 的 Assignee 设为 `@copilot`
3. `@copilot` 自动认领 → 后台跑任务 → 生成 Draft PR 并关联该 Issue
4. 在 PR 评论区继续 `@copilot`，让它迭代修 bug / 补测试

**入口 C：VS Code 内 Copilot Chat**
```
@github create pull request，完成 xxx 任务
```
直接在 IDE 里唤起 Coding Agent，无需切浏览器。

## 七、阶段 5 权限与安全

1. Coding Agent 是 GitHub 内置 App，**无需手动生成 Token**，复用你的 Copilot 账号权限
2. Agent 沙箱为临时隔离环境，任务结束即销毁；**默认只读当前仓库**，只能推送到 `copilot/*` 分支
3. 资源消耗：任务消耗 **GitHub Actions minutes + Copilot AI Credits**，Pro+ 套餐自带额度，超额计费

## 八、⚠️ 学术场景硬性提醒

1. Coding Agent + 科研 skill **只是提示词 + 工具模板**，**不会自动校验文献真实性、实验数据正确性**，
   依然存在学术幻觉。**所有代码、文字、图表描述必须人工逐行核验。**
2. Skill 包只能规范用词与输出格式，**不能自动验证科研结论**。
3. 本仓库的 `test_check.py` 能保证「环境跑得通」，**不能保证「方法选得对」**——
   方法学正确性永远由研究者负责。

## 九、与 CodeWhale 的关键差异

| | Copilot Coding Agent | CodeWhale |
|---|---|---|
| Token 配置 | 原生 GitHub，**无需 token**，开箱即用 Issue→分支→PR | 需手动配置 MCP 服务、填写 token，链路更长 |
| Issue / PR 能力 | 原生支持（内置 App） | 全部依赖手动配置 |
| MCP / skill 支持 | 支持 | 支持 |
| 底层模型 | 受限，只能选平台提供的模型（Claude / Codex 等） | **底层模型自由** |

选型建议：**要 GitHub 原生 Issue→PR 闭环选 Coding Agent；要自由换底层模型选 CodeWhale。**

## 十、数据目录规范

`data/` 采用三层结构，大文件严禁入库（`.gitignore` 已拦截）：

```
data/
├── raw/         # 原始数据，只读不写（DEM、水位观测、遥感影像、再分析产品）
├── interim/     # 中间产物（重投影、裁剪、去云、插值结果）
└── processed/   # 最终成果（分析就绪表、模型输入文件、出图数据）
```

数据来源与许可请记录在 `data/README.md`，保证论文可复现。
