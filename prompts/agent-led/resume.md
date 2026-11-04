# Agent-led 重构续跑

先读根 AGENTS.md、README.md、GOALS.md、PLANS.md、harness/build-log.md、harness/test-results.md 和 harness/agent-led-acceptance.md。提案实际在 docs/refactor/agent-led-initialization/dce-agent-led-refactor/，读取 CHANGE_PROPOSAL.md 与 specs/01–07；以当前代码核对工具名和命令。

在本地分支 refactor/agent-led-project-init 查看 git status/log，不覆盖用户变更，不重做已经通过的阶段，不自动 push/merge。T0–T5 的本地交付与 T6 离线检查已完成；T2 独立产品模块树已按官方源码补齐，但实际实例和 T6 真实平台/Host 验收未完成，不得把文档状态当功能验收完成。

当前阻塞是目标业务 workspace 未给出、当前 DCE 子进程环境三平台配置均缺失、当前 Host 未挂载 DCE MCP。旧 Cursor 启动/旧六工具证据不是本轮 Host 验收；不能读取 .env、Token 文件、私有日志、真实图片缓存或原始 Compose secrets 找凭证。

连接条件就绪后：
1. 核对明确授权的业务 workspace 和三平台 scope；不假设任何数字 ID/名称相关。
2. 按 docs/MCP_FACT_TOOLS.md 在真实 Host 配置受保护进程环境，reload 新 MCP 子进程/会话并枚举九工具。
3. 执行 prompts/agent-led/initialize.md，记录至少三次真实只读 calls；人工确认或记录 unresolved，Host 展示 diff 后保存并 dce project validate/复读。
4. 真实图片必须观察 Host 收到 MCP ImageContent，只有 SDK 布尔摘要不能证明模型看过。不得保存图片到公开仓库。
5. 用 module_tree 和授权 Product ID 验证实际 ZenTao 模块树/权限/分页；官方 v1 路由已核实，旧 modules 的 Bug 页信息仍仅部分目录。
6. 可先运行 .venv/bin/python scripts/check_agent_led_mcp.py --workspace <workspace> --config <non-secret.toml> --catalog <private-cache>；它只证明 SDK 的范围读取，不证明真实 Host。默认不读图片、Compose 或日志。
7. 分别重读真实样本，不把 Swarm mismatch/数量相等/相似名字转为 confirmed。过期 Pipeline/Job/附件诚实记录不可用。
8. 测试、更新 PLANS/build-log/test-results/验收与机器摘要，按阶段本地提交。未达所有完成标准不能标 goal complete。
