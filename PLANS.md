# 2026-11-11 授权推送与分支清理结果

已提交cf667fd并推送origin/feature/upgrade-chatgpt，远端SHA核对一致、同名upstream已设置。新分支成功后，以精确旧HEAD lease删除远端work/dce-v1-offline（5ab897f），再次ls-remote确认已不存在。旧历史私有bundle已verify；有效功能已整合。main=078962e、Tag为空保持；fix=2748c7b是开放PR #1来源，保留且不改PR。本地独立候选及worktree保留。

README/本地部署手册现含GitHub指定开发分支克隆和ff-only更新；本轮运行实现不变，沿用真实431 passed/97.24%证据并复核摘要，不伪称重跑。后续报告归档仍推送同一feature分支；详细实际操作见docs/UPGRADE_EXECUTION_REPORT.md第9节。以下计划与不推送表述均是原阶段历史。

# 2026-11-11 后续授权：提交推送与无用分支清理

用户已明确授权提交、推送和删除无用分支。重新核对工作区干净、远端main=078962e、无Tag、目标分支尚不存在；当前实现与既有431项通过/97.24%报告的摘要一致，当前HEAD的6个可达提交/275个唯一path-blob模式检查通过。更新README/安装指南以支持直接克隆feature/upgrade-chatgpt；只推送该开发分支，不合入main、不创建Tag或PR。

远端work/dce-v1-offline仍为5ab897f，属于已整合旧历史且包含在已验证私有bundle中，待新分支推送验证后删除。fix/zentao-token-refresh-v1.1.1仍是开放PR #1来源（2748c7b），有实际用途，保留；本地独立干净候选及其worktree保持。以下为原整顿任务的历史记录，本条新授权不改写旧验收结论。

# 2026-11-11 本地产品交付完成

结论READY_WITH_LIMITATIONS。最终feature/upgrade-chatgpt在干净提交a9a037b重跑完整离线验收：20阶段PASS，431 passed/0 failed/0 skipped，src/dce覆盖率97.24%。main和独立候选未变、无Tag，四个已整合旧本地分支已在私有bundle恢复/fsck验证后删除，远端引用未动。最终实现摘要复核一致，之后只归档文档/报告。

入口：docs/UPGRADE_EXECUTION_REPORT.md；复现：uv run --offline python scripts/run_acceptance.py。Cursor桌面/真实平台/真实Token过期恢复仍not_verified。以下记录保留各阶段原时间语义。

# 2026-11-11 本地产品化整顿（当前）

T0：工作区原先干净；main=078962e、无Tag；干净候选2748c7b与原5092d6a功能文件逐字节相同。临时工作分支从main创建，dba07db导入候选树，未继承旧敏感祖先。先建立分支以遵守AGENTS本地工作分支提交要求，最终命名和旧分支整理在交付完成后执行。

T1–T4：定点删除25个可再生路径和2份旧原始报告；有效源码/测试/fixture/Schema/Prompt、历史脱敏证据与用户私有目录保留。按真实工具契约整理差异、部署和十五个教程，新增离线验收边界先于编排代码。

T5–T7：新增一键验收，清除业务环境、Python仅loopback、uv强制offline；记录阶段、命令、版本、新JUnit和覆盖率、Wheel隔离CLI/MCP。修复旧stdio checker的2.0过时断言。首轮430/431通过（仅新增自测断言失败），requirements离线解析缺缓存索引；已修复自测与改用锁文件同步独立环境。第二轮431/431、97.24%，Ruff、strict Mypy、锁一致性、Wheel/全隔离九工具通过。增加合成CLI/旧checker验收后将再重跑。

本轮真实平台、Cursor桌面Host、真实Token过期恢复均not_verified，不挪用历史Gate A/B。最终状态、分支/Tag保全、删除备份和最终重跑见docs/UPGRADE_EXECUTION_REPORT.md与docs/acceptance/acceptance-summary.json。禁止push/PR/Tag/远端操作，未修改用户配置或凭证。

# 2026-11-10 独立公开发布候选（本地，待审核）

公开审核发现旧资料包含真实样本身份，并在关联提示词/验收说明中重复。原验收分支和私有证据保留；从已审核的main建立独立候选，导入完整已验收应用快照，仅泛化5份历史文档中的具体身份及现场接入观察。不把旧feature历史作为候选祖先，不改远端、不force push。

候选代码、测试、Schema、依赖锁定文件与已验收快照字节一致；独立venv离线安装后完整426 passed/38.29s/97.24%，ruff和strict mypy55文件通过。Gate A/B既有结果保留为原现场验收事实，本轮不重跑真实日志、不签发授权、不改用户MCP或业务项目。禅道真实Token过期恢复仍未现场验证。

完整候选快照及其main祖先均需公开数据审核，原已公开feature历史仍需另行授权处理。候选发布SHA和提交范围已改变，待用户审核后再决定推送；不得沿用此前针对旧HEAD的推送指令。

# 2026-11-09 V1.1 / V1.1.1正式工程收尾

限定项目Agent-led V1验收、Cursor Host Gate A和Scoped Service Logs Gate B均PASS。真实日志GET仅1次，返回6条脱敏事件，truncated明确；临时授权REVOKED，旧读取进程退出，新入口无日志grant，未发现越权或敏感泄露。精确身份、进程共享单次额度、滚动300秒/20行/16KiB读取/8KiB输出/10秒及撤销机制经过审核；九工具、Token Manager、Project Schema保持。

本轮完整回归426 passed/36.08s/97.24%，ruff、strict mypy55文件、git diff --check通过；不重复真实日志或平台请求。禅道真实Token过期恢复仍not_verified，不能以基础登录成功替代。最终脱敏摘要见harness/v1.1-final-acceptance.md及harness/reports/v1.1-final-summary.json；企业身份、策略、原始返回及用户配置不入Git。历史失败、未验证及准备记录按原时点保留。

仅将审核后的DCE源码、合成测试和脱敏文档提交当前本地分支；不push、创建Tag/Release、修改远端main或业务项目。以下未提交表述均为当时阶段记录，不代表最终状态。

# 2026-11-08 Gate B临时日志授权准备（历史实施记录）

按T0审计→T1预检契约→T2精确策略→T3双入口/Adapter接线→T4私有配置→T5合成安全/STDIO→T6回归与真实目标元数据→T7本地READY报告推进。原日志pair只能限制Endpoint/Stack，本轮最小追加可选私有策略，强制单服务身份、最多300秒/20行、16KiB读取/8KiB输出/10秒，以及跨进程共享的一次派发额度；失败也消耗，撤销与TTL均安全拒绝。

426项完整回归通过/97.24%，ruff、strict mypy55文件通过。真实目标元数据六个GET成功；相同用户配置启动入口仅初始化/枚举，1.1.1、九工具与精确策略限制可见，真实日志调用0/额度未用。不重跑Gate A、不新增其他平台授权，原Token Manager/Schema/业务project.yaml不改。用户级只向dce追加pair+policy，0600备份，其他条目与既有args/env保留；真实身份、策略和报告仅在gitignored私有目录。

本轮READY表示准备就绪，真实日志权限/保留期仍not_verified，等待Cursor在有效期内唯一一次只读验收并立即撤销；不是Gate B PASS。未暂存、提交、推送、触发CI或部署，公开变更仅含DCE源码/合成测试/必要文档。见docs/GATE_B_PREFLIGHT.md和ADR-028；此前阶段记录保持原样。

# 2026-11-08 V1.1.1工程收尾与本地提交

用户已确认真实Cursor Host Gate A PASS：1.1.1、九工具、service_logs发现、原授权Bug连续两次及测试Stack元数据读取通过。准确验收PID/资源ID仅记录在忽略的本地报告，不纳入Git。此前失败和待验记录保留为当时事实。

已审核本轮全部源码/测试/文档。旧Runtime PID位于Cursor工具目录的INSTRUCTIONS.md快照；DCE运行身份由当前进程创建，没有从Catalog或该目录加载/持久化。最小收尾仅从可缓存的握手说明移除瞬时PID，保留稳定Schema摘要、实时结果PID和request_id审计。增加同Catalog双STDIO进程回归，确认说明/Schema稳定、PID/request_id更新；不修改Token Manager或授权。

收尾验证371 passed/31.45s/97.25%，包含既有370项与新增缓存说明回归；ruff、strict mypy54文件、git diff --check通过。14个交付文件人工审阅和辅助敏感扫描零发现、文档链接零缺失；用户级配置/凭证/私有报告均未跟踪，仅合成.env.example模板在库内。

本轮用户已授权仅在当前fix分支提交这14个DCE文件；不得纳入用户级MCP配置、凭证、.env或.local报告，不push、不改远端main。Service Logs Gate B仍not_verified：尚需单独日志权限审批及限定窗口真实只读验收；本轮不执行。

# 2026-11-07 V1.1.1 Cursor Host集成修复（历史实施记录）

T0核对配置/窗口覆盖/进程及Cursor MCP日志；T1先定义CURSOR_HOST_V1_1_1边界/失败/测试；T2补本地启动平台要求及共用日志grant解析；T3运行身份/Schema摘要/固定stderr请求审计；T4备份后仅更新用户级dce启动校验参数；T5合成STDIO与授权/预算回归；T6同一Cursor定义真实STDIO；T7文档与桌面重载方案。全部保持未暂存、未提交、未推送，等待审核。

- 已确认同名dce存在无配置CLI和带凭证入口。Platform configuration is missing是本地平台配置缺失；真实STDIO负例完全复现，不能归因Token。旧日志缺逐调用PID证据，历史两次失败的精确进程归属不杜撰。源码Schema已含service_logs，Cursor旧显示需重载。
- 用户级仅追加三项--require-platform，备份0600、其他MCP/全部scope/凭证源不变，无新Bug/日志grant；业务project.yaml字节不改。不杀其他窗口进程，不用临时配置抖动冒充成功。
- 合成回归370 passed/97.25%，ruff、strict mypy54通过。独立真实STDIO握手1.1.1、九工具、三平台配置、service_logs发现、原授权Bug两次与测试Stack元数据一次通过，Catalog计数不变。实际Cursor桌面重载后调用待用户复验。
- Token Manager与Project Schema实现未改，无CI、部署、真实日志或图片读取。契约/结果见docs/CURSOR_HOST_V1_1_1.md及harness/cursor-host-v1.1.1-acceptance.md，ADR-027；旧失败记录保留。

# 2026-11-06 V1.1.1 禅道认证稳定性

按既有T0→T7顺序完成：T0核对当前Cursor精确scope与旧启动认证链路；T1先定义ZENTAO_AUTH_RECOVERY边界/错误/测试；T2复用现有凭证入口实现进程内Manager；T3 Reader一次GET恢复与并发generation保护；T4 MCP既有脱敏和版本接线；T5合成并发/错误/stdio覆盖；T6完整回归与限定真实只读验收；T7文档、ADR-026、本地交付。

- 真实scope拒绝独立于Token；没有调整Bug/Project/Product allowlist。历史网络错误不推断成过期，Plan13/14记录未改、不恢复Goal、不新增模型调用或预算。
- 357 passed / 97.62%，ruff、strict mypy53文件通过；离线wheel/sdist1.1.1构建通过。真实已授权单个Bug：无TokenGET401，登录201/两次GET200；独立新进程201/200。真实过期/并发不主动制造，Mock通过、真实not_verified。
- 不修改业务源码/分支/project.yaml，不改Cursor或远程权限，不触发CI/部署/真实日志查询，不push。精确scope、路径仅在忽略的私有报告；公开报告不含实际资源ID、URL或凭证。
- 详见 docs/ZENTAO_AUTH_RECOVERY.md 与 harness/zentao-auth-v1.1.1-acceptance.md；保留此前V1.1及其余历史原文。

# 2026-11-05 V1.1 Scoped Service Logs

T0 审计 → T1 契约 → T2 Adapter/独立授权 → T3 安全投影 → T4 MCP → T5 合成测试 → T6 回归打包 → T7 文档完成。仅扩展 portainer_query；九工具、Project Schema V2、Host 职责不变。没有访问业务目录、真实平台、凭证文件或私有日志，没有根因推理、修复、构建/部署业务功能或远程写 API。

- 契约：docs/SCOPED_SERVICE_LOGS.md；运行时导出 schemas/portainer-query.schema.json；ADR-025。
- 离线：323 passed / 97.63%；其中新专项 96 + 新 stdio/HTTP 1；ruff、strict mypy 52 文件、doctor --mock、离线锁包/构建、wheel 隔离导入均通过。
- 真实日志：not_verified，缺少明确读取权限证据；没有主动探测或制造审核事件。空日志保留 retention unknown，不能冒充无权限/过期/事件不存在。
- 风险边界：服务端没有 until/关键词过滤，使用 since + finite tail，再在有限字节和总流截止时间内筛选；达到 tail 可能缺失；自由文本省略，匿名关联仅同进程稳定。
- 本轮用户允许 DCE 本地阶段记录；此前“不提交”的历史回合不扩展为业务仓库提交授权。既有已验收未提交 DCE 基线与 V1.1 增量分开保存在本地分支；不 push/merge，不纳入业务仓库。
- 交付与实际结果：harness/service-logs-v1.1-acceptance.md、harness/reports/service-logs-v1.1-summary.json。

# 2026-11-05 当前增量：Agent-led V1 真实项目缺口

本轮 A–D 已完成实现、测试、文档和当前范围真实只读 SDK 验收；全部保持未提交。保留此前未提交记录，业务 project.yaml 不修改、不自动迁移、不暂存/提交/推送。

| 项目 | 状态 | 证据 |
|---|---|---|
| A GitLab | passed | Project/Branch/Pipeline Job、manual/retried、bridges/分页/空页/权限；实际三个上游空普通 Job，对应同项目下游各 2 Job |
| B Portainer | passed | stack_service 服务端精确选中、安全字段；8KB 内整文件截断、单服务最终 3634 字节未截断 |
| C 项目 Schema | passed | v1 默认与冻结 Schema，v2 typed details/独立 version_match；真实 28 关系纯迁移全字段语义保留，原文件指纹不变 |
| D 验证/文档 | passed_with_host_boundary | 226 tests/97.63%，ruff/strict mypy49、stdio E2E、wheel隔离安装；真实 SDK不是未观察的Cursor新操作调用 |

实际调用示例只留本机 .local/agent-led/incremental-v1/MCP_CALLS.md；公开合成示例/迁移命令见 docs/AGENT_LED_INCREMENTAL_V1.md，契约见 docs/refactor/agent-led-initialization/INCREMENTAL_V1_CONTRACT.md。报告见 harness/incremental-v1-acceptance.md 和 harness/reports/incremental-v1-summary.json。

业务文件保持 v1 / 24 proposed、3 unresolved、1 confirmed，审批/证据/备注完整。本轮不触发 CI、不部署、不请求私有日志、无禅道请求。新增操作需 Cursor MCP 页面关闭再开启 dce 以加载 revision 2.1；不改变已有九工具名称。不将本轮业务文件只读检查扩大为旧独立样本授权。

以下为 2026-11-04 初始化及更早历史记录：

# Agent-led 当前执行状态（2026-11-04）

核心初始化链路已通过：用户回传真实 Cursor Agent 九工具、三平台实际调用、初始化对话，以及修复后 JSON 文本和原生 PNG 到模型；完整关系文件获批准后由 Host 写入业务项目并校验/复读。严格全样本验收仍有模块树权限和旧独立 GitLab 样本范围缺口，整体 goal 未完成。此前缺地址/Host/工作区的 blocked 审计仅作历史，不复用旧阻塞原因。

最新用户约束：允许保存完整候选关系文件，**不要提交**。本轮不 git add/commit/push，包括业务文件和 DCE 的执行记录修改；该约束优先于下方历史 AGENTS 阶段提交约定，不再询问已批准的文件保存。

本地分支 refactor/agent-led-project-init；实际提案路径 docs/refactor/agent-led-initialization/dce-agent-led-refactor/。

| 阶段 | 当前状态 | 证据/遗留 |
|---|---|---|
| T0 审计 | passed | harness/refactor-audit.md；六工具/Schema/Adapter/关系引擎先审计后修改 |
| T1 解耦 | passed | 默认路径无语义 Mapping/AI；保留技术事实与旧消费者 |
| T2 只读能力 | offline_passed_live_partial | 九工具 JSON 文本/结构化兼容；SDK PNG 和 Cursor 模型接收通过；完整模块入口仍 403 |
| T3 项目文件 | passed_offline_and_real_saved | 20 Git roots；完整 683 行/23 关系批准后保存，Schema/CLI/复读通过；22 proposed/1 unresolved/0 confirmed；文件未跟踪 |
| T4 Agent 工作流 | passed_real_host_user_reported | Cursor 九工具/三次实际调用/初始化对话及 JSON/图片复验；原调用截断未知与新复验 false 分开记录 |
| T5 Catalog | passed_offline_real_copy_migrated | 真实旧库副本先备份再迁移；191 实体/219 边/219 证据/11 快照保留，原库不变 |
| T6 验证 | offline_and_core_live_passed_full_samples_pending | 208 passed/97.93%；Host/模型图片/项目文件落地有证据；模块权限/旧样本未验证 |
| T7 文档验收 | updated_uncommitted_full_acceptance_incomplete | README/迁移/清单/harness 更新；按用户要求保持未提交，不标严格全验完成 |

项目保存仅代表允许新增候选记录，没有逐条业务关系审批；approved_by/approved_at 全为空。Bug↔代码 unresolved，Stack/Swarm 仍 candidate/proposed，不推断环境/健康/版本。业务 Git HEAD/index 在保存前后均未变，新增文件 untracked，DCE 服务没有业务目录写接口。

下一步仅为未解决的外部项：管理员核对 tree/browse 读入口/产品范围后补模块树；旧独立 GitLab 样本需明确读取范围，未获批准前不重试被自动审批拒绝的请求。无需重复索取 Host 回传、图片样本、工作区或文件保存批准，不重复已成功的平台请求。

续跑：prompts/agent-led/resume.md；最新证据见 harness/context/agent-led/cursor-recheck-and-approved-save.md、harness/build-log.md、harness/test-results.md 与 harness/agent-led-acceptance.md。本轮无真实平台调用、业务写 API、构建、部署、git add/commit/push/merge。

## 以下为旧 V1 计划和历史执行记录

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

当前进度（2026-11-03）：T0–T7 passed（离线目标完成）；本地分支 `work/dce-v1-offline`；三平台限定只读、源码项目 live discover 与六个已实现 MCP 工具处理的真实补验通过。仅验收已实现 V1 功能，不纳入业务页面/修复执行。
离线基线：133 tests，总体覆盖率 98.58%（行 99.18%、纯分支 96.65%）；ruff、strict mypy、CLI/MCP、独立 wheel 安装通过。
最新 HTTP 修复回归：139 tests，总体 98.58%（行 99.19%、纯分支 96.66%），ruff 与 strict mypy 通过；摘要见 harness/reports/http-encoding-summary.json。
最新 MCP 契约修复回归：144 tests，总体 98.73%，ruff 与 strict mypy（40 files）通过；摘要见 harness/reports/mcp-contract-summary.json。
基线逐项证据：harness/acceptance-report.md。完整真实链路与 Agent 内实际工具调用 not_verified；Cursor 配置及进程启动见本文接入记录。

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

第二阶段（2026-11-03，进行中）：用户要求继续验收，推进 CI 产物/部署静态资源摘要和目标服务任务/镜像证据。实际测试首页同源跳转后 HTTP 200；原生 GUI helper 两次辅助功能未允许，未操作页面。已准备有界、只读、不回显输入的私有部署核验入口并给出运行命令，等待实际报告；13 项新安全检查和原 19 项检查通过。三个前端实际部署分支待补充；不得以候选 develop/master 替代确认。详细状态见 harness/phase2-readonly-progress.md。此阶段尚未通过版本或业务验收。

范围纠正（2026-11-03，当前依据）：用户明确只验收 DCE V1 已开发能力，业务 Bug 表是输入案例，不要求执行公司页面/业务修复回归。停止浏览器操作与辅助功能请求；前端发布分支、审批/回调、完整发布指纹不作为新增 V1 门槛。已运行的额外脚本报告仅保留补充只读观察。使用真实数据 Catalog 补验标准 MCP stdio：四类读取工具五次成功；两类上游工具越界拒绝及未知写工具拒绝通过，预算/只读/候选保留通过。未执行两类工具真实上游成功调用和完整 live discover，继续标 not_verified，不把补充脚本当作产品功能。统一结论见 harness/v1-acceptance-status.md；无需再输入部署或浏览器凭证。

V1 继续补验准备（同日）：用户要求继续，仅为既有 AppServices.discover 与 MCP 上游处理准备私有本机入口。选定原范围内无本地 Compose 的源码项目，只允许固定 commit 的模块 manifest/CI/Dockerfile；BugContext 禁图片，Pipeline Diagnose 禁 trace。真实 HTTPTransport 加范围护栏，无模拟响应或新产品业务实现。护栏六项合成检查通过，入口/SDK 检查 ruff 通过；已提供本机运行命令，需 GitLab Token 与一次禅道登录，等待实际报告。不要重跑额外部署/GUI 脚本；本轮尚未实跑的路径不能标为已通过。

V1 补验结果（同日，当前）：用户已执行入口，本轮限定 V1 路径 passed。产品 AppServices.discover 对一个授权源码项目实跑成功，读取 commit/tree/三个元数据文件，新增六个 build_job；独立库 191 实体/219 关系/219 证据/11 快照。CI incomplete 一条、业务映射未确认、BugContext 模块数 0 均正确保留。真实 BugContext 与 success 流水线诊断成功，六个 McpApplication 工具处理全部成功，输出 519–12289 字节，读取不改变 Catalog、无自动 confirmed。受控出网 GitLab 15 GET / ZenTao 1 GET，无拒绝或非法请求；另一次授权 v1 登录。标准 SDK stdio 证据与本轮处理层证据分开。无需再次运行入口；更多发现范围、图片/Compose/私有失败日志及实际 Host 仍不作已验声明。结果见 harness/v1-acceptance-status.md 与 harness/reports/v1-live-summary.json。

## Cursor 桌面版 stdio 接入（2026-11-03，已落地）

- 用户要求启动现有 MCP 并补充接入文档；不增加业务工具、HTTP 服务或公司写操作。
- 默认接入独立的真实 Catalog 副本：四类本地查询可用；使用 `--live --read-only` 且不设置上游 allowlist，使 Bug/流水线读取明确拒绝，不混入合成结果。
- 安装使用绝对路径，保留已有 Cursor JSONC 配置和其他 MCP；凭证不写配置。系统目录修改按执行器权限申请，实际 Host 未观察到前保留 not_verified。
- 验证计划：标准 MCP SDK 初始化、六工具列表、四类查询、两个越界拒绝、未知写工具拒绝、预算与 Catalog 数量不变；提供可重复运行的本地检查命令。
- 实际结果：全局 JSONC 新增 `dce`，备份并保留四个已有服务，不含 DCE 凭证；Cursor 3.27.6 已启动 DCE 子进程（父进程链包含 Cursor）。真实库副本 191 实体/219 关系/219 证据/11 快照；SDK 四类查询通过、两类上游拒绝和未知写拒绝通过，输出 1991–12289 字节、数量不变。缺失库检查 exit 1 且不建空库。
- 新增 `docs/CURSOR_MCP_SETUP.md` 和可重复的 `scripts/check_mcp_stdio.py`；本机路径、原配置备份、报告与可直接粘贴的提示词只留在 gitignored 私有区。MCP 相关 4 tests、ruff、strict mypy（39 files）、diff check 通过。实际 Agent 会话调用及实时上游配置仍 not_verified；摘要见 harness/reports/cursor-mcp-summary.json。

## Cursor 能力检查暴露的 MCP 契约修正（2026-11-03，修复并重载）

- 用户真实 Cursor 能力检查确认：工具描述模板化、返回 Schema 无业务字段、部署参数互斥约束未发布；连接 ready 与实际平台读取条件未分开。
- 先完善 CLI_MCP_CONTRACT 的边界、失败处理和验收：六工具保持不变；补平台/数据源/会话状态、字段说明、完整数据与错误/截断 Schema、参数互斥；list_tools 不探测网络、不输出凭证和私有范围。
- 核对现有服务：MCP 只在 bug_context / pipeline_diagnose 可请求上游；四类查询读取 Catalog，部署检查未实时比较 Swarm，snapshot_at 为响应生成时间。修正文档和实际发布契约，不把未配置或 CLI-only 能力当作未开发，也不新增业务功能。
- 验证计划为 JSON Schema 正反例、合成受控上游、SDK stdio、全库回归/覆盖率、lint/typecheck；已按下述结果执行，宿主缓存更新单列。
- 实际结果：先以三项失败复现描述/互斥/输出约束缺口，修复后新增五项契约测试；完整 144 passed（11.66s），总体覆盖率 98.73%（行 99.29%、分支 96.88%），契约模块 100%，ruff 和 strict mypy（40 files）通过。输出先做严格模型校验，后端不符合契约时只返回固定安全错误。
- 真实 Catalog 的新 SDK stdio 子进程 revision 1.1：四类查询及已发布 Schema 校验通过；两个 scope 拒绝和未知写工具拒绝保持，输出 1991–12340 字节、数量不变。没有新增上游范围、常驻凭证或公司请求；本轮先完成契约修复，实时接入需明确安全凭证来源。
- 保留原有 MCP/启动范围，只显式设置既有 16KB 输出预算触发重载；实际观察到 Cursor 创建一个新 DCE 子进程，但同时仍有一个原连接进程。不能声称所有窗口已刷新；当前窗口关开 dce 后在新会话再枚举。更新后 Agent 枚举及业务调用仍 not_verified；新子进程、SDK 和宿主缓存证据分开。见 harness/reports/mcp-contract-summary.json。

## 约定

- 以 `.env.example` 为示例，真实配置 `.env` gitignored。
- AI Provider 默认关闭；无 API Key 时规则发现和人工审核仍可用。
- 真正的自动构建/部署在 V1.2/V2.0 单独规划，不因为长任务执行就提前实现。
- 即使对话因环境/额度中断，后续只需将 `prompts/RESUME.md` 发给 Agent。

### Agent-led T0（2026-11-04）

审计完成：harness/refactor-audit.md；先核对六工具、三 Adapter、Mapping/AI/Catalog，定义新契约/失败/测试。基线 .venv/bin/pytest -q：144 passed（7.52s），exit 0。下一步 T1 默认调用路径解耦；真实新版能力 not_verified。

### Agent-led T1（2026-11-04）

默认初始化/发现和 Bug fixture fallback 的语义推理已移出；确定性 Module→CI 保留，旧 mapping CLI 与 init --legacy-mapping 可用。首次回归 3 failed/142 passed，诊断为技术事实被混放在 Mapping 与旧 ai_status 兼容字段；拆分修复后 pytest 145 passed（7.54s），ruff/mypy exit 0。下一步 T2 范围事实查询。

### Agent-led T2（2026-11-04）

新增三个独立事实工具（共九工具），涵盖三平台已有读取、服务详情、分页/ref/path/日志窗口/证据与原生 ImageContent；只读 scope 和输出预算可测，旧六契约保留。针对性 Adapter/HTTP/MCP 54 passed（3.11s），ruff/mypy exit 0；随后图片总预算修正的 facts/contract 回归另记。modules 仅提供 Bug 页实测字段的部分目录，真实图片/模块完整路由与新版上游调用 not_verified；等待目标业务 workspace/连接范围，不读取秘密文件。

### Agent-led T2-budget（2026-11-04）

补充图片协议总字节预算后 facts/MCP 契约 8 passed（1.84s），exit 0；ImageContent 与结构化内容共同受预算限制。T2 实现完成，模块完整目录/真实上游/真实 Host 验收仍 not_verified，不计 P0 全部完成。

### Agent-led T3（2026-11-04）

已实现 schema_version=1、模板/JSON Schema、指定 workspace 只读校验和纯 refresh：六状态、evidence/人工审批、instance/scope、多对多、拒绝保留、变化 stale/conflicted、秘密/重复 YAML/路径隔离。project/model 与 boundary 14 passed（0.65s），ruff/strict mypy exit 0。DCE 无业务文件写接口，真实工作区初始化待目标输入。

### Agent-led T4（2026-11-04）

已提供 initialize/refresh/review/bug-context/service-trace/pipeline-diagnose 六提示词、MCP 实际参数清单、Host 协议，更新 SDK 检查兼容九工具。事实工具条件必填参数同步发布 JSON Schema；工作流/facts/MCP 契约 10 passed（1.99s），ruff passed，strict mypy 修正动态 JSON Schema 类型后 passed（45 files）。真实 Host 调用尚无证据，not_verified。

### Agent-led T5（2026-11-04）

SQLite 0003 增加 cache/history 角色，所有旧表/边/审批/历史保留；旧库升级前 online backup+quick_check，失败阻止迁移；新增 catalog backup/status，迁移与回滚指南。首次 19 failed 根因是旧 0001 动态建表提前创建角色表，固定历史表集合后 Catalog/CLI 19 passed（1.60s），ruff/mypy exit 0。合成旧库证实备份版本、0600、行数、审批/历史及二次打开幂等；未改动真实旧库。

### Agent-led T6（2026-11-04）

完整离线回归 pytest 185 passed/0 failed/0 skipped（15.65s）；总体覆盖率 98.21%、行 98.77%、分支 96.44%；ruff/strict mypy（47 files）/diff/index secret scan passed。标准 stdio→真实 HTTPTransport→本机合成三平台 E2E、原生 ImageContent、双 workspace、审批/拒绝、多对多、迁移和安全边界通过；local wheel 离线打包与隔离导入/Schema/迁移通过。默认沙箱 socket bind/uv cache 受限，经执行器允许后验证，非公司平台操作。真实 doctor exit 2，三平台 AUTH_FAILED/configuration_missing，0 平台请求；当前 Host 未挂 DCE、目标业务 workspace 未提供。T6 外部 P0 not_verified，整体未验收完成；不以旧报告或合成 SDK 替代。新增安全只读 SDK smoke 入口供连接就绪后复验，绝不声称真实 Host 已通过。

### Agent-led T6-followup（2026-11-04）

最终代码审查补强：上游忽略 page limit 时强制单页宽度与显式遗漏；JSON 格式 Compose 同样只返回事实；畸形 Swarm Cluster/Service labels 安全失败。针对性 58 passed（1.41s）；最终全库 187 passed/0 failures/errors/skipped（15.70s），总体覆盖率 98.15%、详见机器摘要；ruff/strict mypy passed。重建最终 wheel 并隔离安装，Schema/0003 角色/九工具枚举通过。外部缺口未变，不宣告整体完成。

### Agent-led T7（2026-11-04）

README/GOALS/PLANS、九工具清单、迁移回滚、安全/运维、Host 六工作流和续跑、ADR 与验收矩阵已同步，旧 V1 文档明确历史范围。当前测试 187 passed、覆盖率 98.15%；文档契约/项目校验 16 passed（0.50s），ruff/strict mypy/diff/新文档相对链接检查通过。真实新版三平台/图片/Host/指定业务 workspace 与完整模块目录仍 pending/not_verified；无真实平台写、构建、部署或业务文件写入。T7 文档交付就绪，整体未验收完成；接续条件和证据见 harness/agent-led-acceptance.md 与 prompts/agent-led/resume.md。

### Agent-led T2-modules-verified（2026-11-04）

Goal 接续第二轮完成实际推进：核对官方 apiv1.php、modulesEntry GET 和 getProductStructure/getDataStructure，新增 Product scope 的 module_tree，完整树搜索后本地分页、字段白名单、节点/深度/2MB 限额；禁止以 Project/Execution ID 替代 Product ID，旧 modules 部分清单兼容。先行测试 2 failed/1 passed 证实缺口；实现后 QueryParams 与 dict 的测试断言类型差异导致 1 failed，修正断言后针对性 69 passed（2.71s），stdio/本机合成 HTTP 1 passed（1.39s）。最终全库 191 passed/0 failed/errors/skipped（15.94s），总体覆盖率 98.18%；ZenTao Adapter 与事实输入契约 100%。ruff/strict mypy/最终 wheel 隔离安装/九工具与迁移检查通过。官方主分支源码不代表当前公司版本；真实平台/图片/Host/指定业务 workspace 仍 not_verified，缺配置与工作区的阻塞重复第 2 个 goal turn，未达 blocked 审计门槛且本轮有实际进展，goal 保持 active。

### Agent-led resumed-local-intake（2026-11-04）

用户明确业务工作区、凭证源与禅道 v1 登录方式，并更换真实缺陷样本。Host 只读核对 20 Git roots、18 根模块清单、17 CI/Dockerfile，私有首层模块关系提议 18 条、confirmed 0，Schema 校验通过；未写业务目录。显式 dotenv/v1 MCP 启动入口已实现，默认不加载 dotenv；文件模式、无插值/执行、别名/重复/冲突、单次登录/无重试/不附旧 Token/父环境隔离/stdio 安全检查通过。先行 5 failed 证实缺口；测试启动 Python resolve 丢失 venv 修复后基础/安全 20 passed，stdio 合成 E2E 2 passed。最终 pytest 199 passed/0 failures/errors/skips（17.71s），总体覆盖率 98.09%，ruff/strict mypy（48 files）与最终 wheel 隔离检查通过。真实凭证只检查变量名并将模式收紧到 0600，正文/值未进入对话或日志，未执行真实登录。三平台地址和实际 Host 仍待用户回复；原 blocked 审计仅历史，不立即沿用旧计数再次标记阻塞。


### Agent-led resumed-http-cursor（2026-11-04）

用户补齐 HTTP 地址并选择 Cursor；新增 URL 别名/显式进程覆盖回归后 pytest 201 passed/0 failed/errors/skipped（18.38s），覆盖率 98.09%（行 98.64%、分支 96.39%），ruff/strict mypy（48 files）与最终 wheel 隔离导入/Schema/0003 角色通过。安装验证首次把 /tmp 与 /private/tmp 路径当作不同，规范化比较后通过。真实 v1 认证 201、Bug 200；标准 SDK 九工具、27 次三平台成功只读 calls（ZenTao 4/GitLab 4/Portainer 19）及一次模块树 403，输出 Schema 均校验。指定 Bug 无附件/内联图片，module 未分配；三 Stack File 63/71/78，实际 Service label 的运行 namespace 八页 78 个唯一 ID，不合并来源或自动确认。真实 Catalog 副本先备份迁移并保留 191/219/219/11，原库不改；全局 Cursor dce 已备份更新且其他四服务保留。23 条私有关系草案（22 proposed/1 unresolved/0 confirmed）和具体 diff ready，Schema/纯 refresh passed，未写业务目录。旧独立 GitLab 固定编号补验被自动审批在执行前拒绝（本轮读取范围未明确授权），移除后只按已配置范围执行；旧样本/其 GitLab Compose 保持 not_verified。真实 Cursor Agent 对话/初始化审核、业务文件落地、含图样本、模块只读权限和旧样本范围仍待补。详见 harness/context/agent-led/resumed-http-cursor.md；无业务写/构建/部署/push/merge。


## 2026-11-04 cursor-text-compatibility

用户回传 Cursor 九个 DCE 工具（另有宿主 mcp_auth）、三次实际成功调用与初始化对话；旧文本仅 DCE result.、结构化信封不可见，原三次 truncated 保持 not_observable。先行 5 failed 复现文本缺陷，九工具改为相同 JSON 文本/structuredContent；预算计量双副本/转义。全形状契约改显式 64KB并保留最小预算检查后 39 passed；新增默认关闭的独立图片总预算（最大 3MB，文本预算/Reader 2MB/来源 scope 不变）后针对性 40 passed。最终全库 208 passed/0 failed/errors/skipped（18.14s），覆盖率 97.93%（行 98.45%、分支 96.31%），ruff/strict mypy（48 files）/最终 wheel 隔离检查通过。真实授权新图片经 stdio 返回原生 PNG，原图 382396 字节、ToolResult 512314 字节、truncated=false、文本与结构化相同，无图片落盘；Cursor 模型接收仍待复验。已备份更新 Cursor 的授权图片样本与显式预算，其他四服务不变。模块接口同 Token Bug 200、模块 403 Access not allowed；官方 v1 modules→tree/browse→checkPriv 源码与该错误相符，推断需核对单独读入口/产品范围，实际实例版本未确认，不索取新 Token或绕过权限。完整683行/23关系草案的保存批准已提出，聊天省略片段不写业务目录，confirmed仍0。旧独立GitLab范围未获本轮明确授权，不重试。详见 harness/context/agent-led/cursor-text-compatibility.md。


### Agent-led cursor-recheck-and-approved-save（2026-11-04）

用户回传 Cursor 修复后两次实际调用：JSON 文本信封可见，Bug 信封/data.truncated 均 false、data.evidence 1（兼容顶层为空）；原生 PNG 实际进入模型，delivered/truncated=false，未保存或转录。用户明确批准完整文件保存并要求不要提交。Host 将与批准 diff 逐字匹配的 683 行/22451 字节草案只创建为业务 .dce/project.yaml，拒绝覆盖/symlink；23 关系保持 22 proposed/1 unresolved/0 confirmed，审批字段全空。真实 CLI validate exit 0、load_project 复读/字节一致/roots 在 workspace 内通过，业务 Git HEAD/index 前后不变，文件 untracked。本轮无 git add/commit/push、真实平台调用或产品代码修改；208 passed/97.93% 保留既有基线，不重复全库测试。更新记录与文档仅本地未提交。核心初始化闭环；完整模块树403、旧独立GitLab范围/Compose仍未验证，严格全样本验收不虚报完成。详见 harness/context/agent-led/cursor-recheck-and-approved-save.md。


2026-11-11 补充诊断：增加旧Catalog checker独立阶段后发现其把合法有界截断一律判失败。合成大Catalog中project_context/discovery_status完整返回，service_trace/deployment_inspect按16KB预算省略data，正确携带omissions/next_action。修复checker为验证Schema、status、字节预算及截断披露，并分别报告complete_reads=2、truncated_reads=2；错误与越权负例仍必须拒绝，未提高预算或屏蔽错误。单独全新合成Catalog实跑已通过。工作树文档JSON用实际Pydantic输入校验，4个调用示例通过；迁移参数修正为--target-version。
