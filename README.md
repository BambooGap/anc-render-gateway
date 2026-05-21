# ANC Render Gateway

ANC Render Gateway 第一阶段只实现本地 Parser Kernel：把自然语言提示词编译成更稳定、可追踪的 Render Packet，并把模拟 RFS 审计失败归一化为可修复的 Patch Packet。

## 为什么先做 Parser Kernel

视频生成模型的不确定性很高。第一阶段先用确定性的本地内核解决提示词切片、物体拓扑锁定、正向约束改写、Source Map 回指、失败归因和补丁生成，证明“推拉窗纠错闭环”可以跑通。

当前不包含 FastAPI、数据库、Redis、云存储、真实视频 API、ComfyUI、真实 VLM 审计或前端页面。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 运行测试

```bash
pytest
```

## 运行 CLI demo

```bash
python -m anc_gateway.cli demo-sliding-window
```

demo 会编译“她轻轻推开了推拉窗，风吹进房间。”，输出包含“上下轨道、水平滑动”的 compiled prompt，模拟 `window_flipping_bug`，归一成 `object_rotation_error`，并生成 Level 2 修复补丁。

## Phase 2 API 服务

启动服务：

```bash
python -m anc_gateway.cli serve
```

等价的 uvicorn 命令：

```bash
uvicorn anc_gateway.api.app:app --reload
```

调用 `/compile`：

```bash
curl -X POST http://127.0.0.1:8000/compile \
  -H "Content-Type: application/json" \
  -d '{
    "state": {
      "id": "state_demo_001",
      "shot_id": "shot_001",
      "objects": [
        {
          "id": "window_01",
          "name": "推拉窗",
          "object_type": "sliding_window",
          "topology": {"dof": "horizontal_slide"}
        }
      ]
    },
    "render_contract": {"shot_id": "shot_001", "ruleset_fingerprint": "rc1"},
    "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。"
  }'
```

调用 `/audit`：

```bash
curl -X POST http://127.0.0.1:8000/audit \
  -H "Content-Type: application/json" \
  -d '{
    "audit": {
      "ok": false,
      "raw_signature": "window_flipping_bug",
      "bad_prompt_fragment_ref": "frag_001"
    },
    "packet": {
      "...": "使用 /compile 返回的完整 CompiledRenderPacket"
    }
  }'
```

调用 `/recover`：

```bash
curl -X POST http://127.0.0.1:8000/recover \
  -H "Content-Type: application/json" \
  -d '{
    "failure_record": {
      "...": "使用 /audit 返回的完整 FailureCacheRecord"
    }
  }'
```

## Phase 2.5 API 稳定性

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

返回：

```json
{"status": "ok"}
```

版本信息：

```bash
curl http://127.0.0.1:8000/version
```

返回：

```json
{
  "service": "anc-render-gateway",
  "phase": "5B-Manual",
  "compiler_version": "anc-parser-kernel/0.1.0",
  "ruleset_fingerprint": "rc1"
}
```

请求追踪：

- 如果请求 header 带 `X-Request-ID`，服务会沿用该值。
- 如果请求 header 不带 `X-Request-ID`，服务会生成 uuid4。
- 所有响应 header 都会返回 `X-Request-ID`。
- 为了兼容 Phase 2 已有 API，`/compile`、`/audit`、`/recover` 的成功响应体不额外包 `data`。

统一错误格式：

```json
{
  "error": {
    "code": "SOURCE_MAP_ATTRIBUTION_ERROR",
    "message": "Unknown source map fragment: frag_999",
    "request_id": "req-001"
  }
}
```

当前处理的 API 层错误包括：

- `SourceMapAttributionError`
- `ValueError`
- Pydantic / FastAPI 请求校验错误
- 未知异常

## Phase 3 轻量持久化

Phase 3 使用 SQLite + SQLAlchemy 2.x 保存 `/compile`、`/audit`、`/recover` 的结果，让一次性 API 调用变成可追踪的 Gateway Transaction 数据。

初始化数据库：

```bash
python -m anc_gateway.cli init-db
```

默认数据库路径：

```text
.anc_gateway/anc_gateway.db
```

通过环境变量覆盖数据库地址：

```bash
export ANC_GATEWAY_DB_URL="sqlite:////tmp/anc_gateway.db"
python -m anc_gateway.cli init-db
```

查看最近失败记录：

```bash
python -m anc_gateway.cli recent-failures
python -m anc_gateway.cli recent-failures --limit 10
```

也可以通过 API 查看：

```bash
curl "http://127.0.0.1:8000/storage/recent-failures?limit=20"
```

当前持久化内容包括：

- `CompileJob`: `/compile` 的输入、输出、condition hash、source map
- `PromptSourceMapRecord`: 每个 fragment 的原文、改写文本、命中规则
- `FailureRecord`: `/audit` 归因后的 failure signature、bad fragment、recovery policy
- `PatchRecord`: `/recover` 输出的 patch packet
- `GatewayTransaction`: 后续串联 compile -> audit -> recover 的事务骨架

## Phase 4 Mock Render Job System

Phase 4 增加本地 mock 渲染任务系统，用来模拟未来接入即梦、Veo、Kling、Runway 等真实视频 API 时的异步生命周期。当前仍不接真实视频 API，`mock_worker` 只生成本地 mock 状态和 `mock://` 视频地址。

创建 mock render job：

```bash
curl -X POST http://127.0.0.1:8000/render-jobs \
  -H "Content-Type: application/json" \
  -d '{
    "condition_hash": "use-condition-hash-from-compile",
    "compiled_prompt": "use-compiled-prompt-from-compile",
    "source_map": {"fragments": {}},
    "vendor": "mock",
    "model": "mock-video-v1",
    "metadata": {"seed": 1}
  }'
```

运行 mock render：

```bash
curl -X POST http://127.0.0.1:8000/render-jobs/{job_id}/run-mock
```

查询任务：

```bash
curl http://127.0.0.1:8000/render-jobs/{job_id}
curl "http://127.0.0.1:8000/render-jobs/recent?limit=20"
```

模拟失败：

```bash
curl -X POST http://127.0.0.1:8000/render-jobs/{job_id}/fail-mock \
  -H "Content-Type: application/json" \
  -d '{"error_message": "mock timeout"}'
```

CLI 演示完整链路：

```bash
python -m anc_gateway.cli mock-render-demo
```

后续真实视频 API 会以 vendor adapter 的形式替换或并列于 `mock_worker`，而不是改写 Parser Kernel 或 API contract。

## Phase 4.5 Vendor Adapter 抽象层

Phase 4.5 增加统一的 Vendor Adapter 抽象层，为后续接入 Veo、即梦、Kling、Runway、Seedance 等真实视频模型预留稳定边界。真实视频 API 不直接写进 route，route 只调用 registry 中注册的 adapter，这样厂商鉴权、提交、查询、取消、返回格式差异都被隔离在 adapter 内。

当前只实现 `mock` vendor adapter：

- `GET /vendors`
- `GET /vendors/mock/capabilities`
- `POST /render-jobs/{job_id}/submit-vendor`

`submit-vendor` 会根据 RenderJob 的 `vendor` 找到 adapter，并把结果写回本地 RenderJob：

- `external_job_id`
- `status`
- `video_uri`
- vendor raw response metadata

CLI 演示：

```bash
python -m anc_gateway.cli vendor-demo
```

后续 Phase 5 会新增真实 vendor adapter，例如：

```text
veo_adapter
jimeng_adapter
kling_adapter
runway_adapter
seedance_adapter
```

这些 adapter 会替换或并列于当前 `mock_adapter`，不改 Parser Kernel，也不改既有 API contract。

## Phase 5A HTTP Vendor Adapter 基础设施

Phase 5A 增加真实 HTTP Vendor Adapter 的通用底座，但仍然不接任何具体真实视频厂商。它解决所有厂商 adapter 都会遇到的共同问题：

- API Key 从环境变量读取
- HTTP JSON 请求
- timeout
- HTTP 错误
- JSON 解析错误
- 厂商状态映射
- 统一 submit/status/cancel 结果模型

当前新增 `fake-http` vendor，用 `httpx.MockTransport` 模拟 HTTP 厂商，不访问真实网络：

```bash
export FAKE_HTTP_API_KEY="local-test-key"
```

创建 `vendor=fake-http` 的 RenderJob 后，可以提交到 fake-http adapter：

```bash
curl -X POST http://127.0.0.1:8000/render-jobs/{job_id}/submit-vendor
```

查看已注册 vendor：

```bash
curl http://127.0.0.1:8000/vendors
curl http://127.0.0.1:8000/vendors/fake-http/capabilities
```

安全约束：

- 不要把 API Key 写进代码
- 不要把 API Key 写进 README
- 不要提交 `.env`
- 后续真实厂商的 key 必须通过环境变量读取，例如 `JIMENG_API_KEY`、`KLING_API_KEY`

当前仍未接真实视频厂商。Phase 5B 才会选择一个真实平台实现具体 adapter。

## Phase 5B-Manual Manual Vendor Workflow

如果暂时没有真实视频生成 API，可以使用 Manual Vendor Workflow。系统会生成可复制到网页端的视频生成提交包，用户手动去平台生成视频，再把 `result_video_uri` 或本地文件路径回填系统，继续走 `/audit` 和 `/recover`。

支持平台：

- `jimeng_web`
- `gemini_flow`
- `generic_web`

明确不支持：

- 模拟登录
- 抓取 cookie
- Playwright / Selenium 浏览器自动化
- 绕过平台限制

创建 manual job：

```bash
curl -X POST http://127.0.0.1:8000/manual-jobs \
  -H "Content-Type: application/json" \
  -d '{
    "condition_hash": "use-condition-hash-from-compile",
    "compiled_prompt": "use-compiled-prompt-from-compile",
    "source_map": {"fragments": {}},
    "platform": "generic_web",
    "visual_anchor_uri": null,
    "notes": "生成前手动检查提示词"
  }'
```

查询 manual job：

```bash
curl http://127.0.0.1:8000/manual-jobs/{manual_job_id}
curl "http://127.0.0.1:8000/manual-jobs/recent?limit=20"
```

手动生成视频后回填：

```bash
curl -X POST http://127.0.0.1:8000/manual-jobs/{manual_job_id}/complete \
  -H "Content-Type: application/json" \
  -d '{
    "result_video_uri": "file:///tmp/manual_video.mp4",
    "user_notes": "网页端手动生成完成"
  }'
```

标记失败：

```bash
curl -X POST http://127.0.0.1:8000/manual-jobs/{manual_job_id}/fail \
  -H "Content-Type: application/json" \
  -d '{"user_notes": "平台额度不足"}'
```

CLI 演示：

```bash
python -m anc_gateway.cli manual-demo
```

完成 manual job 后，可以用回填的视频路径作为审计对象的人工记录，继续通过 `/audit` 归因和 `/recover` 生成修复补丁。后续如果获得正式 API，再实现真实 Vendor Adapter，而不是用自动化绕过网页端限制。

## 当前限制

- 当前只支持规则式中文 Prompt 编译
- RFS 仍是 mock，不包含真实多模态审计
- 未接真实视频 API
- 未接数据库、Redis 或云存储
- 未接视觉锚点
- 未做多角色命名空间隔离
