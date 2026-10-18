# Phase 5 — Rules/Gemini Baselines and Evaluation Plumbing

> Implementation status (2026-10-17): **Complete for local/offline scope.** Shared
> provider/evaluation contracts, fairness guards, metrics, and JSON/CSV artifacts are
> implemented. Focused verification: **12 tests passed**; measured Rules run: **6/6
> exact classifications, 0 unsafe escapes**. Live Gemini/System One runs require credentials.

**Owner:** Yizhe（shared plumbing / fairness / persistence）；Anish（RulesProvider、Gemini baseline、metrics/eval scripts）  
**Depends on:** Phases 2–4  
**Primary output:** Rules、LLM、System One 在相同 inputs/policy 下的可重现真实评估

## 1. 目标

建立 apples-to-apples benchmark，回答：在给定最大 unsafe escape/error threshold 下，多少合法 action 可以自动执行？

评价 System One 的正确方式是整体 safety/coverage/latency/cost/calibration tradeoff，而不是预设它必须在 accuracy 上获胜。

## 2. 建议文件

```text
backend/app/providers/
  rules.py
  gemini.py
  registry.py
backend/app/services/
  metrics.py
  evaluation_runner.py
evaluation/
  run_eval.py
  metrics.py
  manifests/
  results/
backend/tests/
  test_rules_provider.py
  test_gemini_provider.py
  test_evaluation_fairness.py
  test_metrics.py
  test_result_serialization.py
```

## 3. Shared evaluation contract

每一条 evaluation case 固定：

- scenario ID/version
- source record lineage
- expected final action / risk flags
- serialized `AccountingState`
- `AccountingState` hash
- policy config version/hash
- provider name/version
- run ID and timestamp

Runner 只替换 provider：

```text
same AccountingState
  -> RulesProvider / GeminiBaselineProvider / SystemOneProvider
  -> same RiskAssessment schema
  -> same PolicyEngine
  -> comparable PolicyDecision
```

## 4. RulesProvider

RulesProvider 输出同一 `RiskAssessment`，但必须清楚区分：

- deterministic heuristic score
- confidence semantics
- hard pre-check facts（不重复冒充 model signal）

Rules 不应通过 scenario label、`sim_obligation_id` 或 hero vendor 特例作弊。

其目标是可信 baseline，不是故意做弱。

## 5. GeminiBaselineProvider

使用 Gemini `generateContent` 的 structured JSON output，并保持简单：

- 输入同一 `AccountingState`。
- 输出同一 `RiskAssessment`。
- 使用明确 schema validation。
- provider failure 使用同一 fail-safe pathway。
- prompt 不含 PolicyEngine threshold/final answer。
- 记录 model、真实 latency、token/cost（仅在能可靠测量时）。

如果 cost 无法可靠获得，结果标为 unavailable，不能估一个假数字。

## 6. Metrics

Primary：

- Safe Autonomous Execution Coverage

Additional：

- Unsafe Action Escape Rate
- Dangerous Action Prevention Rate
- Human Review Rate
- Accuracy
- Precision / Recall / F1 where meaningful
- p50 / p95 latency
- provider failure rate
- calibration / confidence bucket accuracy（样本足够时）
- measured/traceable cost per 1K actions（可用时）

需要先写清楚 label-to-safe/unsafe 和 predicted decision-to-escape 的数学定义，避免把 `REQUIRE_APPROVAL` 当作错误或成功随意切换。

## 7. Coverage-at-risk analysis

主图/主表应评估不同 confidence/policy thresholds 下：

```text
x-axis: unsafe escape/error rate
y-axis: safe autonomous execution coverage
```

Threshold sweep 必须重新通过同一 PolicyEngine/config variant 计算，不能只后处理挑最好看的点。

## 8. Latency methodology

分别记录：

- ContextBuilder latency
- provider network/model latency
- PolicyEngine latency
- end-to-end latency

报告：

- sample size
- cold vs warm definition
- retry inclusion
- p50/p95 calculation
- failed calls handling
- machine/environment notes

Mock/fake latency 不进入最终结果。

## 9. Result artifacts

每次 run 输出：

- JSON run manifest
- per-case CSV/JSONL
- aggregate metrics JSON/CSV
- error/failure summary
- config and input hashes

结果文件名包含 run ID/provider/date；不要覆盖过去的真实 run。未运行时 benchmark endpoint 应返回 no-results 状态，而不是 placeholder numbers。

## 10. Fairness guards

Runner 自动断言：

- 所有 provider 的 case IDs 相同。
- state hash 相同。
- labels 相同。
- policy config hash 相同。
- action space 相同。
- no provider-specific hidden context。
- input order/seeding 记录清楚。

若任一 guard 失败，整个 run 标为 invalid，不生成 headline comparison。

## 11. Testing checklist

### Provider contracts

- [ ] Rules 和 LLM 都返回 schema-valid RiskAssessment。
- [ ] malformed structured LLM output fail safe。
- [ ] provider-specific metadata 不改变 common signal semantics。

### Metric unit tests

用手工小矩阵验证：

- [ ] accuracy/precision/recall/F1。
- [ ] unsafe escape rate。
- [ ] dangerous prevention rate。
- [ ] human review rate。
- [ ] safe autonomous coverage。
- [ ] percentile latency。
- [ ] empty class/zero denominator behavior。

### Fairness tests

- [ ] state hash mismatch 会中止 run。
- [ ] label mismatch 会中止 run。
- [ ] policy config mismatch 会中止 run。
- [ ] provider 看不到 expected labels/sim truth。
- [ ] failed call 不被悄悄从 denominator 删除。

### Output tests

- [ ] JSON/CSV schema 稳定。
- [ ] run manifest 包含 sample size/model/config hashes。
- [ ] 不存在 NaN/Infinity 等非标准 JSON。
- [ ] 无 benchmark 时不返回 fabricated defaults。

## 12. Exit criteria

- 所有 provider 可在同一 case set 上运行。
- fairness guards 强制执行。
- metrics 有手工 fixture unit tests。
- results 可重现并输出 JSON/CSV。
- latency 和 cost 只来自实际测量。
- mixed/negative results 也能如实呈现。

