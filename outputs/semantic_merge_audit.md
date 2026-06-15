# Semantic Merge Audit

Generated: 2026-06-15

## Existing Capabilities

- **Schema** (`semantic_merge_schema.py`): 完整。包含 `SemanticMergeJudgment`、`HumanExceptionItem`、`AIReviewedClusterGroup`、`SemanticMergeHumanAudit` 四个 Pydantic v2 模型；字段验证、中文校验、confidence gate 约束均已实现。
- **RuleBasedSemanticMergeJudge** (`semantic_merge_judge.py`): 已实现，可离线运行，不调用外部 API；根据字段相似度分数、persona 重叠、domain 重叠、workflow_family 判断 confirm/reject/maybe。
- **Confidence Gate** (`exception_queue.py`): 已实现 `determine_auto_action`、`should_enter_exception_queue`、`build_exception_item`、`exception_priority`；auto_confirm / auto_reject / human_exception 三路分流逻辑完整。
- **SemanticMergeGateConfig** (`exception_queue.py`): 支持 `auto_confirm_threshold`、`auto_reject_threshold`、`human_review_threshold` 及 `require_*` 开关。
- **Store** (`semantic_merge_store.py`): 已实现读写 judgments / exception_queue / ai_reviewed_groups / human_audits；connected components 构建 AI reviewed groups 逻辑完整。
- **Reports** (`semantic_merge_report.py`): 已实现 `build_semantic_merge_report`、`build_human_exception_report`、`build_ai_reviewed_groups_report`；对应三份 `.md` 文件及 `run_summary.json` 合并。
- **CLI**: 已有 `semantic-merge-judge`、`build-ai-reviewed-groups`、`build-semantic-merge-report`、`build-human-exception-report`、`run-stage27` 五条命令。
- **Stage 3 readiness**: `batch_summary.py` 已使用 `effective_reviewed_groups = ai_reviewed_groups + human_reviewed_groups`；readiness 条件已包含 `exception_rate_ok` 和 `auto_confirmed_groups_ok`；已部分实现 Stage 2.8 的 readiness 逻辑。
- **Config**: `configs/semantic_merge_config.yaml` 已存在，含 `enabled`、`mode`、阈值、`conflict_flags`、`output` 字段。

## Missing Capabilities

1. **LLM mode 实现缺失**: `semantic_merge_config.yaml` 只有 `mode: rule_based_stub`；代码中没有真实 LLM judge 实现（无 `LLMSemanticMergeJudge` 类）；`judge_mode` 字段仅为 `rule_based_stub`，无法切换到 `llm` 模式。
2. **Config 字段不完整**: `semantic_merge_config.yaml` 缺少 `llm`（provider / model / base_url_env / api_key_env / timeout_seconds / max_retries / temperature）和 `batch`（max_candidates_per_run / cache_enabled）子块；`thresholds` 节结构也缺失。
3. **`run-stage28` 命令缺失**: 现有最高阶段命令是 `run-stage27`；任务说明要求新增 `run-stage28` 作为 Stage 2.8 主入口。
4. **Review UI 缺少 AI 合并判断 Tab 和人工异常队列 Tab**: 当前 UI 有 4 个 Tab（痛点校准 / 需求主题候选 / 合并建议审核 / 批次总览），缺少展示 `semantic_merge_judgments` 和 `human_exception_queue` 的独立 Tab 及对应交互按钮。
5. **`ui_batch_filter_service.py` 未覆盖 semantic merge 数据**: UI 的 batch 筛选服务不含 AI 判断和异常队列条目。
6. **测试覆盖不足**: `tests/` 目录中无 semantic_merge 相关测试文件；任务说明要求补齐 9 个测试文件。
7. **README 未含 Stage 2.8 说明**: 当前 README 最高描述至 Stage 2.6，缺少 Stage 2.8 章节。
8. **`semantic_merge_audit.md` 本身尚未生成** (本文件即为初始版本，由代码审计生成)。

## Recommended Implementation Path

1. **补全 `semantic_merge_config.yaml`**: 添加 `llm`、`thresholds`、`batch` 节；保持 `mode: rule_based_stub` 为默认。
2. **实现 `LLMSemanticMergeJudge`**: 在 `semantic_merge_judge.py` 中添加真实 LLM 调用分支，读取环境变量 `DEMAND_RADAR_LLM_BASE_URL` / `DEMAND_RADAR_LLM_API_KEY`；失败时自动降级到 human_exception，不中断流程；提供 `FakeLLMJudge` 用于测试。
3. **添加 `run-stage28` CLI 命令**: 完整链路 run-stage26 → suggest-merges → semantic-merge-judge → build-ai-reviewed-groups → build-semantic-merge-report → build-human-exception-report → build-batch-summary。
4. **扩展 Review UI**: 添加「AI 合并判断」和「人工异常队列」两个 Tab；异常队列 Tab 提供确认合并 / 拒绝合并 / 标记 AI 理由不好 / 暂不处理 / 需要重跑五个按钮，写入 `semantic_merge_human_audits.jsonl`。
5. **补齐测试**: 新增 9 个测试文件覆盖 schema、judge、gate、store、groups、exception queue、stage28 CLI 等模块。
6. **更新 README**: 新增 Stage 2.8 节，说明设计原则、配置方式、运行命令、readiness 计算方式。

## Compatibility Risks

- **不覆盖原始数据**: `demand_clusters.jsonl` 和 `cluster_merge_candidates.jsonl` 均只读，semantic merge 只生成新文件，无风险。
- **旧测试**: Stage 1-2.6 测试不依赖 semantic merge 模块，新增 LLM judge 分支不影响旧逻辑。
- **`run-stage27` 保留**: `run-stage28` 新增，不替换 `run-stage27`，向后兼容。
- **UI Tab 顺序**: 新增两个 Tab 时需注意 `st.tabs()` 解构变量数量与现有代码的对齐。
- **rule_based_stub 目标可达性**: 在当前 80 条样本、102 个 merge candidates 上，rule_based_stub 的 auto_confirm 数量依赖字段相似度分数分布；如果高相似度候选不足 8 条，需在报告中说明需要真实 LLM mode，而不是强行调低阈值。
