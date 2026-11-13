# Agent-led V1 增量验收 — 2026-11-05

本轮 A–D 增量已实现并通过离线与当前范围的真实只读 SDK 验收。九个 MCP 工具名称保持，旧六工具 contract 1.1 保留，三个事实工具增至 2.1。业务 project.yaml 未修改，仍是 v1 / 24 proposed、3 unresolved、1 confirmed；本轮没有 git add/commit/push，也没有触发 CI、部署或远程状态修改。

契约：[INCREMENTAL_V1_CONTRACT.md](../docs/refactor/agent-led-initialization/INCREMENTAL_V1_CONTRACT.md)。调用 JSON、数据边界与迁移说明：[AGENT_LED_INCREMENTAL_V1.md](../docs/AGENT_LED_INCREMENTAL_V1.md)。机器结果：[incremental-v1-summary.json](reports/incremental-v1-summary.json)。既有初始化报告作为前阶段证据保留，不替换本轮数据。

## 实现及兼容性

| 目标 | 结果 |
|---|---|
| A GitLab | 原 jobs 仍按 Project/Pipeline 查询；新增 project_jobs、branch_jobs、pipeline_bridges，支持 status/manual/retried、显式分页与下游标识；空页不作无构建结论 |
| B Portainer | stack_service 按 Stack/Endpoint/精确 Compose key 服务端选取；仅返回目标的安全字段与 evidence/文件 revision，整文件输出超预算不阻断单服务 |
| C Schema | v1 可读且原 Schema 固定保留；v2 独立分支/ref、定义/执行、tag/digest、部署定义/运行观察、环境和版本比较；纯迁移仅输出候选，不写业务目录 |
| D 验证 | 226 tests、九工具兼容、合成 stdio E2E、当前范围真实 SDK、wheel 隔离安装与业务文件指纹检查通过 |

Schema v2 不猜旧 ci_job 的含义，不自动赋予环境或版本匹配。VersionMatch 的 matched/mismatched 需 evidence 与具体 digest/完整 commit SHA；latest 相等不产生版本确认。升级只改 schema_version，全部关系状态、审批、证据和备注保留；旧业务 v1 也通过冻结 v1 Schema 验证。

## 测试执行

- 改造前全库：208 passed（12.41s）。
- 事实新增先行测试：6 failed / 3 passed，复现新 operation 无实现、空列表无遗漏提示、单服务路径缺失。实现后相关 facts 回归 42 passed（6.81s）。
- Schema v2 先行：3 failed / 1 passed；实现后包含迁移/旧审批的针对性回归 29 passed（1.71s）。原先将 schema_version=2 当作非法的负例调整为 3；其余 v1 约束保留。新实例默认仍 v1，迁移显式选择 v2。
- 新 stdio→本机合成 HTTP E2E：1 passed（1.45s），实际枚举九工具、调用四种 Job/Bridge 操作、整文件截断与单服务成功，协议 stdout/Schema/文本一致性通过。
- 最终全库：**226 passed，0 failed/errors/skipped（23.08s）**。覆盖率 **97.63%**；行/分支详见机器摘要。`ruff check .`、strict mypy（49 files）通过。
- 离线 wheel 构建及临时隔离安装通过，确认实际从安装包导入新 details 模块、v1/v2 纯迁移、九工具和 revision 2.1 operation Schema。

本轮新增边界覆盖：分支过滤后空页仍有下一页、手动 Job、重试参数、异常游标/过宽页、401/403、不递归跨 Project、输入必填与互斥；Stack Endpoint 不符/越界/精确 key/未解析 YAML/无关无效服务/安全字段；迁移全状态/审批保留、typed details/scope/身份冲突、不可变版本比较与多分支/环境/版本。

示例生成第一次因复用 Python 对象而产生 YAML alias，被既有安全校验拒绝；改为无 alias 的序列化后再验证，不放宽安全规则。所有 fixtures/公开示例为合成数据。

## 当前范围真实只读结果

来源为独立标准 SDK 的实际 MCP stdio，新版 Cursor operation 调用未观察，不伪报 Host 已更新。私有坐标来自用户本轮明确范围、当前 project scope 和实际 API 返回，未猜 Project/Stack ID 或 Compose key。凭证由既有显式本机解析器处理，只进入受保护进程环境；没有禅道请求。

用于最终验收的 **21 次 MCP 调用返回 ok**（初轮 20 次加最终精确服务名复核 1 次；另有 2 次中间复核，不复用为最终版本证据），每次校验发布的输出 Schema、JSON 文本与 structuredContent 一致。分页标记不被当作输出完整；整文件预算截断是预期用例。

| 事实 | 观察结果 |
|---|---|
| Project Job 首页 | 3 条可见 Job 实例，有后续页 |
| 手动状态首页 | 3 条 manual Job，有后续页；未触发任何动作 |
| 三个分支的本次 Pipeline 样本 | 各从当前 ref 查询结果取页首一条，未假定等于之前 Cursor 的相同编号 |
| 各上游 Pipeline 普通 Job | 各为空，明确返回不能证明无构建及检查 bridges 的提示 |
| 各上游 bridge | 各 1 条，返回实际 downstream_pipeline；DCE 不自动扩展 |
| Host 显式查询同项目下游 | 先核对 Project 身份，再按观察到的下游 Pipeline ID 单独查询，各 2 个 Job 实例；不据此推断分支/环境/版本关系 |
| 分支过滤 | 两个当前 Project Job 页过滤后为空，但上游仍有下一页；提示继续分页，避免误判无历史 |
| 整 Stack File | 在显式 **8192 字节**输出预算下 OUTPUT_BUDGET_EXCEEDED / data=null |
| 精确 Compose Service | 同预算返回 1 条，最终代码复核 **3634 字节**，truncated=false、incomplete=false；含安全字段/证据/文件指纹 |

Compose key 从已授权保存文件中的实际 image 标识精确筛选得到唯一候选；未把镜像名称直接当作 key。原始 Compose 仅在内存解析，未保存。保存定义和运行观察始终独立，未写任何业务关系推理。

## 业务文件与迁移检查

真实文件 28 条关系，24 proposed / 3 unresolved / 1 confirmed。v1 读取通过，显式 v2 预览除 schema_version 外全部字段相同；只把预览保存在 DCE 私有运行目录。目标文件逐字指纹在本轮前后不变，未覆盖/写入/自动升级；现有确认、证据和备注保留。

实际可复制的 MCP JSON 只留 `.local/agent-led/incremental-v1/MCP_CALLS.md`，包含本轮观察到的 Pipeline ID 和 Compose key。公开文档使用合成坐标，不含真实拓扑/凭证。当前项目是否采用 v2 属于后续 Host 审核，不在本轮修改范围。

## 使用与限制

在 Cursor 的 MCP 页面把 dce 服务开关关闭再开启一次，并新建会话以载入新版参数；九个工具名称不变。branch_jobs 的页号属于上游 Project Job 页，空过滤结果不能跳过 pagination。更精确的执行追踪可从 pipelines/ref 到 jobs，再到 bridges/已授权下游逐段查询。

本轮只验证当前 Project/Stack 范围。手动状态、下游 Job 可见、标签相同都不等于构建/部署完成或版本一致；已有业务确认不由 DCE 自动扩展。此前其他平台权限和旧独立样本不在这次增量范围。所有本轮代码、文档、执行记录保持本地未提交。


## 收尾安全审查记录

补强了畸形 environment 列表的名称处理和 Job 预期标量字段检查，避免把嵌套配置作为名称/元数据输出。补强时引入服务名变量覆盖，回归出现 3 failed/223 passed；已定位并修正变量名，针对性 17 passed（1.48s），最终全库 226 passed（23.08s）。最终真实复核额外断言返回 name 等于请求的 Compose key，3634 字节、未截断且业务文件指纹不变；错误版本不作为最终验收证据。
