# Phase 2 — Context Builder and Candidate Retrieval

> Implementation status (2026-10-17): **Complete.** Implemented in
> `backend/app/services/` with a company-scoped normalized store; 9 focused tests plus the Phase 1
> regression suite pass.

**Owner:** Yizhe  
**Depends on:** Phase 1 contracts and normalized data  
**Primary output:** provider-neutral、compact、deterministic `AccountingState`

## 1. 目标

从 `ProposedAction` 和 normalized official dataset 构造足够、相关、可审计的 `AccountingState`。所有 provider 必须使用这份相同 state。

ContextBuilder 不做最终风险判断，也不直接调用任何模型。

## 2. 建议文件

```text
backend/app/
  services/
    context_builder.py
    candidate_matcher.py
    feature_calculator.py
  tools/
    accounting.py
    vendor.py
    ledger.py
backend/tests/
  test_context_builder.py
  test_candidate_matcher.py
  test_feature_calculator.py
  test_inference_view.py
```

## 3. 输入与输出

输入：

- validated `ProposedAction`
- company-scoped normalized records
- optional, explicitly tagged scenario overlay
- user constraints supplied at runtime

输出：

- `candidate_matches`
- `business_context`
- bounded `recent_ledger_history`
- named `deterministic_features`
- context build metadata/version

## 4. 实施步骤

### 4.1 Scope resolution

先解析并验证：

- `company_id`
- action/document reference
- vendor/counterparty identity
- action timestamp/as-of date
- currency

任何 cross-company lookup 必须被拒绝。找不到 source record 时返回明确 missing-context/precheck fact，不自行猜测。

### 4.2 Vendor history

从 bills 和 bill payments 构造：

- vendor transaction count
- total/mean/median/stddev amount
- min/max 和 robust statistics（需要时 MAD/IQR，但保持 P0 简单）
- recent same-vendor bills/payments
- typical cost categories/accounts
- payment timing/status history
- repeated memo/description patterns

标准差样本过少时返回 `None` 和 observation count，不能制造 0 代表“无波动”。

### 4.3 Deterministic candidate retrieval

第一版不使用 vector search。

按以下 signals 取候选并记录每个 match reason：

1. exact bill/invoice/source-document/application link
2. same vendor/customer
3. same or near amount
4. nearby date/due date
5. shared advisory reference（只作 signal，不作 identity）
6. normalized memo/description similarity
7. compatible category/account

候选先通过 cheap deterministic filters，再按透明 score 排序。限制 top K 和时间窗口，避免把整套 ledger 送给 provider。

### 4.4 Text normalization

允许：

- Unicode normalization
- case folding
- whitespace/punctuation normalization
- simple token overlap / `difflib` style similarity

不引入 embeddings、FAISS、Chroma、Pinecone 或 pgvector。

保留 original text；normalized text 只用于 feature calculation。

### 4.5 Derived status

对 bills/invoices：

- 聚合 applications。
- 计算 paid amount、open balance。
- 按指定 as-of date 推导 `OPEN | PARTIALLY_PAID | PAID | OVERDUE` 等内部状态。
- 保存 `status_source=derived_as_of` 和 as-of date。

不要依赖最终 report snapshot 去回答历史日期状态，除非请求正好是 report as-of date。

### 4.6 Amount anomaly features

计算：

- absolute deviation from mean/median
- z-score 仅在 stddev 有意义时
- ratio to median/mean，处理 denominator=0
- percentile/rank within vendor history
- historical sample count

特征名称和值必须稳定、JSON serializable，并带 feature version。

### 4.7 Destination context

官方数据没有 vendor destination。ContextBuilder 只能在 scenario overlay 明确提供 synthetic extension 时产生：

- previous destination
- new destination
- changed timestamp
- source/provenance marker

没有 extension 时字段为 `None` / unavailable，不能从 `payment_account_id` 错误推断 vendor destination。

### 4.8 Compact state

定义 deterministic size limits：

- top K candidates
- recent history max records/days
- per-record selected fields
- total serialized bytes/tokens 的软上限

裁剪规则必须 provider-neutral。对三个 provider 使用同一 state snapshot。

## 5. Testing checklist

### Feature math

- [ ] mean/median/stddev 与手算 fixture 一致。
- [ ] 单条历史记录时 stddev/anomaly behavior 明确。
- [ ] Decimal calculations 不出现 float drift。
- [ ] date distance 对边界日期、future/past 正确。
- [ ] zero denominator 和 empty history 安全处理。

### Candidate matching

- [ ] exact document link 排在最前。
- [ ] same vendor + near amount + nearby date 提升 score。
- [ ] 不同 company 的相同 ID/name 永不匹配。
- [ ] candidate reason codes 可解释。
- [ ] top K 和时间窗口严格生效。
- [ ] empty candidates 是合法结果。

### Status and context

- [ ] unpaid、partial、paid、overdue 的 as-of 状态正确。
- [ ] action timestamp 控制可见历史，避免 future leakage。
- [ ] `sim_*` generator truth 不进入 `AccountingState` inference view。
- [ ] 无 synthetic destination 时不会生成 destination history。
- [ ] synthetic extension 带完整 provenance。
- [ ] compact state 不包含全 ledger。

### Provider fairness

- [ ] 同一 action 重建得到相同 state hash。
- [ ] provider choice 不影响 ContextBuilder 输出。
- [ ] state serializer 对 Rules/LLM/System One 完全相同。

## 6. Performance checks

用真实最大/典型 companies 测量：

- context build p50/p95
- candidate scan count
- serialized state size
- peak memory（粗略即可）

这些是 ContextBuilder 性能数据，不得与 Jev/model latency 混合。

## 7. Exit criteria

- `ProposedAction -> AccountingState` 可在真实 records 上运行。
- 所有 deterministic features 有 unit test。
- candidate retrieval 无 vector dependency。
- no future leakage、no sim truth leakage、no cross-company leakage tests 全绿。
- state size 有明确上限，三个 provider 可复用同一 snapshot。
- Phase 3 provider 可以只依赖 `AccountingState` contract 开始实现。

