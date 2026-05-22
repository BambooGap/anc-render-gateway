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
  "phase": "6C",
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

## Phase 5C Manual RFS Audit Workflow

Manual RFS Audit Workflow 用于没有真实 VLM 审计 API 的阶段。用户不需要手写完整 `RFSAuditResult`，只需要选择错误类型、错误 fragment 和备注，系统会自动生成标准审计结果，复用现有 failure normalizer，并保存 `ManualAudit` 和 `FailureRecord`。

提交 manual audit：

```bash
curl -X POST http://127.0.0.1:8000/manual-audits \
  -H "Content-Type: application/json" \
  -d '{
    "manual_job_id": "manual-job-id",
    "bad_prompt_fragment_ref": "frag_001",
    "failure_type": "window_flipping_bug",
    "notes": "窗户被生成成向外翻转"
  }'
```

支持的 `failure_type`：

- `window_flipping_bug`
- `hand_not_touching_panel`
- `extra_limb_generated`
- `visual_anchor_ignored`
- `custom`

`custom` 需要填写 `notes`。如果不传 `rfs_scores`，系统会使用默认人工审计分数：

```json
{
  "overall": 0.5,
  "manual_review": 1.0
}
```

查看最近 manual audits：

```bash
curl "http://127.0.0.1:8000/manual-audits/recent?limit=20"
```

从 manual audit 进入 recover：

1. `POST /manual-audits` 返回 `recovery_policy`、`suggested_positive_lock` 和 `failure_record_id`
2. 使用同一响应中的 failure 信息构造 `FailureCacheRecord`
3. 调用 `POST /recover`

CLI 演示：

```bash
python -m anc_gateway.cli manual-audit-demo
```

后续接入真实 VLM Auditor 时，可以替换 manual audit 的创建来源，但保留当前 `RFSAuditResult -> FailureRecord -> PatchPacket` 的主链路。

## Phase 6A Manual Workflow Web Console

Phase 6A 增加一个极简 Web Console，用 FastAPI 托管静态 HTML/CSS/JS，不引入 Vue、React、Next.js、npm 构建系统或外部 CDN。

启动：

```bash
python -m anc_gateway.cli console
```

浏览器打开：

```text
http://127.0.0.1:8000/console
```

Web Console 支持完整人工流程：

1. 输入 `raw_prompt` 并调用 `/compile`
2. 使用 compiled prompt 创建 `/manual-jobs`
3. 手动去网页端生成视频
4. 回填 `result_video_uri`
5. 提交 `/manual-audits`
6. 使用 `failure_record_id` 调用 `/failures/{failure_record_id}/recover`
7. 查看最近 manual jobs、manual audits、failures

Console 行为：

- 所有请求都带 `X-Request-ID`
- 页面顶部显示当前 `request_id`
- 错误以统一结构显示 `code/message/request_id`
- JSON 输出使用 `pre`
- `compiled_prompt` 和 `copy_instructions` 提供 Copy 按钮

当前仍不包含真实视频 API、真实 VLM、登录系统、Redis、云存储或浏览器自动化。

## Phase 6A.1 Console Usability Patch

Phase 6A.1 只优化 Console 可读性和复制体验，不引入前端框架、npm 构建系统、真实视频 API、真实 VLM、登录系统、云存储或浏览器自动化。

改进内容：

- 长中文 prompt、copy instructions 和 JSON 输出会自动换行，减少横向滚动。
- Manual Audit 区域显示 `source_map` fragment 快捷列表，可以直接点击 `frag_001` 等片段回填 `bad_prompt_fragment_ref`。
- Recover 区域增加 `Copy Patch Prompt`，优先复制 `patch_prompt`，方便下一轮网页端生成。

## Phase 6B Attempt Loop / 多轮修复工作区

Phase 6B 在不破坏单次 Console 流程的前提下，增加 Case / Attempt 工作区，用来记录同一个镜头的多轮人工生成、审计和修复。

新增 API：

- `POST /cases`
- `GET /cases/{case_id}`
- `GET /cases/recent?limit=20`
- `POST /cases/{case_id}/attempts`
- `GET /cases/{case_id}/attempts`
- `GET /attempts/{attempt_id}`
- `POST /attempts/{attempt_id}/manual-job`
- `POST /attempts/{attempt_id}/manual-audit`
- `POST /attempts/{attempt_id}/patch`

Console 的 Workspace 区域支持：

1. 创建 Case
2. 将当前 compile 结果保存为 Attempt
3. 自动挂接 manual job、manual audit 和 patch packet
4. 用上一轮 patch packet 生成下一轮 attempt prompt

CLI 演示：

```bash
python -m anc_gateway.cli attempt-loop-demo
```

当前仍不包含真实视频 API、真实 VLM、登录系统、Redis、云存储、Playwright/Selenium、模拟登录或抓 cookie。

## Phase 6B.1 Attempt Lifecycle Polish

Phase 6B.1 在轻量 Attempt Loop 上补齐生命周期操作和复盘导出，仍保持单次 Console 流程与 Workspace 区域可用。

新增 API：

- `POST /attempts/{attempt_id}/accept`：接受当前 attempt，可用 `accept_case=true` 同步将 case 标记为 `ACCEPTED`。
- `POST /attempts/{attempt_id}/reject`：拒绝当前 attempt，保存 notes，并将状态标记为 `REJECTED`。
- `POST /cases/{case_id}/archive`：归档 case。
- `POST /cases/{case_id}/reopen`：将 case 重新标记为 `ACTIVE`。
- `POST /attempts/{attempt_id}/next`：基于上一轮 prompt 和 patch packet / patch prompt 创建下一轮 attempt，避免重复追加完全相同的修复约束。
- `GET /cases/{case_id}/timeline`：按 `attempt_index` 升序返回面向 Console 展示的时间线。
- `GET /cases/{case_id}/export.md`：导出 Obsidian 友好的 Markdown 复盘。

Console Workspace 增加：

1. `Accept Attempt`
2. `Archive Case`
3. `Export Markdown`
4. `timeline` 展示区

CLI 演示：

```bash
python -m anc_gateway.cli export-case-demo
```

导出的 Markdown 可以直接复制到 Obsidian 新笔记，或通过 Console 的 `Export Markdown` 打开后保存为 `.md` 文件。内容包含 Case 标题、Base Prompt、每轮 Attempt 的状态、Raw/Compiled Prompt、结果视频 URI、Failure/Patch Record ID、Notes，以及自动生成的 Lessons Learned。

当前仍不包含真实视频 API、真实 VLM、Redis、云存储、登录系统、Playwright/Selenium、模拟登录或抓 cookie。

## Phase 6B.2 Post-Acceptance Usability Polish

Phase 6B.2 修复 Console 交互刷新问题，并增强 Case Markdown Export，让导出的 Obsidian 文档包含完整 Patch Prompt / Positive Lock / Recovery Policy 信息。

Console 自动刷新：

- 所有主要操作成功后自动刷新相关区域（Recent Manual Jobs、Recent Manual Audits、Recent Failures、Recent Cases、Timeline、Attempts）
- 新增统一刷新函数：`refreshRecentPanels()`、`refreshCurrentCase()`、`refreshTimeline()`、`refreshWorkspaceState()`
- 页面顶部显示轻量状态提示（如 "Updated"、"Timeline refreshed"、"Case archived"）
- 新增 Recent Cases 区域，支持查看和选择历史 Case

Export Markdown 增强：

- 每个 Attempt 如果有关联 Failure Record，导出完整的失败归因信息：
  - Failure Signature
  - Failure Category
  - Bad Prompt Fragment Ref
  - Bad Prompt Fragment
  - Recovery Policy
  - Suggested Positive Lock
- 每个 Attempt 如果有关联 Patch Record，导出完整的修复补丁信息：
  - Recovery Policy
  - Target Fragment Ref
  - Positive Lock
- 如果某些字段不存在，自动跳过，不输出 null
- Prompt 使用 code block 格式，便于 Obsidian 阅读

README 修正：

- `/version` 示例 phase 从 "6A" 更新为 "6B"
- 当前限制中"未接数据库"改为"当前仅使用本地 SQLite，未接 PostgreSQL/Redis/云存储"

当前仍不包含真实视频 API、真实 VLM、Redis、云存储、登录系统、Playwright/Selenium、模拟登录或抓 cookie。

## Phase 6B.3 Data Validation Hotfix

Phase 6B.3 修复 `result_video_uri` 为空字符串时被接受的问题。

修复内容：

- `CompleteManualJobRequest` 增加 Pydantic v2 `field_validator`：
  - `result_video_uri` 必须是非空字符串
  - 自动 strip 前后空格
  - 空字符串或只有空格时返回 422 错误
- Console 前端增加校验：
  - `result_video_uri` 为空或只有空格时，不发送请求
  - 页面内显示错误提示："result_video_uri is required."
  - 不使用 alert

合法示例：

- `file:///tmp/manual_video.mp4`
- `mock://renders/example.mp4`
- `https://example.com/video.mp4`

非法示例：

- `""`（空字符串）
- `"   "`（只有空格）
- `"\t\n"`（只有空白字符）

当前仍不包含真实视频 API、真实 VLM、Redis、云存储、登录系统、Playwright/Selenium、模拟登录或抓 cookie。

## Phase 6C PromptOps Casebase MVP

Phase 6C 增加 PromptOps Casebase 模块，提供可搜索、可统计、可推荐的案例库，让历史失败经验和修复补丁可以被复用。

新增 API：

- `GET /casebase/search`：按 failure_signature、failure_category、raw_failure_type 或文本搜索案例
- `GET /casebase/stats/failures`：查看 failure signature 统计，按出现次数降序排列
- `GET /casebase/patches`：查看最近保存的 Patch Record
- `POST /casebase/recommend-patches`：根据 failure signature 和可选文本片段推荐修复补丁

推荐策略：

- 精确 failure_signature 匹配（confidence=0.9）
- 同 failure_category 匹配（confidence=0.7）
- bad_prompt_fragment 文本相似匹配（confidence=0.5）

Console Casebase 区域：

- 搜索面板：输入文本或 failure_signature 过滤
- 推荐面板：输入 failure_signature 获取补丁推荐
- Failure Stats：查看 failure signature 出现次数
- Recent Patches：查看最近保存的修复补丁

CLI 演示：

```bash
python -m anc_gateway.cli casebase-demo
```

当前仍不包含真实视频 API、真实 VLM、Redis、云存储、登录系统、Playwright/Selenium、模拟登录或抓 cookie。

## Phase 6C.1 Context-Aware Patch Packet

Phase 6C.1 让 Patch Packet 生成具备基础场景感知能力。之前 `build_patch_packet` 只根据 `failure_signature` 选模板，导致 `object_rotation_error` 对推拉窗和阀门生成相同的"窗扇"补丁。

核心改变：

- 新增 `anc_gateway/recovery/context.py`：`infer_object_context()` 根据 `failure_signature` + `bad_prompt_fragment` + `notes` 推断对象类型和运动模型
- 改造 `anc_gateway/recovery/patch_packet.py`：`build_patch_packet()` 先推断上下文，再根据 `failure_signature + object_type + motion_model` 选择模板
- `PatchPacket` 新增 `patch_context` 字段，记录推断的对象类型、运动模型、置信度和证据

支持的对象类型：

| object_type | 触发条件 | motion_model |
|---|---|---|
| sliding_window | 推拉窗/窗扇/上下轨道 | horizontal_track_slide |
| valve | 阀门/中心轴/顺时针 | center_axis_rotation |
| hinged_door | 门把手/铰链/门板 | hinge_rotation |
| drawer | 抽屉/滑轨/拉出 | drawer_slide |
| button_panel | 按钮/面板/按下 | surface_contact |
| human_body | extra_limb_generated/多出肢体 | body_structure_lock |
| visual_anchor | visual_anchor_ignored/场景跳变 | scene_continuity_lock |
| generic_object | 兜底 | unknown |

效果对比：

| 场景 | 之前 | 之后 |
|---|---|---|
| 推拉窗 + object_rotation_error | 窗扇沿轨道滑动 ✅ | 窗扇沿轨道滑动 ✅ |
| 阀门 + object_rotation_error | 窗扇沿轨道滑动 ❌ | 阀门围绕中心轴旋转 ✅ |
| 门 + object_rotation_error | 窗扇沿轨道滑动 ❌ | 门板绕铰链轴旋转 ✅ |
| 抽屉 + object_rotation_error | 窗扇沿轨道滑动 ❌ | 抽屉沿滑轨平移 ✅ |
| extra_limb_generated | 泛化物理约束 ❌ | 固定肢体数量/五根手指 ✅ |

CLI 演示：

```bash
python -m anc_gateway.cli patch-context-demo
```

当前仍不使用 LLM、向量数据库、真实 VLM、真实视频 API。

## 当前限制

- 当前只支持规则式中文 Prompt 编译
- RFS 仍是 mock，不包含真实多模态审计
- 未接真实视频 API
- 当前仅使用本地 SQLite，未接 PostgreSQL/Redis/云存储
- 未接视觉锚点
- 未做多角色命名空间隔离
