## 2026-11-11 本地产品整顿与验收（当前）

初始Git只读盘点：main 078962e，无Tag，当前fix分支5092d6a，工作区干净；干净候选2748c7b直接基于main，src/tests/scripts/fixtures/examples/schemas/pyproject/lock与原HEAD无差异。无fetch或远端变更。git创建分支首次因沙箱index.lock拒绝，申请本地Git写权限后成功，不是自动审批拒绝；从main创建codex/upgrade-work并导入干净快照，dba07db树一致。

25个未跟踪生成路径及2份旧原始测试报告定点删除；删除前排除symlink与Git跟踪内容，不递归进入.local/.dce/private/.venv。清理记录保留每个路径和引用判断。未删除正式测试/Prompt/Schema。先定义ACCEPTANCE_CONTRACT，再编排与失败路径测试；旧check_mcp_stdio断言从2.0修正到Portainer2.2/其他事实2.1。

第一轮完整离线验收：431总计，430通过、1失败、0跳过，97.24%；唯一失败是新增runner测试把命令文字也当作输出泄漏，改为通过合成环境变量提供输出。Wheel构建成功，隔离requirements解析因markupsafe缓存索引不足失败；uv sync已有锁可直接消费锁中下载证据，改为UV_PROJECT_ENVIRONMENT指定新venv，--locked --offline --no-dev --no-install-project，不修改锁、不降低门槛。新增测试最初4/5，通过修正5/5。

第二轮完整离线验收431 passed、0 failed/skipped、97.24%，Ruff、strict Mypy55源文件、锁检查/安装、Wheel、新venv锁定依赖、源码目录外CLI/doctor/九工具STDIO通过。报告由本次临时XML/coverage生成，不用旧harness结果。补充合成CLI/旧checker独立阶段以及用户指南，最终重跑结果将在最终执行报告与机器摘要中记录。

所有平台响应合成，SDK为本机STDIO，不读取用户凭证、不签发真实日志授权、不访问公司服务；历史Gate A/B保留其原时间语义，真实Token过期恢复仍not_verified。无push/PR/merge/Tag/Release，用户MCP、.env、业务project.yaml均未改。

# Agent 执行日志

状态：AGENT_LED_OFFLINE_PASSED_LIVE_PARTIAL
当前阶段：核心初始化/Host/图片/项目文件已通过，T6/T7 严格全样本仍待模块权限/旧独立样本
最后更新时间：2026-11-05

最新：2026-11-05 A–D 增量通过，226 tests / 97.63%；当前 Project/Stack 的真实 SDK 只读验收通过，新增 Cursor operation 尚待连接重载后使用。业务文件字节未改，24 proposed/3 unresolved/1 confirmed 保持；没有暂存、提交或推送。本轮见 incremental-v1-acceptance.md；此前完整验收的历史边界见 agent-led-acceptance.md，下列 V1 里程碑为历史。

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

从本轮真实 Cursor 桌面对话与用户审核接续，按 prompts/agent-led/resume.md；三平台地址、业务工作区与 Host 选择已给出。真实 SDK、实际 Host 和项目文件落地分别记录。

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

## 真实案例只读验证接续（2026-11-02，Git 远端已验证）

- 读取用户填写的非密钥私有定位表：人工明确测试环境与 Endpoint/Stack；GitLab HTTP 只读已允许。平台 API 凭证未进入当前进程、聊天或文件。
- 首次 `git ls-remote` 在沙箱内网络失败；按环境要求申请沙箱外只读执行后成功，没有绕过网络权限。
- 对五个限定仓库查询指定远端 refs 全部 exit 0；两个用户明确指定的目标分支，均用真实远端 SHA 与本地已有 Git 对象证实包含相应远端 feature HEAD。没有 fetch、checkout、push 或触发 CI。
- 另记录默认分支与指定分支的差异，以及一个前端远端 HEAD 已不在本地对象库的情况：缺少对象时 ancestry 保留 `not_verified`，不把默认分支当作部署分支或伪称完成全部版本验证。
- 远端 SHA、来源实例指纹与本次时间戳仅存 gitignored 私有目录；未将真实名称、地址、ID 或版本写入公开报告。
- 为后续 API 证据准备私有本机运行入口：交互式 `getpass`；拒绝非终端和不隐藏输入的回退；凭证仅存在进程内。HTTP 逐平台确认；跨 GitLab origin 在传凭证前拒绝；GET 仅限 Bug 元数据、指定仓库/ref/pipeline 元数据及所选 Endpoint/Stack/Swarm 标签。
- 不获取图片、源码 raw、job trace 或 StackFile，不执行业务测试脚本、不调用构建/部署/审核/回调。运行报告 0600、目录 0700；错误和部分成功保留诊断，不标记功能通过。
- 本机入口的 9 项合成安全检查通过（unittest，0.006s）；表单路径/API 基址/目标选择器检查通过；私有脚本 ruff 通过。此结果独立于已验收的 133 项产品测试，不能充当真实 API 成功证据。
- 已向用户提供本机终端运行命令，等待其不回显输入只读 API 凭证。GitLab REST、ZenTao、Portainer、运行版本和业务功能仍为 `not_verified`。

## 首轮 API 实跑与失败诊断（2026-11-02，未通过）

- 用户完成本机输入后取得真实 API 报告：GitLab、Portainer 为 `NETWORK_UNAVAILABLE`；ZenTao 首个限定 Bug 返回 `AUTH_FAILED`，其余 Bug 按边界停止，全部功能与部署版本仍 `not_verified`。三平台 HTTP 均由用户在运行时明确授权。
- 凭证仅在已退出的用户进程中存在，未存文件，当前执行器不能恢复其值或自动重放认证请求。
- 在已授权执行器做不带凭证的 TCP 与 GET 诊断：三平台均 TCP connected；直连 GitLab 返回 JSON 404，ZenTao/Portainer 返回 JSON 401。对现有本机回环代理的无凭证对照结果相同。未读取响应正文、未发送任何认证信息；不能据此归因于代理，也不能把私有项目无凭证 404 当作项目不存在。
- 用户终端的首轮异常已被 Reader 归并为固定网络错误，原始异常不可恢复；因此网络失败根因尚未确定。未擅自切换代理、关闭 TLS、换认证头或升权。
- 补强私有入口：同一终端先对精确 API 路径做无凭证预检，连接失败时不再要求输入 Token；异常诊断仅记录固定类别、类型和 errno，不记录原始消息/URL/请求头/正文。去除凭证首尾空白并拒绝内部空白、控制字符与非 ASCII，未经证据不声称首轮失败由输入格式引起。
- 新增本地请求协议错误、超时、拒绝连接、权限拒绝、凭证输入、失败预检不获取凭证、预检 401 后正常认证等检查；私有 unittest 共 14 项通过，ruff 通过。没有修改产品代码，也没有用离线检查冒充真实通过。
- 官方 REST v1 认证说明核对：https://www.zentao.net/book/api/1397.html 及 https://www.zentao.net/book/api/664.html；当前路径和 `Token` 头符合说明，首轮 401 只能确认认证被拒绝，不能认定具体过期或权限原因。已询问用户凭证获取渠道，不索取值。
- 历史 API 报告保持原样；无凭证诊断存独立 `network-check` 报告，避免与认证 API 报告混淆。等待用户运行加强入口后继续定位；未执行任何业务写入。

## 第二轮 API 结果与 HTTP 修复（2026-11-02，部分验证）

- 真实 Portainer 认证成功，所选 Endpoint/Stack 的 Swarm ID 及实际 Namespace 标签一致；属于限定资源的 `observed_verified`，不代表服务副本健康、修复版本已部署或业务功能通过。原始资源标识与服务摘要仅保留在私有目录。
- GitLab 同终端无凭证预检有 JSON 响应，认证请求下层为 `DecodingError`；不再归咎于网络或 Token 可用性。用合成 gzip、deflate、嵌套编码与分页响应复现本地 Reader 重复解压缺陷：修复前 5 failed / 1 passed，修复后 6 passed。
- Reader 继续用解码后的正文执行大小上限，缓冲为 Response 前删除上游内容编码、内容长度与分块传输头，保留 MIME/分页头。坏压缩数据按 `INVALID_PAYLOAD` 失败且不重试，真正网络异常仍维持原有限重试。
- 用户说明禅道 Token 来自 v1 登录；官方源码示例返回 session_id()。具体部署版本/有效期未验证，不把 401 直接断定为过期，也不切换 v2。
- 唯一登录 POST 不再附带已有 Token：先用扩展的认证测试观察 1 failed，再修复至通过；现有不重试登录测试继续通过。私有入口新增一次现取 v1 Token 的本机账号/密码输入，不把秘密放进 argv、文件或报告；密码保留原有空格/Unicode。用户选择此模式并明确同意 HTTP 认证后才发送登录请求。
- 已支持只重试 GitLab/ZenTao，保留 Portainer 历史成功快照，不再次索取其凭证。合成检查覆盖登录 POST 后限定 GET、认证失败不重试、不读取 Bug、密码保真、无敏感报告及平台选择；私有 unittest 19 passed，ruff passed。
- 产品最终检查：139 passed（11.69s），0 failures/skipped；总体覆盖率 98.58%、行 99.19%、分支 96.66%；ruff、strict mypy（39 files）、git diff --check exit 0。摘要见 reports/http-encoding-summary.json；完整本次报告位于 gitignored 私有目录，历史基线报告未覆盖。
- 确认本机运行入口加载工作区修复后的 Reader。GitLab 修复后真实请求及 ZenTao 即时登录还需用户输入本机凭证；未伪称通过。业务页面、调度器、审核通过及回调均未执行。

## 第三轮 API 与真实元数据本地集成（2026-11-02，限定范围通过）

- 用户重跑选择 GitLab/ZenTao 的本机入口：GitLab 五个仓库的 project/ref/commit/有限 pipeline 元数据全部读取成功；两个用户明确目标分支的当前 SHA 流水线均 success。修复后的 Reader 已通过真实 REST 复验，无需更换 GitLab Token。
- ZenTao 一次 v1 登录后立刻读取十四个 Bug 全部成功；只记录字段白名单，不存 Token/密码。前轮 401 的确切失效原因与会话有效期仍不作断言。
- 保留上一轮 Portainer 成功快照；汇总分别列出两轮采集时间，不声称形成当前同步部署快照。三个前端仍只有默认分支观测；manual 和有限查询未命中当前 SHA 均不被当作部署失败或构建不存在。
- 在 gitignored 私有目录，以实际响应白名单元数据和用户案例期望分别建 Snapshot/Evidence；未经过 synthetic fixture 加载器，也未模拟 API 响应。来源实例/资源种类/外部 ID 分离；Bug→仓库只保留 candidate。
- 实跑 Catalog 两次导入：185 Entity / 213 Edge / 213 Evidence / 8 Snapshot，第二次元素数量不变。198 条直接观测、15 条 candidate，无自动 confirmed，证据引用有效。
- 真实 DCE CLI 子进程：两页 Bug 列表无重复；service trace 有观测关系；mapping verify 无缺失证据；stack inspect 保留 version_match=not_verified。五次 exit 0、未截断且满足默认输出预算。
- 私有案例报告和 JSON 汇总已更新；真实名称、ID、SHA、digest 和采集时间仅存私有区。公开结论见 live-readonly-report.md。此轮无产品代码变化，不以重复离线 pytest 冒充新的真实测试。
- 尚未执行完整 live discover、实际 Agent MCP Host、源码 commit→构建镜像→Service 指纹链、页面请求/调度器/审核/回调功能回归。未执行公司业务写入；原有本地工作分支继续保存脱敏记录。

## 第二阶段部署与页面验收启动（2026-11-03，进行中）

- 用户授权继续验收，限定原测试环境和五个组件；保持业务只读，未保存模板、审核通过、触发回调、构建或部署。
- 按 plugin-management 检查浏览器能力：发现未连接的云端工具，未找到适合本机内网窗口的已连接工具，不发起云端连接。采用已安装本机 computer-use/browser-use 技能；两次 doctor 均 ready=false、accessibility=false、screen_recording=true。未绕过缺失权限，已请求人工开启。
- 不带凭证 GET 指定业务入口：同源 301 后 200 HTML；记录正文摘要和同源静态资源路径，不保存 HTML、不访问图片。这不等于页面功能验收通过。
- 只在本机对已定位仓库的受限 CI/Dockerfile 做静态元数据分析，未执行其中脚本或读取 .env。三个前端声明 dist 构建产物；本轮所需 commit/revision 标记未观察到，未按名称补造版本关系。
- 准备私有第二阶段入口：GitLab job-ID 单文件产物与部署 JS/CSS 字节摘要比较；限定 ref/pipeline/job/逻辑请求数和解码后字节；不保存源码、不下载 archive/trace。作业 SHA 不一致不取产物，多 commit 同产物不声称唯一来源。
- 运行侧再校验用户目标 Endpoint/Stack/Swarm/Namespace；名称匹配仅候选。仅针对当前 endpoint Node 的任务容器取 Image/Health 白名单；不执行 exec、不跨未验证节点路由，不把远端服务与本机缓存镜像混为一谈。
- 新 13 项合成部署检查 passed（0.031s）；原私有入口 19 项检查 passed；ruff passed。原私有入口补充传播 not_verified，避免 API 内层失败被包装为通过；无产品代码更改，未重跑全库 pytest 充当新真实证据。
- 已提供需本机不回显输入 GitLab/Portainer 凭证的实际运行命令，等待部署证据报告；同时请求三个前端的人工部署分支。真实版本与业务结果继续 not_verified。脱敏进展见 phase2-readonly-progress.md，真实数据与代码仅在 gitignored 私有目录。

## 验收范围纠正与已实现 MCP 补验（2026-11-03）

- 用户明确：仅验收 DCE V1 已开发能力；业务 Bug 表作为输入案例，不要求业务系统页面和修复回归。此前页面/发布验收扩大了范围，已明确纠正，停止 GUI 和辅助功能权限要求，不增加产品功能或验收门槛。
- 读取用户已执行的附加部署报告：两个平台成功读取元数据，一个前端入口资源摘要相等，另外两个未取得完整摘要；一个名称候选服务有一个运行任务与镜像元数据。仅保留附加只读观察，不作为 V1 通过/失败或代码能力声明，不继续追索页面权限、发布分支与业务回调。
- 在此前捕获真实元数据的 Catalog 上，用标准产品 dce mcp serve --live --read-only 和 MCP SDK stdio 实跑既有接口；未授权任何上游 Bug/Project，无凭证、无新增平台请求、无模拟 API 响应，也未加载 synthetic fixture。
- 六工具列表、readOnly/non-destructive 与严格参数声明通过。project_context（两个来源）、service_trace、deployment_inspect、discovery_status 共五次正向调用通过；未截断，结构化输出 948–12289 UTF-8 字节，均在预算内。
- bug_context/pipeline_diagnose 越界 ID 返回 PERMISSION_DENIED，未知 deploy_execute 返回 NOT_FOUND；仅证明拒绝边界，不声称这两类真实上游成功路径已验收。附件列表为空，未访问真实图片或私有日志。
- 调用前后 Catalog 元素数量不变，15 个候选保留，无自动 confirmed；已有 version_match=not_verified、health=unknown 正确保留。此为真实数据 Catalog 的 SDK stdio 集成，不是实际 Cursor/Grok Host 验收。
- 统一验收状态写入 v1-acceptance-status.md，纠正 README/PLANS/运维与额外观察记录。无产品代码更改，不重跑全库测试代替真实验证；现有 139 passed 基线保持，未验证 live discover 与两类上游成功路径单列 not_verified。

## V1 既有上游路径继续补验准备（2026-11-03）

- 用户再次要求继续，保持刚明确的 V1 边界，不新增产品功能。已准备只调用现有 AppServices.discover/McpApplication.call_tool 的私有验收入口；此前标准 SDK stdio 证据独立保留，不混称调用层次。
- 选择原授权范围内本地未发现 Compose 的一个前端源码项目，按已有默认分支语义发现；不将其当部署分支。其他源码项目本地存在 Compose，未把它们放入此轮原文读取范围。
- 出网护栏委托真实 HTTPTransport，无模拟响应：指定项目/commit/tree、固定 SHA 下 manifest/CI/Dockerfile、单个指定 Bug 和指定流水线/jobs。禁止所有写、越源、图片、Compose、.env、任意源码、私有 trace 和越界 IDs；每平台最多 160 次实际请求。
- 护栏六项合成检查通过（0.002s），涵盖分类允许/拒绝、固定 SHA、分页/query、预算和同源默认端口；私有入口与既有 SDK 检查 ruff 通过。无产品代码变化，139 项产品基线未被这些私有测试替代。
- 使用 SQLite backup API 创建独立私有 Catalog 副本，不覆盖旧库；凭证仅进程内不回显输入，一次 v1 登录后执行既有工具。实际结果仅保留计数、状态、长度和诊断，不保存 Bug 正文、图片或日志。
- 已提供运行命令；当前等待用户本机运行，不能声称 live discover 或两类上游成功已通过。辅助功能、浏览器/发布凭证及前端部署分支不再是本轮必要输入。

## 已实现 V1 核心路径真实补验结果（2026-11-03，限定范围通过）

- 读取用户本机真实报告：status=passed_for_scoped_v1_paths；未新增产品功能，无浏览器依赖，无原始业务正文保留。
- AppServices.discover 按原有默认分支语义对一个授权源码项目 live/read_only 实跑成功；固定 commit 下读取三个元数据文件，发现六个 build_job。实际出网含 7 页 tree，未读取 Compose、.env 或任意源码。
- 独立验收 Catalog 实核：191 Entity / 219 Edge / 219 Evidence / 11 Snapshot；204 条直接观测、15 条候选、confirmed 0，scan complete。CI incomplete 一条保留；Dockerfile/package 元数据解析非 incomplete，未隐藏警告或执行 CI 脚本。
- 既有 MCP 工具处理六次全部成功：BugContext 真上游、Pipeline Diagnose 真上游、ProjectContext、ServiceTrace、DeploymentInspect、DiscoveryStatus。成功路径输出 519–12289 UTF-8 字节，无截断，工具读取前后 Catalog 数量不变。
- BugContext include_assets=false，取得真实摘要并保留 BUSINESS_MAPPING_UNCONFIRMED，模块数 0；不冒称模块关联完成。Pipeline 本次为 success、failure_count=0，不冒称真实失败日志诊断已验证。
- 出网护栏实际允许 15 次 GitLab GET（项目/commit/tree/manifest/选定流水线/jobs）及 1 次指定 Bug GET，denied=0；另有一次已授权 v1 登录认证。未读取图片、Compose 或私有 trace，无公司业务写入、无自动 confirmed。
- 六工具处理层真实证据与前次标准 SDK stdio 证据独立保留，不把本次 in-process handler 调用称作 Cursor/Grok Host 实测。所有凭证仅本机进程内，私有原报告/数据库保留，公开仅脱敏汇总。
- 更新 V1 验收矩阵和机器摘要，不再要求用户重跑本轮入口。未覆盖更多发现范围、真实附件、私有失败日志、Compose 和实际 Host；业务页面和修复执行不属于本次 V1 门槛。

## Cursor 桌面版 MCP 接入（2026-11-03）

- 用户要求把现有 MCP 跑起来并编写启动接入文档。先定义现有工具/数据模式边界与验证步骤；不新增业务能力、端口或公司平台写操作。ADR-015 记录 stdio 生命周期和真实/合成数据分离。
- 本机 Cursor 3.27.6、DCE 虚拟环境已安装；全局 MCP 为 JSONC。使用 Cursor 随附 JSONC parser 做精确新增，校验原有四个服务器对象完全保留；写入前备份、原子替换、权限 0600。原配置/备份中的其他秘密未输出或提交。
- 从此前真实验收库通过 SQLite backup API 创建独立 `.local/cursor/` 副本，原始验收库不变。配置使用绝对入口/库路径、`--live --read-only`、空上游 allowlist、AI 与 HTTP 关闭；四类本地查询可用，两类上游访问拒绝，不把真实库与 synthetic fixture 混用。
- 经执行器允许修改全局配置并打开 Cursor；仅观察进程名和父进程链，确认 Cursor 实际启动 DCE 子进程。未读取 Cursor 私有日志、聊天或凭证，没有关闭/重启现有工作窗口。进程启动不等于一次 Agent 工具调用，该项继续 not_verified。
- 标准 MCP SDK 以 `/` 为工作目录运行真实 DCE 子进程：initialize、六工具 schema/只读声明、project_context/service_trace/deployment_inspect/discovery_status 四次成功、Bug/Project 两次 PERMISSION_DENIED、未知 deploy_execute 返回 NOT_FOUND。响应 1991–12289 字节，均未截断；Catalog 191 Entity / 219 Edge / 219 Evidence / 11 Snapshot，数量不变，无新平台请求。
- 新增可重复的 `scripts/check_mcp_stdio.py`，只打印安全状态/计数，失败不输出上游异常正文。另实跑缺失库检查：exit 1、固定诊断、不创建空库。文档覆盖安装、全局/项目配置、启动、提示词、数据模式、凭证环境、禅道会话失效、排错和停用。
- 运行 `.venv/bin/pytest -q tests/test_mcp.py tests/test_mcp_boundaries.py`：4 passed（5.08s）；`.venv/bin/ruff check .`、`.venv/bin/mypy src`（39 files）和 `git diff --check` 通过。产品源码未变，不重复全库测试充当新的 Host 证据；139 项完整回归仍为前轮基线。
- 公共机器摘要见 reports/cursor-mcp-summary.json；真实来源路径、安装备份位置、进程记录、检查结果和本机提示词保留在 gitignored `.local/cursor/`。所有私有文件已验证被 gitignore 拦截。实时 Bug/流水线凭证与 allowlist 尚未配置；不得把六工具可见写成六类实时上游均可用。

## Cursor 能力检查的 MCP 契约修复（2026-11-03）

- 用户报告实际 Cursor 命名空间 ready、可枚举六个业务工具与宿主 mcp_auth，但未调用业务工具；模板化描述、空 data Schema、互斥输入未发布导致必须翻代码推断平台能力。按实际代码核实报告，先定义契约边界/失败处理/测试，不扩充工具或上游范围。
- 三个新回归测试先观察 3 failed：无平台/状态说明、部署空参数被 Schema 接受、缺少业务必需字段仍被输出 Schema 接受。新增 contracts.py，平台/来源/当前条件在描述与 _meta.dce 中发布；修复 SDK 的 _meta 别名后条件与隐私测试通过，不以 meta 伪字段冒充协议元数据。
- 输入逐字段说明语义/默认值/限制，资源键长度与受控字符可检查；部署参数 oneOf 与运行时一致。六类 data 使用显式模型，完整 envelope/error/truncation Schema；错误兼容 code/error_code。严格校验服务返回，异常内容不进入错误。合成 HTTP 验证 live Bug/失败流水线返回、空 stage/default_branch 及秘密脱敏；所有请求均为合成 GET。
- 枚举不创建 Reader、不调用平台，也不输出 URL/Token/allowlist ID。六种启动条件测试覆盖 fixture、空 scope、缺配置、HTTP 未授权与配置齐全；configured_not_verified 不被写成认证成功。四类本地工具 openWorldHint=false；注册工具仍为六个，无认证/发现/审批/部署工具。
- 纠正时间语义：envelope snapshot_at 是响应生成时间；部署摘要补充已有 Snapshot.observed_at，不读取 Portainer。明确健康 unknown、环境 unresolved、版本 not_verified 的实现局限；CLI 的扫描/审核与 Adapter 能力不等于 MCP 全部可调用。
- 最终全库 `.venv/bin/pytest -q --cov=src/dce --cov-report=term-missing --cov-report=json:<private>`：144 passed（11.66s），总体 98.73%、行 99.29%、分支 96.88%，契约模块 100%；ruff、strict mypy（40 files）通过。SDK stdio 自检在真实 Catalog 副本上通过，四类返回匹配公布 Schema，两个 scope 拒绝与未知写拒绝保留；输出 1991–12340 字节、无截断、数量不变。
- 接入文档新增仅枚举检查提示词、四种 availability 说明及旧进程/旧会话缓存的更新方法。公共摘要见 reports/mcp-contract-summary.json；旧启动报告保留，不覆盖历史记录。实时凭证与 allowlist 未开启，未发新公司请求；Cursor 重载进程、更新后实际 Agent 枚举及业务调用按证据分别记录。

- 执行器批准后，精确更新全局 DCE 非秘密输出预算项以重载，其他 MCP、入口和空上游 allowlist 未变；配置预先备份、原子替换且权限 0600。观察到 Cursor 生成一个新的 DCE 子进程，同时仍有一个原连接进程，不能声称所有旧连接已替换；没有读取宿主聊天/私有日志。新进程启动后独立 SDK 再验 revision 1.1 与真实 Catalog 返回通过。需要在当前使用的 Cursor 窗口关开 dce 后，在新 Agent 会话重新枚举；更新后实际枚举和业务工具调用继续 not_verified。

## 最终风险与边界

离线 P0 无未解决阻塞，已实现核心路径的本轮限定真实补验通过；Cursor 配置与进程启动已观察到。更多平台/发现范围、真实图片、Compose、私有失败日志与实际 Host 内工具调用未覆盖，继续标记 not_verified。业务页面、修复/发布执行、GUI 自动化不属于 V1 验收门槛；业务映射候选须人工确认。

## Agent-led T0 — 2026-11-04

审计完成：harness/refactor-audit.md；先核对六工具、三 Adapter、Mapping/AI/Catalog，定义新契约/失败/测试。基线 .venv/bin/pytest -q：144 passed（7.52s），exit 0。下一步 T1 默认调用路径解耦；真实新版能力 not_verified。

## Agent-led T1 — 2026-11-04

默认初始化/发现和 Bug fixture fallback 的语义推理已移出；确定性 Module→CI 保留，旧 mapping CLI 与 init --legacy-mapping 可用。首次回归 3 failed/142 passed，诊断为技术事实被混放在 Mapping 与旧 ai_status 兼容字段；拆分修复后 pytest 145 passed（7.54s），ruff/mypy exit 0。下一步 T2 范围事实查询。

## Agent-led T2 — 2026-11-04

新增三个独立事实工具（共九工具），涵盖三平台已有读取、服务详情、分页/ref/path/日志窗口/证据与原生 ImageContent；只读 scope 和输出预算可测，旧六契约保留。针对性 Adapter/HTTP/MCP 54 passed（3.11s），ruff/mypy exit 0；随后图片总预算修正的 facts/contract 回归另记。modules 仅提供 Bug 页实测字段的部分目录，真实图片/模块完整路由与新版上游调用 not_verified；等待目标业务 workspace/连接范围，不读取秘密文件。

## Agent-led T2-budget — 2026-11-04

补充图片协议总字节预算后 facts/MCP 契约 8 passed（1.84s），exit 0；ImageContent 与结构化内容共同受预算限制。T2 实现完成，模块完整目录/真实上游/真实 Host 验收仍 not_verified，不计 P0 全部完成。

## Agent-led T3 — 2026-11-04

已实现 schema_version=1、模板/JSON Schema、指定 workspace 只读校验和纯 refresh：六状态、evidence/人工审批、instance/scope、多对多、拒绝保留、变化 stale/conflicted、秘密/重复 YAML/路径隔离。project/model 与 boundary 14 passed（0.65s），ruff/strict mypy exit 0。DCE 无业务文件写接口，真实工作区初始化待目标输入。

## Agent-led T4 — 2026-11-04

已提供 initialize/refresh/review/bug-context/service-trace/pipeline-diagnose 六提示词、MCP 实际参数清单、Host 协议，更新 SDK 检查兼容九工具。事实工具条件必填参数同步发布 JSON Schema；工作流/facts/MCP 契约 10 passed（1.99s），ruff passed，strict mypy 修正动态 JSON Schema 类型后 passed（45 files）。真实 Host 调用尚无证据，not_verified。

## Agent-led T5 — 2026-11-04

SQLite 0003 增加 cache/history 角色，所有旧表/边/审批/历史保留；旧库升级前 online backup+quick_check，失败阻止迁移；新增 catalog backup/status，迁移与回滚指南。首次 19 failed 根因是旧 0001 动态建表提前创建角色表，固定历史表集合后 Catalog/CLI 19 passed（1.60s），ruff/mypy exit 0。合成旧库证实备份版本、0600、行数、审批/历史及二次打开幂等；未改动真实旧库。

## Agent-led T6 — 2026-11-04

完整离线回归 pytest 185 passed/0 failed/0 skipped（15.65s）；总体覆盖率 98.21%、行 98.77%、分支 96.44%；ruff/strict mypy（47 files）/diff/index secret scan passed。标准 stdio→真实 HTTPTransport→本机合成三平台 E2E、原生 ImageContent、双 workspace、审批/拒绝、多对多、迁移和安全边界通过；local wheel 离线打包与隔离导入/Schema/迁移通过。默认沙箱 socket bind/uv cache 受限，经执行器允许后验证，非公司平台操作。真实 doctor exit 2，三平台 AUTH_FAILED/configuration_missing，0 平台请求；当前 Host 未挂 DCE、目标业务 workspace 未提供。T6 外部 P0 not_verified，整体未验收完成；不以旧报告或合成 SDK 替代。新增安全只读 SDK smoke 入口供连接就绪后复验，绝不声称真实 Host 已通过。

## Agent-led T6-followup — 2026-11-04

最终代码审查补强：上游忽略 page limit 时强制单页宽度与显式遗漏；JSON 格式 Compose 同样只返回事实；畸形 Swarm Cluster/Service labels 安全失败。针对性 58 passed（1.41s）；最终全库 187 passed/0 failures/errors/skipped（15.70s），总体覆盖率 98.15%、详见机器摘要；ruff/strict mypy passed。重建最终 wheel 并隔离安装，Schema/0003 角色/九工具枚举通过。外部缺口未变，不宣告整体完成。

## Agent-led T7 — 2026-11-04

README/GOALS/PLANS、九工具清单、迁移回滚、安全/运维、Host 六工作流和续跑、ADR 与验收矩阵已同步，旧 V1 文档明确历史范围。当前测试 187 passed、覆盖率 98.15%；文档契约/项目校验 16 passed（0.50s），ruff/strict mypy/diff/新文档相对链接检查通过。真实新版三平台/图片/Host/指定业务 workspace 与完整模块目录仍 pending/not_verified；无真实平台写、构建、部署或业务文件写入。T7 文档交付就绪，整体未验收完成；接续条件和证据见 harness/agent-led-acceptance.md 与 prompts/agent-led/resume.md。

## Agent-led T2-modules-verified — 2026-11-04

Goal 接续第二轮完成实际推进：核对官方 apiv1.php、modulesEntry GET 和 getProductStructure/getDataStructure，新增 Product scope 的 module_tree，完整树搜索后本地分页、字段白名单、节点/深度/2MB 限额；禁止以 Project/Execution ID 替代 Product ID，旧 modules 部分清单兼容。先行测试 2 failed/1 passed 证实缺口；实现后 QueryParams 与 dict 的测试断言类型差异导致 1 failed，修正断言后针对性 69 passed（2.71s），stdio/本机合成 HTTP 1 passed（1.39s）。最终全库 191 passed/0 failed/errors/skipped（15.94s），总体覆盖率 98.18%；ZenTao Adapter 与事实输入契约 100%。ruff/strict mypy/最终 wheel 隔离安装/九工具与迁移检查通过。官方主分支源码不代表当前公司版本；真实平台/图片/Host/指定业务 workspace 仍 not_verified，缺配置与工作区的阻塞重复第 2 个 goal turn，未达 blocked 审计门槛且本轮有实际进展，goal 保持 active。

## Goal 第三轮阻塞审计（2026-11-04）

当前代码 075212a，初始工作树干净；本轮仅审计提案/验收/代码状态与连接条件。进程中六项平台 URL/凭证变量均缺失、当前工具集合无 DCE、用户未指定业务 workspace；相同阻塞已连续三轮。本轮未发平台请求、未重复 pytest 或 doctor、无新代码测试结果；保留 191 passed/98.18% 基线。逐项审计和恢复输入见 context/agent-led/blocked-audit.md，goal 将设 blocked，绝不设 complete。

## Agent-led resumed-local-intake — 2026-11-04

用户明确业务工作区、凭证源与禅道 v1 登录方式，并更换真实缺陷样本。Host 只读核对 20 Git roots、18 根模块清单、17 CI/Dockerfile，私有首层模块关系提议 18 条、confirmed 0，Schema 校验通过；未写业务目录。显式 dotenv/v1 MCP 启动入口已实现，默认不加载 dotenv；文件模式、无插值/执行、别名/重复/冲突、单次登录/无重试/不附旧 Token/父环境隔离/stdio 安全检查通过。先行 5 failed 证实缺口；测试启动 Python resolve 丢失 venv 修复后基础/安全 20 passed，stdio 合成 E2E 2 passed。最终 pytest 199 passed/0 failures/errors/skips（17.71s），总体覆盖率 98.09%，ruff/strict mypy（48 files）与最终 wheel 隔离检查通过。真实凭证只检查变量名并将模式收紧到 0600，正文/值未进入对话或日志，未执行真实登录。三平台地址和实际 Host 仍待用户回复；原 blocked 审计仅历史，不立即沿用旧计数再次标记阻塞。


## 2026-11-04 resumed-http-cursor

用户补齐 HTTP 地址并选择 Cursor；新增 URL 别名/显式进程覆盖回归后 pytest 201 passed/0 failed/errors/skipped（18.38s），覆盖率 98.09%（行 98.64%、分支 96.39%），ruff/strict mypy（48 files）与最终 wheel 隔离导入/Schema/0003 角色通过。安装验证首次把 /tmp 与 /private/tmp 路径当作不同，规范化比较后通过。真实 v1 认证 201、Bug 200；标准 SDK 九工具、27 次三平台成功只读 calls（ZenTao 4/GitLab 4/Portainer 19）及一次模块树 403，输出 Schema 均校验。指定 Bug 无附件/内联图片，module 未分配；三 Stack File 63/71/78，实际 Service label 的运行 namespace 八页 78 个唯一 ID，不合并来源或自动确认。真实 Catalog 副本先备份迁移并保留 191/219/219/11，原库不改；全局 Cursor dce 已备份更新且其他四服务保留。23 条私有关系草案（22 proposed/1 unresolved/0 confirmed）和具体 diff ready，Schema/纯 refresh passed，未写业务目录。旧独立 GitLab 固定编号补验被自动审批在执行前拒绝（本轮读取范围未明确授权），移除后只按已配置范围执行；旧样本/其 GitLab Compose 保持 not_verified。真实 Cursor Agent 对话/初始化审核、业务文件落地、含图样本、模块只读权限和旧样本范围仍待补。详见 context/agent-led/resumed-http-cursor.md；无业务写/构建/部署/push/merge。


提交前检查：工作流/项目校验/本地凭证回归 25 passed（1.10s），10 份文档相对链接检查通过，git diff --cached --check 与 15 个暂存文件的私有路径/站点扫描通过；.env/.local/private 未入索引。真实 Catalog 原有 11 张业务表计数全部与副本一致，两库 quick_check=ok。


## 2026-11-04 cursor-text-compatibility

用户回传 Cursor 九个 DCE 工具（另有宿主 mcp_auth）、三次实际成功调用与初始化对话；旧文本仅 DCE result.、结构化信封不可见，原三次 truncated 保持 not_observable。先行 5 failed 复现文本缺陷，九工具改为相同 JSON 文本/structuredContent；预算计量双副本/转义。全形状契约改显式 64KB并保留最小预算检查后 39 passed；新增默认关闭的独立图片总预算（最大 3MB，文本预算/Reader 2MB/来源 scope 不变）后针对性 40 passed。最终全库 208 passed/0 failed/errors/skipped（18.14s），覆盖率 97.93%（行 98.45%、分支 96.31%），ruff/strict mypy（48 files）/最终 wheel 隔离检查通过。真实授权新图片经 stdio 返回原生 PNG，原图 382396 字节、ToolResult 512314 字节、truncated=false、文本与结构化相同，无图片落盘；Cursor 模型接收仍待复验。已备份更新 Cursor 的授权图片样本与显式预算，其他四服务不变。模块接口同 Token Bug 200、模块 403 Access not allowed；官方 v1 modules→tree/browse→checkPriv 源码与该错误相符，推断需核对单独读入口/产品范围，实际实例版本未确认，不索取新 Token或绕过权限。完整683行/23关系草案的保存批准已提出，聊天省略片段不写业务目录，confirmed仍0。旧独立GitLab范围未获本轮明确授权，不重试。详见 context/agent-led/cursor-text-compatibility.md。


收尾验证：工作流文档 2 passed（0.51s）、11 份文档相对链接零缺失、21 个暂存文件私有路径/站点扫描通过，git diff --cached --check 通过；凭证源/真实图片/私有运行数据未入索引。


## 2026-11-04 clarification-of-host-restart-and-project-save

用户询问“关开 dce”和文件审批含义，尚未批准业务文件保存。已将私有复验提示词与接入文档改为明确步骤：Cursor Customize→MCPs，关闭再开启 dce 服务开关，等待工具列表后新建 Agent 会话；按官方页面核对。补充项目草案/diff/最终 YAML/规格各自作用和 23 条关系摘要，明确只申请新增业务项目记录，保存不把 proposed/unresolved 改为 confirmed；审批来源为规格 05 阶段 F。仅文案变更，不重跑平台或全库回归，208 tests 基线保留；diff check 通过，业务目录仍未写。

文档工作流检查：2 passed（0.57s）；未运行真实平台读取或改写业务工作区。


## 2026-11-04 cursor-recheck-and-approved-save

用户回传 Cursor 修复后两次实际调用：JSON 文本信封可见，Bug 信封/data.truncated 均 false、data.evidence 1（兼容顶层为空）；原生 PNG 实际进入模型，delivered/truncated=false，未保存或转录。用户明确批准完整文件保存并要求不要提交。Host 将与批准 diff 逐字匹配的 683 行/22451 字节草案只创建为业务 .dce/project.yaml，拒绝覆盖/symlink；23 关系保持 22 proposed/1 unresolved/0 confirmed，审批字段全空。真实 CLI validate exit 0、load_project 复读/字节一致/roots 在 workspace 内通过，业务 Git HEAD/index 前后不变，文件 untracked。本轮无 git add/commit/push、真实平台调用或产品代码修改；208 passed/97.93% 保留既有基线，不重复全库测试。更新记录与文档仅本地未提交。核心初始化闭环；完整模块树403、旧独立GitLab范围/Compose仍未验证，严格全样本验收不虚报完成。详见 context/agent-led/cursor-recheck-and-approved-save.md。


收尾：目标业务文件另经独立 JSON Schema 校验通过；文档工作流 2 passed（0.79s），8 份文档相对链接零缺失，11 个公开工作区文件私有路径/站点扫描通过，git diff --check 通过。DCE HEAD 未变、暂存区为空；没有 git add/commit/push。


## 2026-11-05 incremental-v1-implementation

2026-11-05 增量 A–C：实现前契约见 docs/refactor/agent-led-initialization/INCREMENTAL_V1_CONTRACT.md。现有未提交记录保留且不提交。基线208 passed（12.41s）；事实能力先行6 failed/3 passed复现缺口，新增project_jobs/branch_jobs/pipeline_bridges与stack_service后针对性42 passed（6.81s）。Schema v2先行3 failed/1 passed；新增typed details、独立version_match与纯迁移，旧v1输出省略新空字段以满足冻结原Schema；旧“版本2无效”负例改为版本3，针对性29 passed（1.71s）。阶段全库221 passed（13.35s），ruff/strict mypy49 files通过。当前真实业务文件只读核对28关系24proposed/3unresolved/1confirmed，迁移预览除schema_version外全字段一致，原文件指纹不变。后续补stdio增量E2E、真实限定只读、完整覆盖率和调用示例；尚未声称增量真实验收通过。


## 2026-11-05 incremental-v1-final-verification

增量 A–D 完成。新增 stdio→本机合成 HTTP E2E 1 passed（1.45s），九工具名称/旧六工具1.1/事实工具2.1、双份信封一致、分页与预算边界通过。收尾安全审查补强畸形 environment 名称和 Job 标量字段；中间因服务名变量覆盖出现 3 failed/223 passed，修正后针对性17 passed（1.48s），最终全库 `.venv/bin/pytest -q --cov=src/dce --cov-report=json:/tmp/dce-incremental-v1-coverage.json --junitxml=/tmp/dce-incremental-v1-tests.xml --tb=short`：226 passed、0 failures/errors/skipped（23.08s），总体97.63%（行98.27%、分支95.72%）。`ruff check .`、strict mypy（49 files）通过，最终 wheel 重建/隔离安装验证实际包的新details模块、v1/v2纯迁移、精确服务名和九工具通过；文档工作流2 passed（0.54s）。

真实当前授权范围使用标准 SDK stdio；最终验收选取21次 status=ok（初轮20次、修复后精确服务名复核1次），另2次中间复核留痕，不充当最终版本证据。各分支本次选取的3条上游Pipeline普通Jobs均空，但各有1条bridge；Host核对同项目后显式查询观察到的下游，各2条Jobs。Project/manual首页各3条；两次分支过滤页为空但上游仍有下一页。相同8192字节预算，整Stack截断，目标单服务3634字节、truncated=false、incomplete=false且服务名精确相等。未自动扩展下游、未读私有日志、未保存原始Compose、未请求禅道、未触发CI或部署。不能将空Jobs认定没有构建，也不据此推定分支/环境/版本业务关系。

业务v1文件前后指纹不变，28关系仍24 proposed/3 unresolved/1 confirmed；v2仅在私有目录预览，解析模型除版本外全部值一致，审批/证据/备注保留。本轮没有git add/commit/push，保留此前未提交改动。实际调用JSON保存在gitignored私有目录，公开例子全部合成。新版Cursor operation尚未观察，需重载dce连接后使用；SDK证据不冒充Cursor证据。完整报告 incremental-v1-acceptance.md，机器结果 reports/incremental-v1-summary.json。

收尾独立检查：业务v1、纯迁移v2、两份公开project示例均通过运行时及JSON Schema校验，28条关系/审批/证据/备注保持；17份改动Markdown的70条相对链接有效，35个公开改动文件新增内容的私有路径/主机/项目坐标扫描通过。工作流文档2 passed（0.55s），ruff/strict mypy49 files/diff check通过；DCE索引为空、HEAD未变，业务文件最终指纹与本轮基线一致。


## 2026-11-05 V1.1 Scoped Service Logs（T0→T7）

先读 README/GOALS/PLANS/specs、安全边界并审计 Adapter、FactScope、九工具 Schema、DceError、脱敏与双份输出预算；确认上一轮已验收 DCE 基线仍未提交。先定义 docs/SCOPED_SERVICE_LOGS.md，再扩展既有 Portainer/facts/MCP。无业务目录读取/修改，无真实内网请求，无 .env/Token/私有日志读取，无远程写操作。

新增 service_logs、独立 --portainer-log-scope E:S；核对 Stack.Id/Type/EndpointId/SwarmId、当前 Cluster.ID、Service.ID/namespace/Version，精确名称查找先服务端 name/label filters。服务日志 since/tail/follow=false，受控 raw payload、行数、输出双份字节与总流截止时间，不重试、不降级无限读；正确区分分帧/UTF-8/Task/TTY/Systemerr。任意原文省略，仅固定事件/异常/HTTP 状态/HMAC 关联摘要，不执行注入文本。错误保留来源、窗口、错误码与未知保留期；只有明确过期错误才 LOGS_EXPIRED。

诊断记录：首次专项 33 passed/40 failed，主要因旧输出错误契约仅允许 data=null；修复为 service_logs 专属错误上下文扩展后，另发现并修正测试复用 calls 导致并发版本用例误判。首次全量受沙箱限制有3个 loopback bind错误；仅对本机合成服务器放行后，最终全量 `.venv/bin/pytest -q --tb=short --cov=src/dce --cov-report=term-missing`：323 passed/27.50s，97.63%。新专项96 passed/2.67s；新 stdio+HTTP 1项与原226项均通过。ruff check .、strict mypy52文件通过。uv首次缓存权限失败；获许可后 uv sync --locked --offline --dev 与 uv build --offline 通过，1.1.0 wheel 隔离导入/版本/输入Schema及临时Catalog doctor --mock通过。

真实日志 not_verified：没有明确日志读取权限证据，所以未探测真实日志接口，没有制造审核事件或伪报403。管理员确认权限后才可在已授权测试 pair 上执行一次小窗口有限读取。服务端没有until/关键词过滤、tail可能挤出历史、日志保留期未知、原文省略和HMAC仅进程内稳定均已记录。交付 docs/SCOPED_SERVICE_LOGS.md、schemas/portainer-query.schema.json、harness/service-logs-v1.1-acceptance.md、reports/service-logs-v1.1-summary.json；ADR-025。按当前仓库本地分支协议保留已验收 DCE 基线及本轮增量，不提交业务内容，不push/merge。

最终分帧审阅补充：多 Task 没有末尾换行时保留独立消息；合法超大 frame 到原始字节上限时归类截断。新增2项回归，最终96专项+1新stdio+226原回归=323通过，97.63%；wheel已按最终代码重建。DCE基线本地检查点74ab016，V1.1增量单独提交；Project Schema和业务项目未纳入增量。

## 2026-11-06 V1.1.1 禅道认证稳定性（T0→T7）

先核对实际Cursor启动allowlist、权限→认证→HTTP→错误映射链路，再定义ZENTAO_AUTH_RECOVERY契约。范围外Bug的本地拒绝与旧Token无关；旧入口启动时只登录一次，固定Token没有过期恢复。历史NETWORK_UNAVAILABLE没有证据归因过期，Plan13/Plan14失败记录保持原样，不恢复Goal或启动模型验收。

本地分支fix/zentao-token-refresh-v1.1.1基于ff5c124。复用现有本机凭证加载；新增进程内Manager，首次授权GET懒登录、single-flight刷新、generation防迟到覆盖、原GET最多重放一次；登录POST不重试，失败熔断到重启。严格区分认证JSON、业务403、scope、404、网络、HTML/跳转。Token/密码不落盘，传输诊断整体省略，旧/新Token与账号密码参与响应脱敏。包/MCP server version1.1.1，九工具Schema、错误枚举、Project Schema V2与service_logs保持。

真实过程：ruff初轮修复格式后通过；首次专项37 passed，补stdio恢复和并发失败/两代秘密/有界错误等后中间44 passed。最终完整 `.venv/bin/pytest -q --tb=short --cov=src/dce --cov-report=term-missing` **357 passed/27.20s/97.62%**，零失败、错误、跳过；净增33项认证测试+1项stdio场景。strict mypy53文件、ruff check .、git diff --check通过。uv sync --locked --offline --dev及uv build --offline成功；隔离wheel导入版本1.1.1、九工具、service_logs存在和wheel/sdist无私有目录检查通过。

用户明确授权的既有单个Bug只读验收：本地拒绝零HTTP；同一授权路径无TokenGET401并命中严格JSON认证失效规则；登录POST201、连续GET200两次且仅一次登录；独立新进程POST201/GET200。总计2个认证POST、3个成功GET、1个无凭证GET，guard只允许授权Bug及登录路径，网络重试0，使用独立临时Catalog。不保存正文/图片/Token/Cookie，私有状态和精确scope仅在gitignored `.local/auth-refresh-v1.1.1/`。真实过期恢复/并发未主动制造，Mock通过、真实not_verified；Cursor窗口未重载，Host调用未冒充通过。

交付docs/ZENTAO_AUTH_RECOVERY.md、harness/zentao-auth-v1.1.1-acceptance.md、ADR-026和Cursor启用说明。初轮22个拟交付文件人工diff审阅、凭证模式/内网地址/真实案例ID扫描和文档链接检查零发现；后续纳入本记录再复核。没有修改业务项目、Cursor配置、远程权限，未触发CI/部署/真实日志读取；仅本地提交，不push。

提交前最终复核：23文件范围一致，人工内容审阅与凭证/内网地址/真实案例ID辅助扫描零发现、相对文档链接零缺失；index PUBLIC_DATA_CHECK_OK、git diff --cached --check通过。私有诊断/状态文件均被gitignore拦截，schemas、Project实现及业务文件未入增量。

## 2026-11-07 V1.1.1 Cursor Host集成（未提交）

用户回传桌面两次AUTH_FAILED/Platform configuration is missing及缺service_logs的工具Schema；保留失败，不以之前进程存活/包版本检查冒充Host验收。核对README/GOALS/PLANS/specs、用户级/业务工作区覆盖、PPID/启动时间/解释器及Cursor MCP日志。用户级仅一个dce属性、业务工作区无覆盖，现场却有同名旧CLI与本地凭证两个启动定义；旧CLI未带平台配置/凭证文件。日志有多个历史配置指纹及匹配两种进程启动时间的事件，但缺逐调用PID审计，历史失败精确PID归属不杜撰。

先定义docs/CURSOR_HOST_V1_1_1.md，再加10项测试先行全部失败。补本地--require-platform启动校验、共用CLI日志grant解析与本地--portainer-log-scope；serverInfo统一包版本，Tool/Result元数据及固定stderr审计提供PID/Schema/既有request_id关联，无新MCP工具/业务字段。首轮24项有1项暴露可选诊断挤占1024字节预算的旧兜底分支，修复为优先原信封/省略可选_meta并兼容无error成功信封，随后24通过。三平台合成STDIO/服务日志/契约专项116通过，追加request_id后专项15通过。最终全量 `.venv/bin/pytest -q --tb=short --cov=src/dce --cov-report=term-missing` **369 passed / 29.97s / 97.25%**；ruff、strict mypy54文件、git diff --check通过。

用户级只改dce，先在忽略目录0600备份，追加三个--require-platform；绝对路径、原凭证源、全部Bug/Project/Product/GitLab/Endpoint/Stack授权和env不变、其他MCP条目一致。没有新增Bug或日志grant，不反复临时改配置，不按进程名批量杀其他窗口。

完全相同command/args/env/cwd、原Catalog的独立真实STDIO：握手1.1.1、九工具、三平台配置加载，Portainer契约2.2及service_logs可发现，日志Scope因未授予而blocked；既有授权Bug连续两次与测试Stack元数据一次成功/未截断，资源身份核对通过，初始化/工具/结果/stderr PID一致。原Catalog计数和验收期间配置指纹不变；不保存正文/图片/Token/Cookie。按现场无配置CLI定义做独立负例，临时Catalog/无平台环境，两次完全复现同一AUTH_FAILED，零平台请求，证明不是Token过期；两入口Schema都含service_logs。追加固定request_id字段后只补本地STDIO身份检查/合成回归，不重复业务读取。

真实Cursor桌面重载后的调用待用户复验：不把SDK会话PID当作Cursor进程，不把旧PID退出/新PID存活当作集成成功。已提供目标窗口停用/重载/启用/新会话及请求ID对照步骤。未改Token Manager刷新算法/凭证加载器/Project Schema或业务project.yaml，后者指纹一致；无CI、部署、真实日志或图片读取，无暂存/提交/推送。公开结果harness/cursor-host-v1.1.1-acceptance.md，ADR-027；企业配置、备份和安全实测事实仅在gitignored `.local/cursor-host-v1.1.1/`。

最终内容审阅再发现诊断可能挤掉边界内的数据/图片，调整为任何裁剪前先省略可选结果_meta，恢复原日志静态计量接口，并加1项确实验证原结果仍可返回的边界测试。新增边界/契约专项16通过；最终全量 **370 passed / 45.69s / 97.25%**，strict mypy54通过。真实平台读取不重复；另以同入口实际STDIO执行本地discovery_status，确认request_id/stderr/PID关联、零平台请求。14文件内容审阅及辅助扫描零发现，文档链接零缺失；配置/凭证备份均被忽略，index仍为空增量，业务文件指纹不变。

## 2026-11-08 V1.1.1工程收尾与本地提交

用户明确回传真实Cursor Host Gate A PASS：1.1.1、九工具、service_logs可发现、原授权Bug连续两次及测试Stack元数据读取成功。验收PID与业务资源ID仅追加到忽略的本地验收报告，来源标明用户确认；未重跑公司请求，不将旧失败或旧待验记录改成当时已通过。Service Logs Gate B仍not_verified，本轮不新增日志授权或执行真实日志读取。

检查全部14文件差异及Cursor工具目录：JSON工具定义不含旧PID且service_logs枚举正确，旧Runtime PID实际来自缓存的INSTRUCTIONS.md。DCE在进程内用os.getpid构建runtime，未发现Catalog读写持久化路径。仅从可缓存握手说明移除瞬时PID，保留稳定Schema摘要、实时元数据和request_id审计，不手工改Host缓存，不重启已通过连接。新增同一合成Catalog连续两个STDIO进程的回归，旧实现先行失败；修正后专项17 passed。最终全量 **371 passed / 31.45s / 97.25%**，ruff、strict mypy54文件、git diff --check通过。

用户级MCP及实际配置/凭证源仅检查路径和Git跟踪状态，凭证正文未打开；实际源均未跟踪，库内仅合成.env.example。公开Schema摘要与此前验收完全一致，Token Manager/凭证加载器/Schema源未改，Bug allowlist和日志权限未调整。14文件人工审阅/辅助扫描零敏感发现，相对链接零缺失；私有报告、企业MCP配置和备份不纳入提交。按用户授权仅在当前fix分支本地提交 `fix: stabilize Cursor MCP host integration`，不push、不改远端main、不访问或修改业务项目。

## 2026-11-08 Gate B授权准备（未提交，真实日志0次）

原--portainer-log-scope仅Endpoint:Stack，覆盖整Stack，不能满足本轮单服务授权。先写GATE_B_PREFLIGHT契约和失败测试，追加可选私有策略：固定来源/Stack/Endpoint/Swarm/namespace/完整Service ID与名称，Fact层与Adapter入口两次限制选择器，实际元数据再次比对。两个入口要求策略和唯一日志pair同时生效，不变更其他平台、Token Manager或九工具输入Schema。

私有文件0600/目录0700、摘要及TTL检查；O_EXCL标记在日志GET前预占一次，跨进程与重启共享，失败/超时/取消不返还。滚动300秒在派发前再次收紧，整数since向内取整避免不足1秒越界，最多20行、实际策略16KiB原始payload/8KiB完整MCP结果/10秒；follow仍由Schema禁止且线上参数固定false。

真实目标元数据GET六项均200，精确Stack/Endpoint/Swarm/namespace/Service匹配，Docker API1.47/json-file；不保存原始Env/服务配置/凭证。真实service_logs始终0。最初双入口STDIO测试因两次读取时钟构造出略超300秒窗口而被拒，修正为单个end派生start后通过；不放宽服务端限制。新增55项合成安全测试覆盖越权/篡改/撤销/配额竞争/失败消费/双入口。最终完整426 passed/38.22s/97.24%，ruff、strict mypy55文件通过。

用户级先0600备份，仅dce追加日志pair+精确策略；原args/env、凭证源、其他MCP完全一致。同一实际入口只执行initialize/tools/list，握手1.1.1、九工具、三平台配置和精确限制可见，未占额度、不重跑Gate A。策略最长1小时并检查未使用；本地READY报告记录有效期、执行参数、Cursor重载和立即撤销步骤。READY不是Gate B PASS；真实日志权限与保留期等待一次实际读取，任何失败都不自动重试。业务项目/关系/project.yaml、Git index/HEAD及远程均不修改；所有企业身份/配置/报告仅在忽略的本地目录，源代码变更等待用户审核，不自动提交。

## 2026-11-09 V1.1 / V1.1.1正式工程收尾

核对当前fix分支及既有提交：V1.1日志能力、禅道认证恢复及Host集成均已有各自提交；剩余为Gate B精确策略、一次性额度及双入口接线、55项合成测试和预检文档，不重复已有提交。人工审核确认Name/ID精确白名单、实际Stack/Swarm/Service归属、滚动窗口/行/字节/超时、固定脱敏摘要、九工具兼容及每次请求重查策略的撤销机制。未新增依赖、MCP工具、业务Schema或远程写操作。

后续真实Cursor独立执行阶段已完成GET1次，6条脱敏事件，truncated明确；同request_id的Cursor请求/结果摘要、DCE成功审计、持久额度及撤销检查相互对应。临时授权REVOKED，旧读取进程退出，新进程无日志参数，未发现越权或敏感泄露。实际身份/策略/用户配置/原始响应不纳入公开摘要，历史准备0次及失败记录仍保留各自时点。ZenTao真实Token过期后的自动恢复仍not_verified，Mock覆盖不冒充现场通过。

本轮最终全量 `.venv/bin/pytest -q --tb=short --cov=src/dce --cov-report=term-missing`：**426 passed / 36.08s / 97.24%**，无失败或跳过；ruff check .、mypy --strict src/dce（55文件）、git diff --check通过。只运行合成/本机HTTP测试，没有重复真实日志或三平台读取。正式摘要harness/v1.1-final-acceptance.md和机器结果harness/reports/v1.1-final-summary.json，并同步README/历史报告的当前结论入口。

仅提交已审阅的DCE源码、合成测试和脱敏文档；用户级MCP/实际凭证源/全部.local均未跟踪，真实策略与日志不进入Git。人工内容审阅结合辅助扫描及文档链接检查，不以普通diff检查代替隐私审核。按用户指令仅本地提交，不push、不创建Tag/Release、不修改远端main或业务项目。

## 2026-11-10 独立脱敏发布候选

保留原验收分支，先检查main的两条可达提交及30个唯一blob，未发现阻断资料；刷新远端后main基线未变。创建无upstream的独立本地worktree，导入完整已验收快照，泛化5份相互引用的历史文档。实际样本身份、环境接入画像及现场凭证文件状态不复制到公开资料，保留抽象的授权/关系核验与历史行为契约；不编造样本或改写旧成功/失败结果。

初始一致性检查尝试write-tree时因沙箱只读索引锁失败，改为只读cached diff核对，失败发生在文档写入前。随后逐文件比较确认功能代码、测试、Schema和依赖锁定文件未变。独立虚拟环境uv sync --locked --offline --dev通过；完整426 passed/38.29s/97.24%，ruff、strict mypy55文件通过，包实际从候选路径加载。没有连接公司平台或重新运行真实日志验收，没有修改原venv、MCP配置、凭证或业务工作区。

本地候选以干净main为唯一父基线，不纳入旧feature/验收分支的敏感祖先；原分支和旧远端均不重写。当前只准备可审核候选，后续推送须使用新SHA和新范围，不能声称旧公开历史已清除。只提交脱敏快照，不push、不force push、不创建PR/Tag/Release。


2026-11-11 补充诊断：增加旧Catalog checker独立阶段后发现其把合法有界截断一律判失败。合成大Catalog中project_context/discovery_status完整返回，service_trace/deployment_inspect按16KB预算省略data，正确携带omissions/next_action。修复checker为验证Schema、status、字节预算及截断披露，并分别报告complete_reads=2、truncated_reads=2；错误与越权负例仍必须拒绝，未提高预算或屏蔽错误。单独全新合成Catalog实跑已通过。工作树文档JSON用实际Pydantic输入校验，4个调用示例通过；迁移参数修正为--target-version。


2026-11-11 备份与复核：四条旧开发分支分别为原最终5092d6a的祖先，独有历史18/33/35/38提交均已有最终干净功能快照覆盖；旧资料脱敏差异刻意不导回产品。创建新的.local/upgrade-chatgpt-history-backup-20261111/development-branches.bundle（0700目录/0600文件），git bundle verify通过；在临时裸仓库恢复四个原HEAD完全一致，git fsck --full --no-reflogs通过。不checkout旧代码，不读取既有.local私有材料，备份不进入Git。

产品代码审阅确认src/Schema/fixture/example/Prompt/pyproject/uv.lock与2748c7b仍无差异；只有验收编排、合成测试、checker修复与文档/CI入口改动。CI改为调用同一验收入口（未触发真实GitHub工作流）。README精简为入口，旧历史结论转向带原日期的harness，不再混入当前安装步骤。


2026-11-11 最终交付：本地临时分支提交dba07db/bfa9c2d/a9a037b后命名feature/upgrade-chatgpt，目标预先不存在。四个旧分支全部按备份审计显式删除，本地仅main/feature/独立干净候选；main=078962e、候选2748c7b与零Tag均保持。没有修改origin引用。最终在干净a9a037b501949047e58abe7b6c27cf2b93c4a53a执行完整入口，20阶段全PASS、431 passed/0failed/0skipped、97.24%；执行时间2026-11-11T02:23:42.165971+00:00至2026-11-11T02:24:40.275142+00:00。实现SHA256 ef6a689d26fdb1bbf2803a5b27206d8e5063f0155531b9047b03e43a41744428重算一致。最终报告/指南归档不改变被测代码。测试过程中再生的18个缓存路径收尾定点删除，保护根未动。

最终补充重装实测：在临时目录使用git clone --no-local --single-branch --branch feature/upgrade-chatgpt，仅本机传输；git cat-file确认四个旧开发HEAD对象不在新对象库。新目录锁定离线uv sync、导入路径在新clone、CLI --help、doctor --mock均PASS，临时目录自动移除。指南明确--no-local防止本地克隆优化硬链接旧对象库；此补充不冒充runner计数。


2026-11-11 用户追加授权提交推送与删除无用分支：只读git ls-remote确认main=078962e、fix=2748c7b、work=5ab897f、无Tag，feature尚不存在。gh pr list只读确认PR #1仍OPEN且head是fix，因此保留该有用分支，不修改PR。现有本地工作区干净；6个待推送可达提交/275个唯一path-blob模式检查PASS，运行实现摘要匹配原431 passed/97.24%证据，不无意义重跑未改变的实现。私有旧分支bundle再次verify通过，work远端HEAD是备份中5092d6a的祖先。README/指南补GitHub指定开发分支安装与ff-only更新，计划先推送并验证新分支，再以精确旧HEAD lease删除无用work分支。无main/Tag/真实公司服务操作。


2026-11-11 授权操作已执行：cf667fd9db4e4444376727064eef470e83049d0c提交文档与授权范围，git -c push.followTags=false push --porcelain --set-upstream origin HEAD:refs/heads/feature/upgrade-chatgpt成功；ls-remote确认同SHA。随后git push仅删除work/dce-v1-offline，并使用--force-with-lease=refs/heads/work/dce-v1-offline:5ab897f292167f872e5ae0959a247b4b72f0bfa1作并发保护，返回deleted；再次ls-remote实际仅main/feature/fix三个远端分支，无Tag。main078962e/fix2748c7b未变。PR #1仍OPEN，fix有用途保留；本地稳定候选及worktree不动。无强推产品/main、PR操作、Tag/Release或公司API调用。最终归档文档后将同步同一feature分支，并核对本地/远端一致及工作区干净。


2026-11-11 首次真实GitHub托管离线CI核对：run42948651340（cf667fd）失败，已用gh run view只读核对阶段和合成失败日志。setup-uv设置UV_CACHE_DIR=/home/runner/work/_temp/setup-uv-cache；runner的环境白名单遗漏该非秘密路径。pytest等前置全部PASS，wheel_build失败。按契约补充只继承UV_CACHE_DIR并维持凭证/代理隔离、offline=true；新增子进程缓存/凭证隔离行为回归。CI改在新runner.temp生成报告并always上传两份摘要，避免旧跟踪报告冒充本次结果。需本地完整回归和新推送CI实证后才能标修复通过。

CI缓存修复本地新验收：2026-11-11T02:55:00.853797+00:00至2026-11-11T02:55:55.171111+00:00，20阶段PASS，432 passed/0failed/0skipped，覆盖率97.24%。6个验收器行为测试也单独通过。真实执行HEAD=508bf9054ebd32f311823828eed361a47da1419f，dirty=true（修复未提交），新实现摘要c10f4a0d504eca421e4400c11c8c332f6e626d808884c147262adbe9e967d867，随后提交代码据此核对。没有降低离线/安全/覆盖率约束，GitHub实际结果仍待新推送核对。


CI缓存修复已真实托管复核：8a6249047c0d292fc425e322adbe086b834a627c推送成功，run42949449061/job130290046546在2026-11-11T02:57:06Z至02:58:23Z整体success；准备依赖、统一离线验收、actions/upload-artifact、后处理全部成功。gh run watch --exit-status退出0，gh run view再次只读核对headSHA/任务/步骤success。API确认新摘要artifact13823709365存在、未过期、5120字节；两次下载均因TLS握手超时未复读附件，不把它伪称已验证JSON内容。本地真实432 passed/97.24%和实现摘要c10f4a0d504eca421e4400c11c8c332f6e626d808884c147262adbe9e967d867保持。随后仅提交本段/计划/执行报告并同步feature；源业务包、Schema、锁、平台Scope继续与干净候选一致。main/PR/Tag未修改，work远端已删除，当前分支upstream正确。


## 2026-11-12 用户主动项目初始化1.2

初始feature/upgrade-chatgpt=3be4651，工作区干净，main/独立干净候选保留。按用户确认方案先写PROJECT_MODE_CONTRACT，再实现确认broker（SDK原生/127.0.0.1一次页面）、有界发现、ProjectRuntime/私有CAS授权、双入口和十工具。DCE只写私有授权状态，不写业务工作区。无公司平台连接、用户凭证/真实项目读取或Cursor配置修改。

新增真实本机SDK合成STDIO双入口完整初始化/保存/恢复/连续新Bug/Stack服务隔离/撤销；Roots缺失/多root/跨根、持久文件篡改/权限/symlink、审核拒绝/原生/本机页CSRF/Origin/重放/超时、分页与审批保留等行为测试。原九工具legacy测试保留，版本断言改为真实1.2.0。MCP最低依赖升到已锁定且实测的1.30，使用form确认和Roots接口；未放宽业务scope/日志授权。

初次局部旧E2E因沙箱禁止loopback bind失败，授权仅本机合成服务后通过；新页面测试最初受全局禁止IP夹具阻挡，专用页面模块仅允许loopback并验证外部IP仍拒绝。macOS拒绝POST后未读body引起TCP reset，改为有界读取/超时/Content-Length，未隐藏失败。新增测试一处缺失import及stderr断言与既有协议不符已修复。

首次完整runner：456 passed、0failed/skip、93.45%，但Ruff新增Wheel smoke字符串长行FAIL；其他19阶段含Wheel双模式均PASS。长行修正后第二轮20阶段PASS。审阅进一步补精确日志策略与项目范围相交、部分初始化状态、未变审批保留、未知confirmed降为候选，最终结果另记。本次覆盖率分母扩展，75%原硬阈值不变，未删失败测试或伪报97.24%。

2026-11-12 项目模式提交前验收：10:40:12→10:41:16 UTC，20阶段全部PASS，468 passed、0failed/skip、93.79%。Ruff、strict mypy58源码、锁一致性、Wheel1.2.0隔离安装及两种模式SDK均通过。追加Roots/form不支持的显式回退、原生拒绝不绕行审批、递归提案拒绝；修正后实跑，不伪造外部验收。最终审阅给Wheel机器证据补project_tools=10和无初始化启动字段；待干净提交重验并按既有授权推送同一feature分支、核对托管CI。当前只读ls-remote确认feature仍3be4651、main078962e、fix2748c7b且无Tag，没有新增分支可清理。

实现提交d30ac9e和文档43633a9完成。43633a9干净工作区10:45:56→10:47:00 UTC实跑20阶段PASS，468 passed/93.79%。人工核对发现新Wheel证据字段被旧报告白名单过滤，补允许两项固定非秘密字段，准备最终重验；不是工具功能失败，原两模式隔离Wheel已实跑通过。文档澄清审批回退临时loopback端口和只读产品边界。

最终19b7a7e干净工作区10:48:30→10:49:34 UTC：20阶段PASS，468/468、0failed/skip、93.79%；Wheel1.2.0隔离证据保留legacy9/project10、无初始化启动，源码摘要fe81c5848c22335d6b172cde78f3dc55c1b17c7342fa4c0c1f2da4bf2b4f5b0e。正常推送3be4651..19b7a7e至origin/feature/upgrade-chatgpt成功。随后仅定点清除18个无Git跟踪缓存路径65文件（有symlink/异常文件则拒绝），清理报告逐项记录；真实用户凭证/项目/配置未触及。GitHub CI43203834300已启动，待实际结论。

GitHub CI43203834300实际success，offline job 1m57s，锁定安装/完整runner/报告上传及清理步骤全成功；gh run watch --exit-status退出0。没有下载并复读Linux报告，不把本机468/93.79数字冒充Linux artifact。最终仅归档报告/当前计划/清理记录，核对实现摘要不变后正常推送同一feature；真实Cursor/公司平台/Token过期恢复仍not_verified。


2026-11-13 Host Roots修复：用户反馈project_context两种参数均在绑定前返回通用INVALID_PAYLOAD。只审阅代码/合成数据，不读取业务项目/凭证，不调公司平台。先写失败与授权契约，再补8个行为回归，旧代码8FAIL；修复Roots首次不可用时的人工绑定、已绑定失败不降级、旧策略不能免确认及stale Root解析。错误日志只含固定阶段/异常类型/原因码/request_id，不打印原异常。

真实STDIO malformed roots/list回复回归最初因沙箱loopback绑定失败；授权仅合成本机服务后，发现approval_url被通用脱敏为[URL]。随后补canonical remote_url完整保存/complete，以及已知凭证（含转义/换行）、审批前拒绝、外部URL不放行等回归。修复仅在项目控制响应保留已校验文档和当前Broker有效本机链接，未修改普通平台/日志脱敏器。

局部39PASS，Ruff/strict mypy58源码PASS。首轮完整执行03:53:02→03:54:07 UTC，20阶段PASS，483/483、0failed/skip、94.04%，dirty=true的实现摘要f970cdcfb4a731d7f59c5acb3ef972ca2e6e00e0524c865efcfcb619e007e8d6；报告位于本轮新临时目录。没有把旧468项结果冒充本轮，也未降低75%门槛。准备提交后干净复验与归档；真实Cursor Roots原始故障类型仍待现场复测，完整生产初始化不标记通过。


f1b8e2c提交后干净工作区最终复验：2026-11-13 03:56:03→03:57:04 UTC，20阶段全部PASS，483/483、0failed/skip、94.04%，实现摘要仍f970cdcfb4a731d7f59c5acb3ef972ca2e6e00e0524c865efcfcb619e007e8d6。报告记录dirty=false及实际执行提交；只归档新报告和升级说明，不再改源码。准备正常快进推送同名feature并核对托管CI，不修改main/Tag/PR。用户还需在Cursor重启DCE后现场重试，未声称真实业务项目已初始化完成。
