# Agent 执行日志

状态：IN_PROGRESS
当前阶段：T6（T0–T5 已验证）
最后更新时间：2026-11-01

## 里程碑

| 阶段 | 状态 | 提交/验收证据 |
|---|---|---|
| T0 | passed | Python 3.12.11；pytest 13 passed / branch coverage 100%；mypy 10 files；CLI smoke passed |
| T1 | passed | 47 tests / 99.48% branch coverage；ruff + mypy + doctor mock |
| T2 | passed | 79 tests / 97.41% branch coverage；三平台 scoped mock、快照差集、恢复与安全静态解析 |
| T3 | passed | 93 tests / 97.77% branch coverage；Alembic 0001→0002、事务/版本/审核与双向查询 |
| T4 | passed | 107 tests / 98.02% branch coverage；规则/AI/review/Catalog 关键分支 100% |
| T5 | passed | 119 tests / 97.86% branch coverage；CLI 全流程/子进程/预算/授权门禁 |
| T6 | implementing | 六个只读 MCP 工具与 stdio 客户端契约 |
| T7 | pending | |

## 下次继续动作

继续 T6：MCP SDK stdio、六工具 schema、安全输出和真实客户端离线集成。

## T0 执行记录

- 创建本地分支 `work/dce-v1-offline`；初始仅文档，无实现，无已完成阶段。
- `uv sync --python 3.12 --dev` exit 0，生成 uv.lock；仅公共依赖下载。
- `.venv/bin/pytest -q --cov=dce --cov-report=term-missing` exit 0：13 passed，100% 分支覆盖率。
- `.venv/bin/mypy src` exit 0：10 source files。
- `.venv/bin/dce doctor --mock` exit 0：3 平台合成契约，live 均 not_verified。
- 初次 ruff exit 1（测试行过长）；ruff format 修复后 check exit 0。
- `git diff --check` exit 0。真实平台未调用。

## T1 执行记录

- 实现 ZenTao v1 / GitLab REST v4 / Portainer 与 Docker proxy GET；唯一特许 POST 是 ZenTao token 认证且不自动重试。
- HTTP：固定 origin、禁止重定向、timeout、流式字节上限、有限退避、错误分类、分页循环与页数上限。
- 图片：files=[] 内嵌 2 图、Token、MIME+magic、跨域/HTTP/SVG/HTML/超限拒绝；私有目录、原子写、失败清理测试。
- doctor 使用 Adapter；独立能力矩阵、单平台失败隔离；mock 不出网。
- `pytest -q --cov=dce --cov-report=term-missing` exit 0：47 passed，99.48% 分支覆盖率。
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
- 最终 79 passed，branch coverage 97.41%；外部平台 not_verified。

## T3 执行记录

- SQLAlchemy SQLite Catalog 与打包 Alembic 0001/0002；旧实体/关系版本历史回填测试通过。
- 实体/边/证据/独立快照/ScanRun/Approval/Audit 持久化；完整批次原子导入，失败另记 scan 状态。
- 来源复合键、幂等写入、历史版本、最近校验、有效期；不可变快照/证据冲突与缺失引用回滚。
- Entity 与 Edge 独立 scope 成员；完整扫描来源消失软删除/过期；其他活跃 scope 保护共享资源。
- 审核 accept/reject/revoke/override 保留 actor/reason/timestamp 与 before/after；扫描不能写 confirmed，冲突单独记录。
- 有界分页、双向 trace、证据/版本/审计查询；本地目录 0700/数据库 0600。
- `ruff check .`、`mypy src`（32 files）、`pytest -q --cov=src/dce --cov-report=term-missing`、`git diff --check` exit 0。
- 93 passed，branch coverage 97.77%。修复 mypy 动态 SQL 类型注解与关系消失保护分支。
- 覆盖率命令从包名改源码路径：包名过滤会把 Alembic 动态脚本计为未执行；源码路径正确测量迁移。README/tasks/acceptance/CI 已同步。
- 真实外部平台仍 not_verified。

## T4 执行记录

- 规则以显式 module_paths 建立模块→build job 证据；名称相似仅 candidate，线索不足保留多个 unresolved。
- Provider 协议、Noop/Fake、默认关闭；仅 UUID/受控类型/证据 ID 摘要，不发送名称/URL/源码/日志。
- 严格候选 schema/引用/状态校验；超时/异常回退规则，AI 阶段失败持久化，可有限重跑。
- AI/规则同边合并幂等；Mapping scope 不取得实体所有权；候选上限与证据排序。
- 审核预览证据/版本/环境/影响，期望版本原子校验；环境显式确认，stale 不能接受；撤销保留审计。
- `ruff check .`、`mypy src`（36 files）、`pytest -q --cov=src/dce --cov-report=term-missing`、`git diff --check` exit 0。
- 107 passed，branch coverage 98.02%；rules、AI、MappingService、Catalog 100% 分支覆盖。
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
- 119 passed，branch coverage 97.86%；真实平台 not_verified。

## 风险与阻塞

无。真实平台仍 not_verified。
