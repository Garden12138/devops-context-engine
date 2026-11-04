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
