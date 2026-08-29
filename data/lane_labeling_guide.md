# LLM 发展史技术线+关系标注规范（guide.md）

> 用途：本文件是所有论文节点「技术线归属 + 关系连线」标注的唯一权威规范。子Agent 进行批处理标注时必须严格遵循本文件的判定定义、字段 schema、黄金样本示例。标注结果将生成 `data/papers_lanes.json`，驱动泳道图渲染。
>
> 生成日期：2026-08-29 · 版本 v1 · 由主 Agent 亲自制定（先立标杆再铺量）

---

## 一、9 条技术线（Lane）判定定义

每条论文节点必须先判定**唯一主线 `line`**（决定泳道位置），再补**副线 `tags`**（多线交叉标记）。主线由「论文最核心的贡献性质」决定；tags 由「论文还影响了哪些线」决定（可 0~4 个）。

| # | 线名 | 核心判定依据（论文贡献指向哪个技术维度） | 典型代表 |
|---|------|------|------|
| 1 | **arch** 架构革命 | 提出/定义新的模型架构、注意力变体、线性/稀疏/SSM 等结构本身 | Transformer、Mamba、Switch、DeepSeek-V2 MLA |
| 2 | **pretrain** 预训练与 Scaling | 预训练目标/配方、缩放定律、数据规模、涌现现象、scaling 修正 | GPT-3、Scaling Laws、Chinchilla、FineWeb |
| 3 | **align** 对齐与后训练 | SFT/RM/RLHF/DPO/偏好优化、指令微调、安全对齐方法 | InstructGPT、DPO、Constitutional AI、LLaMA-2 |
| 4 | **reason** 推理与测试时计算 | CoT/长思维链、test-time scaling、RL 推理、思考模式 | CoT、o1、R1、Kimi K1.5、Qwen3 |
| 5 | **longctx** 长上下文与效率 | 位置编码、上下文扩展、注意力加速、KV 压缩、量化/投机 | RoPE、FlashAttention、ALiBi、StreamingLLM |
| 6 | **multi** 多模态 | 视觉/图文/音视频表征、VLM、多模态对齐 | CLIP、ViT、LLaVA、Qwen2.5-VL |
| 7 | **agent** Agent 与工具 | 工具调用、行动推理、Agent 范式、RL agentic | ReAct、Toolformer、Kimi K2、UI-TARS |
| 8 | **eng** 工程与部署 | 训练并行/显存、推理服务、分页/KV cache、部署框架 | Megatron、DeepSpeed、vLLM、GQA |
| 9 | **opensrc** 开源生态与旗舰 | 开源权重/底座、旗舰模型发布、生态影响 | LLaMA、Llama-2、GPT-4、DeepSeek-V3、Kimi K3 |

> **主线 vs 副线判定优先级**：当一篇论文多线兼顾时，按「定义范式者 > 工业落地者 > 生态影响者」定主线。例：DeepSeek-V3 既架构(MoE/MLA)又开源旗舰，主线归 **arch**（MLA 是定义性贡献），tags 含 opensrc/pretrain/eng。

---

## 二、4 类关系（Relation）判定定义

关系连接两个节点（`source` 为本篇，`target` 为关联节点），`type` 取以下四类之一。**仅标显著关系**，每篇通常 1-3 条，宁缺毋滥。

| type | 中文 | 判定标准 | 示例 |
|------|------|------|------|
| `found` | 奠基 | 本篇是 target 的源头/前置基石，target 直接继承本篇的核心思想 | Attention→全部 Transformer 系；CoT→o1/R1；CLIP→LLaVA |
| `inherit` | 继承融合 | 本篇承接 target（或同类）的既有思想并**融合/改进**，形成新一代 | FlashAttention 承接 MQA；InstructGPT 承接 FLAN+RLHF 思想 |
| `branch` | 分支 | 本篇与 target 出自同一母体但**分化**出独立路线 | GPT(BERT) 双轨；DPO 从 RLHF 分支；GQA 从 MQA 分支 |
| `compete` | 竞争 | 本篇与 target 是**同期对立/互竞**路线，争夺同一问题的最优解 | Mamba vs Transformer；DPO vs PPO；Chinchilla vs Kaplan |

> **判定注意**：
> - `found` 和 `inherit` 容易混淆：`found` 强调「源头开创」，target 是后来者；`inherit` 强调「本篇是后来者」，承接前人。用「谁更早/谁是源头」判别。
> - `branch` 强调「同源分化」；`compete` 强调「同期互竞」。DPO 与 PPO 是竞争（都解 RLHF 偏好），DPO 之于 RLHF 是分支（同一问题换了参数化路线）。
> - 关系 target 必须是库内已收录的论文（用 slug）。若 target 未收录，只记 intent 不硬连。

---

## 三、字段 Schema（每篇节点）

```json
{
  "id": "arXiv号或null",
  "slug": "论文slug（库内唯一键）",
  "line": "主线技术线（arch/pretrain/align/reason/longctx/multi/agent/eng/opensrc）",
  "tags": ["副线1", "副线2"],
  "related": [
    {"target": "关联论文slug", "type": "found|inherit|branch|compete"}
  ]
}
```

- `line`：必填，1 个。
- `tags`：可选，0-4 个，**不含主线重复**。
- `related`：可选，每篇 1-3 条，仅显著关系。

---

## 四、黄金样本（17 篇，资深标注基准）

以下 17 篇由主 Agent 亲自标注，作为子Agent 判定其他 116 篇的**参照基准**（9 条主线全覆盖）。子Agent 应依据这些样本的判定风格（主线选择的优先逻辑、关系类型的判别标准）处理未标注篇目。

### 样本 1 · Attention Is All You Need
```json
{"id":"1706.03762","slug":"Attention_Is_All_You_Need","line":"arch","tags":["pretrain","longctx","eng"],
 "related":[{"target":"BERT","type":"inherit"},{"target":"Switch_Transformers","type":"inherit"},{"target":"RoPE_RoFormer","type":"inherit"},{"target":"CLIP","type":"inherit"}]}
```
> 主线 arch（定义 Transformer 结构本身）；tags 含 pretrain（作为一切预训练底座）、longctx（位置编码/注意力议题起点）、eng（高效训练）。relation：attention 奠基给 BERT/Switch/RoPE/CLIP 全部继承。全为 `inherit`（都是后来者承接本篇架构）。

### 样本 2 · BERT
```json
{"id":"1810.04805","slug":"BERT","line":"pretrain","tags":["arch"],
 "related":[{"target":"Attention_Is_All_You_Need","type":"inherit"},{"target":"GPT-1","type":"branch"}]}
```
> 主线 pretrain（MLM 预训练范式定义）；tags arch（沿用 Transformer 编码器）。relation：inherit 自 Attention；与 GPT-1 同源（都基于 Transformer）但双向 vs 单向 per-task 分化 → branch。

### 样本 3 · GPT-3（Language Models are Few-Shot Learners）
```json
{"id":"2005.14165","slug":"GPT-3_Few-Shot_Learners","line":"pretrain","tags":["arch","reason"],
 "related":[{"target":"Kaplan_Scaling_Laws","type":"inherit"},{"target":"Chain-of-Thought","type":"found"},{"target":"InstructGPT_RLHF","type":"found"}]}
```
> 主线 pretrain（few-shot/in-context 范式）；found 给 CoT（ICL 的推理延伸）与 InstructGPT（对齐的载体起点）。

### 样本 4 · Scaling Laws for Neural Language Models（Kaplan）
```json
{"id":"2001.08361","slug":"Kaplan_Scaling_Laws","line":"pretrain","tags":[],
 "related":[{"target":"Chinchilla","type":"compete"},{"target":"GPT-3_Few-Shot_Learners","type":"found"}]}
```
> 主线 pretrain（缩放定律）；与 Chinchilla 互竞（Kaplan 低估数据 vs Chinchilla 修正）→ compete；found 给 GPT-3（规模化的理论依据）。

### 样本 5 · Chinchilla（Training Compute-Optimal）
```json
{"id":"2203.15556","slug":"Chinchilla","line":"pretrain","tags":["arch"],
 "related":[{"target":"Kaplan_Scaling_Laws","type":"compete"},{"target":"LLaMA","type":"found"}]}
```
> 主线 pretrain（纠正算力最优配置）；found 给 LLaMA（高效小模型路线的直接依据）。

### 样本 6 · InstructGPT（RLHF）
```json
{"id":"2203.02155","slug":"InstructGPT_RLHF","line":"align","tags":["adapt"],
 "related":[{"target":"FLAN","type":"inherit"},{"target":"DPO","type":"branch"}]}
```
> 主线 align（RLHF 三段式定义）；inherit FLAN 的指令微调思想；branch 出 DPO（同一对齐问题不同参数化）。

### 样本 7 · Chain-of-Thought
```json
{"id":"2201.11903","slug":"Chain-of-Thought","line":"reason","tags":["align"],
 "related":[{"target":"GPT-3_Few-Shot_Learners","type":"inherit"},{"target":"Self-Consistency","type":"branch"},{"target":"o1_Learning_to_Reason","type":"found"}]}
```
> 主线 reason（推理范式开山）；inherit GPT-3 的 ICL；branch Self-Consistency（同族采样扩展）；found o1（长思维链推理的源头）。

### 样本 8 · DPO
```json
{"id":"2305.18290","slug":"DPO","line":"align","tags":["reason"],
 "related":[{"target":"InstructGPT_RLHF","type":"compete"},{"target":"Constitutional_AI","type":"compete"}]}
```
> 主线 align（偏好优化重参数化）；与 RLHF/Constitutional AI 互竞（同为对齐问题的不同解法）→ compete。

### 样本 9 · CLIP
```json
{"id":"2103.00020","slug":"CLIP","line":"multi","tags":["pretrain","arch"],
 "related":[{"target":"ViT","type":"inherit"},{"target":"LLaVA","type":"found"},{"target":"Flamingo","type":"found"}]}
```
> 主线 multi（图文对比表征）；found 给 ViT（视觉编码）、LLaVA/Flamingo（多模态对齐起点）。

### 样本 10 · ViT
```json
{"id":"2010.11929","slug":"ViT","line":"multi","tags":["arch"],
 "related":[{"target":"Attention_Is_All_You_Need","type":"inherit"},{"target":"CLIP","type":"inherit"}]}
```
> 主线 multi（Transformer 用于视觉）；inherit Attention（结构）+ CLIP（视觉表征思路）。

### 样本 11 · FlashAttention
```json
{"id":"2205.14135","slug":"FlashAttention","line":"longctx","tags":["eng","arch"],
 "related":[{"target":"MQA","type":"inherit"},{"target":"EAGLE","type":"branch"},{"target":"DeepSeek-V2_MLA","type":"inherit"}]}
```
> 主线 longctx（注意力 IO 效率）；inherit MQA（KV 优化启蒙、MQA 的工程化延伸）；branch 出 EAGLE（加速解码领域）；inherit DeepSeek-V2 MLA。

### 样本 12 · RoFormer（RoPE）
```json
{"id":"2104.09864","slug":"RoPE_RoFormer","line":"longctx","tags":["arch"],
 "related":[{"target":"ALiBi","type":"compete"},{"target":"Position_Interpolation","type":"inherit"},{"target":"LongRoPE","type":"inherit"}]}
```
> 主线 longctx（旋转位置编码）；与 ALiBi 互竞（免训练外推不同方案）；inherit 给位置插值/LongRoPE 等长上下文外推。

### 样本 13 · ReAct
```json
{"id":"2210.03629","slug":"ReAct","line":"agent","tags":["reason"],
 "related":[{"target":"Chain-of-Thought","type":"inherit"},{"target":"Toolformer","type":"branch"},{"target":"Kimi_K2","type":"found"}]}
```
> 主线 agent（推理+行动交替范式）；inherit CoT；branch Toolformer（同为工具使用但方式不同）；found Kimi K2（agentic 浪潮源头）。

### 样本 14 · Mamba
```json
{"id":"2312.00752","slug":"Mamba","line":"arch","tags":["longctx"],
 "related":[{"target":"Attention_Is_All_You_Need","type":"compete"},{"target":"Jamba","type":"inherit"},{"target":"Mamba-2","type":"inherit"}]}
```
> 主线 arch（选择性 SSM 线性架构）；与 Transformer 互竞（注意力是否必要）→ compete；inherit 给 Jamba/Mamba-2（混合/继承）。

### 样本 15 · DeepSeek-V3
```json
{"id":"2412.19437","slug":"DeepSeek-V3","line":"arch","tags":["opensrc","pretrain","eng"],
 "related":[{"target":"DeepSeek-V2_MLA","type":"inherit"},{"target":"Kimi_K2","type":"compete"},{"target":"GLM-5","type":"compete"}]}
```
> 主线 arch（细粒度 MoE + 无辅助损失负载均衡）；inherit DeepSeek-V2 MLA；与 Kimi K2/GLM-5 互竞（同期开源旗舰）。

### 样本 16 · vLLM（Efficient Memory Management / PagedAttention）
```json
{"id":"2309.06180","slug":"vLLM_PagedAttention","line":"eng","tags":["longctx","arch"],
 "related":[{"target":"MQA","type":"inherit"},{"target":"FlashAttention","type":"inherit"},{"target":"Speculative_Decoding","type":"inherit"}]}
```
> 主线 eng（KV 分页管理 + 连续批处理服务引擎 vLLM，定义工业级推理服务范式）；tags longctx（KV 管理与长上下文相关）、arch（涉及注意力计算管理）；inherit MQA/FlashAttention（承接其 KV 优化与注意力效率思想）、Speculative_Decoding（同属推理加速工程线，被 vLLM 生态继承）。

### 样本 17 · LLaMA
```json
{"id":"2302.13971","slug":"LLaMA","line":"opensrc","tags":["pretrain","arch"],
 "related":[{"target":"Chinchilla","type":"inherit"},{"target":"LLaMA_2","type":"found"},{"target":"Alpaca","type":"branch"}]}
```
> 主线 opensrc（开源权重奠基，开启开源纪元）；tags pretrain（公开数据训练逼近 GPT-3）、arch（沿用 Transformer）；inherit Chinchilla（高效小模型的缩放依据）；found LLaMA-2（直接后继）；branch Alpaca（基于 LLaMA 的指令微调衍生）。

---

## 五、标注流程（子Agent 执行）

1. **判定主线**：按「—、9 线判定定义」的贡献性质定位，选出唯一主线。
2. **补副线 tags**：按论文影响的技术维度补 0-4 个，不含主线重复。
3. **建关系 related**：按「二、4 类关系」从深度解读报告的「启示/后续影响」章节提取显著关系，target 必须是库内 slug，type 用 found/inherit/branch/compete，每篇 1-3 条。
4. **产出**：输出 JSON（schema 见「三、」），每篇一个条目，共 116 篇（133 - 17 黄金样本）。
5. **黄金样本复用**：已标注的 17 篇直接作为正确示例，子Agent 处理同类型论文时参照其风格。

## 六、质检要点

- `line` 必须存在且为 9 线之一。
- `tags` 不得与主线重复。
- `related.target` 必须是库内已有 slug（可查询 master 验证）。
- `related.type` 必须为四类之一。
- 关系**宁缺毋滥**，避免过度标注导致泳道图连线杂乱。
