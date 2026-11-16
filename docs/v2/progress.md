# DCE 2.0 实施进度

| 日期 | 任务 | 提交短 SHA | 测试数 / 覆盖率 | 现场验收 | 偏差或备注 |
|---|---|---|---|---|---|
| 2026-11-16 | T0.1 | 2bc6ca7 | 46 passed / 未测覆盖率 | — | pytest、ruff、mypy、公开数据检查通过；1951 行；仅删除 T0.1 内 217 个路径；保留离线测试夹具 |

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
