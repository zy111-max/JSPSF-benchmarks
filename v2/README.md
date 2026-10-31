# JSPSF-benchmarks v2.0.0

**重新设计顺序柔性的 JSPSF 算例集，共 290 个算例。** 以我们创建的 JSPSF-001～161 为基础，加工时间、指定机器和参考工艺顺序保持不变，只重新设计工艺先后关系 `FF`，柔性大小按算例规模和形状调整。

| 系列 | 编号 | 算例数 | 命名示例 | 用途 |
|---|---|---:|---|---|
| S 标准系列 | `JSPSF2-S001`～`JSPSF2-S161` | 161 | `abz5_SF2` | 与 v1 一一对应，编号相同，`JSPSF2-S006` 对应 `JSPSF-006` |
| C 复杂系列 | `JSPSF2-C001`～`JSPSF2-C129` | 129 | `abz5_SF2C` | 只放在能构成难题的基础算例上，搜索空间更大，各工件柔性差异更大 |

**算例来源要分清：**

- 本版本只改造我们创建的 JSPSF-001～161，v1.0.0 中这 161 个算例的原文件仍然保留。
- 论文已有的算例 JSPSF-162～221 不参与改造，保持原样。
- 专利使用的 8 个算例（`metadata/example_8_instance_subset.csv`）是 v1.0.0 的原数据。`ft6_SF2` 这类同基础的 2.0 算例是新算例，不能与其混用。

## 与 v1.0.0 的不同

| 项目 | v1.0.0（JSPSF-001～161） | v2.0.0 |
|---|---|---|
| 加工时间 `P`、机器 `M` | 取自 JSPLIB | **完全相同** |
| 参考工艺顺序 | 是 `FF` 的一个可行顺序 | **相同**，所有弧仍沿参考顺序方向 |
| `FF` 来源 | 159 例按直接边密度 0.35～0.45 生成连接有向无环图，2 例复用 | 290 例全部重新生成，确定性种子见清单 |
| `FF` 结构 | 随机有向无环图 | 分段结构：段与段之间先后固定，段内工序完全自由、分成并行分支或稀疏约束 |
| 柔性大小 | 不按规模分档，无序比 0.18～0.40 | **按规模和形状分档**，无序比 0.17～0.65 |
| 工件间差异 | 所有算例使用同一密度范围 | S 系列目标无序比 ±0.05，C 系列 ±0.20 |
| `FF` 存储 | 可能含冗余边 | 只存直接边，无冗余 |
| 算例数 | 161 | 290 |
| 工件序列空间（log10，平均） | 114.8 | S 154.3，C 176.6 |
| 附带界 | 无 | 每例给出下界和启发式上界 |

**无序比** 指同一工件内没有先后关系的工序对所占比例，0 就是经典 JSP。**工件序列空间** 指各工件合法工序顺序数之积，只统计工件内部决策，不含机器顺序。

每个算例的对比数据见 [`metadata/changes_from_v1.csv`](metadata/changes_from_v1.csv)。

有 25 个算例的序列空间小于对应的 v1 算例（la21～25、swv11～20、ta38/39/54/57/59 中的部分算例），这是规则取舍的结果：这些形状下柔性过大反而更容易到达下界，所以优先保留难度。

## 柔性设计规则

记 `ρ = 工件数 / 机器数`。

| 形状 | 工序数 | 代表规模 | S 目标无序比 | C 目标无序比 |
|---|---:|---|---:|---:|
| ρ ≤ 1 | ≤ 100 | 6×6、10×10 | 0.40 | 0.40 |
| ρ ≤ 1 | 101～225 | 15×15 | 0.45 | 0.55 |
| ρ ≤ 1 | > 225 | 20×20 | 0.50 | 0.60 |
| 1 < ρ ≤ 1.4 | 300 | 20×15 | 0.35 | 0.45 |
| 1.4 < ρ < 2 | ≤ 225 | 15×10 | 0.20 | 0.20 |
| 1.4 < ρ < 2 | > 225 | 30×20 | 0.30 | 0.30 |
| ρ ≥ 2 | ≤ 300 | 10×5、15×5、20×5、20×10、30×10 | 0.40 | 0.40 |
| ρ ≥ 2 | > 300 | 30×15、50×10、50×15、50×20、100×20 | 0.20 | 0.20 |

规则来自对 10 种形状的 30 秒校准实验：

- 方形算例在各档柔性下都难，N8 与 JMX 的差距在 0.4～0.5 附近最明显。
- 从 ρ≈1.5 起，最优值主要由机器负荷决定，柔性稍大就很快到达下界，所以大算例的无序比反而要小。
- 小矩形算例在任何柔性下都能很快到达下界，这里的柔性只用于增大搜索空间。

每个工件先在目标附近抽取自己的无序比，再随机切分工序段，从 256 个候选中取最接近目标的方案，所以柔性工序的位置在各工件之间是随机的。实现见 [`tools/generate_v2.py`](tools/generate_v2.py) 和 [`tools/rule_v2.py`](tools/rule_v2.py)，每例的种子和参数见 [`metadata/generation_manifest.csv`](metadata/generation_manifest.csv)。

C 系列不包含 ft6（规模太小）以及 ft20、la1～15、la26～35、swv16～20。这些矩形算例在 v1 上几乎都能很快到达机器负荷下界，放松工序顺序不会让它们变难。

## 实测难度

**结论：2.0 增大了决策空间，但 10 秒短时运行下的难度与 v1 相近，不能认为整体更难。** 柔性是对经典 JSP 的松弛，因此更大的柔性不一定带来更高的求解难度。

下表用同一禁忌搜索、同一贪心初解、种子 0、每种邻域 10 秒，比较 N8、N8+NSF1、JMX 三种邻域。下界统一取较强的 Jackson 界。

| 集合 | 算例数 | 工件序列空间 log10 | 到达下界的算例数 | 与下界差距 % | N8 比 JMX 差 % |
|---|---:|---:|---:|---:|---:|
| v1 全部 | 161 | 114.8 | 42 | 7.49 | 4.96 |
| v2 S 系列 | 161 | 154.3 | 44 | 5.82 | 4.98 |
| v1 中与 C 系列同基础的算例 | 129 | 133.3 | 12 | 9.32 | 6.02 |
| v2 C 系列 | 129 | 176.6 | 9 | 7.65 | 5.71 |

- 配对比较中，N8 与 JMX 的差距没有显著变化（S 系列 p=0.78，C 系列 p=0.26）。与下界的差距有所下降（S 系列 p=2.9e-6，C 系列 p=0.0013）。
- 部分形状确实变难：15×10 到下界的算例数从 v1 的 4/5 降到 S 的 2/5、C 的 1/5，50×15 从 6/10 降到 4/10、1/10。
- 部分形状变容易：30×15 从 0/10 升到 2/10，la 10×10 从 1/5 升到 S 的 2/5、C 的 3/5。
- 这是单种子短时实验，只能说明大致趋势。

也测试过同等无序比下的其他结构，包括少量长柔性段，以及把瓶颈机器工序设为固定分隔点。前者与随机分段没有明显差别。后者提高了 Cmax，但更容易接近下界，所以都没有采用。

## 目录

| 路径 | 内容 | 文件数 |
|---|---|---:|
| `data/canonical/` | 统一 JSON | 290 |
| `data/dat/` | OPL DAT | 290 |
| `data/txt/` | 通用 TXT | 290 |
| `metadata/instances.csv` | 算例索引：规模、柔性指标、下界、指纹 | |
| `metadata/changes_from_v1.csv` | 每个算例与 v1 的对比 | |
| `metadata/generation_manifest.csv` | 生成参数和种子 | |
| `metadata/upper_bounds.csv` | 下界和启发式上界 | |
| `metadata/files.csv` | 全部数据文件的 SHA-256 | |
| `tools/` | 生成、校验和测试脚本 | |

格式与 v1 相同，读取工具通用。JSON 新增 `Version`、`Series`、`BaseCanonicalID`、`BaseInstanceName`、`UnorderedShare`、`Log10JobSequences`、`LowerBound`、`FlexDesign`、`SizeClass` 字段，`schema` 为 `JSPSF-JSON-V2`。

## 下界与上界

`lower_bound` 是以下两者中的较大值，都是有效下界：工件总加工时间；每台机器的抢占式 Jackson 界。其中工序的头长取其全部工艺前序的加工时间之和，因为同一工件的工序不能重叠，尾长同理。

`upper_bound` 来自上述 10 秒运行的最好解，调度方案经独立检查，但方案本身不随数据发布。53 个算例上下界相等，已证明最优。其余算例的上界**不是**已知最优值，引用时请作为参考。

由于参考工艺顺序仍然可行，经典 JSP 的任何可行解都是 v2 算例的可行解，JSPLIB 的已知最优值或上界也是对应 v2 算例的有效上界。

## 校验与复现

以下命令都在仓库根目录运行，只需要 Python 3.10+ 标准库：

```bash
python tools/validate_dataset.py v2 --expected-instances 290
python v2/tools/validate_v2.py
python tools/example_read.py v2/data/canonical/JSPSF2-S006_ft6_SF2.json
```

重新生成算例（结果逐字节相同，不含上界表）：

```bash
python v2/tools/build_v2.py --v1-root . --out v2
```

## 来源与引用

加工时间和机器数据继承自 [tamy0612/JSPLIB](https://github.com/tamy0612/JSPLIB)，来源和许可说明见仓库根目录的 [NOTICE.md](../NOTICE.md)。引用时请注明版本 `v2.0.0` 和具体算例名。

---

## English summary

Version 2.0.0 holds **290 instances with redesigned sequence flexibility**: 161 standard instances (`JSPSF2-S001` to `S161`, numbered as in v1) and 129 complex instances (`JSPSF2-C001` to `C129`). Processing times, machines and the reference operation order of JSPSF-001 to JSPSF-161 are unchanged; only `FF` is regenerated, as staged designs whose unordered share depends on instance size and on the jobs-to-machines ratio. All v1.0.0 files stay as they were.

The search space of job sequences grows from 10^115 on average to 10^154 (S) and 10^177 (C). **Short runs do not show that the set is harder overall than v1**: with 10 s of tabu search, 44 of 161 S instances and 9 of 129 C instances reached the lower bound, against 42 of 161 for v1 and 12 of 129 on the same bases. Flexibility relaxes the classic JSP, so more of it does not by itself mean a harder instance. Some shapes became harder (15×10, 50×15), others easier (30×15, la 10×10).

Each instance comes with a valid lower bound and a heuristic upper bound. Upper bounds are not claimed optimal unless they equal the lower bound (53 instances).
