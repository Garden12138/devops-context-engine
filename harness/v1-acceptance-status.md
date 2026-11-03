# DCE V1.0 已实现能力验收状态

更新日期：2026-11-03。用户明确：业务 Bug 表仅作为真实输入案例，只验证 DCE 已开发功能。此前引入业务页面与修复回归作为验收门槛属于范围扩大，已纠正；无需浏览器或辅助功能权限。

**结论：本次限定范围的 V1 真实补验通过。** 实跑产品源码 discover、真实 BugContext、成功流水线诊断和六个 MCP 工具处理逻辑；不扩大为所有外部接口/路径均已验证。脱敏机器摘要见 [V1 真实补验摘要](reports/v1-live-summary.json)。

## 范围

验收既有三平台只读 Adapter、发现/静态解析、关系/证据、Catalog、CLI 和六个 MCP Tools，以及权限、分页、预算、脱敏与失败处理。不新增浏览器自动化或业务修复执行能力。

| 已实现能力 | 离线证据 | 当前真实证据 |
|---|---|---|
| 三平台只读 Adapter | 合成认证、分页、错误、编码及边界测试通过 | GitLab 五个仓库、ZenTao 十四个 Bug、Portainer 限定 Stack/服务读取成功 |
| 发现与静态解析 | 模块/CI/Compose/Swarm、快照差异测试通过 | 产品 AppServices.discover 对一个授权源码项目真实执行成功，固定 commit 读取三个元数据文件；识别六个 build_job，保留一条 CI incomplete 警告 |
| 关系与证据 | 确定规则、候选、审计与撤销通过 | 最新独立验收库 204 条直接观测、15 条业务候选；来源实例和平台 ID 分离，无自动 confirmed |
| Catalog | 迁移、幂等、历史及安全测试通过 | 捕获数据重复导入幂等；真实 discover 后独立库为 191 Entity / 219 Edge / 219 Evidence / 11 Snapshot，工具读取前后数量不变 |
| CLI | 所有既有命令的离线契约/子进程通过 | 捕获真实数据的两页列表、trace、mapping verify、stack inspect 五次通过 |
| MCP Catalog 读取工具 | 六工具离线成功路径通过 | 标准 SDK stdio 已有五次正向调用；本轮再经产品工具处理逻辑调用 project_context、service_trace、deployment_inspect、discovery_status 全部成功 |
| MCP 上游工具 | bug_context、pipeline_diagnose 离线成功路径通过 | 真实 BugContext（include_assets=false）成功，成功流水线诊断成功；均经既有 McpApplication.call_tool 与真实 HTTP，不是模拟响应 |
| Cursor 桌面版接入 | 标准 SDK stdio 与宿主独立验证 | 用户另行要求接入后，已安装全局 dce 配置并观察到 Cursor 启动 DCE 子进程；真实 Catalog 副本四类查询自检通过。Agent 内实际工具调用仍 not_verified，详见 reports/cursor-mcp-summary.json |
| 权限和输出边界 | 只读、最小 scope、预算、脱敏及不执行外部指令测试通过 | 六工具本轮处理全部成功，输出 519–12289 UTF-8 字节；受控出网 15 次 GitLab GET、1 次 Bug GET，另有一次已授权 v1 登录认证，无图片/Compose/trace 请求；旧 SDK 越界/未知写工具拒绝证据保留 |

产品离线回归为 139 passed，ruff 与 strict mypy 通过。真实验证发现的 HTTP 重复解压问题已经修复并通过 GitLab REST 复验；不是以报告或文档代替代码修复。

## 不作为 V1 未完成项

- 在业务网页点击、保存、审核，测试定时任务或业务回调；这些是业务系统自身的修复回归。
- 触发 CI、发布、部署、回滚或禅道状态回写；V1 不提供这些写能力。
- 浏览器自动化、GUI 权限和实际 Cursor/Grok Host 操作不作为原 V1 门槛；用户另行要求的 Cursor 接入已有配置及进程启动证据，Agent 内实际调用仍单列验证。
- 用临时验收脚本做完整发布指纹验收或保证某个业务 Bug 已修复；已取得的额外只读观察保留，不升级为产品功能或强制门槛。

## 仍需如实保留的限制

本轮只对一个源码项目执行 live discover，不代表更多项目、平台或版本差异全部覆盖。真实图片、Compose 原文、私有日志以及失败流水线 trace 分析未读取/未实跑；不据此声明这些真实路径通过。

BugContext 正确保留 BUSINESS_MAPPING_UNCONFIRMED，本例模块返回数为 0；十五条业务候选尚未人工确认。CI 静态解析一条 incomplete 提示保留，未执行脚本消除不确定性。这些是数据/证据边界，不能改成虚假的 confirmed 或声称业务 Bug 已修复。

三平台源快照来自不同时间；Portainer 相关工具本轮读取捕获后的 Catalog。标准 SDK stdio、真实上游工具处理与 Cursor 进程启动分别保留证据，不声称已完成 Cursor Agent 内实际调用或 Grok Host 操作。私有标识、地址、SHA、业务正文和报告仅在 gitignored 私有区；本文仅记录脱敏结论。
