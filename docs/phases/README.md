# Yizhe Implementation Phases

本目录把 [`architecture.md`](../architecture.md) 拆成可以逐阶段执行、测试和交付的计划。

> Current status (2026-10-17): Phases 0–7 are implemented and locally verified.
> Live System One/Gemini benchmark execution remains opt-in because it requires external
> credentials and network access; no placeholder live metrics are reported.
> Full regression after the Gemini migration: **106 passed, 3 credential-gated live tests skipped**.

## 顺序与依赖

```text
Phase 0 Dataset Discovery (done)
        |
        v
Phase 1 Normalization + Domain Models
        |
        v
Phase 2 Context Builder
        |
        +----------------------+
        |                      |
        v                      v
Phase 3 System One       Phase 4 Policy + Scenarios
        |                      |
        +----------+-----------+
                   v
        Phase 5 Baselines + Evaluation
                   |
                   v
        Phase 6 LangGraph Orchestration
                   |
                   v
        Phase 7 FastAPI + SSE + Integration
```

System One 的 live feasibility 是高风险依赖。编号上它是 Phase 3，但应在 Phase 1 scaffolding 完成后尽早执行其 30–45 分钟 spike，不必等待 Phase 2 的所有 polish。

## 文档索引

1. [Phase 1 — Normalization and Domain Models](./phase-1-normalization-and-domain-models.md)
2. [Phase 2 — Context Builder and Candidate Retrieval](./phase-2-context-builder.md)
3. [Phase 3 — System One Feasibility and Provider Abstraction](./phase-3-system-one-provider.md)
4. [Phase 4 — Scenario Integration and PolicyEngine](./phase-4-policy-and-scenarios.md)
5. [Phase 5 — Baselines and Evaluation Plumbing](./phase-5-evaluation.md)
6. [Phase 6 — LangGraph Orchestration](./phase-6-langgraph.md)
7. [Phase 7 — FastAPI, SSE, and End-to-End Integration](./phase-7-api-sse-integration.md)

## 每个 phase 的共同规则

- 开始前确认上一阶段 exit gate 已通过。
- 先写/更新 contracts 和 tests，再接入高层 consumer。
- 每个 PR 保持单一架构目的；不要跨 phase 顺手加功能。
- 对真实 dataset 的任何 synthetic modification 必须记录 source IDs、变更、原因和 label。
- provider、policy、graph、execution 四层必须保持独立。
- 阶段完成时保存测试命令和结果摘要；benchmark 数字只来自真实运行。
- 如果安全关键测试失败，该 phase 不算完成。

## 建议的工作节奏

每个 phase 使用同一循环：

1. 写 acceptance tests / fixtures。
2. 实现最小 happy path。
3. 实现错误与 fail-safe path。
4. 运行 unit + contract + integration tests。
5. 更新相应文档和 schema examples。
6. 只在 exit gate 全绿后进入下一 phase。

## Yizhe 的优先级

1. System One feasibility 和 fail-safe behavior。
2. PolicyEngine authority invariant。
3. 真实 dataset 到 AccountingState 的正确性。
4. Provider comparison fairness。
5. 可演示的端到端链路。
6. SSE、human review 等 P1 polish。

不要为了 P1/P2 功能牺牲前三项。

