# Agent-led 重构验收 — 2026-11-04

结论：**核心 Agent-led 初始化链路通过；严格全样本验收仍有外部缺口。** 用户已回传 Cursor 九工具、三平台实际调用、初始化对话及修复后 JSON 文本/真实 PNG 进入模型的复验。完整候选关系文件已获批准，由 Host 保存、CLI 校验和复读通过；22 proposed、1 unresolved、0 confirmed，审批字段为空。用户最新要求不要提交，本轮未 git add/commit/push；完整模块树 403 和旧独立 GitLab 范围仍未解决。

依据：docs/refactor/agent-led-initialization/dce-agent-led-refactor/CHANGE_PROPOSAL.md 与 specs/01–07；根 AGENTS/GOALS/PLANS。旧 V1 仅为历史兼容证据。T0 基线 6fd0a90（144 tests），代码按 T0→T7 本地分阶段提交；无 push/merge。审计见 [refactor-audit.md](refactor-audit.md)，执行过程见 [build-log.md](build-log.md)、[test-results.md](test-results.md)。

| 阶段 | 交付与当前判定 |
|---|---|
| T0 | passed：核对旧六工具的实际名称/Schema/实现/测试、Adapter、Mapping/AI/Catalog，定义边界后改代码 |
| T1 | passed：默认路径无语义 Mapping/模型调用；技术事实、Adapter、transport 与兼容入口保留 |
| T2 | offline passed / live partial：三个事实工具加旧六工具，scope/分页/错误/证据/预算/ImageContent；真实完整模块树 403；原样本无图，新授权样本的原生 PNG 已通过 SDK |
| T3 | passed offline and real saved：完整 683 行/23 关系按批准保存，Schema/CLI/复读通过；22 proposed、1 unresolved、0 confirmed，文件未跟踪 |
| T4 | passed real Host user reported：九工具/三次实际调用/初始化对话，以及修复后 JSON 文本和原生 PNG 到模型均已回传 |
| T5 | passed including real copy：真实旧库副本备份后迁移，保留全部历史数量和原库；角色为 resource_cache_and_history |
| T6 | offline passed / live partial：208 tests，三平台 SDK 与用户回传 Host 证据分开；项目文件/图片到模型通过，完整模块/旧独立样本尚待验 |
| T7 | updated uncommitted / strict full-sample acceptance incomplete：README/清单/harness/续跑同步；按用户要求不提交，不虚报严格全验完成 |

## 最新离线结果

- `.venv/bin/pytest -q --cov=src/dce --cov-report=json:/tmp/dce-agent-led-coverage.json --junitxml=/tmp/dce-agent-led-tests.xml --tb=short`：**208 passed，0 failed/errors/skipped，18.14s**。
- 总体覆盖率 **97.93%**，行 **98.45%**，分支 **96.31%**；ruff 与 strict mypy（48 files）通过。
- 新增文本 Host 成功/错误/截断/转义与双副本预算、显式图片预算测试通过；URL 别名与进程优先级保持通过；默认 CLI 仍不自动加载 dotenv。凭证只由受保护本机程序处理，正文/值不进入对话或报告。
- `uv build --wheel --offline --out-dir /tmp/dce-agent-led-dist` 和临时隔离安装通过；使用 `-S`、显式依赖路径、规范化 `/tmp` 与 `/private/tmp` 后，确认实际导入 wheel，实际安装包的 JSON 文本/结构化错误语义一致、新图片预算配置通过；此前模板/Schema/0003 Catalog 角色检查保留。首次断言把 macOS 同一临时目录的两种路径当作不同，修正验证脚本后通过，不改产品行为。
- 合成 stdio→HTTPTransport 三平台 E2E、原生 ImageContent、双 workspace、多对多、审批/拒绝/刷新、备份迁移、安全边界均包含于全库回归；不是实际 Agent Host 验收。

## 离线 P0 证据

| 场景 | 测试/证据 | 状态 |
|---|---|---|
| 三平台所有新增 operation / Schema / source/revision/观察时间 | test_facts.py，含 26 类 operation 组合 | passed（合成） |
| instance/Project/Bug/Endpoint/Stack 范围、空 scope、不允许秘密路径 | test_facts.py，拒绝发生在打开 Reader 前 | passed |
| Tree 单页、ref/path、cursor 检验、trace tail、输出遗漏 | test_facts.py、旧 Reader/预算测试 | passed |
| 同源图片/HTML 假图/越源/大小/原生 ImageContent/总预算 | test_facts.py、test_agent_e2e.py、旧 connector/MCP tests | passed（合成） |
| Swarm/Stack 独立来源、env/auth 过滤、非典型文件名 Compose | test_facts.py，历史 mismatch 和 current/saved/runtime 旧用例保留 | passed（合成） |
| confirmed 需证据与人工元数据，confidence 不批准 | test_project_context.py | passed |
| 六状态、新关系 proposed、审批/备注/拒绝保留、变化 stale/conflicted | test_project_context.py | passed |
| 双 workspace / 来源实例 ID / 同数字跨平台 / 多对多 | test_project_context.py、test_agent_e2e.py、旧链路用例 | passed |
| YAML 注入/重复 key/alias/体积/secret/路径和 symlink 逃逸 | test_project_context.py、旧安全测试 | passed |
| 模型无关、默认无 Mapping/AI 调用、事实读取不改 Catalog | test_agent_boundary.py、test_facts.py | passed |
| 旧六工具/CLI 保留，旧库先备份，审批历史不变 | test_mcp*.py、test_catalog_migration.py、test_cli_workflow.py | passed |
| MCP stdio→HTTPTransport→三平台合成读取、原生图片、Host harness 写文件 | test_agent_e2e.py | passed；不是实际 Agent Host |
| 调用审计只含已知工具名/状态/错误码 | test_facts.py；无参数/正文/密钥 | passed |

## 本轮真实只读证据

详细诊断见 [resumed-http-cursor.md](context/agent-led/resumed-http-cursor.md)；本机私有报告只留 gitignored 目录，不公开地址、资源名/ID、原始 Compose、图片、日志或凭证。

| 项目 | 当前证据与边界 |
|---|---|
| ZenTao v1 登录 / Bug / Project / Product / 附件元数据 | 实际认证 201、Bug 200；SDK 各操作成功；Bug module 为未分配，附件/内联图片均 0 |
| GitLab 工作区精确源项目 | 由本地 remote 确定 selector，Project/Tree/Commit/CI 文件读取成功；不推断 Bug 归属，不运行 CI |
| Portainer | Endpoint/Swarm Info/三 Stack 元数据与 Stack File、Service 列表/详情成功；保存配置的服务数分别 63、71、78 |
| 运行 namespace | 从实际 Service 的 namespace label 得到查询范围；8 页共 78 个不同 Service ID，完整分页；环境 unresolved、健康 unknown |
| 历史 Swarm mismatch | 两个 Stack 的 SwarmId 仍不匹配当前集群，一个匹配；只作独立来源事实，关系未自动 confirmed |
| SDK 协议 | 九工具枚举；27 次成功真实 tools/call，另一次完整模块树 PERMISSION_DENIED；输出 Schema 校验通过，分页遗漏显式标记 |
| 真实 Catalog 副本 | SQLite backup 后迁移 0003，191 entities/219 edges/219 evidence/11 snapshots 保留，原库不改；迁移前备份已创建 |
| Cursor 配置 | 全局 dce 备份更新为显式本地入口，保留其他四服务，配置无密码/Token；CLI 历史未登录不影响桌面用户回传；九工具/三次实际调用与初始化已记录，用户最新复验确认 JSON 文本和原生 PNG 实际进入模型，不再待复验 |
| 项目关系草案 | 20 Git roots，18 本地模块提议，加精确源身份/独立 Swarm 候选和 Bug 未知；22 proposed、1 unresolved、0 confirmed；完整 diff 获批后由 Host 保存，CLI validate exit 0/复读/字节一致性通过；文件 untracked，HEAD/index 不变 |

安装包欢迎页曾导致禅道认证路由 404；按实际同源链接核实应用根，再用显式进程 URL 覆盖，未猜测接口/执行页面指令/修改 .env。SDK 入口只用 GET 和 v1 认证 POST。一次基于保存 Stack 元数据的 namespace 查询得到 0；该结果保留，不冒充运行 namespace。随后按实际 Service label 独立查询得到完整 78，两个来源不合并。

## 核心验收收口与剩余项

| 缺口 | 判定 / 下一步 |
|---|---|
| 真实 Cursor Agent | passed_user_reported；九工具/三次实际 calls/初始化对话及后续文本/图片模型接收均已回传。原三次 truncated 仍 not_observable，新 Bug 复验的信封/data.truncated 均 false，保留不同采集证据 |
| 业务项目文件落地 | passed；用户批准完整 diff，Host 以只创建新文件方式保存，CLI 校验/复读与源字节一致；审批字段全空、文件未跟踪，Git HEAD/index 未变；本轮未提交 |
| 真实图片到模型 | 真实 SDK 已收到授权新 Bug 的原生 PNG（382396 字节，ToolResult 512314 字节），truncated=false，无图片落盘；用户另回传 Cursor 实际收到 MCP ImageContent 并给出非敏感外观判断，image_delivery=delivered/truncated=false；模型接收 passed_user_reported |
| 完整产品模块树 | PERMISSION_DENIED（403，Access not allowed）；同 Token 读 Bug 200，登录正常。官方 v1 模块入口的 tree/browse 会独立检查权限，推断应核对该读入口/产品范围；实际实例版本未确认，不以 Bug 页部分清单冒充 |
| 旧独立 GitLab Project/Pipeline/Job 和 GitLab Compose | not_verified；补验命令被自动审批拒绝，原因是固定旧编号的本轮读取范围未明确授权。移除所有该类调用后只查当前工作区；需用户明确范围后再验，只读元数据，不请求私有日志 |
| 跨平台业务关系、环境/健康/版本 | unresolved/unknown/not_verified；不因数量相等、名称或 ID 相似确认，不把旧 Catalog 当项目真相 |

此前“地址/工作区/Host 选择缺失”的三轮 blocked 记录仅为历史。本轮没有重新宣布完成或重复旧阻塞计数。当前仅剩完整模块树权限与旧独立样本授权/其仓库 Compose 重验。Cursor 文本/模型图片复验、项目保存批准及文件落地均已完成，不再索取或重复。核心初始化已闭环，严格全样本验收未完成，不标 goal complete。

机器摘要见 [agent-led-summary.json](reports/agent-led-summary.json)，接续见 [resume.md](../prompts/agent-led/resume.md)。所有 fixtures 为合成或显式脱敏；无真实业务写、构建、部署、push 或 merge。


## Cursor 文本和真实图片接续

详细契约、先行失败与修复结果见 [cursor-text-compatibility.md](context/agent-led/cursor-text-compatibility.md)。服务器九工具的 TextContent 与 structuredContent 返回同一脱敏 JSON，预算计入双副本和转义；图片可显式配置独立总预算（默认 null，最大 3MB），文本预算/Reader 2MB 上限/来源 scope 不变。Cursor 配置已备份更新授权含图 Bug 与图片预算，其他四服务保留，无凭证嵌入。

用户提供的聊天 diff 省略了 relationships 条目，不能保存该片段；本机完整草案确有 683 行/23 关系、全部 evidence，经校验。用户随后明确批准完整 diff 并要求不要提交；Host 已保存、校验及复读，confirmed 仍 0、审批字段全空。详见 [cursor-recheck-and-approved-save.md](context/agent-led/cursor-recheck-and-approved-save.md)。本轮无新的平台读取，不 git add/commit/push。


## 最新执行边界

本轮无产品代码修改，208 项全库回归/97.93% 覆盖率为此前已通过的基线，不虚报重新跑过。实际新验证为目标业务文件的 CLI validate（exit 0）、Schema/工作区边界/复读、与获批完整草案的字节一致性和 Git HEAD/index 不变。Cursor 结果为用户回传的真实会话证据，来源标注 user_reported，不伪称执行器直接观察桌面。执行记录和文档更新保留本地未提交。
