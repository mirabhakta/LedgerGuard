# Phase 6 — LangGraph Workflow Orchestration

> Implementation status (2026-10-17): **Complete.** All four policy routes,
> interrupt/resume flows, versioned state, SQLite checkpoint support, and an independent
> idempotent execution guard are implemented. Focused verification: **9 tests passed**.

**Owner:** Yizhe  
**Depends on:** Stable ContextBuilder、DecisionProvider、PolicyEngine  
**Primary output:** 可暂停、恢复、审计且不会绕过 policy 的 agent workflow

## 1. 目标

用 LangGraph 表达金融 agent 的长流程生命周期和 conditional routing。LangGraph 移动 state，不做风险判断，不拥有最终授权。

P0 优先完成 ALLOW/BLOCK terminal flow。Human review 和 missing-context loop 在核心链稳定后加入。

## 2. 建议文件

```text
backend/app/graph/
  state.py
  graph.py
  routing.py
  nodes/
    plan_action.py
    build_context.py
    precheck.py
    evaluate_risk.py
    policy_decide.py
    human_review.py
    request_context.py
    execute.py
    blocked.py
backend/app/tools/
  execution.py
backend/tests/
  test_graph_routing.py
  test_graph_interrupts.py
  test_graph_resume.py
  test_graph_fail_safe.py
```

## 3. AgentState

保持小且显式：

- `user_goal`
- `proposed_action`
- `accounting_state`
- `precheck_result`
- `provider_outcome`
- `risk_assessment`
- `policy_decision`
- `human_response`
- `execution_result`
- `audit_id`
- `current_scenario`
- `error_state`
- schema/workflow version

不要把数据库 session、HTTP client、API key 或整套 ledger 存进 graph state。

## 4. Nodes

每个 node 单一职责：

- `plan_action`: 接收/验证已有 proposal；P0 不需要复杂 LLM planner。
- `build_context`: 调用 ContextBuilder。
- `hard_precheck`: 产生 deterministic result。
- `system_one_evaluate`: 通过 provider interface 调用选定 provider；名称可内部泛化为 evaluate risk。
- `policy_decide`: 唯一调用 PolicyEngine 的节点。
- `human_review`: interrupt 并等待 explicit response。
- `request_context`: interrupt 并声明缺失字段/问题。
- `execute_action`: 再验证授权并只做 simulated execution。
- `blocked_terminal`: 保存 terminal outcome。

Node 不隐藏业务 policy；threshold 不出现在 graph routing code。

## 5. Routing

```text
START
  -> plan_action
  -> build_context
  -> hard_precheck
  -> evaluate_risk (unless hard terminal violation)
  -> policy_decide

ALLOW             -> execute_action -> END
REQUIRE_APPROVAL  -> human_review -> interrupt
REQUEST_CONTEXT   -> request_context -> interrupt
BLOCK             -> blocked_terminal -> END
```

Resume：

- human approve -> record resolution -> authorized simulated execution
- human reject -> blocked terminal
- new context -> update with provenance -> rebuild context -> re-evaluate -> re-run policy

## 6. Execution guard

`execute_action` 和底层 `simulate_payment`/posting tool 都要独立验证：

- action identity matches decision
- policy decision is `ALLOW`, or explicit approved review references same action/risk snapshot
- decision/audit is not stale or superseded
- execution not already completed（idempotency）

Graph routing 正确不是唯一安全边界；execution tool 自身也必须拒绝未授权调用。

## 7. Persistence and checkpoints

P1 human-in-the-loop 使用 SQLite checkpointer 或明确 repository：

- thread/workflow ID
- state schema version
- current node/status
- interrupt payload
- audit/action IDs
- resume input and actor

恢复失败、schema mismatch 或缺失 state 时 fail safe 到 review/block，不从头自动重新规划并执行。

## 8. Error handling

- Context build error -> typed error + safe terminal/review。
- Provider error -> PolicyEngine fail-safe pathway。
- Policy error/config missing -> `BLOCK` 或 operational error，不执行。
- Checkpoint write failure -> 不执行。
- SSE delivery failure -> 不应改变已持久化 workflow outcome。
- Node retry 必须幂等，尤其是 audit 和 execution。

## 9. Testing checklist

### Routing

- [ ] ALLOW 到 execute。
- [ ] BLOCK 到 terminal，never execute。
- [ ] REQUIRE_APPROVAL interrupt。
- [ ] REQUEST_CONTEXT interrupt。
- [ ] hard precheck block 可安全跳过 provider。

### Interrupt/resume

- [ ] approve/resume 执行同一原 action。
- [ ] reject/resume block。
- [ ] request-context update 带 provenance 并重新 build/evaluate/policy。
- [ ] 重复 resume/idempotency。
- [ ] stale review response 被拒绝。

### Failure safety

- [ ] provider timeout 不到 execute。
- [ ] missing/corrupt checkpoint 不到 execute。
- [ ] graph node exception 不到 execute。
- [ ] audit persistence failure 不到 execute。
- [ ] unauthorized direct execution tool call 被拒绝。

### State integrity

- [ ] serialize/deserialize round trip。
- [ ] schema version mismatch 行为明确。
- [ ] resume 不重新生成或改变原 financial facts。
- [ ] risk/decision/review references 保持一致。

使用 fake provider、in-memory/temporary SQLite 和 injected clock；不要让默认 graph tests 调真实 Jev。

## 10. Exit criteria

- 四种 PolicyDecision 都有明确 route。
- ALLOW/BLOCK flow 稳定；P1 interrupt/resume 有测试后再启用。
- execution tool 是第二道 authorization guard。
- checkpoint/restore failure fail safe。
- graph state 小、typed、versioned。
- LangGraph 未复制 PolicyEngine 判断。

