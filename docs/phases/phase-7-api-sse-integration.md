# Phase 7 — FastAPI, SSE, and End-to-End Integration

> Implementation status (2026-10-17): **Complete.** FastAPI REST/SSE contracts,
> SQLite audit/execution persistence, replay, filters, dashboard, stable errors, three
> hero flows, and failure injection are implemented. See
> [`API_HANDOFF.md`](../API_HANDOFF.md) for frontend integration. Focused verification:
> **14 tests passed**. Full black-box Uvicorn verification is documented in
> [`FASTAPI_TESTING.md`](../FASTAPI_TESTING.md).

**Owner:** Yizhe  
**Depends on:** Phases 1–6  
**Primary output:** 前端可稳定消费的 REST/SSE surface 和可演示的安全端到端链路

## 1. 目标

把已测试的 application workflow 暴露为稳定 FastAPI endpoints，接入 SQLite audit 和 SSE live events，并完成三个 hero cases 的端到端验证。

Route handler 不新增业务判断；它只验证 transport、调用 service/graph 并映射 response。

## 2. 建议文件

```text
backend/app/
  main.py
  api/
    actions.py
    dashboard.py
    demo.py
    benchmarks.py
    stream.py
    errors.py
  services/
    replay.py
    audit.py
    event_bus.py      # in-process/simple; no Kafka/Redis
  db/
    models.py
    repositories.py
    session.py
backend/tests/
  test_api_contract.py
  test_sse.py
  test_demo_flow.py
  test_audit_persistence.py
  test_end_to_end_safety.py
```

## 3. P0 API

### `GET /api/actions`

支持稳定 filters：

- final action
- risk/reason code
- provider
- scenario

定义分页、排序和空结果；不要一次返回完整 state/raw metadata。

### `GET /api/actions/{action_id}`

返回：

- proposed action
- relevant context summary
- candidate matches
- risk assessment or provider failure
- policy decision
- audit details
- review/execution state

不存在返回 stable 404 error schema。

### `POST /api/demo/run`

输入 named scenario/provider，创建新的 run/action/audit ID，启动同一真实 pipeline。不得从 route 直接返回预写 decision。

### `GET /api/benchmarks`

只返回已存在的 measured results。没有结果时返回明确 empty/not-run 状态，不返回看似真实的 placeholder。

## 4. P1 API

### `GET /api/dashboard`

从持久化 action decisions 聚合：

- processed/allowed/review/context/blocked counts
- safe autonomous execution rate（若 labels 支持）
- measured median latency
- current provider

聚合定义与 evaluation metric 一致或明确区分 live operational metric。

### `POST /api/actions/{id}/resolve`

接受：

- approve
- reject
- request more info
- match existing（如 contract 支持）

验证 action 当前确实等待 review/context、resolution 尚未完成、request 引用正确 state version。所有 resolution 写 audit。

### `GET /api/stream`

SSE event 类型：

- `action_received`
- `precheck_complete`
- `system_one_started` / internal generalized provider start
- `risk_assessment_ready`
- `policy_decision`
- `execution_simulated`
- `review_required`
- `context_requested`
- `action_blocked`

## 5. SSE design

每个 event：

- monotonic/event ID
- action/audit ID
- type
- timestamp
- schema version
- minimal payload

要求：

- heartbeat/comment 防止 idle connection 误断。
- client disconnect 清理 subscriber，不取消已持久化 workflow。
- bounded in-memory queue，定义 slow-consumer 行为。
- replay/reconnect 使用 last-event ID 或 action-detail refetch。
- 不在 event 中发送 secrets、完整 raw provider body 或未裁剪 ledger。

P0/P1 不引入 Redis/Kafka；单进程 in-memory broadcaster + SQLite replay 已足够 demo。

## 6. Error contract

统一 response：

- stable error code
- human-readable message
- correlation/audit ID when available
- retryable boolean where meaningful

不直接暴露 stack trace、API key、provider headers 或内部 filesystem path。

典型 mapping：

- validation -> 422
- not found -> 404
- invalid state transition/conflict -> 409
- provider unavailable but safely handled -> action response with fail-safe decision；必要时 operational 503
- internal persistence/invariant failure -> 500，且 no execution

## 7. Persistence integration

事务顺序要避免“执行了但 audit 没写”：

1. persist received action
2. persist state/provider/policy events
3. verify authorization
4. persist execution intent/idempotency key
5. simulated execution
6. persist execution outcome
7. emit event referencing persisted outcome

如果关键 persistence 失败，不执行。

## 8. Frontend handoff

给 Mira：

- OpenAPI schema
- sample canonical responses
- enum/reason-code catalog
- SSE event catalog and order
- empty/error/loading behavior
- provider failure display semantics
- measured benchmark schema

Contracts 改动必须同步 frontend types 或提供 generated types workflow。

## 9. Hero end-to-end flows

至少验证：

1. **Safe normal payment** -> real-derived context -> assessment -> `ALLOW` -> simulated execution。
2. **Destination change** -> disclosed synthetic destination overlay -> risk -> `REQUIRE_APPROVAL` -> interrupt/review。
3. **Semantic duplicate** -> real-derived candidate + disclosed modification -> duplicate signal -> `BLOCK`，或进入单独的人工 `match existing` resolution path；`MATCH_EXISTING` 不是 `FinalAction`。

每个 flow 都展示 source lineage、real risk signals、policy reason、threshold 和真实 latency。

## 10. Testing checklist

### API contract

- [ ] response 通过 Pydantic/OpenAPI schema。
- [ ] filters/pagination/404/409/422。
- [ ] enum 与 reason codes 稳定。
- [ ] benchmark no-results 不伪造数据。
- [ ] provider internal error 不泄露 secrets。

### SSE

- [ ] content type 和 event framing 正确。
- [ ] happy-path event order。
- [ ] BLOCK/review/context 分支 event order。
- [ ] disconnect cleanup。
- [ ] reconnect/replay behavior。
- [ ] slow consumer queue policy。
- [ ] 重试不会重复 execution event。

### Persistence/audit

- [ ] action/risk/decision/review/execution 可关联。
- [ ] config/model/schema versions 保存。
- [ ] failed provider attempt 保存但不暴露 secret。
- [ ] restart 后 detail endpoint 可读。
- [ ] idempotency 防止 demo run 重复执行。

### End-to-end safety

- [ ] 三个 hero flows 完整运行。
- [ ] direct route 无法绕过 graph/policy 调 execution。
- [ ] provider timeout -> fail-safe API result -> no execution。
- [ ] database/checkpoint failure -> no execution。
- [ ] review approval 引用 stale action 时拒绝。

用 FastAPI test client/`httpx.AsyncClient`、temporary SQLite、fake provider。另设 opt-in live Jev end-to-end smoke test。

## 11. Demo reliability

- 为 live outage 准备真实已运行结果的 replay/cache，明确标注 recorded result，不伪装成 live。
- 保留可重复 seed/scenario IDs。
- 启动 health/self-check 验证 DB、dataset、config；Jev live mode 额外验证 credential/model。
- demo script 前做冷启动和连续三次 rehearsal。
- 即使 SSE 断开，action detail API 仍能展示持久化结果。

## 12. Exit criteria

- P0 endpoints 完整，P1 endpoints 按时间启用。
- OpenAPI/API contract tests 全绿。
- SSE branch ordering 和 reconnect 行为有测试。
- SQLite audit 可重放 action detail。
- 三个 hero scenarios 端到端成功。
- failure injection 证明没有未授权 simulated execution。
- frontend 获得稳定 schema/examples。
- 所有展示的 latency/benchmark 数字来自真实运行。

