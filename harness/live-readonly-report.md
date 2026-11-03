# 限定真实只读验证报告

验证日期：2026-11-02。结论：三平台在限定元数据范围取得成功认证和读取证据；已捕获元数据的 Catalog/CLI 本地集成通过。完整发现、部署指纹、业务功能及实际 Agent 接入仍未验证。

2026-11-03 范围说明：业务系统页面和修复回归不是 DCE V1 验收门槛。此报告保留原采集结果；新增 MCP stdio 与已实现能力的准确状态见 [V1 验收状态](v1-acceptance-status.md)，不因未执行业务回归认定 V1 功能缺失。

## 范围与证据

| 层次 | 实际执行 | 结果 |
|---|---|---|
| Git 远端 | 五个限定仓库的指定 refs 只读查询 | 成功；两个明确目标分支的 feature 包含关系已证实 |
| GitLab REST | 五个限定仓库的项目、ref、commit 与有限流水线查询 | 成功；两个明确目标分支的对应 SHA 流水线成功 |
| ZenTao v1 | 用户本机一次登录获取 Token，立即读取十四个指定 Bug 元数据 | 全部成功；记录状态不作为功能测试判定 |
| Portainer | 指定 Endpoint/Stack，Swarm ID 与 Namespace 标签一致性 | 成功；保留前一轮快照，不冒充当前最新状态 |
| Catalog | 捕获的真实白名单元数据规范化后导入两次 | 185 Entity / 213 Edge / 213 Evidence / 8 Snapshot；幂等 |
| CLI | 两页 Bug 列表、服务 trace、证据校验、Stack 查询 | 五次子进程通过，分页无重复，未超响应预算 |

198 条直接元数据关系为 `observed_verified`；15 条用户案例中的 Bug→仓库关系保持 `candidate`，无自动 `confirmed`。业务项目、GitLab 项目、Stack 的来源实例和 ID 分离。

本次调用使用产品 Reader 与 Adapter，发现并修复了已解码正文携带原内容编码被重复解压的问题；修复后真实 GitLab REST 复验成功。离线回归 139 passed、总体覆盖率 98.58%，见 [回归摘要](reports/http-encoding-summary.json)。

## 未覆盖项

- GitLab/ZenTao 与 Portainer 在不同时间采集，不构成同步的部署快照。
- 三个前端的部署分支尚未由人工明确确认；默认分支观测不代表部署分支。一个默认分支流水线为 manual，一个有限查询未命中当前 SHA，均不据此判定部署成功或失败。
- 运行引用缺少源码 revision；源码 commit→构建镜像→目标服务的完整指纹链尚未建立。digest 的存在也不能单独证明构建来源。
- Service 定义不代表副本健康；页面行为、请求次数、调度器、审核通过和回调闭环未执行。
- 未验证完整 live discover、BugContext 图片能力或实际 Cursor/Grok MCP Host；本地 Catalog/CLI 使用捕获元数据，没有模拟 API 响应。

## 安全与保留

用户在本机不回显输入凭证，进程内使用，不保存值。唯一 POST 为一次禅道 v1 登录认证；未调用业务写接口。未获取图片、源码 raw、job trace 或 StackFile，未触发构建/部署、审核、回调或禅道回写。

本报告只保留脱敏结论。真实案例、资源标识、地址、版本、采集时间和 CLI 输出仅位于 gitignored 私有目录，未加入 fixtures 或 Git。旧报告保持原样；私有汇总明确记录每个平台的来源报告与时间。
