# DCE 2.0 实施进度

| 日期 | 任务 | 提交短 SHA | 测试数 / 覆盖率 | 现场验收 | 偏差或备注 |
|---|---|---|---|---|---|
| 2026-11-16 | T0.1 | 2bc6ca7 | 46 passed / 未测覆盖率 | — | pytest、ruff、mypy、公开数据检查通过；1951 行；仅删除 T0.1 内 217 个路径；保留离线测试夹具 |
| 2026-11-16 | T0.2 | 82a9fa5 | 54 passed / 未测覆盖率 | — | pytest、ruff、mypy、公开数据检查通过；1511 行；按已答复范围清理四个遗留文件；配置错误细分留到 T1.1 |
| 2026-11-16 | T0.3 | 041437c | 75 passed / 80.80% | — | uv lock、uv sync --locked --dev 完成；pytest、ruff、mypy、公开数据检查通过；dce --version 为 2.0.0；1647 行；M0 完成，用户检查删除范围 diff 后再进入 M1 |
| 2026-11-16 | T1.1 | f4ef9ff | 81 passed / 未测覆盖率 | — | pytest、ruff、mypy、公开数据检查通过；1705 行；凭证权限、缺键、URL、HTTP 与内联凭证分别报错 |
| 2026-11-16 | T1.2 | c21d480 | 100 passed / 未测覆盖率 | — | pytest、ruff、mypy、公开数据检查通过；1903 行；配置路径校验及显式工作区绑定完成 |
| 2026-11-16 | T1.3 | b17da34 | 113 passed / 未测覆盖率 | — | pytest、ruff、mypy、公开数据检查通过；2142 行；新写 CI 静态解析，覆盖三种形态与未知表达式 |
| 2026-11-16 | T1.4 | 8e5600b | 118 passed / 未测覆盖率 | — | pytest、ruff、mypy、公开数据检查通过；2201 行；Maven parent group、依赖闭包及不安全 XML 跳过完成 |
| 2026-11-16 | T1.5 | f8ea350 | 123 passed / 未测覆盖率 | — | pytest、ruff、mypy、公开数据检查通过；2233 行；只读接口和编码测试完成；两处格式问题修正后复跑并并入本地提交 |
| 2026-11-16 | T1.6 | f940505 | 126 passed / 未测覆盖率 | — | pytest、ruff、mypy、公开数据检查通过；2548 行；带来源与 TODO 注释的配置、同 namespace 精确服务匹配、proposed 差异完成 |
| 2026-11-16 | T1.7 | 37e71e2 | 160 passed / 88.85% | — | pytest、ruff、mypy、公开数据检查通过；2809 行；逐项 pass/fail、两项固定 warn 及 scope 404 warn 完成；例外按已答复第 4 条执行 |
| 2026-11-16 | T1.8 | 381b706 | 168 passed / 89.03% | R1 PASS（2026-11-17） | pytest、ruff、mypy、公开数据检查通过；3135 行；workspace 94.79%、loop 95.74%、platforms 81.37%；stdio 列出 12 工具并调用 dce_status；text/structuredContent 一致；run 仅本地只读；M1 离线及现场验收完成，未开始 M2 |
| 2026-11-17 | R1.1 自检诊断截断修复 | 82f9b4f | 172 passed / 88.96% | PASS（2026-11-17） | pytest、ruff、mypy、公开数据检查通过；当前工作树 3173 行；根据现场验收调整：优先返回 fail/warn、截断 pass，scope 查询 404 沿用既有兼容 warn；用户回归 337 pass / 3 warn / 0 fail，三条警告正文完整；保留既有 CI 解析器未提交改动 |
| 2026-11-17 | R1.2 CI 脚本解析修复归档 | 77ff7b3 | 172 passed / 88.96% | R1 已通过 | pytest、ruff、mypy、公开数据检查通过；3173 行；根据现场验收调整：保留脚本引号内及转义分号，回归夹具统一为 demo-*；归档此前保留的 CI 改动；按用户本次明确要求提交并普通推送当前功能分支 |
| 2026-11-17 | T2.1 | 3045bad | 180 passed / 89.40% | — | pytest、ruff、mypy、公开数据检查通过；3297 行；先校验产品再解析正文和图片，默认 6 张；actions 缺失返回 HISTORY_UNAVAILABLE |
| 2026-11-17 | T2.2 | 6d9a373 | 190 passed / 89.79% | — | pytest、ruff、mypy、公开数据检查通过；3397 行；原子替换、flock、events 追加及并发更新完成 |
| 2026-11-17 | T2.3 | da1a29e | 195 passed / 90.04% | — | pytest、ruff、mypy、公开数据检查通过；3477 行；git 列表参数、shell=False、禁提示、60 秒超时；本地 bare 夹具覆盖全部读函数 |
| 2026-11-17 | T2.4 | fe1d0fe | 213 passed / 90.47% | — | pytest、ruff、mypy、公开数据检查通过；3667 行；9 步部署计划、模块/依赖排序、六类约定警告与 9 列顺序表完成；仅本地 git 夹具 |
| 2026-11-17 | T2.5 | 8e14072 | 216 passed / 90.65% | R2 PASS（2026-11-18） | pytest、ruff、mypy、公开数据检查通过；3744 行；workspace 94.40%、loop 98.16%、platforms 81.43%；MCP 原生图片、CLI 图片保存、stdio 本地 bare 计划创建/刷新完成；补充审计输出脱敏回归 |
| 2026-11-18 | T3.1 | c13046c | 236 passed / 90.69% | — | pytest、ruff、mypy、公开数据检查通过；3776 行；七条方法/平台/路径白名单、请求前拒绝、写请求零重试；无范围偏差 |
| 2026-11-18 | T3.2 | 5fe1e58 | 256 passed / 90.77% | — | pytest、ruff、mypy、公开数据检查通过；3846 行；五类目标守卫逐项正反例、内置保护分支持续生效；无范围偏差 |
| 2026-11-18 | T3.3 | 9fd664a | 267 passed / 91.00% | — | pytest、ruff、mypy、公开数据检查通过；3986 行；detached 临时 worktree 合并/冲突清理、普通推送竞争重试一次、HEAD/分支/文件保持、逐次写审计完成；无范围偏差 |
| 2026-11-18 | T3.4 | c71ad0b | 308 passed / 91.30% | — | pytest、ruff、mypy、公开数据检查通过；4302 行；计划内 direct/child job 动作、补建最多一次、只读假时钟轮询、旧构建与 digest/失败分类完成；无范围偏差 |
| 2026-11-18 | T3.5 | 8d78f75 | 310 passed / 91.37% | R3 PASS（2026-11-18） | pytest、ruff、mypy、公开数据检查通过；4358 行；MCP/CLI 接入、stdio 本地合并、批量独立报告、CLI 分段等待完成；无范围偏差，M3 离线与现场验收完成，未开始 M4 |
| 2026-11-18 | T4.1 | a1e3914 | 327 passed / 91.52% | — | pytest、ruff、mypy、公开数据检查通过；4426 行；Portainer 更新/兼容状态、registry 认证、任务过滤、分帧与 TTY 日志脱敏完成；无范围偏差 |
| 2026-11-18 | T4.2 | e3bfa4b | 381 passed / 92.06% | — | pytest、ruff、mypy、公开数据检查通过；4661 行；构建前置跳过、配置守卫、两条更新路径逐次审计、任务/digest 判定及假时钟只读核验完成；deploy.py 覆盖率 100%；无范围偏差 |
| 2026-11-18 | T4.3 | 19a6286 | 386 passed / 92.06% | R4 PASS（2026-11-19） | pytest、ruff、mypy、公开数据检查通过；4694 行；MCP/CLI 部署和核验接入、二选一参数校验、CLI 分段等待及 stdio 诊断完成；现场最终结果见第 6 条 |
| 2026-11-18 | R4.1 核验判定修复 | d811ed3 | 390 passed / 92.09% | — | ruff、mypy、公开数据检查通过。非测试代码 4723 行。根据现场验收调整：排除部署前的历史任务失败，滚动完成但缺少运行 digest 时返回 digest_unverified。R4 现场按人工镜像证据通过。 |
| 2026-11-19 | T5.1 | 73e352a | 396 passed / 91.60% | — | pytest、ruff、mypy、公开数据检查通过。非测试代码 4841 行。验证截图和记录提交检查、阶段回退、MCP 和 CLI 接入。 |

2026-11-18 M4 离线结果：T4.1–T4.3 按顺序各一个本地任务提交（a1e3914、e3bfa4b、19a6286）。全部 386 tests passed，覆盖率 92.06%（workspace 94.40%、loop 97.14%、platforms 82.92%，deploy.py 100%）；ruff、mypy、公开数据检查通过。非测试代码 4694 行，各源文件不超过 400 行，无范围偏差、无新增待确认。测试仅用 MockTransport、本地 bare git 和假时钟；未访问真实平台或业务工作区，未 push。R4 现场验收待用户执行，未开始 M5。本提交仅归档最终任务 SHA 与离线结果。

2026-11-18 M3 离线结果：T3.1–T3.5 按顺序各一个本地提交（c13046c、5fe1e58、9fd664a、c71ad0b、8d78f75）。全部 310 tests passed，覆盖率 91.37%（workspace 94.40%、loop 96.53%、platforms 82.02%）；ruff、mypy、公开数据检查通过。非测试代码 4358 行，各源文件不超过 400 行，无范围偏差、无新增待确认。测试仅用 MockTransport、本地 bare git 和假时钟；当前分支只作本地提交。R3 现场验收待用户执行，未开始 M4。本提交仅归档最终任务 SHA 与离线结果。

2026-11-17 M2 离线结果：T2.1–T2.5 各一个本地提交，全部 216 tests passed，覆盖率 90.65%；ruff、mypy、公开数据检查通过，stdio 仅用本地 bare git 夹具调用 deploy_plan。非测试代码 3744 行，未超预算。无新增待确认；R2 现场验收待用户执行，未开始 M3。各任务 SHA 在后续提交归档，本行和 T2.5 结果另作进度归档提交。

2026-11-17 发布授权：用户明确要求“提交推送”，本次允许将 `feature/v2-bugfix-loop` 普通推送到 origin 同名分支。该要求覆盖本次操作的“只本地提交”限制；仍不 force push、不推标签、不建 MR、不修改其他本地分支，不开始 M2。

2026-11-17 R1 最终结果：PASS。用户已完成操作清单第 1–7 步，第 7 步负向自检 PASS：基线为 337 pass / 3 warn / 0 fail（12.3 秒），错误 job 为 336 pass / 3 warn / 1 fail（22.7 秒），恢复后回到基线（20.9 秒），三次合计约 56 秒，配置已原样恢复。用户确认正常操作可在 15 分钟内。3 项 warn 为 scope 查询接口 HTTP 404 的兼容性提示和两项首次写权限提示，均符合既有 T1.7 规则。显示修复后，用户再次回归为 337 pass / 3 warn / 0 fail，并提供三条警告完整正文。M1 离线与现场验收完成，未开始 M2。真实细节仅记在 `.local/v2/acceptance-notes.md`。

2026-11-17 R1 显示修复复查：当前工作树 172 tests passed、覆盖率 88.96%（workspace 94.40%、loop 95.74%、platforms 81.37%），ruff、mypy 通过；3173 行，含既有 CI 解析器及测试的未提交改动，本次保留这些改动。

2026-11-18 R2 最终结果：PASS（依据用户在 Cursor 会话中提供的第 1–5 步结果，耗时未记录）。缺陷列表返回 1 条且未截断；Agent 正确描述截图；其他产品缺陷按产品范围拒绝且无正文；独立验收副本中的历史修复计划与手写顺序表一致；同一 run 的未提交临时文件使 DIRTY 出现，删除后该警告消失。历史提交缺少 bug#ID，BUGS_WITHOUT_COMMITS 及表格缺陷列为空均符合契约。本次历史修复为单服务场景，公共库下游建议由既有离线测试覆盖。M2 离线与现场验收完成，无新增待确认，停在 M2；真实环境细节仅记在 `.local/v2/acceptance-notes.md`。

2026-11-18 R2 归档复核：216 tests passed / 90.65%；ruff、mypy、公开数据检查通过；非测试代码 3744 行，无实现改动。

2026-11-18 R3 首次核对：FAIL（用户报告，待补核验收证据）。G2 材料、普通推送与测试分支合并、用户工作副本的分支/HEAD/文件保持一致、compile 与自动 build 成功及 digest 持久化均已核对。待补核 Cursor 工具调用确认弹窗是否实际出现，以及 GitLab 流水线中计划外 job 的线上情况。冲突演练为可选，本次未做。ci_status 按现有契约返回计划内 job；流水线由分支及 merge_sha 定位。此次先记录 R3 FAIL，停在 M3，待现场补核后更新；真实细节仅记入 .local/v2/acceptance-notes.md。本次仅归档反馈，实现未变；复核 310 tests passed / 91.37%，ruff、mypy、公开数据检查通过，非测试代码 4358 行。

2026-11-18 R3 最终结果：PASS。用户确认亲自看到宿主工具调用弹窗并点击 Run；用户提供的 GitLab 完整 Jobs 页面显示测试分支的流水线对应本次合并提交，仅有计划内的 compile 和自动 build 两个 job，均已通过，其他分支专属 job 未生成。结合此前已核对的 G2 材料、普通推送及合并、用户工作副本分支/HEAD/文件保持一致、构建成功及 digest 持久化，R3 必选项全部通过；可选冲突演练未做，全程验收耗时未单独记录。真实名称、提交与流水线编号等现场细节仅记在 .local/v2/acceptance-notes.md；截图未复制进仓库。M3 离线与现场验收完成，无新增待确认，停在 M3，未开始 M4。本次仅归档验收结果，实现未变；复核 310 tests passed / 91.37%，ruff、mypy、公开数据检查通过，非测试代码 4358 行。

2026-11-18 R4 首次核对：FAIL（用户现场反馈，耗时未记录）。构建成功并取得 digest。Portainer 首选更新 HTTP 404，Docker 回退 HTTP 200，部署请求通过。滚动状态为 `completed`、副本为 1/1，但 DCE 返回两条任务退出错误且 `running_digest=null`，收敛核验失败。日志及脱敏通过。现有 run 已构建成功，构建未完成的负向验证和 Portainer 页面核对待做。现场细节记录在 `.local/v2/acceptance-notes.md`，停在 M4。本次归档复核 386 tests passed / 92.06%，ruff、mypy、公开数据检查通过，非测试代码 4694 行。

## 待确认

### 8. T5.2 禅道解决配置与请求契约（已答复）

2026-11-19：03 第 3.3 节说明 `zentao.resolve.assign_to` 可以填写具体账号，现有配置模型也接受非默认的 `assign_to` 和 `resolved_build`。按本次 M5 指令及 03 第 6.5 节，请求中的 `assignedTo` 取缺陷的 `openedBy`，`resolvedBuild` 固定为 `trunk`。

请确认怎样处理填写了非默认值的既有配置。建议保留两个配置键，在调用 `bug_resolve` 时对非默认值返回具体的配置错误，并在 03 第 3.3 节写明支持的取值和修改方法。

用户答复（2026-11-19，原文）：

第 8 条：不报配置错误，改为按配置取值：assign_to 为 opener 时取实时读到的 openedBy，否则原样作为账号传递；resolved_build 原样传递，默认 trunk；resolution 仍只允许 fixed。bug_resolve 实时读取缺陷，不依赖 run 中的快照。

设计文档见 `9921309`。

### 7. T5.3 写修复记录前的缺陷元数据来源（已答复）

2026-11-19：04 第 2 节要求 `dce_status(run_id)` 从本地返回 `title`、`severity`、`pri`、`opened_at` 等字段。07 的 S1 先调用 `bug_get`，S4 才由 `deploy_plan` 创建 run，S10 读 `record_facts` 写记录，S11 才调用 `bug_resolve`。当前 `bug_get` 只返回元数据，`deploy_plan` 只持久化缺陷 ID，且目前可在没有禅道连接和凭证时执行。03 第 6.1 节和 04 第 2、5 节未规定由哪一步把这些字段写入 run。照现有流程运行，S10 取不到提出时间，无法满足 R5 第 3 项。

建议为 `deploy_plan` 明确补齐缺陷元数据的职责，在新建或刷新 run 时，对缺少元数据的缺陷调用禅道只读接口，校验产品后将 03 第 4 节及 04 第 2 节所需字段写入 run。`dce_status` 继续只读本地。请确认这一方案，以及缺少凭证或读取失败时是否仍须允许生成部署计划。

R4 已核对为 PASS，既有待确认项均已答复。按交接规则暂停在 T5.1 开始前。

用户答复（2026-11-19，原文）：

第 7 条：同意由 deploy_plan 在新建或刷新 run 时从禅道补齐缺陷元数据。禅道读取失败时仍生成部署计划，只追加 BUG_METADATA_UNAVAILABLE 警告；产品不符时返回 OUT_OF_SCOPE 且不写 run；dce_status 保持只读本地，缺失字段为 null 并给 BUG_METADATA_MISSING 警告。不要用刷新计划来补元数据。

设计文档见 `9921309`。从 T5.1 继续。

### 6. R4 的失败任务归属与运行镜像 digest（已答复）

03 第 6.4 节未区分 Swarm 保留的历史失败任务与本次更新的任务。当前实现用全部任务判定失败，并从运行任务的 `Spec.ContainerSpec.Image` 提取 digest。请只读核对两条失败任务的创建或状态变更时间、当前状态及期望状态，确认是否属于本次更新。另核对当前运行任务的完整镜像引用；如只带 tag，再查看该任务对应的运行容器镜像所关联的 `RepoDigests`（页面如有显示）。

2026-11-18 补核：两条失败任务均早于本次部署。服务更新时间与本次部署对应，运行副本 1/1。运行任务只显示 tag，容器页面所示的 Image ID 和构建镜像的 manifest digest 是不同字段，镜像详情未提供 `RepoDigests`。已按现场结果明确历史失败过滤与 `digest_unverified` 判定。运行镜像 digest 比对及构建未完成的负向验证仍待做，R4 整体为 FAIL。

2026-11-19 补核：GitLab build 日志确认 DCE 提取的仓库 digest 来自目标镜像 tag 的本次推送。日志中的构建 Image ID 与 Portainer 运行容器的 Image ID 完整一致，运行镜像身份已人工核对。第 3 步的 `service_status` 自动收敛仍待验证，现场尚未取得运行任务的仓库 digest。修复后只读复测和第 1 步构建未完成的负向验证待做，R4 保留 FAIL，停在 M4。本次复核 390 tests passed / 92.09%，ruff、mypy、公开数据检查通过。

2026-11-19 R4 最终结果：PASS（用户确认现场验收以编译、推送、部署和运行同一镜像为准，耗时未记录）。本次部署后新容器运行正常，完整 Image ID 与 CI 构建日志一致。两条失败任务已确认属于本次部署前的历史记录。自动仓库 digest 核验保留工具的实际结果，现场接受人工核对。构建未完成的负向验证改为现场可选，离线仍覆盖跳过、无写请求和 `PRECONDITION_FAILED`。已同步 06 的验收口径。本次复核 390 tests passed / 92.09%，ruff、mypy、公开数据检查通过。停在 M4。

### 5. R1 现场 3 项 warn 与初始化全程耗时（已答复）

2026-11-17：用户报告负向自检第 7 步 PASS，基线与恢复后的 check 均为 passed=true、337 pass / 3 warn / 0 fail。06 的 R1 要求 warn 仅剩两项首次写权限验证提示；第 3 项 warn 的 id/detail 尚未提供。用户报告的 56 秒为第 7 步三次 check 合计，初始化 scan、人工处理 TODO 与 check 的全程耗时尚未提供。

请提供 3 项 warn 的 id/detail，并确认初始化全流程是否在 15 分钟内；据此记录完整 R1 的 PASS/FAIL。当前仅第 7 步标记 PASS，停在 M1。

用户对耗时的答复（2026-11-17，原文）：第二点全流程很快的，只不过我第一次做，很多东西都没找到，正常是可以在15min以内的

执行决定：耗时按用户反馈记录为正常操作可在 15 分钟内；剩余工作仅需取得 warn 的 id/detail，由实现者判断额外警告的原因。

用户对 warn 的答复（2026-11-17，原文）：

这次 `project_setup(action="check")` 的汇总是 **3 warn**。返回被截断，检查列表里只带出 1 条警告正文。另外 2 条在列表末尾，被截掉了；它们的 `id` 和 `detail` 来自同配置下上一次完整自检。

| id | detail |
|---|---|
| `gitlab.token_scope` | GitLab /personal_access_tokens/self HTTP 404: 无法读取 scopes。 |
| `portainer.write` | 写权限需首次部署时验证 |
| `zentao.resolve` | 解决权限需首次使用时验证 |

执行决定：3 项 warn 均符合 05 第 T1.7 节及已答复第 4 条的规则；统一 03/04/06 的兼容性提示说明，`api` scope 继续按共同前置要求核对。本次发现超大自检结果会把末尾 warn/fail 截掉，用合成数据复现后修复为优先返回 fail/warn、截断 pass；修复后需重载 MCP 复查警告显示。原 R1 步骤已由用户执行，当前仅剩本次显示修复的现场回归，未开始 M2。

现场回归答复（2026-11-17）：用户报告 `project_setup(action="check")` 为 337 项通过、0 项失败、3 项警告，并逐项提供 `gitlab.token_scope`、`portainer.write`、`zentao.resolve` 的完整 detail。显示修复回归 PASS，完整 R1 标记 PASS；本条已处理完毕，停在 M1。

### 4. T1.7 两项固定 warn 与逐项 pass/fail 测试要求（已答复）

2026-11-16：T1.1–T1.6 已分别完成本地提交。准备开始 T1.7 时核对到：

- 本次用户要求 doctor“每项都有 pass 和 fail 测试”；05 的 T1.7 也写“每个检查项至少一个 pass 用例和一个 fail 用例”。
- 同一节又明确 `portainer.write`、`zentao.resolve` 为“固定 warn”；04 第 1 节的返回示例分别说明“写权限需首次部署时验证”“解决权限需首次使用时验证”。
- 对这两个固定 warn 检查，无法同时构造符合上述契约的 pass 与 fail 状态；M1 自检也没有验证真实写权限的操作设计。

建议明确例外：这两项始终返回 warn，并各写测试断言固定 warn 及首次使用验证提示；其余所有检查项逐项覆盖 pass/fail，`gitlab.token_scope` 另测接口 404 时的 warn。请确认是否按此执行，并同步统一 05 的 T1.7 测试要求。

按 CODEX_HANDOFF 第 1.3 节暂停在 T1.7 之前；T1.7、T1.8 和 M1 的最终离线验收、R1 操作清单尚未完成，未开始 M2。

用户答复（2026-11-16，原文）：同意

执行决定：按上述建议执行；两项固定 warn 各测试状态和首次使用验证提示，其余检查项逐项覆盖 pass/fail，另测 token_scope 接口 404 的 warn；同步修正 05 与交接提示后继续 T1.7、T1.8。

### 1. M0 清场中未列出的遗留模块（已答复）

2026-11-16：已用 `git ls-files` 列出 T0.1 规定的删除路径并逐项核对，尚未删除文件、创建 tag 或提交。以下遗留文件未列入 T0.1 的删除范围，也未列为独立保留模块：

- `src/dce/common/output.py`
- `src/dce/common/service_logs.py`
- `src/dce/security/log_grant.py`
- `src/dce/security/log_summary.py`

`portainer.py` 仍引用 `common.service_logs.LogControls` 和 `security.log_grant.ServiceLogGrant`；`docker_logs.py` 仍引用 `common.service_logs` 的时间与参数处理，以及 `security.log_summary.summarize`。迁移后的目标目录没有这些旧模块。

建议：T0.2 迁移时，将日志解码仍需要的辅助逻辑并入已点名保留的模块，按用户要求移除 `ServiceLogGrant` 参数，再删除上述四个遗留文件并清理空包目录。请确认这些额外删除路径及处理方式。

用户答复（2026-11-16，原文）：1、允许 2、统一

执行决定：按建议在 T0.2 处理上述四个文件。

### 2. progress.md 表头约定冲突（已答复）

`CODEX_HANDOFF.md` 第 1.2 节要求 `日期 / 任务 / 提交短 SHA / 测试数与覆盖率 / 现场验收 / 偏差或备注`；05 的 T0.1 要求 `日期 / 任务 / 提交 / 离线结果 / 现场验收 / 备注`。

本文件暂按第 1.2 节建立表头。建议统一采用本文件表头，并同步修正 05 的 T0.1。请确认。

用户答复（2026-11-16，原文）：1、允许 2、统一

执行决定：统一采用第 1.2 节的表头，并已同步修正 05 的 T0.1。

### 3. T0.3 锁文件更新与依赖同步联网（已答复）

2026-11-16：已请求允许联网执行 `uv lock` 和 `uv sync --locked --dev`，等待用户答复后执行。T0.3 工程配置、CLI 骨架及测试已准备，尚未提交。

当前复用已有环境离线验证（`UV_NO_SYNC=1`、`UV_OFFLINE=1`）：75 tests passed；覆盖率 80.80%；ruff、mypy 通过；`dce --version` 输出 `2.0.0`；非测试代码 1647 行。锁文件更新后须在同步后的环境中复跑检查。

用户答复（2026-11-16，原文）：允许

执行决定：仅为更新锁文件和同步计划内的依赖联网，然后在新环境中复跑全部检查。

执行结果：`uv lock`、`uv sync --locked --dev` 完成；新环境中 75 tests passed，覆盖率 80.80%，ruff、mypy 通过，版本输出 `2.0.0`；非测试代码 1647 行。T0.3 为 CLI 占位提前引入已在计划中列出的临时 `NOT_IMPLEMENTED`，M5 删除。
