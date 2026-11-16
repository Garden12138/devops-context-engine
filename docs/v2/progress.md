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

## 待确认

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
