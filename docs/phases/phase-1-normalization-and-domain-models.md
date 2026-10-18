# Phase 1 — Dataset Normalization and Domain Models

> Implementation status (2026-10-17): **Complete.** Implemented in `backend/app/data/`
> and `backend/app/models/`; covered by 14 focused tests using the real RWM v4 dataset.

**Owner:** Yizhe  
**Depends on:** Phase 0 dataset discovery  
**Primary output:** 真实 QuickBooks YAML 可以安全加载、规范化并形成稳定 typed contracts

## 1. 目标

把 sponsor dataset 从 company-scoped RWM v4 YAML 转成 LedgerGuard 可复用的 canonical accounting representation，同时定义后续所有模块共享的 Pydantic contracts。

Phase 1 不做风险判断、不调用 Jev、不决定 action 是否允许。

## 2. 输入事实

以 [`DATASET_REPORT.md`](../DATASET_REPORT.md) 为准：

- 100 company worlds；22 个 YAML logical files。
- empty entity arrays 是合法业务状态。
- 金额是 decimal strings。
- entity IDs 只在 company 内唯一。
- `currency` 来自 `manifest.yaml`。
- `payment destination` / `payment method` 缺失。
- `sim_*` 字段可能造成 label leakage。

## 3. 建议文件

```text
backend/
  app/
    data/
      loader.py
      schema_inspector.py
      mappings.py
      normalizer.py
    models/
      accounting.py
      action.py
      state.py
      risk.py
      policy.py
      errors.py
    config.py
  tests/
    fixtures/
    test_dataset_loader.py
    test_schema_inspector.py
    test_normalizer.py
    test_domain_models.py
data/
  raw/          # already downloaded; do not mutate
  normalized/   # generated artifacts, if materialized
  scenarios/
  labeled/
```

## 4. 实施步骤

### 4.1 Project scaffolding

- 建立 Python 3.12+ package 和依赖清单。
- 配置 pytest；需要时加入 pytest-asyncio。
- 选择并固定 Pydantic major version。
- 将 raw archive/path 作为配置输入，不能硬编码用户机器绝对路径。
- 明确 generated data 是否进入 git；大文件默认不提交。

### 4.2 Loader

`loader.py` 应：

- 发现 `company-*/rwm-v4/world-*`，验证 exactly one world per company。
- 读取 `index.json`、company manifest 和指定 entity files。
- 将 directory `company_id` 注入 row wrapper，不修改原 payload。
- 支持合法 empty YAML arrays。
- 对缺失文件、非法 YAML、非预期 root shape 返回 typed error。
- 支持按 company/entity lazy load，避免无条件把 401 MB 全放入内存。
- 保持 deterministic ordering，方便 fixtures 和 evaluation hash。

### 4.3 Schema inspector

`schema_inspector.py` 应检查：

- required logical files 是否存在。
- schema/realize version 是否受支持。
- top-level key set、observed types 和 money/date conventions。
- `index.entity_counts` 与实际 row counts。
- manifest currency 和 dataset ID。
- 跨 company 的 ID collision 是否被正确隔离。

Schema drift 策略：

- required field 丢失 -> fail closed / typed load error。
- 新增未知字段 -> 保留在 raw metadata，并发出 warning，不静默丢失。
- optional field 缺失 -> canonical `None`，记录 source absence。
- unsupported schema version -> 明确拒绝，不猜映射。

### 4.4 Raw and canonical models

定义：

- `RawQuickBooksRecord`
- `CanonicalAccountingRecord`
- typed account/document reference objects
- record/source/status enums
- provenance metadata

Canonical identity：

```text
record_id = f"{company_id}:{record_type}:{source_id}"
```

金额：

- parse 为 `Decimal`。
- 拒绝 NaN、Infinity、超过允许 precision 的值。
- bank amount 保留 sign。
- index 的 integer cents 使用显式转换。

### 4.5 Mappings

`mappings.py` 按 entity type 定义显式 mapping，不做一个难以审计的万能 dict mapper。

至少支持：

- bills
- bill payments
- vendors
- accounts
- bank transactions
- invoices
- customer payments
- sales receipts
- journal entries
- company/index/manifest context

`doc_number` 只能映射为 reference，不能成为 canonical ID。

### 4.6 Leakage boundary

区分两种 view：

- `audit/raw view`: 可包含 `sim_*` 和 provenance。
- `inference view`: 默认排除 `sim_obligation_id`、`sim_payment_id`、`provenance_note` 等 generator truth。

用一个明确 serializer/filter 实现，不能依赖调用方“记得不要传”。

### 4.7 Runtime contracts

定义稳定 Pydantic models：

- `ProposedAction`
- `CandidateMatch`
- `BusinessContext`
- `AccountingState`
- `RiskSignal` / `RiskAssessment`
- `PolicyDecision`
- `FinalAction`

MVP `ActionType` 只包含四种：

- `PAY_VENDOR_BILL`
- `POST_TRANSACTION`
- `MATCH_EXISTING`
- `ADD_TRANSACTION`

Synthetic destination metadata 必须包含 `is_synthetic` / provenance，而不是伪装成 raw dataset field。

## 5. Testing checklist

### Dataset loader

- [ ] 全部 100 companies 可发现。
- [ ] 实际 row totals 与 Phase 0 report/index 一致。
- [ ] empty invoices/sales receipts/projects/estimates 文件正确返回空集合。
- [ ] 缺失 manifest、损坏 YAML、错误 root type 会产生 typed error。
- [ ] loader 不修改 raw files。
- [ ] 读取顺序在重复运行中稳定。

### Schema and normalization

- [ ] `company-001` 和另一 company 中相同 source ID 产生不同 canonical ID。
- [ ] decimal string round-trip 不丢失 cents。
- [ ] signed bank transaction 保留符号。
- [ ] missing optional field -> `None`；missing required field -> error。
- [ ] unknown fields 保留在 raw metadata。
- [ ] advisory `doc_number` collision 不影响 identity。
- [ ] journal entry lines 保持 balance；normalizer 不编造 net amount。
- [ ] `currency` 正确从 manifest join。

### Leakage and contracts

- [ ] inference serializer 不包含禁止的 `sim_*` / provenance fields。
- [ ] audit serializer 保留 traceability。
- [ ] Pydantic rejects invalid enum、negative/invalid amount where contract disallows it、malformed references。
- [ ] JSON serialization 可重现；相同输入得到相同 normalized output/hash。

## 6. Fixtures

至少保存这些真实、带 source path 的小 fixtures：

- 一个 product bill
- 一个 operating bill
- 一个 bill payment application
- 一个 invoice/customer payment pair
- 一个 bank transaction/source-document pair
- 一个 journal entry
- 一个 empty entity file
- 一个 project company record

Fixtures 是真实数据裁剪，不是重新发明的 accounting world。

## 7. Exit criteria

- loader 可以读取全部 sponsor dataset。
- canonical identity、Decimal 和 company scope tests 全绿。
- runtime contracts 可被下一阶段直接导入。
- inference view 已有 leakage test。
- 没有引入 provider、policy 或 API 业务逻辑。
- `pytest -q` 通过，并记录测试数量/结果。

## 8. Handoff

输出给 Phase 2：

- normalized record access interface
- typed models
- fixture factory
- stable serialization/hash
- documented optional/synthetic fields

