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

## 当前限制

- 当前只支持规则式中文 Prompt 编译
- RFS 仍是 mock，不包含真实多模态审计
- 未接真实视频 API
- 未接视觉锚点
- 未做多角色命名空间隔离
