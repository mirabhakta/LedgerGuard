# LedgerGuard Backend / AI Infrastructure Architecture

**Owner:** Yizhe  
**Status:** Phases 0–7 implemented and locally verified (live external provider benchmarks remain credential-gated)  
**Primary source:** [Final Product & Technical Specification](https://docs.google.com/document/d/1kbs8MvBZYKtwyxwiX1skNhEmmC5sLictJwdaVNIWKHg/edit?tab=t.0)  
**Dataset source:** [Phase 0 Dataset Report](./DATASET_REPORT.md)

## 1. Yizhe 的目标

Yizhe 负责把 LedgerGuard 的产品原则变成一条可靠、可测试、可比较的后端执行链：

```text
ProposedAction
  -> deterministic pre-checks
  -> ContextBuilder
  -> DecisionProvider
  -> RiskAssessment
  -> deterministic PolicyEngine
  -> PolicyDecision
  -> LangGraph routing
  -> simulated execution / review / context request / block
  -> audit + SSE events
```

最终要保证：

1. System One 只做模糊语义判断。
2. 确定性代码负责事实计算和最终授权。
3. LangGraph 只负责编排，不拥有金融决策权。
4. 所有执行均为模拟执行。
5. 所有 provider 接收相同 `AccountingState`，输出相同 `RiskAssessment`。
6. 任何超时、不可用、解析失败或低置信度都不能静默变成 `ALLOW`。

## 2. 不可破坏的架构约束

### 2.1 Authority boundary

唯一可以产生最终授权结果的组件是 `PolicyEngine`。

- `SystemOneProvider` 可以输出风险概率和置信度，不能执行 action。
- `OpenJevProvider` 是本地、独立的 masked-logit System One-style baseline；它不等同于官方 Jev，不能执行 action。
- `GeminiBaselineProvider` 可以输出同构风险信号，不能执行 action。
- `RulesProvider` 是比较基线，不应绕过统一 policy。
- FastAPI route 不直接调用 Jev，也不直接授权付款。
- LangGraph node 不得根据 prompt 文本自行决定执行。
- `execute_action` 必须验证已有 `PolicyDecision.final_action == ALLOW`，或者已记录的人工批准允许继续。

### 2.2 Deterministic vs semantic boundary

由普通代码处理：

- 金额、均值、中位数、标准差和偏离度
- 日期差和时间窗口
- company-scoped ID equality
- payment application/document linkage
- required field validation
- hard limits、allowlists、unsupported currency
- threshold comparison和最终路由

由 System One / Jev 判断：

- goal-action alignment
- semantic duplicate obligation risk
- contextual counterparty or destination-change risk
- missing-context judgment
- action anomaly relative to compact business context

### 2.3 Scope boundary

不引入 Kafka、Redis、Kubernetes、vector database、microservices、RAG、fine-tuning 或真实支付连接。不把产品做成聊天机器人、QuickBooks clone 或通用 fraud detector。

## 3. Phase 0 已确认的数据现实

后续实现必须以真实 sponsor dataset 为基础：

- 100 家 synthetic companies，Realized World Model v4。
- 主要格式是 YAML，不是预设的 CSV。
- 记录 ID 是 company-scoped；canonical ID 必须包含 `company_id`。
- 金额主要是两位小数字符串；规范层必须使用 `Decimal`，不能用 binary float。
- AP 数据完整：bills、bill payments、vendors、accounts、bank links、AP aging。
- bill/invoice payment status 需要根据 applications 和 as-of date 推导。
- vendor bank destination 和 payment method 不存在，必须作为明确标记的 synthetic extension。
- `doc_number` 只是 advisory，不可作为主键。
- `sim_*` / `provenance_note` 只用于 traceability 和 label construction；默认从 provider context 中移除，避免 ground-truth leakage。

## 4. 目标系统结构

```text
                       +----------------------+
                       | React/Vite Frontend  |
                       +----------+-----------+
                                  |
                         REST + SSE contracts
                                  |
                       +----------v-----------+
                       | FastAPI API Layer    |
                       | validation / authz*  |
                       +----------+-----------+
                                  |
                       +----------v-----------+
                       | Application Service  |
                       | run/replay/resolve   |
                       +----------+-----------+
                                  |
                       +----------v-----------+
                       | LangGraph Workflow   |
                       | orchestration only   |
                       +----------+-----------+
                                  |
              +-------------------+--------------------+
              |                   |                    |
     +--------v--------+  +-------v---------+  +-------v---------+
     | ContextBuilder |  | DecisionProvider|  | PolicyEngine    |
     | deterministic  |  | semantic signals|  | final authority |
     +--------+--------+  +-------+---------+  +-------+---------+
              |                   |                    |
     +--------v--------+  +-------v--------------------v---------+
     | Normalized Data |  | Audit repository / SQLite            |
     +--------+--------+  +---------------------------------------+
              |
     +--------v----------------------------------------------+
     | Official QuickBooks YAML + disclosed scenario overlay |
     +-------------------------------------------------------+

* Hackathon P0 may omit production authentication.
```

## 5. 模块边界与依赖方向

```text
backend/app/
  api/          HTTP/SSE transport only
  graph/        workflow state, nodes, routing, interrupt/resume
  models/       stable Pydantic domain and API contracts
  providers/    DecisionProvider implementations
  policy/       deterministic pre-checks, thresholds, final decision
  services/     context, scenarios, audit, replay, metrics
  tools/        fact retrieval and simulated execution
  data/         loading, inspection, mappings, normalization
  db/           SQLite models/repositories/session
```

允许的依赖方向：

```text
api -> application services / graph
graph -> services + providers + policy + tools
services -> models + data + repositories
providers -> models
policy -> models + policy config
tools -> models + repositories
data -> models (canonical models only)
```

禁止的依赖：

- `api -> SystemOneProvider` 直接调用
- `providers -> policy` 修改 threshold 或 final action
- `policy -> external model API`
- `tools/execution -> provider` 决定是否执行
- `graph -> database internals` 绕过 repository/service
- `models -> FastAPI/LangGraph/httpx` 等框架层依赖

## 6. 核心数据契约

### 6.1 Raw and canonical accounting data

`RawQuickBooksRecord` 保留 source path、company scope、raw entity type 和原始 payload。

`CanonicalAccountingRecord` 建议包含：

- `record_id`: `company_id:record_type:source_id`
- `company_id`
- `dataset_id`
- `record_type`
- `timestamp`
- typed vendor/customer/counterparty fields
- `amount: Decimal | None`
- `currency`
- `memo` and description fields
- source-specific category
- typed account references
- source-document references
- direct/derived status plus `status_source`
- `source`
- restricted `raw_metadata`

不要为 journal entry 编造净金额。保留 debit/credit lines；如需特征，明确命名为 `total_debits` 等 derived feature。

### 6.2 Runtime domain models

`ProposedAction`：

- MVP action type 仅包含 `PAY_VENDOR_BILL`、`POST_TRANSACTION`、`MATCH_EXISTING`、`ADD_TRANSACTION`
- 金额与币种
- company-scoped counterparty/document/account references
- `agent_goal`
- optional `agent_reasoning_summary`，且明确不可信
- synthetic destination metadata 必须带 provenance

`CandidateMatch`：与 proposed action 相关的少量 ledger candidates，包含 source ID、日期、金额、counterparty、category、description 和 derived/direct status。

`BusinessContext`：industry、current account、vendor history、historical statistics、known accounting patterns、optional synthetic destination history、user constraints。

`AccountingState`：所有 provider 共用的不可变输入快照：

- `proposed_action`
- `candidate_matches`
- `business_context`
- `recent_ledger_history`
- `deterministic_features`
- schema/version metadata

`RiskAssessment`：五个独立 signal 的 probability/score 与 confidence，加 provider/model name、latency、schema version。Provider failure 不应伪造概率；使用明确的 error/fallback metadata，并由 policy fail safe。

`PolicyDecision`：

- `final_action`: `ALLOW | REQUIRE_APPROVAL | REQUEST_CONTEXT | BLOCK`
- `reason_codes`
- `triggered_thresholds`
- provider identity
- risk snapshot/reference
- `audit_id`

## 7. 关键执行路径

### 7.1 Normal path

1. Validate `ProposedAction`。
2. Run deterministic hard pre-checks。
3. Build compact `AccountingState` from normalized official data。
4. Serialize one provider-neutral context snapshot。
5. Call selected `DecisionProvider`。
6. Validate `RiskAssessment`。
7. Apply centralized `PolicyConfig` in `PolicyEngine`。
8. Persist action, context hash, signals, threshold hits and decision。
9. Route through LangGraph。
10. Emit ordered SSE events。
11. Simulate execution only for authorized state。

### 7.2 Provider failure path

```text
timeout / network error / malformed response / unknown model
  -> capture typed ProviderError
  -> write audit event
  -> no fabricated risk output
  -> PolicyEngine fail-safe decision
  -> REQUIRE_APPROVAL for semantic-dependent actions
     or BLOCK for malformed/hard-policy violations
```

### 7.3 Human review path

`REQUIRE_APPROVAL` 进入 explicit graph interrupt。Resume 时必须引用原 action、risk assessment、reason codes、reviewer response 和新的 audit event，不得重新偷偷生成财务事实。

### 7.4 Missing context path

P1/P2 才实现完整循环：`REQUEST_CONTEXT -> interrupt -> targeted update -> rebuild context -> re-evaluate -> re-run policy`。P0 只需可靠记录和展示请求，不应为了 conversational loop 推迟 hero flow。

## 8. Provider abstraction 与公平比较

统一接口：

```python
class DecisionProvider(Protocol):
    async def evaluate(self, state: AccountingState) -> RiskAssessment:
        ...
```

公平性要求：

- 同一 scenario 使用同一份 `AccountingState` 序列化结果或 hash。
- Rules、LLM、official System One、OpenJev 使用同一 label 与 action space。
- OpenJev 与 official System One 共享语义问题，但保持独立 provider/model provenance；其 raw masked-logit confidence 不宣称经过 RLCD calibration。
- 尽可能使用同一 `PolicyEngine`。
- 不为 System One 提供隐藏的额外上下文，也不刻意削弱 LLM context。
- 分开报告 cold/warm latency、样本量、失败率和 retry policy。
- 不使用 `sim_obligation_id` 等 generator truth 作为正常 provider feature。

## 9. PolicyEngine 设计

所有 threshold 集中在 `backend/app/policy/config.py`，由 typed settings/config 加载。Policy evaluation 顺序必须固定并可测试：

1. malformed/unsupported/hard-rule violation -> `BLOCK`
2. duplicate probability 超过 block threshold -> `BLOCK`
3. counterparty/destination-change risk 超过 review threshold -> `REQUIRE_APPROVAL`
4. missing-context probability 超过 threshold -> `REQUEST_CONTEXT`
5. 任一必要 signal confidence 低于 threshold -> `REQUIRE_APPROVAL`
6. provider failure -> fail-safe decision，绝不 `ALLOW`
7. 其余 -> `ALLOW`

每个分支返回 machine-readable reason code 和实际触发值/threshold。不得根据 `scenario_id` 硬编码答案。

## 10. Persistence、audit 与 SSE

SQLite 是 hackathon 默认持久层。最小数据表/存储对象：

- action record
- accounting-state snapshot/hash
- provider attempt and latency
- risk assessment
- policy decision
- human resolution
- workflow checkpoint（只在 LangGraph interrupt/resume 需要时）
- benchmark run metadata/result reference

Audit 要求：

- append-oriented；更新用新 event 表达
- UTC timestamp，并在 UI/API 明确时区
- source record IDs 和 scenario modifications 可追溯
- secrets、完整 API key、敏感 request headers 永不记录
- model/provider、threshold config version、schema version 可重现

SSE event 顺序：

```text
action_received
precheck_complete
system_one_started (provider-specific name may be generalized internally)
risk_assessment_ready
policy_decision
execution_simulated | review_required | context_requested | action_blocked
```

事件至少包含 `event_id`、`action_id`、`audit_id`、type、timestamp 和必要 payload。客户端重连应能使用 event ID 或 replay endpoint 恢复，而不重复执行 action。

## 11. API 边界

P0：

- `GET /api/actions`
- `GET /api/actions/{action_id}`
- `POST /api/demo/run`
- `GET /api/benchmarks`

P1：

- `GET /api/dashboard`
- `GET /api/stream`
- `POST /api/actions/{action_id}/resolve`

Route 只做 transport validation、dependency invocation 和 response mapping。业务错误必须映射为稳定 error schema；provider 原始错误不能直接泄露给客户端。

## 12. Yizhe 与团队的责任边界

| Area | Yizhe 主责 | 合作者 / handoff |
|---|---|---|
| Backend architecture | 模块边界、contracts、dependency direction、fail-safe invariant | 全员 review |
| Dataset integration | loader/normalizer contract、canonical IDs、runtime data access | Anish 使用 normalized data 生成 scenarios |
| Provider abstraction | `DecisionProvider`、SystemOneProvider、provider error model | Anish 实现 Rules/LLM baseline，必须遵守 contract |
| Policy | config、pre-check、engine、reason codes、audit integration | Anish 提供 scenario labels；共同调 threshold |
| Context | builder contract、deterministic features、provider-neutral snapshot | Anish/产品侧校验 scenario realism |
| Evaluation plumbing | shared runner inputs、provider registry、result persistence、fairness guards | Anish 主写 metrics/eval scripts；Mira/Kubra 展示结果 |
| LangGraph | workflow state、routing、interrupt/resume、execution gate | Mira 对接 review UX |
| FastAPI/SSE | endpoints、schemas、stream ordering、integration | Mira 前端对接；Kubra deployment/integration test |

任何跨人修改 data contract 的 PR 必须同时更新 API/schema documentation 和 consumer tests。

## 13. Testing architecture

测试不是最后一个 phase，而是每个 phase 的 exit gate。

### 13.1 Test layers

1. **Unit tests:** normalization functions、feature calculations、provider parsing、policy thresholds、graph routing。
2. **Contract tests:** Pydantic serialization、provider interface、API schemas、SSE payloads。
3. **Dataset tests:** 实际 sponsor archive load、schema drift、empty entity files、company scoping、Decimal precision。
4. **Integration tests:** action -> context -> provider stub -> policy -> audit；graph interrupt/resume；FastAPI endpoints。
5. **Live smoke tests:** Jev `/v1/models` 和 `/v1/systemone`，默认不进入离线 CI。
6. **Evaluation regression tests:** metric math、fairness hash、machine-readable JSON/CSV、无 placeholder/fake result。
7. **End-to-end safety tests:** 未得到 `ALLOW` 或显式人工批准时，execution tool 必须拒绝执行。

### 13.2 Test conventions

- 默认测试完全离线、可重复、无真实 API key。
- `httpx.MockTransport` 或等价 fake transport 测 System One/OpenJev request/response。
- frozen fixtures 必须来自真实 dataset row，并记录 source path/ID。
- synthetic fixture 必须显式标明 modification 和 reason。
- threshold 测试覆盖 `just below / exactly equal / just above`。
- 时间相关测试注入 clock，不依赖 wall clock。
- latency 只在真实调用时测量；mock latency 不作为 benchmark。
- 测试失败时不自动更新 snapshots 或 labels。

### 13.3 Global safety invariant test

整个项目至少有一个跨层测试证明：

```text
for final_action in [REQUIRE_APPROVAL, REQUEST_CONTEXT, BLOCK]:
    execution_tool(action, policy_decision) raises ExecutionNotAuthorized
```

还要测试 provider timeout、malformed response 和 graph state restore failure 均不能到达自动执行。

### 13.4 Phase gate command

每一阶段完成后，至少运行：

```bash
pytest -q
```

随着项目建立，再增加：

```bash
ruff check backend evaluation
mypy backend evaluation
pytest -q --cov=backend/app --cov-report=term-missing
```

工具是否最终采用由 Phase 1 scaffolding 决定；不要为了工具配置阻塞核心 demo，但 safety-path tests 必须始终通过。

## 14. 配置与 secrets

环境变量建议统一以 `LEDGERGUARD_` 为前缀：

- provider selection
- TypeSafe base URL/API key
- explicit connect/read/write timeout
- SQLite URL/path
- policy config path/version
- log level
- live-test opt-in flag

`.env` 仅本地使用且不得提交。启动时验证必要配置；缺少 Jev key 时允许离线 provider/tests 运行，但 live System One mode 必须明确失败，不能退化为 auto-allow。

## 15. Observability

结构化日志至少包含：

- `action_id`, `audit_id`, `scenario_id`
- provider/model and attempt
- latency and error category
- final action and reason codes
- threshold config version
- graph node transition

禁止日志：API key、authorization header、完整 provider raw body（除非经过脱敏并在 debug fixture 中）。

## 16. 实施阶段

| Phase | 内容 | Yizhe 的主要交付 | Exit gate |
|---|---|---|---|
| 0 | Dataset discovery | 已完成 `DATASET_REPORT.md` | 真实 schema、counts、mapping 已确认 |
| 1 | Normalization + domain models | loader、normalizer、typed contracts、project test scaffolding | 实际 dataset load + schema/Decimal/company-scope tests |
| 2 | Context Builder | deterministic features、candidate retrieval、compact AccountingState | fixture calculations 与 leakage tests |
| 3 | System One feasibility + provider abstraction | model discovery、typed request/parse、timeouts、fail-safe provider behavior | live feasibility record + mocked failure tests |
| 4 | Scenario integration + PolicyEngine | centralized thresholds、reason codes、audit-ready decisions | boundary tests + no scenario hardcoding + execution denial |
| 5 | Baselines + evaluation plumbing | fair shared runner、result storage、metrics integration | identical input hashes + reproducible JSON/CSV |
| 6 | LangGraph orchestration | state graph、routing、interrupt/resume、execution gate | all branch/restore tests |
| 7 | FastAPI + SSE + end-to-end integration | REST/SSE contracts、SQLite audit、hero flow integration | API contract + SSE order + end-to-end safety tests |

详细计划位于 [`docs/phases/`](./phases/README.md)。

## 17. 完成定义

Yizhe 的 backend/AI infrastructure 部分达到 demo-ready 的最低条件：

- 实际 sponsor dataset 可重复加载和规范化。
- 四个 provider（rules、Gemini、official System One、OpenJev）遵守同一接口和 RiskAssessment schema。
- Jev 至少在真实项目 scenarios 上成功调用并记录真实 latency。
- PolicyEngine 是唯一 authority，且所有 threshold/reason code 可审计。
- 至少三个 hero scenarios 能完成 action -> decision -> simulated outcome。
- provider failure 和 state recovery failure fail safely。
- API/SSE 返回稳定 contracts，前端不依赖内部对象。
- benchmark 使用真实运行结果、相同输入、相同 labels 和可重现输出。
- 所有 safety-critical tests 通过。

