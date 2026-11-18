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

| 2026-11-18 | T3.2 | 本任务提交（下项归档 SHA） | 256 passed / 90.77% | — | pytest、ruff、mypy、公开数据检查通过；3846 行；五类目标守卫逐项正反例、内置保护分支持续生效；无范围偏差 |

2026-11-17 M2 离线结果：T2.1–T2.5 各一个本地提交，全部 216 tests passed，覆盖率 90.65%；ruff、mypy、公开数据检查通过，stdio 仅用本地 bare git 夹具调用 deploy_plan。非测试代码 3744 行，未超预算。无新增待确认；R2 现场验收待用户执行，未开始 M3。各任务 SHA 在后续提交归档，本行和 T2.5 结果另作进度归档提交。

2026-11-17 发布授权：用户明确要求“提交推送”，本次允许将 `feature/v2-bugfix-loop` 普通推送到 origin 同名分支。该要求覆盖本次操作的“只本地提交”限制；仍不 force push、不推标签、不建 MR、不修改其他本地分支，不开始 M2。

2026-11-17 R1 最终结果：PASS。用户已完成操作清单第 1–7 步，第 7 步负向自检 PASS：基线为 337 pass / 3 warn / 0 fail（12.3 秒），错误 job 为 336 pass / 3 warn / 1 fail（22.7 秒），恢复后回到基线（20.9 秒），三次合计约 56 秒，配置已原样恢复。用户确认正常操作可在 15 分钟内。3 项 warn 为 scope 查询接口 HTTP 404 的兼容性提示和两项首次写权限提示，均符合既有 T1.7 规则。显示修复后，用户再次回归为 337 pass / 3 warn / 0 fail，并提供三条警告完整正文。M1 离线与现场验收完成，未开始 M2。真实细节仅记在 `.local/v2/acceptance-notes.md`。

2026-11-17 R1 显示修复复查：当前工作树 172 tests passed、覆盖率 88.96%（workspace 94.40%、loop 95.74%、platforms 81.37%），ruff、mypy 通过；3173 行，含既有 CI 解析器及测试的未提交改动，本次保留这些改动。

2026-11-18 R2 最终结果：PASS（依据用户在 Cursor 会话中提供的第 1–5 步结果，耗时未记录）。缺陷列表返回 1 条且未截断；Agent 正确描述截图；其他产品缺陷按产品范围拒绝且无正文；独立验收副本中的历史修复计划与手写顺序表一致；同一 run 的未提交临时文件使 DIRTY 出现，删除后该警告消失。历史提交缺少 bug#ID，BUGS_WITHOUT_COMMITS 及表格缺陷列为空均符合契约。本次历史修复为单服务场景，公共库下游建议由既有离线测试覆盖。M2 离线与现场验收完成，无新增待确认，停在 M2；真实环境细节仅记在 `.local/v2/acceptance-notes.md`。

2026-11-18 R2 归档复核：216 tests passed / 90.65%；ruff、mypy、公开数据检查通过；非测试代码 3744 行，无实现改动。

## 待确认

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
