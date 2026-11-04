# 07 — 验收标准

## DCE 能力层
- 三平台连接可独立检查。
- 只读工具分页/截断/超时/权限错误可解释。
- MCP stdout 无普通日志；凭证不泄漏。
- 图片能力明确区分“URL 可用”和“Image Content 已送达”。
- Compose/CI 解析只输出事实，不输出跨平台业务推理。

## Agent 初始化
- 识别 workspace、Git roots、Git Remote、模块和构建入口。
- 根据本地证据缩小平台查询范围。
- 形成多对多关系候选和 evidence。
- 用户确认前关系不能标记 confirmed。
- `.dce/project.yaml` 可校验、可复读。
- 两个 workspace 初始化后关系互相隔离。

## 维护
- refresh 保留人工确认和备注。
- 新关系先 proposed。
- 证据变化标记 stale/conflicted。
- 拒绝关系不会被下一次扫描自动恢复。
- 文件修改前展示 diff。

## 真实样本
- Stack 31 曾匹配当前 Endpoint 1 Swarm ID；19/21 曾不匹配。验收时重读。
- GitLab Compose 78、Stack 21 Compose 71、Swarm namespace 78 必须分别记录来源；不能仅按数量判定一致。
- Stack 31 Compose 必须实际读取后才可比较。
- Bug 4314 图片必须验证 MCP Image Content 是否真正送达模型。
- Pipeline 22154/Job 63820 重新检查可访问性；过期就标记不可用，不得编造。
- `link-forge` Project 314 与 Bug 4314 不得假设相关。

## Host 验收
至少一个真实 Cursor/Codex Host：MCP connect、tools/list、至少三个真实只读 tools/call；在当前业务项目中完成初始化对话；人工确认一条真实关系或明确记录 unresolved 原因；无未经授权写操作、无凭证泄漏。
