# Phase 4 — Scenario Integration and Deterministic PolicyEngine

> Implementation status (2026-10-17): **Complete.** Centralized immutable policy,
> deterministic prechecks, six traceable scenarios, fail-safe provider handling, and
> audit hashes are implemented. Focused verification: **17 tests passed**.

**Owner:** Yizhe（PolicyEngine / integration）；Anish（scenario generation / labels）  
**Depends on:** Phase 1 contracts、Phase 2 context、Phase 3 provider error model  
**Primary output:** 可审计、可配置、与 scenario ID 无关的最终授权决策

## 1. 目标

建立 deterministic PolicyEngine，将 hard facts、provider risk signals 和 confidence 映射成：

- `ALLOW`
- `REQUIRE_APPROVAL`
- `REQUEST_CONTEXT`
- `BLOCK`

同时把从真实 sponsor records 派生的 scenario 接入同一 pipeline，证明 engine 不依赖 demo-specific hardcoding。

## 2. 责任边界

Yizhe：

- `PolicyConfig`
- deterministic pre-checks
- `PolicyEngine`
- reason codes / triggered thresholds
- provider failure fallback
- audit-ready `PolicyDecision`
- scenario loader/validator integration

Anish：

- scenario selection/generation
- expected labels/risk flags
- modification documentation
- scenario realism review

共同：

- threshold tuning methodology
- hero scenarios acceptance
- policy/evaluation contract

## 3. 建议文件

```text
backend/app/
  policy/
    config.py
    prechecks.py
    engine.py
    reasons.py
  services/
    scenario_generator.py
    scenario_loader.py
    audit.py
backend/tests/
  test_prechecks.py
  test_policy_engine.py
  test_scenarios.py
  test_execution_authority.py
data/scenarios/
  scenarios.jsonl
```

## 4. PolicyConfig

集中定义并 version：

- absolute amount hard limit
- supported currencies
- duplicate block threshold
- counterparty/destination review threshold
- missing-context threshold
- anomaly review threshold（若启用）
- minimum required confidence
- required signals by action type
- provider failure fallback

禁止 threshold 散落在 routes、graph nodes、prompts 或 scenario files 中。

配置加载后应 immutable；audit 保存 config version/hash，而不是只保存“用了默认值”。

## 5. Deterministic pre-checks

在 provider 前检查：

- malformed/missing required fields
- unsupported action type/currency
- invalid/non-positive amount where action requires payment
- cross-company references
- exact source-document/application duplicate
- hard payment/account constraints
- impossible/unknown account references

Pre-check 输出结构化 facts/reason codes，不直接复用 free-form text。

对于明确 hard violation，可以跳过 semantic provider 并 `BLOCK`；跳过原因必须 audit。

## 6. Policy evaluation order

建议固定顺序：

```text
hard violation                         -> BLOCK
duplicate risk >= block threshold      -> BLOCK
counterparty/destination risk >= review-> REQUIRE_APPROVAL
missing context >= threshold           -> REQUEST_CONTEXT
required confidence < minimum          -> REQUIRE_APPROVAL
provider failure                       -> REQUIRE_APPROVAL or BLOCK
otherwise                              -> ALLOW
```

优先级本身是 policy contract。每个 decision 记录：

- evaluated rules in order
- actual signal/value
- threshold/comparator
- winning rule
- reason codes
- provider and assessment reference
- `audit_id`

## 7. Provider failure policy

不要伪造 RiskAssessment。PolicyEngine 接收明确的 provider outcome union：success 或 typed failure。

默认：

- 需要 semantic judgment 的 action -> `REQUIRE_APPROVAL`
- malformed action/hard policy violation -> `BLOCK`
- 如果 provider 不需要被调用且 hard facts 足够 -> 按 deterministic policy 处理

失败原因必须显示为 `PROVIDER_TIMEOUT`、`PROVIDER_UNAVAILABLE`、`INVALID_PROVIDER_RESPONSE` 等，而不是泛化成 low confidence。

## 8. Scenario model

每个 scenario：

- `scenario_id`
- `scenario_type`
- `source_company_id`
- `source_record_ids`
- `original_data`
- `modifications`
- `modification_reason`
- `synthetic_fields`
- `expected_action`
- `expected_risk_flags`
- schema/version

MVP：

1. `SAFE_NORMAL_PAYMENT`
2. `SEMANTIC_DUPLICATE`
3. `PAYMENT_DESTINATION_CHANGE`
4. `MISSING_CONTEXT`
5. `ACTION_GOAL_MISMATCH`
6. `HIGH_AMOUNT_BUT_PLAUSIBLE`

要求：

- 尽可能从真实 bill/vendor/history 派生。
- destination-change 明确标记 synthetic，因为原数据没有 vendor bank destination。
- scenario file 不能携带 provider 应看不到的 expected label 到 `AccountingState`。
- `sim_obligation_id` 可辅助 lineage/label construction，但必须从 inference view 删除。

## 9. 禁止做法

```python
if scenario_id == "semantic_duplicate_1":
    return FinalAction.BLOCK
```

同样禁止：

- 把 expected action 放入 prompt/context。
- 针对 hero vendor 名称写特例。
- 为了让 demo 通过直接修改 provider score。
- 根据 mock provider 名称改变 threshold。

## 10. Testing checklist

### Pre-checks

- [ ] unsupported currency、malformed reference、hard limit 正确 block。
- [ ] exact company-scoped duplicate 正确识别。
- [ ] 同 ID 不同 company 不会误判。
- [ ] 无 hard violation 时保留完整 facts 给后续 context/provider。

### Threshold boundaries

每个 threshold 测试：

- [ ] just below
- [ ] exactly equal
- [ ] just above

同时测试多信号冲突时固定优先级，例如 duplicate block 应优先于 missing-context request。

### Confidence and failures

- [ ] 低于 minimum confidence -> approval。
- [ ] exactly minimum 的 inclusive/exclusive semantics 明确。
- [ ] timeout/unavailable/malformed response 不允许自动执行。
- [ ] provider failure reason code 和 audit data 正确。

### Scenarios

- [ ] 每个 scenario source IDs 在真实 dataset 中存在。
- [ ] modifications 与 original data 可 diff。
- [ ] synthetic fields 全部披露。
- [ ] labels 不进入 inference view。
- [ ] scenario schema/version validation。
- [ ] 重新生成 deterministic（固定 seed 时）。

### Authority invariant

- [ ] `BLOCK` 无法执行。
- [ ] `REQUEST_CONTEXT` 无法执行。
- [ ] 未人工解决的 `REQUIRE_APPROVAL` 无法执行。
- [ ] 只有 `ALLOW` 或已记录的显式人工批准能进入 simulated execution。

## 11. Exit criteria

- PolicyEngine 不依赖 provider implementation 或 scenario ID。
- 所有 thresholds 集中、versioned、有 boundary tests。
- 六类 MVP scenarios 可追溯到真实 records。
- provider failure path fail safe。
- 全局 execution authority test 通过。
- decision 包含 reason codes、triggered thresholds、provider、risk reference 和 audit ID。

