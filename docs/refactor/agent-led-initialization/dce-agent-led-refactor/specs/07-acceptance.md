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

## 用户本地限定验收

- 使用用户明确授权的测试资源，真实身份与证据保留在本地受保护目录；公开样例保持合成。
- Stack、Endpoint和当前Swarm身份逐项核对；不匹配时标记冲突或未知，不假定环境状态。
- 当前源码配置、Stack保存配置、运行服务分别记录来源，不以数量相等判断版本一致。
- Compose与图片在授权范围内实际读取后才可比较；图片必须验证MCP Image Content是否到达模型。
- Pipeline/Job/Trace重新检查可访问性；过期或无权限就记录实际状态，不编造。
- 不同来源实例及平台的项目、仓库和缺陷不得自动绑定。

## Host 验收
至少一个真实 Cursor/Codex Host：MCP connect、tools/list、至少三个真实只读 tools/call；在当前业务项目中完成初始化对话；人工确认一条真实关系或明确记录 unresolved 原因；无未经授权写操作、无凭证泄漏。
