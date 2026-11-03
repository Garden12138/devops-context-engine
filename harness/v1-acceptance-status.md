# DCE V1.0 已实现能力验收状态

更新日期：2026-11-03。用户明确：业务 Bug 表仅作为真实输入案例，只验证 DCE 已开发功能。此前引入业务页面与修复回归作为验收门槛属于范围扩大，已纠正；无需浏览器或辅助功能权限。

## 范围

验收既有三平台只读 Adapter、发现/静态解析、关系/证据、Catalog、CLI 和六个 MCP Tools，以及权限、分页、预算、脱敏与失败处理。不新增浏览器自动化或业务修复执行能力。

| 已实现能力 | 离线证据 | 当前真实证据 |
|---|---|---|
| 三平台只读 Adapter | 合成认证、分页、错误、编码及边界测试通过 | GitLab 五个仓库、ZenTao 十四个 Bug、Portainer 限定 Stack/服务读取成功 |
| 发现与静态解析 | 模块/CI/Compose/Swarm、快照差异测试通过 | 完整 live discover 尚未实跑；不以私有补充脚本代替产品 discover 验收 |
| 关系与证据 | 确定规则、候选、审计与撤销通过 | 198 条直接观测、15 条业务候选；来源实例和平台 ID 分离，无自动 confirmed |
| Catalog | 迁移、幂等、历史及安全测试通过 | 185 Entity / 213 Edge / 213 Evidence / 8 Snapshot；捕获数据重复导入幂等 |
| CLI | 所有既有命令的离线契约/子进程通过 | 捕获真实数据的两页列表、trace、mapping verify、stack inspect 五次通过 |
| MCP Catalog 读取工具 | 六工具离线成功路径通过 | 标准 SDK stdio：project_context 两个来源、service_trace、deployment_inspect、discovery_status，共五次成功调用 |
| MCP 上游工具 | bug_context、pipeline_diagnose 离线成功路径通过 | 本轮仅验证越界 PERMISSION_DENIED；真实上游成功调用仍 not_verified |
| 权限和输出边界 | 只读、最小 scope、预算、脱敏及不执行外部指令测试通过 | 六个工具只读声明正确；未知写工具 NOT_FOUND；输出未截断且小于 16 KB，Catalog 数量和十五条候选未改变 |

产品离线回归为 139 passed，ruff 与 strict mypy 通过。真实验证发现的 HTTP 重复解压问题已经修复并通过 GitLab REST 复验；不是以报告或文档代替代码修复。

## 不作为 V1 未完成项

- 在业务网页点击、保存、审核，测试定时任务或业务回调；这些是业务系统自身的修复回归。
- 触发 CI、发布、部署、回滚或禅道状态回写；V1 不提供这些写能力。
- 浏览器自动化、GUI 权限和实际 Cursor/Grok Host 操作；既有 MCP 契约以 SDK 客户端验证，实际 Host 接入单列后续验证。
- 用临时验收脚本做完整发布指纹验收或保证某个业务 Bug 已修复；已取得的额外只读观察保留，不升级为产品功能或强制门槛。

## 仍需如实保留的限制

完整 live discover、MCP bug_context/pipeline_diagnose 真实上游成功路径尚未实跑；真实图片和私有日志未读取。不能把 API 元数据成功等同于这些路径通过，也不能把允许保留 unknown/candidate 的模型结果视作实现缺失。

三平台源快照来自不同时间，SDK 此轮读取捕获后的 Catalog，不代表同步重查远端。私有标识、地址、SHA、业务正文和报告仅在 gitignored 私有区；本文仅记录脱敏结论。
