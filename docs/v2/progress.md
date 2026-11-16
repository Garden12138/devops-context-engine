# DCE 2.0 实施进度

| 日期 | 任务 | 提交短 SHA | 测试数 / 覆盖率 | 现场验收 | 偏差或备注 |
|---|---|---|---|---|---|
| 2026-11-16 | T0.1 | 2bc6ca7 | 46 passed / 未测覆盖率 | — | pytest、ruff、mypy、公开数据检查通过；1951 行；仅删除 T0.1 内 217 个路径；保留离线测试夹具 |
| 2026-11-16 | T0.2 | 82a9fa5 | 54 passed / 未测覆盖率 | — | pytest、ruff、mypy、公开数据检查通过；1511 行；按已答复范围清理四个遗留文件；配置错误细分留到 T1.1 |
| 2026-11-16 | T0.3 | 041437c | 75 passed / 80.80% | — | uv lock、uv sync --locked --dev 完成；pytest、ruff、mypy、公开数据检查通过；dce --version 为 2.0.0；1647 行；M0 完成，用户检查删除范围 diff 后再进入 M1 |

| 2026-11-16 | T1.1 | f4ef9ff | 81 passed / 未测覆盖率 | — | pytest、ruff、mypy、公开数据检查通过；1705 行；凭证权限、缺键、URL、HTTP 与内联凭证分别报错 |

## 待确认

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
