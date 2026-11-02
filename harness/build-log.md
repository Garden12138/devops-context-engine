# Agent 执行日志

状态：OFFLINE_COMPLETE
当前阶段：T0–T7 全部离线验收通过
最后更新时间：2026-11-01

## 里程碑

| 阶段 | 状态 | 提交/验收证据 |
|---|---|---|
| T0 | passed | ca28f8a；Python 3.12.11；pytest 13 passed / coverage (branch enabled) 100%；mypy 10 files；CLI smoke passed |
| T1 | passed | 7719fdc；47 tests / 99.48% coverage (branch enabled)；ruff + mypy + doctor mock |
| T2 | passed | 59724e4；79 tests / 97.41% coverage (branch enabled)；三平台 scoped mock、快照差集、恢复与安全静态解析 |
| T3 | passed | 5839502；93 tests / 97.77% coverage (branch enabled)；Alembic 0001→0002、事务/版本/审核与双向查询 |
| T4 | passed | ae07de1；107 tests / 98.02% coverage (branch enabled)；规则/AI/review/Catalog 关键分支 100% |
| T5 | passed | 1cfcd3c；119 tests / 97.86% coverage (branch enabled)；CLI 全流程/子进程/预算/授权门禁 |
| T6 | passed | 1e5984a；123 tests / 97.93% coverage (branch enabled)；真实 SDK stdio 六工具/资源/错误/注入 |
| T7 | passed | 133 tests；总体 98.58% / 行 99.18% / 纯分支 96.65%；独立 wheel 安装与逐项 P0 报告 |

## 下次继续动作

离线目标已完成。真实平台与 Cursor/Grok 实际执行器仍 not_verified；用户可按 OPERATIONS 独立进行授权只读 smoke。

## T0 执行记录

- 创建本地分支 `work/dce-v1-offline`；初始仅文档，无实现，无已完成阶段。
- `uv sync --python 3.12 --dev` exit 0，生成 uv.lock；仅公共依赖下载。
- `.venv/bin/pytest -q --cov=dce --cov-report=term-missing` exit 0：13 passed，100% 覆盖率（启用分支统计）。
- `.venv/bin/mypy src` exit 0：10 source files。
- `.venv/bin/dce doctor --mock` exit 0：3 平台合成契约，live 均 not_verified。
- 初次 ruff exit 1（测试行过长）；ruff format 修复后 check exit 0。
- `git diff --check` exit 0。真实平台未调用。

## T1 执行记录

- 实现 ZenTao v1 / GitLab REST v4 / Portainer 与 Docker proxy GET；唯一特许 POST 是 ZenTao token 认证且不自动重试。
- HTTP：固定 origin、禁止重定向、timeout、流式字节上限、有限退避、错误分类、分页循环与页数上限。
- 图片：files=[] 内嵌 2 图、Token、MIME+magic、跨域/HTTP/SVG/HTML/超限拒绝；私有目录、原子写、失败清理测试。
- doctor 使用 Adapter；独立能力矩阵、单平台失败隔离；mock 不出网。
- `pytest -q --cov=dce --cov-report=term-missing` exit 0：47 passed，99.48% 覆盖率（启用分支统计）。
- `ruff check .`、`mypy src`（15 files）、`dce doctor --mock`、`git diff --check` exit 0。
- 修复首次检查暴露的闭包 lint 和动态 JSON 类型收窄错误，所有修复后检查通过。
- 外部 API 兼容性 not_verified；未访问内网，未调用业务写接口。

## T2 执行记录

- 静态解析 Maven reactor、Gradle settings、Go work/module、Node workspaces、Dockerfile、CI 显式 include、Compose。
- 禁止执行脚本；大小/节点上限、非法 YAML/XML、alias/动态表达式 incomplete、OCI 引用验证；Compose 仅变量名。
- 显式 scope 的 GitLab/ZenTao/Portainer crawler；固定 commit 读取、相关路径白名单、节流、私有原子 checkpoint。
- 失败状态持久化，已完成仓库复用、commit 变化失效重读；Catalog ScanRun 将在 T3 接入。
- 独立 git_current / portainer_saved / swarm_runtime 快照、来源实例复合身份、版本指纹和证据。
- 合成验收：3 Stack、1 current Swarm、2 stale、78 namespace services、73 images、5 组复用；71→78 差集为 072–078。
- 三平台 Mock HTTP 联合测试验证范围、master、Endpoint/Swarm/标签、快照差异及原始 secrets 不进入 cache。
- HTTP 日志开启 DEBUG 时仍过滤 URL、主机与凭证；图片/写操作拦截回归通过。
- `ruff check .`、`mypy src`（24 files）、`pytest -q --cov=dce --cov-report=term-missing`、`git diff --check` exit 0。
- 最终 79 passed，coverage (branch enabled) 97.41%；外部平台 not_verified。

## T3 执行记录

- SQLAlchemy SQLite Catalog 与打包 Alembic 0001/0002；旧实体/关系版本历史回填测试通过。
- 实体/边/证据/独立快照/ScanRun/Approval/Audit 持久化；完整批次原子导入，失败另记 scan 状态。
- 来源复合键、幂等写入、历史版本、最近校验、有效期；不可变快照/证据冲突与缺失引用回滚。
- Entity 与 Edge 独立 scope 成员；完整扫描来源消失软删除/过期；其他活跃 scope 保护共享资源。
- 审核 accept/reject/revoke/override 保留 actor/reason/timestamp 与 before/after；扫描不能写 confirmed，冲突单独记录。
- 有界分页、双向 trace、证据/版本/审计查询；本地目录 0700/数据库 0600。
- `ruff check .`、`mypy src`（32 files）、`pytest -q --cov=src/dce --cov-report=term-missing`、`git diff --check` exit 0。
- 93 passed，coverage (branch enabled) 97.77%。修复 mypy 动态 SQL 类型注解与关系消失保护分支。
- 覆盖率命令从包名改源码路径：包名过滤会把 Alembic 动态脚本计为未执行；源码路径正确测量迁移。README/tasks/acceptance/CI 已同步。
- 真实外部平台仍 not_verified。

## T4 执行记录

- 规则以显式 module_paths 建立模块→build job 证据；名称相似仅 candidate，线索不足保留多个 unresolved。
- Provider 协议、Noop/Fake、默认关闭；仅 UUID/受控类型/证据 ID 摘要，不发送名称/URL/源码/日志。
- 严格候选 schema/引用/状态校验；超时/异常回退规则，AI 阶段失败持久化，可有限重跑。
- AI/规则同边合并幂等；Mapping scope 不取得实体所有权；候选上限与证据排序。
- 审核预览证据/版本/环境/影响，期望版本原子校验；环境显式确认，stale 不能接受；撤销保留审计。
- `ruff check .`、`mypy src`（36 files）、`pytest -q --cov=src/dce --cov-report=term-missing`、`git diff --check` exit 0。
- 107 passed，coverage (branch enabled) 98.02%；rules、AI、MappingService、Catalog 100% 分支覆盖。
- 无外部 AI 请求，真实平台 not_verified。

## T5 执行记录

- 完整 CLI 命令树与共用 AppServices；默认离线、JSON/table、统一错误、预算截断、全命令帮助。
- init/discover 显式 live/read_only/Scope；MockTransport 测试 CLI 调用路径，无内网请求。
- BugContext 同一 Adapter Token 认证获取两张合成 PNG；摘要/证据/候选/人工状态、附件私有路径。
- 修复拒绝映射被 fixture 回退重新召回的问题；来源实例歧义 fail closed。
- Pipeline 摘要区分 Buildx 与 missing_make，保留 master，不触发 Pipeline。
- Stack 三类快照摘要，stale/unknown health/environment/version；分页/trace 与 review 版本门禁。
- 真实 CLI 子进程 smoke、1024 字节预算、损坏 SQLite/URL/参数安全失败通过。
- `ruff check .`、`mypy src`（37 files）、`pytest -q --cov=src/dce --cov-report=term-missing`、`git diff --check` exit 0。
- 119 passed，coverage (branch enabled) 97.86%；真实平台 not_verified。

## T6 执行记录

- MCP SDK stdio，仅六个只读工具；CLI/MCP 共用 AppServices，严格 schema、固定 error_code。
- 真实 Python ClientSession 子进程完成 initialize/list_tools/六工具/错误/资源读取；stdout 仅协议。
- structuredContent 单份 payload，预留协议预算；discovery_status 压缩为进度/异常计数/待审核数。
- 附件只返回当前会话注册 URI；资源读取验证 SHA256、边界、大小和 symlink，拒绝未知/篡改引用。
- 默认离线，live/read_only 与 Bug/项目 allowlist 显式启用；不注册审核/部署/触发工具。
- 恶意指令文本仅数据，未创建标记文件；URL/Token 脱敏与预算测试通过。
- `ruff check .`、`mypy src`（39 files）、`pytest -q --cov=src/dce --cov-report=term-missing`、`git diff --check` exit 0。
- 123 passed，coverage (branch enabled) 97.93%；README 增加 Cursor 可运行配置，Grok/真实内网 not_verified。

## T7 执行记录

- 按 REQ-01–12 / NFR-01–06 / AC-01–17 / T0–T7 逐项审计，证据写入 acceptance-report.md。
- 合成多模块/Job/镜像/运行服务链补齐并 E2E；Node glob 只认 package 根；缺 Namespace 证据不能确认当前 Stack。
- 补测并修复平台子路径、畸形附件 URL、损坏/原子失败 checkpoint、Catalog 入库/审核二次脱敏。
- 本地 pre-commit 已启用 .githooks；index blob、凭证文件名拒绝、私网地址/主机与历史扫描；从不打开凭证文件。
- ruff check . / mypy src（39 files）/ git diff --check exit 0。
- 最终 pytest -q --cov=src/dce --cov-report=term-missing --cov-report=json:harness/reports/coverage.json --junitxml=harness/reports/pytest.xml exit 0：133 passed、0 failures/errors/skipped。
- 覆盖率口径更正：早期日志的百分比是启用分支统计的总体值，已改正称谓；最终总体 98.58%、行 99.18%、纯分支 96.65%。命名安全/状态/关系模块的纯分支 100%，详见 reports/summary.json。
- JUnit 主机名脱敏为 offline-runner，完整 coverage 与 JUnit/摘要已保留；测试始终合成，autouse 禁止 IP socket。
- uv build --offline exit 0，wheel/sdist 成功；wheel Python 源文件逐字节匹配，独立临时 venv 安装迁移/243实体/335边/331证据/6快照/双图/6工具/doctor mock 成功。
- OPERATIONS 安装/Mock/用户本地 smoke/恢复/移除指南完成；Cursor 配置有效，Grok 与真实平台 not_verified。
- License/GitHub 审查：不擅自授予许可，不创建远端、不 push/merge/release；不影响本地离线 P0。
- 最后行为核对补齐 live init/discover 入库后的本地规则生成（无新增平台请求）；重新完整运行 133 tests 通过。
- 最后报告整理的 EOF 空行由 diff --check 发现并修正。
- 补齐 AI 候选独立 ai_candidate 快照与脱敏 rationale Evidence；无效输出不留伪证据、重复候选幂等；再次完整 133 tests 通过。
- T7 由本地提交 test: certify offline V1 acceptance and operations 保存；提交钩子再次执行暂存区检查。

## 真实案例只读验证尝试（2026-11-02，未完成）

- 边界：按用户提供的 14 个 Bug、5 组组件与最终闭环限定核验；不执行公司构建、部署、审核通过或回调，不读取凭证文件、真实图片、私有日志或原始 Compose。
- `.venv/bin/dce doctor --live --read-only` exit 2：ZenTao/GitLab/Portainer 均 `AUTH_FAILED` / `Platform configuration is missing.`；请求在配置检查处停止，无平台响应或网络成功证据。
- 注意该命令本次 JSON 顶层 `status` 为 `ok`，但三平台均错误且退出码为 2；不得将顶层字段当作连通验收通过。
- 只读核对 5 个实际本地仓库：模块标记存在；2 条案例明确指定的本地目标分支包含 feature HEAD。此项仅证明本地提交包含关系，不能证明每个 Bug 已修复或远端/构建/部署状态。
- 案例和本地版本仅写入 gitignored 私有目录 `.local/live-validation/`。报告断言通过：14 个去重 Bug、5 个顺序组件、2 条本地证据关系、模块标记存在；所有远端与功能结果保持 `not_verified`。未把真实案例加入 fixtures，也未伪造 API 响应。
- 未执行现有 HTTP 远端查询：按 SECURITY 已请求明确确认；安全凭证注入方式、测试入口和环境/Stack/Service 范围待补充。
- 发现现有 `discover` 仅采集默认分支；指定部署 ref 需独立核对，不能以默认分支扫描结果冒充。
- 本轮没有产品代码或架构变化，不重跑离线测试替代真实验收；本地文档检查结果另记于下。
- `git diff --check` exit 0；`git check-ignore` 确认两个案例文件均被忽略；暂存前 `scripts/check_public_data.py` exit 0（暂存后另由提交钩子检查）。

## 风险与边界

离线 P0 无未解决阻塞。真实平台/API版本/企业网络及实际 Agent 接入 not_verified；P1 递归 CI include、云模型 HTTP 插件和共享鉴权服务为后续扩展，不虚报完成。
