# JSPSF-benchmarks

**顺序柔性作业车间调度（JSPSF）算例库。** 收录我们创建的算例和论文已有的算例，共 **221 个不同的调度输入**，同时保存 **443 个原格式数据文件**，另提供去重后的 221 份统一 JSON，便于 Python、MATLAB、C++ 等读取。

所有公开算例名称统一使用 **`_SF` 后缀**：我们创建的算例如 `ft6_SF.dat`、`ft6_SF.txt`，论文已有的算例保留原编号，如 `01_la10_SF.dat`、`01_la10_SF.mat`。JSON 的 `InstanceName` 同样使用 SF 名称；`OriginalInstanceName` 和各清单的 `source_name` 保留原名称，数值输入不变。

**仓库地址：<https://github.com/zy111-max/JSPSF-benchmarks>**  
**固定版本：<https://github.com/zy111-max/JSPSF-benchmarks/tree/v1.0.0>**

**v2.0.0：** [`v2/`](v2/README.md) 只改造我们创建的 JSPSF-001～161，重新设计顺序柔性，共 290 个算例（标准系列 161 个、复杂系列 129 个），并标注了与 v1 的不同之处。论文已有的算例和 v1.0.0 的全部数据文件没有改动。
**2.0 固定版本：<https://github.com/zy111-max/JSPSF-benchmarks/tree/v2.0.0>**

## 参考上下界

本库以**约束规划（CP）模型作为主要求解方法**，目标为最小化最大完成时间 Cmax。

- [v1.0.0 参考表](metadata/upper_bounds.csv)：161 个有效结果，其中 139 例已证明最优。
- [v2.0.0 参考表](v2/metadata/upper_bounds.csv)：290 例，其中 279 例已证明最优。

两表均采用 `canonical_id、instance_name、lower_bound、upper_bound、proved_optimal、method` 六列。CP 求解器在精确最优性判定下返回 `OPT/OPTIMAL` 或等价的最优性证明状态，且模型符合算例定义时，该结果即为该算例已证明的最优值。表中以 `proved_optimal=yes` 标记，此时上下界相等；`no` 表示仅有参考界值，不将上界称为最优值。

**来源与范围：** 上界均来自已独立校验的 CP 可行调度。v1 保留维护者 2026-07-29 批次的 148 个有效历史结果，并以每例 3600 秒重新求解原先无有效结果的 13 例，现覆盖自建的全部 161 例；文献已有的 60 例未纳入此表。v2 的已证最优行取 CP 最优值；其余 11 行的下界采用工件负载与 Jackson 有效解析界，`method` 明确区分其来源。

**求解环境：** v2 使用 OptalCP 2026.4.0 Academic、Python 3.14.4、Windows 11、Intel Core Ultra 9 285H、16 个逻辑处理器、可见内存 31.68 GiB；每例 2 个求解线程，最多 8 例并发，Auto 搜索、种子 0。先每例 300 秒，对未完成证明的 18 例再以每例 3600 秒重跑，逐例保留较好的解。v1 历史记录未完整保存版本、硬件及随机种子；可用旧脚本的默认设置为 1800 秒、16 线程，实际调用参数未完整保存，因此不据此补写未记录的环境。本次 v1 的 13 例重跑使用与 v2 相同的 CP 模型、初解策略、求解环境及搜索参数，每例时限为 3600 秒，最优性绝对和相对容差均为 0。

## 算例来源

| 类别 | 编号 | 算例数 | 目录 | 说明 |
|---|---|---:|---|---|
| **我们创建的算例** | JSPSF-001～161 | 161 | `data/expanded/` | 以 JSPLIB 经典算例为基础增加顺序柔性，159 例的 FF 为新生成，2 例复用已有 FF |
| **论文已有的算例** | JSPSF-162～221 | 60 | `data/legacy/` | 来源见下文，保持原样；其中 `18_or18_SF` 含 0 加工时间，加工时间全为正的有 59 个 |
| **专利使用的算例** | 我们创建的算例中的 8 个 | 8 | `data/expanded/` | 不是新的一组数据，见下文列表 |
| **v2 重新设计的算例** | JSPSF2-S001～S161、JSPSF2-C001～C129 | 290 | `v2/` | 由我们创建的 161 个算例改造而来，论文已有的算例不参与 |

## 下载与内容

- [下载 v1.0.0 全部文件 ZIP](https://github.com/zy111-max/JSPSF-benchmarks/archive/refs/tags/v1.0.0.zip)
- [221 个不同算例的索引](metadata/instances.csv)
- [全部数据文件及校验值](metadata/files.csv)
- [专利使用的 8 个不同规模算例](metadata/example_8_instance_subset.csv)

| 路径 | 内容 | 文件数 |
|---|---|---:|
| `data/expanded/dat/` | 我们创建的算例，OPL DAT 格式 | 161 |
| `data/expanded/txt/` | 我们创建的算例，通用 TXT 格式 | 161 |
| `data/legacy/opl/` | 论文已有算例的旧版 OPL 数据 | 61 |
| `data/legacy/mat/MIN/` | 论文已有算例的 MATLAB 数据，保留原组名 | 20 |
| `data/legacy/mat/MID/` | 论文已有算例的 MATLAB 数据，保留原组名 | 20 |
| `data/legacy/mat/MAX/` | 论文已有算例的 MATLAB 数据，保留原组名 | 20 |
| `data/canonical/` | 按调度输入去重、去除填充后的统一 JSON | 221 |

**文件数不等于不同算例数。** DAT/TXT 是我们创建的算例的不同格式；旧版 OPL 中，59 例与论文已有算例的 MAT 数据相同，另 2 例（`yn1`、`la29`）与我们创建的算例相同。因此整体包含 161 个我们创建的算例与 60 个论文已有算例的调度输入，共 221 例。两个文件同名并不保证加工时间、机器和工艺关系相同，应使用索引和输入指纹进行对应。

去重同时检查了原始输入矩阵和传递闭包，两种方式均得到 221 个不同输入。MAT 原文件中的 `Power` 等附加数值变量完整保留；统一 JSON 只提取调度输入，不包含能耗模型的全部参数。

## 专利使用的算例

专利使用以下 8 个不同规模的算例，全部属于**我们创建的算例**，数据是 v1.0.0 的原文件。v2 中的 `ft6_SF2` 等同基础算例重新设计过顺序柔性，是不同的算例，不能与这 8 个算例混用。

| 算例 | 编号 | 工件×机器 | 工序数 |
|---|---|---|---:|
| `ft6_SF` | JSPSF-006 | 6×6 | 36 |
| `la4_SF` | JSPSF-012 | 10×5 | 50 |
| `la9_SF` | JSPSF-017 | 15×5 | 75 |
| `abz5_SF` | JSPSF-001 | 10×10 | 100 |
| `abz6_SF` | JSPSF-002 | 10×10 | 100 |
| `la23_SF` | JSPSF-031 | 15×10 | 150 |
| `swv3_SF` | JSPSF-060 | 20×10 | 200 |
| `ta20_SF` | JSPSF-097 | 20×15 | 300 |

## 问题含义

每个工件有若干道工序，每道工序的加工机器与加工时间已给定。工件内部只需遵守指定的工艺先后关系，没有固定先后的工序可由调度决定次序。同一工件不能同时加工多道工序，每台机器同一时刻也只能加工一道工序；工序加工不可中断。

`FF` 是原文件保存的工艺先后关系矩阵，可能只列直接边，也可能包含冗余边。若模型需要完整的工艺可达矩阵，读取后应计算传递闭包，**不能把输入 FF 的存储边数直接当作全部可达关系数**。本仓库保持原关系不变，没有预先为工件固定完整工艺链。

经典 JSP 的最优值对应原固定工艺链，不能直接当作这些 JSPSF 实例的最优值。本库不附加未经验证的最优值。

## 数据格式

所有工件、工序、机器的标识均采用 **1-based 编号**；JSON 数组的实际下标遵循编程语言习惯。

### 统一 JSON

| 字段 | 含义 |
|---|---|
| `NbJobs` / `NbMachines` | 工件数 / 机器数 |
| `NbOps` | 各工件的工序数 |
| `P[i][j]` | 加工时间 |
| `M[i][j]` | 唯一指定的机器编号 |
| `FF[i][j][k]` | 为 1 时，工件 i 的工序 j 必须先于工序 k |
| `CanonicalID` / `InstanceName` | 本库稳定标识 / 以 SF 后缀标识的公开名称 |
| `OriginalInstanceName` | 对应源文件中的原算例名称 |
| `SourceFiles` | 与此输入对应的仓库内文件 |
| `PositiveProcessingTimes` | 所有加工时间是否严格为正 |

JSON 按每个工件真实工序数保存，不包含 OPL 的补零区域。论文已有的算例中工序数不一定等于机器数。

### OPL DAT

保留原 `NbJobs`、`NbMachines`、`NbOps`、`P`、`M`、`FF` 等数值字段。公开副本将文件名和 `InstanceName` 改为 SF 名称，并把 `ResultFile` 的本机绝对输出路径改为同目录相对文件名；原名保留在注释和清单中，不改变任何调度数据。原始和公开文件的 SHA-256 均列于 `metadata/files.csv`。原 MAT 只修改文件名，文件字节保持不变。

### 通用 TXT

`[OPERATIONS]` 每行：`Job Operation Machine ProcessingTime`。  
`[PRECEDENCE]` 每行：`Job PredecessorOperation SuccessorOperation`。  
例如 `1 2 5` 表示工件 1 的工序 2 必须先于工序 5。

## 来源与引用

### 论文已有的算例（JSPSF-162～221）

根据维护者提供的来源说明，这批算例来自：

> Yang Zhou, Guiliang Gong, Xiahui Liu, Zhipeng Yuan, Jinbo Hu, Ao He, Jie Li. **A dual-population memetic algorithm for job shop scheduling problem considering sorting flexibility.** *Computers & Operations Research*, 191 (2026), 107439. DOI: [10.1016/j.cor.2026.107439](https://doi.org/10.1016/j.cor.2026.107439).

出版社页面介绍了 60 个算例。这里保留现有本地数据的分组和数值，在清单中保留原名称，并给出文件身份校验；尚未将其逐一与出版社官方附属数据包核对，故不把本库称为原作者官方发布仓库。61 个旧 OPL 文件也不能简单当作论文中 60 个算例的一一编号对应。

### 我们创建的算例（JSPSF-001～161）

这 161 个算例的基础加工时间和机器数据取自 [tamy0612/JSPLIB](https://github.com/tamy0612/JSPLIB)，覆盖 ABZ、FT、LA、ORB、SWV、TA、YN 七类。原始家族文献见 [JSPLIB 的参考文献](https://github.com/tamy0612/JSPLIB#references)。

转换清单标明 **159 例生成了 FF，2 例复用了已有 FF**；复用项为 `la29_SF` 和 `yn1_SF`。新生成部分采用确定性种子和连接有向无环图，生成参数与逐例种子见 `metadata/conversion_manifest.csv`。现有清单不证明全部 161 个 FF 均为新增设计。

这批算例没有 `orb07`：其原 JSP 输入含零加工时长，而原转换程序要求正加工时间。本次上传未重新生成或补改该实例。

引用本库时，请同时引用所使用数据对应的原论文或原始 JSP 家族，建议注明版本 `v1.0.0` 和具体文件名/输入指纹。来源和许可范围见 [NOTICE.md](NOTICE.md)；本次发布没有为第三方数据擅自指定统一开源许可证。

## 原数据注意项

旧 MAT 文件 `MIN/18_or18_SF.mat`（原名 `18JSPPSF_or18_M.mat`）的 **工件 10、工序 10、机器 4 加工时间为 0**。本库原样保留并在 JSON/索引中标注。故 221 例中有 220 例加工时间均为正，1 例含零时长；若模型假设加工时间严格为正，应明确处理该例，不能静默改值。

## 读取与文件核验

统一 JSON 可使用各语言的标准 JSON 库读取，DAT 与 TXT 字段定义见上文。数组下标与机器、工件、工序的编号方式应按数据格式说明处理。

[`metadata/files.csv`](metadata/files.csv) 列出文件路径、SHA-256 和调度输入指纹，可据此核对下载文件；[`metadata/instances.csv`](metadata/instances.csv) 给出算例对应关系与规模。

---

## English summary

This repository contains **221 distinct JSPSF scheduling inputs**, preserved in **443 original-format data files** (161 expanded OPL DAT + 161 equivalent TXT + 61 legacy OPL DAT + 60 original MATLAB MAT). A deduplicated, padding-free canonical JSON representation is provided for all 221 inputs.

The maintainer identifies the legacy collection as originating from Zhou et al. (2026), DOI [10.1016/j.cor.2026.107439](https://doi.org/10.1016/j.cor.2026.107439). The expanded collection derives base JSP data from [JSPLIB](https://github.com/tamy0612/JSPLIB), with 159 generated precedence designs and two reused designs. Local legacy files have not been authenticated against an official supplementary archive. Source attribution is not a new license grant.

Processing times, fixed machine assignments, and stored precedence relations are preserved. Public filenames and `InstanceName` labels use the `_SF` suffix, such as `ft6_SF`; legacy file identifiers retain their original numeric prefixes. Original names remain in `OriginalInstanceName` and the manifests. Machine-local `ResultFile` paths are made relative in published DAT copies. Original MAT bytes are unchanged. One original legacy instance (`18_or18_SF`) contains a zero processing time and is explicitly flagged. No complete process chain is fixed by this release. See the manifests for file identities, aliases, and instance-level data provenance.

**Sources.** The expanded collection (JSPSF-001 to JSPSF-161) holds the instances we created; the legacy collection (JSPSF-162 to JSPSF-221) holds the existing instances from the literature. Eight of our instances, listed in `metadata/example_8_instance_subset.csv`, are the ones used in the patent, in their v1.0.0 form.

**Version 2.0.0** adds [`v2/`](v2/README.md): 290 instances with redesigned sequence flexibility on the processing times, machines and reference order of JSPSF-001 to JSPSF-161 (161 standard, 129 complex). The legacy collection and all v1.0.0 data files stay unchanged.
