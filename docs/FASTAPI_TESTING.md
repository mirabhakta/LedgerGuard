# FastAPI Testing Guide

这份文档用于本地、演示前和 CI 中验证 Yizhe 负责的 FastAPI/application pipeline。所有执行仍然是 `SIMULATED`，不会连接真实支付系统。

## 1. 启动隔离测试服务

建议使用临时数据库，避免污染 demo 数据：

```bash
export LEDGERGUARD_DB_PATH=/tmp/ledgerguard-fastapi-test.sqlite3
export LEDGERGUARD_CORS_ORIGINS=http://localhost:5173
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

第一次加载某个 company 会解析 sponsor YAML，因此冷请求明显慢于 warm request。演示前先调用一次 safe scenario 做 warm-up。

## 2. 一键黑盒 smoke test

保持服务运行，在另一个 terminal 执行：

```bash
.venv/bin/python tools/smoke_fastapi.py --base-url http://127.0.0.1:8000
```

成功输出：

```text
PASS: health, OpenAPI, CORS, ALLOW/idempotency, review/stale guard, BLOCK, context resume, SSE replay, pagination, and dashboard
```

它会实际验证：

- health 和 typed OpenAPI response schema；
- browser CORS preflight；
- safe payment `ALLOW -> SIMULATED`；
- idempotency key 不重复执行；
- destination change 等待审批、stale hash 返回 `409`、正确审批后执行；
- semantic duplicate `BLOCK` 且无 authorization/execution；
- missing context 补充 provenance 后重新评估；
- SSE `Last-Event-ID` replay；
- pagination `count/total` 和 dashboard aggregation。

## 3. 自动测试

FastAPI/application focused suite：

```bash
.venv/bin/python -m pytest -q \
  backend/tests/test_api_contract.py \
  backend/tests/test_event_bus.py \
  backend/tests/test_persistence_failure.py
```

完整回归：

```bash
.venv/bin/python -m compileall -q backend evaluation
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
```

Gemini provider 的离线 contract/error tests（不产生 API 费用）：

```bash
PYTHONPATH=. .venv/bin/pytest -q backend/tests/test_gemini_provider.py
```

默认服务的 Gemini 配置：

```bash
cp .env.example .env
# 编辑 .env，把 GEMINI_API_KEY= 后面填入真实 key
```

应用和测试会自动读取项目根目录的 `.env`。该文件已被 Git 忽略；
`.env.example` 不含 secret，可以提交。也支持 `GOOGLE_API_KEY`，同时存在时它优先。

FastAPI 请求使用 `"provider":"gemini"`。旧的 `"provider":"llm"` 已移除，
以免运行记录无法区分实际模型供应商。

外部 System One live test 默认跳过。只有在明确希望产生真实 API 调用时才运行：

```bash
RUN_TYPESAFE_LIVE_TESTS=1 TYPESAFE_API_KEY=... \
  .venv/bin/python -m pytest -q -m live backend/tests/test_system_one_live.py
```

Gemini live structured-output test 同样默认跳过；它会调用真实 API，只有明确需要时运行：

```bash
RUN_GEMINI_LIVE_TESTS=1 PYTHONPATH=. \
  .venv/bin/pytest -q -m live \
  backend/tests/test_gemini_live.py backend/tests/test_gemini_fastapi_live.py
```

## 4. 手工 HTTP 检查

### Health 与 OpenAPI

```bash
curl -sS http://127.0.0.1:8000/api/health | jq
curl -sS http://127.0.0.1:8000/openapi.json | jq '.paths | keys'
```

预期 health 为 `status=ok`、四个 providers、六个 scenarios。`POST /api/demo/run` 的 200 schema 应引用 `ActionDetailResponse`，不是任意 object。

本地 OpenJev 测试默认跳过。先按 [OPENJEV_SETUP.md](OPENJEV_SETUP.md) 启动独立
OpenJev server，再运行：

```bash
RUN_OPENJEV_LIVE_TESTS=1 PYTHONPATH=. \
  .venv/bin/pytest -q -m live backend/tests/test_openjev_live.py
```

FastAPI 请求使用 `"provider":"openjev"`。它是独立的开源 System One-style
baseline，不应在结果或 UI 中标记为官方 Jev。

### Safe hero flow

```bash
curl -sS -X POST http://127.0.0.1:8000/api/demo/run \
  -H 'Content-Type: application/json' \
  -d '{
    "scenario_id":"safe-normal-payment-001",
    "provider":"rules",
    "idempotency_key":"manual-safe-001"
  }' | jq '{action_id,status,decision:.policy_decision.final_action,execution:.execution_result.status,authorization:.execution_authorization.authorization_type}'
```

预期：`ALLOW`、`executed`、`SIMULATED`、`POLICY_ALLOW`。使用相同 idempotency key 重试必须返回同一个 `action_id`；换 scenario 重用该 key 必须返回 `409 IDEMPOTENCY_KEY_CONFLICT`。

### Approval flow

先运行 `destination-change-001`，保存返回的 `action_id` 和 `policy_decision.assessment_hash`：

```bash
curl -sS -X POST http://127.0.0.1:8000/api/actions/ACTION_ID/resolve \
  -H 'Content-Type: application/json' \
  -d '{
    "resolution":"approve",
    "actor":"reviewer@example.com",
    "assessment_hash":"EXACT_ASSESSMENT_HASH"
  }' | jq
```

错误 hash 必须返回 `409 STALE_REVIEW_RESPONSE`。成功后应有 `HUMAN_APPROVAL` authorization 和 `SIMULATED` execution。第二次 resolve 必须返回 `409 INVALID_STATE_TRANSITION`。

### BLOCK flow

```bash
curl -sS -X POST http://127.0.0.1:8000/api/demo/run \
  -H 'Content-Type: application/json' \
  -d '{"scenario_id":"semantic-duplicate-001","provider":"rules"}' \
  | jq '{decision:.policy_decision.final_action,reasons:.policy_decision.reason_codes,execution_result,execution_authorization}'
```

预期 `BLOCK`，且 execution 和 authorization 都是 `null`。

### Pagination、filters 和 dashboard

```bash
curl -sS 'http://127.0.0.1:8000/api/actions?final_action=ALLOW&limit=10&offset=0' | jq
curl -sS 'http://127.0.0.1:8000/api/actions?reason_code=POLICY_ALLOW' | jq
curl -sS http://127.0.0.1:8000/api/dashboard | jq
curl -sS http://127.0.0.1:8000/api/benchmarks | jq
```

`count` 是当前 page 数量，`total` 是 filter 后总数。Benchmark 只能显示已有 measured artifacts；没有时必须返回 `status=not_run`。

## 5. SSE 测试

实时连接：

```bash
curl -N http://127.0.0.1:8000/api/stream
```

在另一个 terminal 触发 scenario。事件应按真实节点进度出现：

```text
action_received
precheck_complete
provider_started                 # hard precheck BLOCK 时没有
risk_assessment_ready            # hard precheck BLOCK 时没有
policy_decision
execution_simulated | review_required | context_requested | action_blocked
```

断线回放：

```bash
curl -sS -H 'Last-Event-ID: 12' \
  'http://127.0.0.1:8000/api/stream?once=true'
```

返回必须从 event 13 开始。测试还覆盖超过 100 条事件的分页 replay、bounded queue 丢弃最旧消息，以及 subscriber cleanup。

## 6. Restart / SQLite 测试

1. 运行 `destination-change-001`，不要 resolve。
2. 正常停止 Uvicorn。
3. 使用同一个 `LEDGERGUARD_DB_PATH` 重启。
4. 提交正确 approval。
5. 确认 workflow 从 `*.checkpoints.sqlite3` 恢复并只执行一次。

数据库一致性：

```bash
sqlite3 /tmp/ledgerguard-fastapi-test.sqlite3 'PRAGMA integrity_check;'
sqlite3 /tmp/ledgerguard-fastapi-test.checkpoints.sqlite3 'PRAGMA integrity_check;'
```

两者都必须输出 `ok`。

## 7. Error/security checklist

- `{}` demo payload -> `422 VALIDATION_ERROR`。
- 不存在的 action -> `404 ACTION_NOT_FOUND`。
- 不存在的 scenario/provider -> stable `404` code。
- provider timeout/unavailable -> fail-safe decision，绝不自动执行。
- provider raw exception、API key、filesystem path 不出现在 HTTP response/SSE。
- malformed/extra financial fields 被 Pydantic 拒绝。
- persistence failure before execution intent -> `500 WORKFLOW_ERROR` 且无 execution。
- policy failure fallback 只能配置为 `REQUIRE_APPROVAL` 或 `BLOCK`。
- CORS origin 必须在 `LEDGERGUARD_CORS_ORIGINS`；不要在共享部署中使用 `*`。

## 8. 部署限制

Hackathon 版本建议单进程运行：

```bash
.venv/bin/uvicorn backend.app.main:app --workers 1
```

SQLite 和 in-memory live SSE fan-out 面向单实例 demo。多 worker/多实例时，已持久化 replay 仍可用，但跨 worker 的即时 push 需要 Redis/Postgres pub-sub 等共享 broadcaster。生产部署还需要 authentication/authorization、rate limiting、request-size limit、TLS/reverse proxy、backup 和 observability。
