# Agent-led 重构续跑

先读根 AGENTS.md、README.md、GOALS.md、PLANS.md、harness/build-log.md、harness/test-results.md 和 harness/agent-led-acceptance.md。提案实际在 docs/refactor/agent-led-initialization/dce-agent-led-refactor/，读取 CHANGE_PROPOSAL.md 与 specs/01–07；以当前代码核对工具名和命令。

在本地分支 refactor/agent-led-project-init 查看 git status/log，不覆盖用户变更，不重做已经通过的阶段，不自动 push/merge。T0–T5 的本地交付与 T6 离线检查已完成；T2 独立产品模块树已按官方源码补齐，但实际实例和 T6 真实平台/Host 验收未完成，不得把文档状态当功能验收完成。

用户已给目标业务 workspace、本机凭证源、三平台 HTTP 地址并选择 Cursor。当前入口显式读取该授权本机文件，正文/值不得进入对话；默认 CLI 不自动加载。已在全局 Cursor 配置替换 dce 并备份，其他四服务保留。标准 SDK 已枚举九工具、完成 27 次真实读取；这些不是 Cursor Agent 实际调用的证明。不得读取私有日志、桌面凭证、真实图片缓存或原始 Compose secrets 找凭证。

最新离线 201 tests passed/98.09%，ruff/mypy（48 files）/最终 wheel 隔离检查通过。真实旧 Catalog 副本已先备份后迁移并保留 191 实体/219 边/219 证据/11 快照。私有项目草案位于 .local/agent-led/intake/project.proposed.yaml，23 条关系（22 proposed/1 unresolved/0 confirmed），具体 diff 已生成，业务目录未写；校验与纯 refresh 通过。继续从这里，不重做 T0–T5。

最新接续：用户已回传 Cursor 九工具（另有 Host mcp_auth）、三次真实成功调用与初始化对话；原可见文本只有 DCE result.、structuredContent 未进入模型，原三次 truncated 只能记 not_observable。九工具已修正为相同 JSON 文本/结构化信封，新增可选 image_output_budget（默认 null、最大 3MB），文本/双副本元数据仍受 output_budget 约束，Reader 原图仍限 2MB。当前 208 tests passed/97.93%，ruff/mypy/最终 wheel 检查通过；已授权的新 Bug 原生 PNG（382396 字节）经 stdio SDK 交付，模型接收未验证，无图落盘。

当前缺口：按私有 CURSOR_RECHECK.md 重载 Cursor，只补验 JSON 文本可见性与原生图片进模型；完整 683 行/23 关系草案的保存批准已询问，尚无批准，不把聊天里省略 relationships 的 diff 写入业务目录。module_tree 仍 403 Access not allowed，同 Token Bug 200；官方源码显示 tree/browse 独立方法权限，推断需管理员核对该读入口/产品范围，实际实例版本未确认，不重新索取 Token。旧独立 GitLab 范围在本次答复中未获明确授权，不重试或绕过。不得重新索取已有 Host 三次调用、图片样本、地址或工作区。

连接条件就绪后：
1. 核对明确授权的业务 workspace 和三平台 scope；不假设任何数字 ID/名称相关。
2. 按 docs/MCP_FACT_TOOLS.md 在真实 Host 配置受保护进程环境，reload 新 MCP 子进程/会话并枚举九工具。
3. 执行 prompts/agent-led/initialize.md，记录至少三次真实只读 calls；人工确认或记录 unresolved，Host 展示 diff 后保存并 dce project validate/复读。
4. 真实图片必须观察 Host 收到 MCP ImageContent，只有 SDK 布尔摘要不能证明模型看过。不得保存图片到公开仓库。
5. 用 module_tree 和授权 Product ID 验证实际 ZenTao 模块树/权限/分页；官方 v1 路由已核实，旧 modules 的 Bug 页信息仍仅部分目录。
6. 可先运行 .venv/bin/python scripts/check_agent_led_mcp.py --workspace <workspace> --config <non-secret.toml> --catalog <private-cache>；它只证明 SDK 的范围读取，不证明真实 Host。默认不读图片、Compose 或日志。
7. 先读本轮私有真实证据，不重复已成功请求：三份 Stack File 服务数 63/71/78，实际运行 namespace 8 页 78 个唯一 Service ID。GitLab Compose 源尚未重验；不能把保存配置、运行数量和旧报告合为同一事实。两个 Swarm mismatch 仍保留候选，不转 confirmed。旧独立样本需明确范围批准，过期 Pipeline/Job/附件诚实记录不可用。
8. 测试、更新 PLANS/build-log/test-results/验收与机器摘要，按阶段本地提交。未达所有完成标准不能标 goal complete。
