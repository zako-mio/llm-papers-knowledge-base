# LLM 关键节点论文全集（2017–2026）

收录大语言模型发展史上 133 篇关键论文，按五个时代组织，附优先级分级、推荐阅读路线与多技术线泳道图。

## 统计总览

| 指标 | 数量 |
|---|---:|
| 收录总篇数 | 133 |
| 可下载 PDF | 112 |
| 仅索引（无公开PDF） | 21 |
| P3 必读核心 | 38 |
| P2 重要 | 81 |
| P1 补充 | 14 |

**五时代分布**：

| 时代 | 论文数 |
|---|---:|
| E1 · 奠基期：注意力革命与预训练范式确立（2017–2019） | 10 |
| E2 · 规模化时代：Scaling Laws、涌现与对齐萌芽（2020–2022H1） | 21 |
| E3 · 对齐与开源爆发：ChatGPT冲击波（2022H2–2023） | 26 |
| E4 · 工程化时代：长上下文、MoE 与开源追平（2023H2–2024） | 32 |
| E5 · 推理与Agent时代：o1时刻之后（2025–2026） | 44 |

## 使用说明

- **目录结构**：本地 PDF 按 `papers/E1` … `papers/E5` 五个时代目录存放。
- **文件命名规则**：`{日期}_{优先级}_{简称}.pdf`，例如 `2017-06_P3_Attention_Is_All_You_Need.pdf`。
- **优先级含义**：
  - **P3 = 必读核心**（38 篇）：建立主线骨架的里程碑工作；
  - **P2 = 重要**：对主线有实质贡献或影响深远的分支；
  - **P1 = 补充**：扩展视野与查证细节用。
  - 同级内按发表时间越新越优先阅读。

## 在线浏览与视图

- **多技术线泳道图**（`docs/timeline.html`，转置版）：**左侧固定时间纵轴 + 顶部固定技术线横轴 + 中间可滚动画布**（上下滚动为主浏览时间，sticky 双轴随滚动保持轴固定）。9 条技术线（架构革命 / 预训练与Scaling / 对齐与后训练 / 推理与测试时计算 / 长上下文与效率 / 多模态 / Agent与工具 / 工程与部署 / 开源生态与旗舰）横向并排，节点按（时间×技术线）落位，P3 高亮 / P2 / P1 弱化。**图例即筛选器**：点击技术线图例聚焦高亮该线（Ctrl+点击多选筛选），关系类型图例（奠基/继承/分支/竞争）点击高亮对应关系线；节点悬停看完整信息+关系标签、点击进深度解读。**这是展示"多种技术线并行发展"的主视图。**
- **卡片列表视图**（`docs/list.html`）：按时代分组的逐篇卡片，可筛选时代/优先级，查看完整标题/机构/贡献/背景档案，与泳道图一键互切。
- **深度解读总览**（`docs/analysis/index.html`）：133 篇六层深度解读（问题定位→概念内核→方法拆解→证据链→批判→启示）的入口索引，点击进入各篇 HTML 阅读版。
- 三者均为 `GitHub Pages` 发布页（`https://zako-mio.github.io/llm-papers-knowledge-base/`），可直接在线浏览。

## 推荐阅读路线（P3 先行）

1. [2017-06] Attention Is All You Need —— 纯自注意力Transformer架构，完全弃用RNN/CNN
2. [2018-10] BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding —— 双向编码器+MLM预训练，理解类任务全面刷新
3. [2020-01] Scaling Laws for Neural Language Models —— 幂律刻画损失随参数/数据/算力可预测下降
4. [2020-05] Language Models are Few-Shot Learners —— 175B下few-shot/in-context learning系统实证
5. [2020-05] Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks —— 参数记忆+非参数检索的seq2seq生成，命名RAG范式
6. [2020-10] An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale —— 纯Transformer做图像分类，patch序列化
7. [2021-01] Switch Transformers: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity —— top-1路由极简MoE，首次训到万亿参数
8. [2021-02] Learning Transferable Visual Models From Natural Language Supervision —— 4亿图文对比学习，零样本分类
9. [2021-04] RoFormer: Enhanced Transformer with Rotary Position Embedding —— 旋转位置编码：绝对位置实现相对内积
10. [2021-06] LoRA: Low-Rank Adaptation of Large Language Models —— 冻结权重训低秩增量矩阵，可训练参数骤降
11. [2021-09] Finetuned Language Models Are Zero-Shot Learners —— 提出指令微调：多任务指令化微调激发零样本泛化
12. [2022-01] Chain-of-Thought Prompting Elicits Reasoning in Large Language Models —— 中间推理步骤示例大幅提升复杂推理
13. [2022-03] Training language models to follow instructions with human feedback —— SFT+奖励模型+PPO三段RLHF，1.3B胜175B
14. [2022-03] Training Compute-Optimal Large Language Models —— 证明Kaplan低估数据：算力最优应参数数据约等比扩
15. [2022-05] FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness —— IO感知分块tiling+online softmax精确加速
16. [2022-10] ReAct: Synergizing Reasoning and Acting in Language Models —— 推理轨迹与动作交替生成的Agent范式
17. [2022-12] Constitutional AI: Harmlessness from AI Feedback —— 用原则驱动AI自我批评修订，RLAIF替代人工标注
18. [2022-12] Self-Instruct: Aligning Language Models with Self-Generated Instructions —— LLM自举生成指令数据，175种子扩至52K
19. [2023-02] LLaMA: Open and Efficient Foundation Language Models —— 7-65B开源权重，公开数据训练逼近GPT-3
20. [2023-03] GPT-4 Technical Report —— 首个商用强多模态(图像输入)LLM技术报告
21. [2023-05] Direct Preference Optimization: Your Language Model is Secretly a Reward Model —— 奖励重参数化进目标，偏好优化变监督分类损失
22. [2023-07] Llama 2: Open Foundation and Fine-Tuned Chat Models —— 开源7B-70B基础+RLHF聊天模型，开放商用
23. [2023-09] Efficient Memory Management for Large Language Model Serving with PagedAttention —— KV缓存分页管理+连续批处理服务引擎vLLM
24. [2023-12] Mamba: Linear-Time Sequence Modeling with Selective State Spaces —— 选择性SSM：数据依赖参数+硬件感知扫描
25. [2024-02] DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models —— GRPO：去Critic组内相对优势估计，省显存且稳定的RL算法
26. [2024-05] DeepSeek-V2: A Strong, Economical, and Efficient Mixture-of-Experts Language Model —— 多头潜在注意力MLA：KV压入低秩潜向量
27. [2024-07] The Llama 3 Herd of Models —— 系统化后训练：SFT+拒绝采样+DPO多轮迭代
28. [2024-08] Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters —— 测试时计算可更高效，小模型+test-time超14x大模型
29. [2024-09] Learning to Reason with LLMs (OpenAI o1) —— 官方宣告大规模RL驱动长思维链范式，o1首秀
30. [2024-12] DeepSeek-V3 Technical Report —— 无辅助损失负载均衡+MTP+FP8训练的671B细粒度MoE
31. [2025-01] DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning —— 纯RL涌现长CoT反思验证，GRPO+规则可验证奖励
32. [2025-07] Kimi K2: Open Agentic Intelligence —— 1.04T总参32B激活MoE，MuonClip优化器+agentic数据合成
33. [2025-08] GLM-4.5: Agentic, Reasoning, and Coding (ARC) Foundation Models —— 专家迭代+slime异步解耦RL基建的agentic后训练
34. [2025-10] DeepSeek-OCR: Contexts Optical Compression —— 视觉压缩原语：长文本转图像实现上下文光学压缩
35. [2026-02] GLM-5: from Vibe Coding to Agentic Engineering —— 744B-A40B MoE，引入DSA稀疏注意力+异步Agent RL
36. [2026-04] Thinking with Visual Primitives —— 点框空间标记作为最小思维单位嵌入CoT，弥合Reference Gap；CSA视觉KV压缩7056倍
37. [2026-04] DeepSeek-V4 Technical Report (Pro/Flash) —— CSA+HCA混合注意力+mHC超连接+Muon优化器+FP4量化感知训练，1M上下文
38. [2026-07] Kimi K3: Open Frontier Intelligence —— 2.8T总参/104B激活首个开源3T级，KDA+AttnRes+MoonClip二阶优化器

> 读完这 38 篇即建立主线骨架，再按时代下探 P2/P1。

## 分时代论文清单

### E1 · 奠基期：注意力革命与预训练范式确立（2017–2019）

2017年之前，序列建模由LSTM/GRU加attention的seq2seq统治，循环网络的串行计算是根本枷锁。《Attention Is All You Need》用纯自注意力抛弃循环结构，赌注是「可并行性大于归纳偏置」——2018年被GPT与BERT双双验证后，Transformer成为唯一底座。本时期的主线是「预训练表示学习」路线之争：ELMo（特征融合）、GPT-1（生成式预训练+微调）、BERT（双向编码+MLM）三连击终结了任务专用架构时代；GPT-2又在2019年反手证明「语言模型是无监督多任务学习者」，为zero-shot范式埋下伏笔。同期还有一条工程暗线：Sparse Transformer与MQA开始处理注意力的平方复杂度与KV显存问题——当时只是边缘研究，数年后成为推理系统的命脉。

| 日期 | 级别 | 论文 | 机构 | 核心贡献 | 资源 |
|---|---|---|---|---|---|
| 2017-06 | P3 | Attention Is All You Need | Google Brain/Research | 纯自注意力Transformer架构，完全弃用RNN/CNN | [arXiv](https://arxiv.org/abs/1706.03762) · [code](https://github.com/tensorflow/tensor2tensor) |
| 2018-02 | P2 | Deep Contextualized Word Representations | AI2 | 双向LSTM深度上下文词表示，动态嵌入替代静态向量 | [arXiv](https://arxiv.org/abs/1802.05365) · [code](https://github.com/allenai/allennlp) |
| 2018-06 | P2 | **Improving Language Understanding by Generative Pre-Training**「※无公开PDF」 | OpenAI | 确立生成式预训练+判别式微调两阶段范式 | [外部链接](https://s3-us-west-2.amazonaws.com/openai-assets/research-covers/language-unsupervised/language_understanding_paper.pdf) |
| 2018-10 | P3 | BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding | Google | 双向编码器+MLM预训练，理解类任务全面刷新 | [arXiv](https://arxiv.org/abs/1810.04805) · [code](https://github.com/google-research/bert) |
| 2019-02 | P2 | **Language Models are Unsupervised Multitask Learners**「※无公开PDF」 | OpenAI | 论证语言模型天然是多任务学习者，zero-shot可用 | [外部链接](https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf) |
| 2019-04 | P2 | Generating Long Sequences with Sparse Transformers | OpenAI | strided/fixed稀疏注意力，复杂度O(L√L) | [arXiv](https://arxiv.org/abs/1904.10509) · [code](https://github.com/openai/sparse_attention) |
| 2019-09 | P2 | Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism | NVIDIA | 模型并行+张量切分，可训练多亿级参数LLM | [arXiv](https://arxiv.org/abs/1909.08053) · [code](https://github.com/NVIDIA/Megatron-LM) |
| 2019-10 | P2 | Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer | Google | text-to-text统一框架+系统消融预训练配方+C4语料 | [arXiv](https://arxiv.org/abs/1910.10683) · [code](https://github.com/google-research/text-to-text-transfer-transformer) |
| 2019-10 | P2 | ZeRO: Memory Optimizations Toward Training Trillion Parameter Models | Microsoft | ZeRO优化器分片，显存开销随GPU数线性下降，支撑万亿参 | [arXiv](https://arxiv.org/abs/1910.02054) · [code](https://github.com/microsoft/DeepSpeed) |
| 2019-11 | P2 | Fast Transformer Decoding: One Write-Head is All You Need | Google | 多query头共享单组KV，压缩KV cache | [arXiv](https://arxiv.org/abs/1911.02150) |

### E2 · 规模化时代：Scaling Laws、涌现与对齐萌芽（2020–2022H1）

GPT-3的175B few-shot宣告「规模即能力」，Kaplan定律给了烧钱的理论依据，行业进入军备竞赛。但此时主流范式仍是「预训练大模型+微调/提示」：FLAN证明指令微调有效却未成气候，直到InstructGPT用RLHF把「听话」变成可训练目标，对齐问题才正式登堂入室。Chinchilla修正Kaplan定律，引爆「数据vs参数」的全行业重估，直接催生了后来的LLaMA高效路线。更重要的是CoT的发现——「思考过程」可以被提示诱导出来，当时只被视为提示技巧，两年后被证明是新范式的种子。基础设施方面：FlashAttention重写注意力的IO逻辑、Switch Transformer验证MoE通往万亿参数、ViT/CLIP打通视觉表征——多模态与效率的地基在本时期全部打完。

| 日期 | 级别 | 论文 | 机构 | 核心贡献 | 资源 |
|---|---|---|---|---|---|
| 2020-01 | P3 | Scaling Laws for Neural Language Models | OpenAI | 幂律刻画损失随参数/数据/算力可预测下降 | [arXiv](https://arxiv.org/abs/2001.08361) |
| 2020-02 | P2 | REALM: Retrieval-Augmented Language Model Pre-Training | Google | 将MIPS检索嵌入预训练目标端到端训练 | [arXiv](https://arxiv.org/abs/2002.08909) · [code](https://github.com/google-research/language/tree/master/language/realm) |
| 2020-05 | P3 | Language Models are Few-Shot Learners | OpenAI | 175B下few-shot/in-context learning系统实证 | [arXiv](https://arxiv.org/abs/2005.14165) |
| 2020-05 | P3 | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | Meta AI | 参数记忆+非参数检索的seq2seq生成，命名RAG范式 | [arXiv](https://arxiv.org/abs/2005.11401) · [code](https://github.com/huggingface/transformers) |
| 2020-06 | P1 | GShard: Scaling Giant Models with Conditional Computation and Automatic Sharding | Google | MoE稀疏+自动分片，600B+多语翻译T5 | [arXiv](https://arxiv.org/abs/2006.16668) · [code](https://github.com/google-research/t5x) |
| 2020-10 | P3 | An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale | Google Brain | 纯Transformer做图像分类，patch序列化 | [arXiv](https://arxiv.org/abs/2010.11929) · [code](https://github.com/google-research/vision_transformer) |
| 2021-01 | P3 | Switch Transformers: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity | Google | top-1路由极简MoE，首次训到万亿参数 | [arXiv](https://arxiv.org/abs/2101.03961) · [code](https://github.com/google-research/t5x) |
| 2021-02 | P3 | Learning Transferable Visual Models From Natural Language Supervision | OpenAI | 4亿图文对比学习，零样本分类 | [arXiv](https://arxiv.org/abs/2103.00020) · [code](https://github.com/OpenAI/CLIP) |
| 2021-04 | P3 | RoFormer: Enhanced Transformer with Rotary Position Embedding | 追一科技 | 旋转位置编码：绝对位置实现相对内积 | [arXiv](https://arxiv.org/abs/2104.09864) · [code](https://github.com/ZhuiyiTechnology/roformer) |
| 2021-06 | P3 | LoRA: Low-Rank Adaptation of Large Language Models | Microsoft | 冻结权重训低秩增量矩阵，可训练参数骤降 | [arXiv](https://arxiv.org/abs/2106.09685) · [code](https://github.com/microsoft/LoRA) |
| 2021-08 | P2 | Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation | MosaicML | 线性位置偏置(ALiBi)让模型外推远超训练长度 | [arXiv](https://arxiv.org/abs/2108.12409) · [code](https://github.com/ofirpress/attention_with_linear_biases) |
| 2021-09 | P3 | Finetuned Language Models Are Zero-Shot Learners | Google | 提出指令微调：多任务指令化微调激发零样本泛化 | [arXiv](https://arxiv.org/abs/2109.01652) · [code](https://github.com/google-research/flan) |
| 2022-01 | P2 | Grokking: Generalization Beyond Overfitting on Small Algorithmic Datasets | OpenAI | 发现长时训练后从记忆到泛化的延迟突变现象 | [arXiv](https://arxiv.org/abs/2201.02177) |
| 2022-01 | P3 | Chain-of-Thought Prompting Elicits Reasoning in Large Language Models | Google | 中间推理步骤示例大幅提升复杂推理 | [arXiv](https://arxiv.org/abs/2201.11903) |
| 2022-03 | P2 | Self-Consistency Improves Chain of Thought Reasoning in Language Models | Google | 多条CoT采样+多数投票，并行测试时扩展开山之作 | [arXiv](https://arxiv.org/abs/2203.11171) |
| 2022-03 | P3 | Training language models to follow instructions with human feedback | OpenAI | SFT+奖励模型+PPO三段RLHF，1.3B胜175B | [arXiv](https://arxiv.org/abs/2203.02155) |
| 2022-03 | P3 | Training Compute-Optimal Large Language Models | DeepMind | 证明Kaplan低估数据：算力最优应参数数据约等比扩 | [arXiv](https://arxiv.org/abs/2203.15556) |
| 2022-04 | P2 | PaLM: Scaling Language Modeling with Pathways | Google | 540B dense稳定训练实证+跨任务涌现能力评估体系 | [arXiv](https://arxiv.org/abs/2204.02311) |
| 2022-04 | P2 | Flamingo: a Visual Language Model for Few-Shot Learning | DeepMind | Perceiver Resampler桥接冻结LLM，少样本多模态 | [arXiv](https://arxiv.org/abs/2204.14198) |
| 2022-05 | P3 | FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness | Stanford/UC Berkeley等 | IO感知分块tiling+online softmax精确加速 | [arXiv](https://arxiv.org/abs/2205.14135) · [code](https://github.com/Dao-AILab/flash-attention) |
| 2022-11 | P2 | Fast Inference from Transformers via Speculative Decoding | Google Research | 小模型草稿+大模型并行验证的无损加速解码 | [arXiv](https://arxiv.org/abs/2211.17192) |

### E3 · 对齐与开源爆发：ChatGPT冲击波（2022H2–2023）

ChatGPT于2022年11月末引燃消费级AI浪潮，InstructGPT的三段式配方成为行业圣经，CAI、Self-Instruct、DPO随后围绕「如何更快更省地对齐」层层演进：人工标注贵就AI反馈（RLAIF），标注少就自举合成（Self-Instruct），PPO难训就把偏好优化变成监督损失（DPO）。LLaMA权重外泄意外开启开源纪元，Alpaca用不到600美元复刻指令跟随，证明「数据质量>算力堆砌」。GPT-4技术报告确立多模态旗舰标杆，开源界以LLaVA等应战。Agent概念在ReAct、Toolformer、ToT中成形——彼时还只是论文里的演示。同时社区开始正视「部署成本决定生死」：Position Interpolation打开长上下文之门，AWQ/GPTQ把量化推向4bit，投机解码起步。这一年，能力的民主化与技术平民化同时发生。

| 日期 | 级别 | 论文 | 机构 | 核心贡献 | 资源 |
|---|---|---|---|---|---|
| 2022-10 | P3 | ReAct: Synergizing Reasoning and Acting in Language Models | Google Brain+Princeton | 推理轨迹与动作交替生成的Agent范式 | [arXiv](https://arxiv.org/abs/2210.03629) · [code](https://github.com/ysymyth/ReAct) |
| 2022-10 | P2 | GLM-130B: An Open Bilingual Pre-trained Model | 清华KEG×智谱AI | 千亿级开源中英双语稠密模型，自回归填空架构 | [arXiv](https://arxiv.org/abs/2210.02414) · [code](https://github.com/THUDM/GLM-130B) |
| 2022-10 | P2 | GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers | IST Austria+HF | 基于OBQ的逐层权重量化，4bit近无损 | [arXiv](https://arxiv.org/abs/2210.17323) · [code](https://github.com/IST-DASLab/gptq) |
| 2022-12 | P3 | Constitutional AI: Harmlessness from AI Feedback | Anthropic | 用原则驱动AI自我批评修订，RLAIF替代人工标注 | [arXiv](https://arxiv.org/abs/2212.08073) |
| 2022-12 | P3 | Self-Instruct: Aligning Language Models with Self-Generated Instructions | UW/Microsoft | LLM自举生成指令数据，175种子扩至52K | [arXiv](https://arxiv.org/abs/2212.10560) · [code](https://github.com/yizhongw/self-instruct) |
| 2022-12 | P2 | Teaching Small Language Models to Reason | Google | 最早系统化CoT蒸馏：教师CoT微调小学生模型 | [arXiv](https://arxiv.org/abs/2212.08410) |
| 2023-01 | P2 | BLIP-2: Bootstrapping Language-Image Pre-training with Frozen Image Encoders and Large Language Models | Salesforce | Q-Former轻量桥接视觉与冻结LLM | [arXiv](https://arxiv.org/abs/2301.12597) · [code](https://github.com/salesforce/LAVIS) |
| 2023-02 | P3 | LLaMA: Open and Efficient Foundation Language Models | Meta | 7-65B开源权重，公开数据训练逼近GPT-3 | [arXiv](https://arxiv.org/abs/2302.13971) · [code](https://github.com/meta-llama/llama) |
| 2023-02 | P2 | Toolformer: Language Models Can Teach Themselves to Use Tools | Meta AI | 自监督生成API调用数据教会LLM用工具 | [arXiv](https://arxiv.org/abs/2302.04761) · [code](https://github.com/facebookresearch/toolformer) |
| 2023-03 | P2 | **Stanford Alpaca: An Instruction-following LLaMA Model**「※无公开PDF」 | Stanford | 52K Self-Instruct数据+LLaMA低成本复刻指令能力 | [外部链接](https://arxiv.org/abs/2303.08774v4) |
| 2023-03 | P2 | Self-Refine: Iterative Refinement with Self-Feedback | CMU+AI2 | 同一模型生成-自评-修改循环，无需外部奖励 | [arXiv](https://arxiv.org/abs/2303.17651) · [code](https://github.com/madaan/self-refine) |
| 2023-03 | P2 | Reflexion: Language Agents with Verbal Reinforcement Learning | Northeastern+MIT | 失败后生成语言化反思存入记忆，下轮重试 | [arXiv](https://arxiv.org/abs/2303.11366) · [code](https://github.com/noahshinn/reflexion) |
| 2023-03 | P3 | GPT-4 Technical Report | OpenAI | 首个商用强多模态(图像输入)LLM技术报告 | [arXiv](https://arxiv.org/abs/2303.08774) |
| 2023-04 | P2 | Are Emergent Abilities of Large Language Models a Mirage? | Stanford | 论证涌现多为非线性不连续指标造成的测量伪象 | [arXiv](https://arxiv.org/abs/2304.15004) |
| 2023-04 | P2 | Visual Instruction Tuning | UW/Microsoft/Wisconsin | 语言模型指令微调对齐视觉，通用多模态助手 | [arXiv](https://arxiv.org/abs/2304.08485) · [code](https://github.com/haotian-liu/LLaVA) |
| 2023-05 | P2 | GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints | Google Research | 分组共享KV，MQA效率与MHA质量折中 | [arXiv](https://arxiv.org/abs/2305.13245) |
| 2023-05 | P2 | LIMA: Less Is More for Alignment | Meta | 仅1000条精选样本SFT即获强对齐 | [arXiv](https://arxiv.org/abs/2305.11206) |
| 2023-05 | P3 | Direct Preference Optimization: Your Language Model is Secretly a Reward Model | Stanford | 奖励重参数化进目标，偏好优化变监督分类损失 | [arXiv](https://arxiv.org/abs/2305.18290) · [code](https://github.com/eric-mitchell/direct-preference-optimization) |
| 2023-05 | P2 | Tree of Thoughts: Deliberate Problem Solving with Large Language Models | Princeton+DeepMind | 将推理组织为树搜索，支持分支回溯与多步前瞻 | [arXiv](https://arxiv.org/abs/2305.10601) · [code](https://github.com/princeton-nlp/tree-of-thought-llm) |
| 2023-05 | P2 | Voyager: An Open-Ended Embodied Agent with Large Language Models | NVIDIA+Caltech等 | 技能库+自动课程+迭代提示的终身学习Agent | [arXiv](https://arxiv.org/abs/2305.16291) · [code](https://github.com/MineDojo/Voyager) |
| 2023-06 | P2 | Extending Context Window of Large Language Models via Positional Interpolation | Meta | 训练时线性内插位置索引，低成本扩窗至32k | [arXiv](https://arxiv.org/abs/2306.15595) |
| 2023-06 | P2 | AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration | MIT韩松组 | 按激活分布识别保护约1%关键权重通道 | [arXiv](https://arxiv.org/abs/2306.00978) · [code](https://github.com/mit-han-lab/llm-awq) |
| 2023-06 | P2 | H2O: Heavy-Hitter Oracle for Efficient Generative Inference of Large Language Models | 斯坦福 | 重锤词元理论+KV动态驱逐，保留5%缓存近无损 | [arXiv](https://arxiv.org/abs/2306.14048) · [code](https://github.com/FMInference/H2O) |
| 2023-07 | P1 | **NTK-aware Scaled RoPE（社区方案）**「※无公开PDF」 | r/LocalLLaMA社区 | 按NTK理论非线性缩放RoPE高频维度免微调扩窗 | [外部链接](https://www.reddit.com/r/LocalLLaMA/comments/14lz7j5/) |
| 2023-07 | P2 | FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning | Princeton/Together AI | 沿序列维并行+warp级分工重排 | [arXiv](https://arxiv.org/abs/2307.08691) · [code](https://github.com/Dao-AILab/flash-attention) |
| 2023-07 | P3 | Llama 2: Open Foundation and Fine-Tuned Chat Models | Meta | 开源7B-70B基础+RLHF聊天模型，开放商用 | [arXiv](https://arxiv.org/abs/2307.09288) · [code](https://github.com/facebookresearch/llama) |

### E4 · 工程化时代：长上下文、MoE 与开源追平（2023H2–2024）

开源追平战白热化：Mixtral让开源MoE首次对标GPT-3.5，Llama 3与Qwen2.5把基座推到新高度，而DeepSeek从追赶者转变为路线输出者——DeepSeekMoE的细粒度专家、V2的MLA潜在注意力先后成为国产乃至全球开源的标准蓝本。长上下文从32k一路卷到2M（YaRN/LongLoRA/LongRoPE），vLLM的分页革命让服务吞吐提升一个量级。架构层面出现深刻反思：Mamba引发「注意力是否必要」之辩，Jamba/Mamba-2最终走向混合折中。对齐方法学上，Llama 3公开工业级后训练章节，Tülu 3更进一步开放全套数据代码并首创RLVR术语。年末两声惊雷定义了下一年的竞争维度：DeepSeek-V3以约557万美元训练成本逼近顶级闭源，o1则宣告预训练scaling放缓后，「推理时计算」成为新的扩展轴心。

| 日期 | 级别 | 论文 | 机构 | 核心贡献 | 资源 |
|---|---|---|---|---|---|
| 2023-09 | P3 | Efficient Memory Management for Large Language Model Serving with PagedAttention | UC Berkeley | KV缓存分页管理+连续批处理服务引擎vLLM | [arXiv](https://arxiv.org/abs/2309.06180) · [code](https://github.com/vllm-project/vllm) |
| 2023-09 | P2 | YaRN: Efficient Context Window Extension of Large Language Models | Nous Research等 | NTK式插值+注意力温度修正，400 token微调扩至128k | [arXiv](https://arxiv.org/abs/2309.00071) · [code](https://github.com/jquesnelle/yarn) |
| 2023-09 | P2 | LongLoRA: Efficient Fine-tuning of Long-Context Large Language Models | 上海交大等 | Shifted Sparse Attention+放宽LoRA，低成本训100k窗口 | [arXiv](https://arxiv.org/abs/2309.12307) · [code](https://github.com/dvlab-research/LongLoRA) |
| 2023-09 | P2 | Qwen Technical Report | 阿里云通义千问 | 初代中英双语1.8B-72B全尺寸开源基座 | [arXiv](https://arxiv.org/abs/2309.16609) · [code](https://github.com/QwenLM/Qwen) |
| 2023-09 | P2 | Efficient Streaming Language Models with Attention Sinks | MIT | attention sink机制让LLM稳定流式4M+超长对话 | [arXiv](https://arxiv.org/abs/2309.17453) · [code](https://github.com/mit-han-lab/streaming-llm) |
| 2023-12 | P3 | Mamba: Linear-Time Sequence Modeling with Selective State Spaces | CMU/Princeton | 选择性SSM：数据依赖参数+硬件感知扫描 | [arXiv](https://arxiv.org/abs/2312.00752) · [code](https://github.com/state-spaces/mamba) |
| 2023-12 | P2 | Gated Linear Attention Transformers with Hardware-Efficient Training | UIUC等 | 门控数据依赖遗忘的线性注意力并行化 | [arXiv](https://arxiv.org/abs/2312.06635) · [code](https://github.com/fla-org/flash-linear-attention) |
| 2023-12 | P1 | InternVL: Scaling up Vision Foundation Models and Aligning for Generic Visual-Linguistic Tasks | 上海AI实验室等 | 6B视觉编码器对齐LLM的V1系列开端 | [arXiv](https://arxiv.org/abs/2312.14238) · [code](https://github.com/OpenGVLab/InternVL) |
| 2023-12 | P2 | Gemini: A Family of Highly Capable Multimodal Models | Google DeepMind | 原生多模态预训练，超长上下文 | [arXiv](https://arxiv.org/abs/2312.11805) |
| 2024-01 | P2 | DeepSeek LLM: Scaling Open-Source Language Models with Longtermism | DeepSeek-AI | 67B稠密开源，重估缩放定律提出数据参数新配比 | [arXiv](https://arxiv.org/abs/2401.02954) · [code](https://github.com/deepseek-ai/DeepSeek-LLM) |
| 2024-01 | P2 | Mixtral of Experts | Mistral AI | 开源8专家top-2稀疏MoE大模型 | [arXiv](https://arxiv.org/abs/2401.04088) · [code](https://github.com/mistralai/mistral-src) |
| 2024-01 | P2 | DeepSeekMoE: Towards Ultimate Expert Specialization in Mixture-of-Experts Language Models | DeepSeek-AI | 细粒度专家切分+共享专家隔离双机制 | [arXiv](https://arxiv.org/abs/2401.06066) · [code](https://github.com/deepseek-ai/DeepSeek-MoE) |
| 2024-01 | P2 | EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty | 中科大+微软 | 在特征层自回归的轻量草稿头，利用目标模型特征 | [arXiv](https://arxiv.org/abs/2401.15077) · [code](https://github.com/SafeAILab/EAGLE) |
| 2024-02 | P1 | KTO: Model Alignment as Prospect Theoretic Optimization | ContextualAI/MIT | 基于前景理论，仅需二元好坏信号免配对偏好 | [arXiv](https://arxiv.org/abs/2402.01306) · [code](https://github.com/ContextualAI/HALOs) |
| 2024-02 | P3 | DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models | DeepSeek-AI | GRPO：去Critic组内相对优势估计，省显存且稳定的RL算法 | [arXiv](https://arxiv.org/abs/2402.03300) |
| 2024-02 | P2 | LongRoPE: Extending LLM Context Window Beyond 2 Million Tokens | 微软亚洲 | 非均匀维度插值+进化搜索，三阶段扩至2048k | [arXiv](https://arxiv.org/abs/2402.13753) · [code](https://github.com/microsoft/LongRoPE) |
| 2024-03 | P2 | Jamba: A Hybrid Transformer-Mamba Language Model | AI21 Labs | Mamba-Attention-MoE层间混合生产级架构 | [arXiv](https://arxiv.org/abs/2403.19887) · [code](https://github.com/ai21labs/Jamba) |
| 2024-05 | P2 | Transformers are SSMs: Generalized Models and Efficient Algorithms Through Structured State Space Duality | Princeton/CMU | SSD框架统一SSM与线性注意力对偶视角 | [arXiv](https://arxiv.org/abs/2405.21060) · [code](https://github.com/state-spaces/mamba) |
| 2024-05 | P3 | DeepSeek-V2: A Strong, Economical, and Efficient Mixture-of-Experts Language Model | DeepSeek-AI | 多头潜在注意力MLA：KV压入低秩潜向量 | [arXiv](https://arxiv.org/abs/2405.04434) · [code](https://github.com/deepseek-ai/DeepSeek-V2) |
| 2024-06 | P2 | DeepSeek-Coder-V2: Breaking the Barrier of Closed-Source Models in Code Intelligence | DeepSeek-AI | 236B MoE代码模型(21B激活)，338语言128K上下文 | [arXiv](https://arxiv.org/abs/2406.11931) · [code](https://github.com/deepseek-ai/DeepSeek-Coder-V2) |
| 2024-06 | P1 | ChatGLM: A Family of Large Language Models from GLM-130B to GLM-4 All Tools | 智谱AI×清华 | GLM对话系三代演进与全工具能力总结 | [arXiv](https://arxiv.org/abs/2406.12793) |
| 2024-06 | P2 | The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale | HuggingFace | 15T开放语料+全程消融清洗流水线，FineWeb-Edu质量分级 | [arXiv](https://arxiv.org/abs/2406.17557) · [code](https://github.com/huggingface/datatrove) |
| 2024-07 | P2 | Qwen2 Technical Report | 阿里云通义千问 | 0.5B-72B全谱系升级，57B-A14B MoE首秀 | [arXiv](https://arxiv.org/abs/2407.10671) · [code](https://github.com/QwenLM/Qwen2) |
| 2024-07 | P2 | FlashAttention-3: Fast and Accurate Attention with Asynchrony and Low-precision | Together AI/Princeton等 | Hopper异步流水(warp专用/tma)+FP8量化 | [arXiv](https://arxiv.org/abs/2407.08608) · [code](https://github.com/Dao-AILab/flash-attention/tree/hopper) |
| 2024-07 | P3 | The Llama 3 Herd of Models | Meta | 系统化后训练：SFT+拒绝采样+DPO多轮迭代 | [arXiv](https://arxiv.org/abs/2407.21783) · [code](https://github.com/meta-llama/llama3) |
| 2024-08 | P3 | Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters | OpenAI/UMD | 测试时计算可更高效，小模型+test-time超14x大模型 | [arXiv](https://arxiv.org/abs/2408.03314) |
| 2024-09 | P3 | **Learning to Reason with LLMs (OpenAI o1)**「※无公开PDF」 | OpenAI | 官方宣告大规模RL驱动长思维链范式，o1首秀 | [外部链接](https://openai.com/index/learning-to-reason-with-llms/) |
| 2024-11 | P2 | Scaling Laws for Precision | Harvard/MIT/Stanford/Databricks | 精度感知scaling law：低精度训练折损有效参数量 | [arXiv](https://arxiv.org/abs/2411.04330) |
| 2024-11 | P2 | Tülu 3: Pushing Frontiers in Open Language Model Post-Training | AI2 | 全开放SFT+DPO+RLVR三阶段配方与数据，首创RLVR术语 | [arXiv](https://arxiv.org/abs/2411.15124) · [code](https://github.com/allenai/open-instruct) |
| 2024-12 | P1 | DeepSeek-VL2: Mixture-of-Experts Vision-Language Models for Advanced Multimodal Understanding | DeepSeek-AI | MoE稀疏VLM家族，动态分辨率切片视觉编码 | [arXiv](https://arxiv.org/abs/2412.10302) · [code](https://github.com/deepseek-ai/DeepSeek-VL2) |
| 2024-12 | P2 | Qwen2.5 Technical Report | 阿里云通义千问 | 18T token预训练，Math/Coder专项衍生最丰富 | [arXiv](https://arxiv.org/abs/2412.15115) · [code](https://github.com/QwenLM/Qwen2.5) |
| 2024-12 | P3 | DeepSeek-V3 Technical Report | DeepSeek-AI | 无辅助损失负载均衡+MTP+FP8训练的671B细粒度MoE | [arXiv](https://arxiv.org/abs/2412.19437) · [code](https://github.com/deepseek-ai/DeepSeek-V3) |

### E5 · 推理与Agent时代：o1时刻之后（2025–2026）

R1用纯强化学习复现o1并登上Nature封面，「GRPO+可验证奖励（RLVR）」一夜之间成为行业标配；s1和QwQ证明小团队小成本也能上桌。竞争轴心随之从「模型有多聪明」转向「能连续干多久」：Kimi以K2的万亿参数MuonClip零尖峰训练起步，K2.5引入Agent Swarm并行编排，K3更以2.8T参数刷新开源规模上限并凭KDA线性注意力首次在编程对决中登顶胜过闭源；DeepSeek线从V3.2的DSA token级稀疏走到V4的CSA+HCA混合注意力与FP4量化感知训练，把百万token推理链的成本压到原来的几分之一；最激进的多模态想法来自《Thinking with Visual Primitives》——提出Reference Gap，把边界框与空间点变成思维链的最小单位。GLM线以GLM-4.5的slime异步RL基建奠基，GLM-5确立「DSA+异步Agentic RL」范式后经5.1/5.2快速迭代出Solid 1M长程能力；Qwen则以Qwen3.5的397B-A17B门控DeltaNet线性注意力和Omni全模态推进原生多模态智能体。闭源侧，GPT-5系统卡把「旗舰」重定义为快慢模型路由系统，Gemini 2.5普及思考预算，Claude Opus 4.5率先突破SWE-bench 80%。MiniMax M2系列押注小激活高效率路线，字节Seed从开源中尺寸走向单体Agent。至2026年年中，前沿竞争收敛于三条主轴：稀疏/线性注意力的效率革命、agentic RL的工程基建、多模态推理的原语化。

| 日期 | 级别 | 论文 | 机构 | 核心贡献 | 资源 |
|---|---|---|---|---|---|
| 2025-01 | P2 | UI-TARS: Pioneering Automated GUI Interaction with Native Agents | 字节跳动Seed | 纯视觉GUI Agent，截图进动作出免系统层API | [arXiv](https://arxiv.org/abs/2501.12326) · [code](https://github.com/bytedance/UI-TARS) |
| 2025-01 | P2 | MiniMax-01: Scaling Foundation Models with Lightning Attention | MiniMax | 456B-A45.9B闪电注意力混合MoE，原生1M上下文 | [arXiv](https://arxiv.org/abs/2501.08313) · [code](https://github.com/MiniMax-AI/MiniMax-01) |
| 2025-01 | P2 | Kimi k1.5: Scaling Reinforcement Learning with LLMs | Moonshot AI | 长短链联合RL与long2short，非MoE达o1级 | [arXiv](https://arxiv.org/abs/2501.12599) |
| 2025-01 | P3 | DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning | DeepSeek-AI | 纯RL涌现长CoT反思验证，GRPO+规则可验证奖励 | [arXiv](https://arxiv.org/abs/2501.12948) · [code](https://github.com/deepseek-ai/DeepSeek-R1) |
| 2025-01 | P2 | s1: Simple test-time scaling | Stanford+UW+AI2 | 1000样本SFT+budget forcing，最小代价复现o1测试时扩展曲线 | [arXiv](https://arxiv.org/abs/2501.19393) · [code](https://github.com/simplescaling/s1) |
| 2025-02 | P2 | Native Sparse Attention: Hardware-Aligned and Natively Trainable Sparse Attention | DeepSeek-AI+北大/UW | 压缩+选择+滑窗三分支原生可训练稀疏注意力 | [arXiv](https://arxiv.org/abs/2502.11089) · [code](https://github.com/deepseek-ai/NSA) |
| 2025-02 | P2 | MoBA: Mixture of Block Attention for Long-Context LLMs | Moonshot AI+清华 | 块级top-k门控路由，把MoE思想引入注意力 | [arXiv](https://arxiv.org/abs/2502.13189) · [code](https://github.com/MoonshotAI/MoBA) |
| 2025-02 | P1 | Qwen2.5-VL Technical Report | 阿里Qwen团队 | 原生动态分辨率+文档解析+GUI Agent能力 | [arXiv](https://arxiv.org/abs/2502.13923) · [code](https://github.com/QwenLM/Qwen2.5-VL) |
| 2025-03 | P1 | **QwQ-32B: Embracing the Power of Reinforcement Learning**「※无公开PDF」 | 阿里Qwen团队 | 官方博客：32B两阶段RL(规则验证器+通用RM)逼近R1并集成工具调用 | [外部链接](https://qwenlm.github.io/blog/qwq-32b/) |
| 2025-03 | P1 | Towards Reasoning Era: A Survey of Long Chain-of-Thought | 哈工大/中南/HKU/复旦 | Long CoT首个系统综述：分类法+overthinking/test-time scaling梳理 | [arXiv](https://arxiv.org/abs/2503.09567) · [code](https://github.com/LightChen233/Awesome-Long-Chain-of-Thought-Reasoning) |
| 2025-04 | P2 | **The Llama 4 Herd (Scout/Maverick)**「※无公开PDF」 | Meta | iRoPE交错位置编码原生10M上下文，MoE原生多模态 | [外部链接](https://llama.meta.com) |
| 2025-05 | P2 | Qwen3 Technical Report | 阿里通义 | 128K上下文，MoE+稠密多尺寸，思考模式 | [arXiv](https://arxiv.org/abs/2505.09388) · [code](https://github.com/QwenLM/Qwen3) |
| 2025-06 | P2 | MiniMax-M1: Scaling Test-Time Compute Efficiently with Lightning Attention | MiniMax | 首个开源混合注意力推理模型，CISPO算法80K思考预算 | [arXiv](https://arxiv.org/abs/2506.13585) · [code](https://github.com/MiniMax-AI/MiniMax-M1) |
| 2025-06 | P2 | **Gemini 2.5 Technical Report**「※无公开PDF」 | Google DeepMind | 思考预算+原生多模态+1M上下文全档家族 | [外部链接](https://storage.googleapis.com/deepmind-media/gemini/gemini_v2_5_report.pdf) |
| 2025-07 | P3 | Kimi K2: Open Agentic Intelligence | Moonshot AI | 1.04T总参32B激活MoE，MuonClip优化器+agentic数据合成 | [arXiv](https://arxiv.org/abs/2507.20534) · [code](https://github.com/MoonshotAI/Kimi-K2) |
| 2025-08 | P3 | GLM-4.5: Agentic, Reasoning, and Coding (ARC) Foundation Models | Z.ai/智谱 | 专家迭代+slime异步解耦RL基建的agentic后训练 | [arXiv](https://arxiv.org/abs/2508.06471) · [code](https://github.com/zai-org/GLM-4.5) |
| 2025-08 | P2 | GPT-5 System Card | OpenAI | 快慢模型+实时路由统一系统，safe-completions安全训练 | [arXiv](https://arxiv.org/abs/2601.03267) |
| 2025-08 | P2 | **Seed-OSS-36B Open Source Models**「※无公开PDF」 | 字节跳动Seed | 12T token 36B开源，512K原生长上下文 | [外部链接](https://github.com/ByteDance-Seed/seed-oss) |
| 2025-09 | P1 | WebExplorer: Explore Progressive Web Information Acquisition | MiniMax | 长程信息搜索Agent数据管线与框架 | [arXiv](https://arxiv.org/abs/2509.06501) |
| 2025-09 | P2 | HunyuanImage 3.0: Unified Multimodal Understanding and Generation | 腾讯混元 | 原生多模态自回归统一理解+生成，MoE图像生成+原生CoT | [arXiv](https://arxiv.org/abs/2509.23951) · [code](https://github.com/Tencent-Hunyuan) |
| 2025-10 | P3 | DeepSeek-OCR: Contexts Optical Compression | DeepSeek-AI | 视觉压缩原语：长文本转图像实现上下文光学压缩 | [arXiv](https://arxiv.org/abs/2510.18234) · [code](https://github.com/deepseek-ai/DeepSeek-OCR) |
| 2025-10 | P2 | Kimi Linear: An Expressive, Efficient Attention Architecture | Moonshot AI | KDA(Kimi Delta Attention)线性混合架构 | [arXiv](https://arxiv.org/abs/2510.26692) |
| 2025-11 | P2 | **Kimi K2 Thinking（技术博客/模型发布）**「※无公开PDF」 | Moonshot AI | 思考-行动交错推理，连续两百余步工具调用，原生INT4 | [外部链接](https://moonshotai.github.io/Kimi-K2/thinking.html) |
| 2025-11 | P2 | **System Card: Claude Opus 4.5**「※无公开PDF」 | Anthropic | SWE-bench首破80%，ARC-AGI-2 37.6% | [外部链接](https://www.anthropic.com/claude-opus-4-5-system-card) |
| 2025-12 | P2 | DeepSeek-V3.2: Pushing the Frontier of Open Large Language Models (DSA) | DeepSeek-AI | DSA：lightning索引器+细粒度top-k token选择 | [arXiv](https://arxiv.org/abs/2512.02556) · [code](https://huggingface.co/deepseek-ai/DeepSeek-V3.2-Exp) |
| 2026-02 | P3 | GLM-5: from Vibe Coding to Agentic Engineering | Z.ai/智谱 | 744B-A40B MoE，引入DSA稀疏注意力+异步Agent RL | [arXiv](https://arxiv.org/abs/2602.15763) |
| 2026-02 | P2 | Kimi K2.5: Visual Agentic Intelligence | Moonshot AI | 文视联合训练+Agent Swarm并行编排(PARL) | [arXiv](https://arxiv.org/abs/2602.02276) · [code](https://huggingface.co/moonshotai/Kimi-K2.5) |
| 2026-02 | P2 | **Qwen3.5: Towards Native Multimodal Agents**「※无公开PDF」 | 阿里通义 | Gated DeltaNet线性注意力+稀疏MoE 397B-A17B原生多模态智能体旗舰 | [外部链接](https://qwen.ai/blog?id=qwen3.5) |
| 2026-02 | P2 | **Forge: Scalable Agent RL Framework and CISPO**「※无公开PDF」 | MiniMax | 白盒黑盒Agent统一RL环+CISPO复合奖励 | [外部链接](https://www.minimax.io/news/forge-scalable-agent-rl-framework-and-algorithm) |
| 2026-03 | P1 | IndexShare: Sharing the Indexer of Sparse Attention | 智谱 | DSA索引器每4层共享一次 | [arXiv](https://arxiv.org/abs/2603.12201) |
| 2026-03 | P2 | Seed1.8 Model Card | 字节跳动Seed | 搜索/GUI/视频工具统一单体Agent | [arXiv](https://arxiv.org/abs/2603.20633) |
| 2026-04 | P3 | **Thinking with Visual Primitives**「※无公开PDF」 | DeepSeek-AI+北大+清华 | 点框空间标记作为最小思维单位嵌入CoT，弥合Reference Gap；CSA视觉KV压缩7056倍 | [外部链接](https://github.com/deepseek-ai/Thinking-with-Visual-Primitives) |
| 2026-04 | P1 | **GLM-5.1（迭代版，无独立技术报告）**「※无公开PDF」 | 智谱Z.ai | SWE-Bench Pro 58.4全球最佳，长程8小时闭环 | [外部链接](https://docs.bigmodel.cn/cn/guide/models/text/glm-5.1) |
| 2026-04 | P3 | DeepSeek-V4 Technical Report (Pro/Flash) | DeepSeek-AI | CSA+HCA混合注意力+mHC超连接+Muon优化器+FP4量化感知训练，1M上下文 | [arXiv](https://arxiv.org/abs/2606.19348) · [code](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) |
| 2026-04 | P2 | Qwen3.5-Omni Technical Report | 阿里通义 | Thinker/Talker双MoE+ARIA文语流对齐，全模态实时交互 | [arXiv](https://arxiv.org/abs/2604.15804) |
| 2026-04 | P1 | **Qwen3.6 (35B-A3B)**「※无公开PDF」 | 阿里通义 | 小激活开源Agentic Coding钢炮 | [外部链接](https://qwen.ai/blog?id=qwen3.6-35b-a3b) |
| 2026-04 | P1 | **Manifold-Constrained Hyper-Connections (mHC)**「※无公开PDF」 | DeepSeek-AI | 流形约束的超连接升级残差结构，随V4报告发表 | [外部链接](https://arxiv.org/abs/2606.19348) |
| 2026-05 | P2 | The MiniMax-M2 Series Technical Report | MiniMax | 230B总参/A10B激活极致轻旗舰系列+Forge大规模Agent RL | [arXiv](https://arxiv.org/abs/2605.26494) · [code](https://huggingface.co/MiniMaxAI/MiniMax-M2.5) |
| 2026-06 | P2 | **GLM-5.2: Built for Long-Horizon Tasks**「※无公开PDF」 | 智谱Z.ai | IndexShare/KVShare改进DSA，Solid 1M无损上下文，critic-based PPO | [外部链接](https://z.ai/blog/glm-5.2) |
| 2026-06 | P2 | Seed 2.0 Model Card | 字节跳动Seed | 长尾知识+复杂指令遵循系统性增强 | [arXiv](https://arxiv.org/abs/2607.00248) |
| 2026-07 | P3 | Kimi K3: Open Frontier Intelligence | Moonshot AI | 2.8T总参/104B激活首个开源3T级，KDA+AttnRes+MoonClip二阶优化器 | [arXiv](https://arxiv.org/abs/2607.24653) · [code](https://huggingface.co/moonshotai/Kimi-K3) |
| 2026-08 | P2 | **Qwen3.8-Max: A New Bar for Coding and Cowork**「※无公开PDF」 | 阿里通义 | 编程与协同办公新旗舰；宣布开源 Max 本尊(2.4T总参/A95B激活) | [外部链接](https://qwen.ai/blog?id=qwen3.8) |
| 2026-08 | P2 | **GLM-5.3：Frontier Foundation Model（文本旗舰）**「※无公开PDF」 | 智谱Z.ai | 基座同GLM-5.2、能力全来自后训练：SAO结合上下文压缩的RL+端到端环境合成流水线，强制思考档位 | [外部链接](https://z.ai/blog/glm-5.3) |
| 2026-08 | P2 | **GLM-5.3-Flash（ox-alpha/牛来，原生多模态低延迟版）**「※无公开PDF」 | 智谱Z.ai | 320B/18B激活、45层原生多模态(text+image+video)，首个稀疏注意力+线性注意力混合开源前沿模型(linear局部递归+DSA/IndexShare全局索引+mHC流形超连接+IndexPool索引缓存压缩)，1M上下文，INT4/fp8，MIT | [外部链接](https://z.ai/blog/glm-5.3-flash) |

## 附录·数据口径

- `conf=verified`（本轮联网一手核验）：**100** 篇——标题、机构、日期、链接均经 arXiv/官网实时核对。
- `conf=cited`（高置信知识库条目）：**33** 篇——来自权威综述与知识库交叉印证，未逐条回源。
- 统计口径与 `data/papers_master.json` 完全一致，本 README 由脚本生成，勿手改。
