# Phase 3 — System One Feasibility and Provider Abstraction

> Implementation status (2026-10-17): **Adapter/offline contract complete; live spike pending
> credentials.** Sixteen focused tests pass and the opt-in live test skips safely when
> `TYPESAFE_API_KEY` is unavailable. See `docs/SYSTEM_ONE_FEASIBILITY.md`.

**Owner:** Yizhe  
**Depends on:** Phase 1 contracts；Phase 2 的最小 AccountingState fixture  
**Primary output:** 可验证、typed、fail-safe 的 `SystemOneProvider`

## 1. 目标

确认 TypeSafe System One / Jev 对 LedgerGuard 五类 semantic signals 具备实际可用性，并将 API 封装在统一 `DecisionProvider` 后面。

这是核心 feasibility gate。不要等所有 UI 或 LangGraph 完成后才第一次调用 Jev。

## 2. 前置原则

- API schema 必须从当前官方 docs/实际响应确认，不能按记忆猜 request body。
- 先调用 `GET /v1/models`，不硬编码未经验证的 alias。
- API key 只从 environment 读取。
- 使用 async `httpx.AsyncClient` 和明确 connect/read/write/pool timeout。
- provider failure 不能产生 `ALLOW`。
- 不把五个独立判断压成一句 “Is this safe?”。

## 3. 建议文件

```text
backend/app/providers/
  base.py
  registry.py
  system_one.py
  errors.py
backend/app/services/
  risk_prompt.py        # only if needed; no policy thresholds here
backend/tests/
  test_provider_contract.py
  test_system_one_provider.py
  test_system_one_live.py   # opt-in marker only
docs/
  SYSTEM_ONE_FEASIBILITY.md
```

## 4. 30–45 分钟 early spike

在正式 provider 完成前先做：

1. 确认 key/base URL。
2. 调用 `GET /v1/models`，保存实际 model metadata（不保存 secret）。
3. 按官方 schema 构造最小 `POST /v1/systemone`。
4. 测试五类问题所支持的 question type。
5. 用 10–20 个真实数据派生的 ambiguous actions 调用。
6. 记录真实 response shape、probability/confidence semantics、latency 和错误形态。
7. 判断 signals 是否有足够 separation；若没有，先调整问题和 compact context。

所有结果明确标注日期、model、sample size 和是否 warm/cold。Spike 数字不是最终 benchmark。

## 5. Provider interface

`base.py` 定义：

```python
class DecisionProvider(Protocol):
    async def evaluate(self, state: AccountingState) -> RiskAssessment:
        ...
```

同时定义 typed errors：

- configuration/model discovery error
- timeout
- transport/unavailable
- authentication/authorization
- rate limit
- invalid request
- malformed/invalid response
- unsupported schema/model

不要让上层依赖 raw `httpx` exceptions。

## 6. System One request design

使用同一 compact AccountingState 构造五个 named questions：

- `goal_alignment`
- `duplicate_obligation_risk`
- `counterparty_change_risk`
- `missing_context`
- `action_anomaly`

每个问题：

- 使用 API 实际支持的 yes/no、choice 或 score type。
- 定义清楚 high/low score 方向。
- 避免把 deterministic facts 要求模型重新计算。
- 不包含 policy threshold 或最终 action 指令。
- 不暴露 `sim_*` ground truth。

Request serializer 应独立测试并 versioned，确保 baseline fairness 所用 context 不被悄悄改变。

## 7. Response parsing

Parser 必须：

- 验证所有 required named outputs。
- 验证 probability/score/confidence 范围。
- 区分 missing signal、null、wrong type 和 out-of-range。
- 记录 API/model 返回的真实 model identity。
- 使用 monotonic clock 测真实调用 latency。
- 不用默认 0 或默认高 confidence 填补 malformed response。

成功才生成完整 `RiskAssessment`。失败生成 typed provider failure，由 PolicyEngine 处理 fail-safe。

## 8. Retry and timeout policy

Hackathon 默认保持简单：

- 明确短 timeout，具体值集中配置。
- 只对确定 transient 的错误做有限 retry。
- retry 次数和 backoff 可审计。
- invalid response/auth error 不盲目 retry。
- 整体 deadline 不因 retry 无上限扩张。
- 每次 attempt 单独记录，最终 latency 定义清楚。

## 9. Testing checklist

### Contract and request

- [ ] provider 接受 `AccountingState` 并返回 `RiskAssessment`。
- [ ] 五个 signals 都存在且方向一致。
- [ ] request 不含 policy threshold/final action。
- [ ] request 不含 `sim_*` / provenance truth。
- [ ] model name 来源于 discovery/configured verified result。

### Response parsing

- [ ] valid response 正确映射全部 signals。
- [ ] missing question、renamed key、wrong type、out-of-range 均失败。
- [ ] malformed JSON / unexpected content type 被捕获。
- [ ] latency 字段来自 monotonic measurement，不是 fake value。
- [ ] provider/model metadata 正确保留。

### Failure behavior

- [ ] connect/read timeout。
- [ ] DNS/network unavailable。
- [ ] 401/403 auth failure。
- [ ] 429 rate limit。
- [ ] 5xx unavailable。
- [ ] model list empty / alias unavailable。
- [ ] retry exhaustion。
- [ ] 所有失败路径都不能返回可导致 auto-allow 的默认 assessment。

使用 `httpx.MockTransport` 或同等 fake transport；默认 CI 不访问网络。

### Live tests

- [ ] `@pytest.mark.live` 且需要 explicit opt-in env flag。
- [ ] 没有 key 时 skip，而不是失败整个离线 suite。
- [ ] 结果不包含 key/authorization header。
- [ ] live latency 与 mock test 明确分开。

## 10. Feasibility document

`SYSTEM_ONE_FEASIBILITY.md` 至少记录：

- API/model discovery 时间和结果
- exact supported request/response schema summary
- questions and types
- 10–20 cases 的真实 input lineage
- raw measured latency summary
- signal separation observations
- API failures/limitations
- go / revise questions / contingency decision

不宣称 System One 永远正确；typed output reliability 与 semantic accuracy 分开描述。

## 11. Exit criteria

- `/v1/models` 和 `/v1/systemone` 在真实项目案例上调用成功，或明确记录阻塞证据。
- 完整 provider contract 和 failure taxonomy 已测试。
- malformed/timeout/unavailable 不会导致 allow。
- 五个 decomposed signals 保留。
- 没有 hard-coded secret 或未经验证 model alias。
- live spike 结果可重现且不冒充最终 benchmark。

