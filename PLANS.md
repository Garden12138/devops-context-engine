# V1.0 执行总计划（长任务的唯一状态入口）

## 阶段定义

| 顺序 | 阶段 | 可交付产物 | 验收门槛 |
|---|---|---|---|
| T0 | 项目初始化 | 包管理、lint/typecheck/test、CLI 入口、配置与脱敏 | 离线测试启动成功 |
| T1 | Adapter | ZenTao/GitLab/Portainer 只读接口 | 模拟服务测试 + 错误/分页/授权测试 |
| T2 | Discovery | Repo/Module/CI/Compose/Swarm 解析 | 合成多模块、多服务、历史 Stack 场景通过 |
| T3 | Catalog | Entity/Edge/Evidence/Snapshot/ScanRun/Review 持久化 | 迁移、幂等、版本、去重测试通过 |
| T4 | Mapping | 规则关联 + AI 可选候选 + 审核 | 不自动确认模糊关系，证据可追溯 |
| T5 | CLI | init/discover/catalog/trace/bug context/mapping review | CLI 契约、退出码与安全输出通过 |
| T6 | MCP | 只读工具，CLI 共用服务层 | MCP 离线集成契约、最小输出验证 |
| T7 | E2E 与文档 | fixtures、测试报告、内网 smoke 指南 | 所有 P0、质量门槛、无泄密 |

## 运行纪律

当前进度（2026-11-02）：T0–T7 passed（离线目标完成）；本地分支 `work/dce-v1-offline`；三平台限定元数据只读核验及捕获数据 Catalog/CLI 通过。
离线基线：133 tests，总体覆盖率 98.58%（行 99.18%、纯分支 96.65%）；ruff、strict mypy、CLI/MCP、独立 wheel 安装通过。
最新 HTTP 修复回归：139 tests，总体 98.58%（行 99.19%、纯分支 96.66%），ruff 与 strict mypy 通过；摘要见 harness/reports/http-encoding-summary.json。
基线逐项证据：harness/acceptance-report.md。完整真实链路与实际 Agent 接入 not_verified。

- 一次只推进一个阶段，测试不过不跳阶段；阶段完成记录测试命令、退出码与摘要。
- 当前阶段以 `harness/build-log.md` 标记为准；每个阶段前更新进度；若不存在，创建它。
- 每阶段在 `harness/context/TN.md` 记录结构变化、关键假设、实施决策、待解决点。避免长上下文崩溃后失去信息。
- API 版本差异应先能力探测，不在未验证条件下假设某路由支持写操作。
- 每阶段可自动本地提交小批量代码；**禁止自动推送、改动公司 GitLab/Portainer/ZenTao 资源**。
- 若涉及需要人工批准的操作：创建待办/阻塞记录并推进其他安全任务；不得绕过权限。

## 真实案例验证接续（2026-11-02）

- 用户提供一个包含 14 个 Bug、5 组组件及最后回调闭环的真实案例，授权推进限定范围的只读验证。
- 已核对本机 5 个相关 Git 仓库的元数据、模块标记与本地分支；其中 2 条指定目标分支的提交包含关系可本地证实。
- 本地引用不代表远端最新版本、Bug 修复正确性、构建成功或实际部署；真实平台和功能验收仍为 `not_verified`。
- 实跑 `.venv/bin/dce doctor --live --read-only`：exit 2，三平台均因未配置而返回 `AUTH_FAILED`，未发出平台请求。
- 现有远端需要 HTTP；已请求按 SECURITY 的明确放行，答复前不联网。还需安全连接方式、测试环境入口及可信资源范围。
- 本次完整案例、版本和证据仅保留在 gitignored 的 `.local/live-validation/`；公开记录不包含真实资源名称、地址或 ID。
- 接续先获取缺失连接条件，再核对指定 ref；现有 `discover` 只读取默认分支，不能代替案例指定分支的验证。

接续进展（同日）：用户已在私有表中确认测试环境及目标 Endpoint/Stack，并允许 GitLab HTTP 只读查询。五个限定仓库的真实 `ls-remote` 已成功；两个明确目标分支均包含相应远端 feature HEAD。三个前端的实际部署分支尚待确认，默认分支不作为部署事实。GitLab REST、ZenTao、Portainer 与功能回归仍 `not_verified`；已提供本机不回显输入凭证的限定 API 核验入口，等待用户在本机运行。

首轮 API 实跑（同日）：GitLab/Portainer 为 `NETWORK_UNAVAILABLE`；ZenTao 首个 Bug 为 `AUTH_FAILED`，余项未请求。随后在授权执行器做无凭证诊断，三平台直连均可建立 TCP 并返回 JSON HTTP 响应；这不能证明用户终端当时的网络条件或 API 凭证有效。私有入口已增加同终端无凭证预检、安全异常分类和单段凭证校验，14 项安全检查通过；需用户再次在本机输入凭证，收集可定位的诊断。尚未取得认证成功或业务功能通过的证据。

第二轮 API 实跑（同日）：Portainer 已通过认证及 Endpoint/Swarm/Namespace 一致性核对，实际服务定义与 digest 证据仅保存在私有报告；没有源码 revision，健康与部署版本仍未验证。GitLab 底层为 `DecodingError`：已用合成 gzip/deflate 流复现 Reader 重复解压并修复，同时将损坏编码归为 `INVALID_PAYLOAD` 而非可重试网络错误。ZenTao 仍 401；用户确认凭证来自 v1 登录，私有入口已支持一次现取 v1 Token 后立即执行限定 GET，登录不附旧 Token、不重试、不保存凭证。等待只重试 GitLab/ZenTao 的新报告，保留 Portainer 成功证据，不重复索取其凭证。

第三轮 API 实跑（同日）：GitLab 修复后五个仓库的限定元数据读取成功；ZenTao 现取 v1 Token 后十四个 Bug 全部读取成功。结合前轮 Portainer 保留快照，三平台均取得实际成功证据；明确各自采集时间不同。将已捕获白名单元数据导入独立私有 Catalog，185 个实体、213 条关系、213 条证据、8 个快照；重复导入幂等、五次 CLI 查询通过。15 条 Bug→仓库关系仍为 candidate，无自动 confirmed。脱敏结论见 harness/live-readonly-report.md；无需再次运行同一轮认证检查。后续缺口为前端实际部署分支、源码/镜像/运行版本链与页面/审核/回调回归；尚未验证完整 live discover 或实际 Agent Host。

## 约定

- 以 `.env.example` 为示例，真实配置 `.env` gitignored。
- AI Provider 默认关闭；无 API Key 时规则发现和人工审核仍可用。
- 真正的自动构建/部署在 V1.2/V2.0 单独规划，不因为长任务执行就提前实现。
- 即使对话因环境/额度中断，后续只需将 `prompts/RESUME.md` 发给 Agent。
