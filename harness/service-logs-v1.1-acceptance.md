# V1.1 Scoped Service Logs 验收

2026-11-09后续验收：**Gate A PASS / Gate B PASS / 临时授权REVOKED**。限定单服务真实日志GET1次、返回6条脱敏事件、truncated明确，未发现越权或敏感泄露。最终426项回归通过，详见[工程收尾摘要](v1.1-final-acceptance.md)。下文保留2026-11-05实施及当时未验证记录，不将后续通过追写到早期执行中。

2026-11-05；范围：现有 DCE Agent-led 只读层。离线 passed，真实日志 not_verified。没有访问业务仓库、.env/私钥/Token 文件、私有日志或真实 Portainer，没有制造审核事件；未 push/merge/部署。

## 修改文件（仅本轮增量）

- 包版本：`pyproject.toml`、`uv.lock`、`src/dce/__init__.py`。
- 契约/边界：`src/dce/common/service_logs.py`、`src/dce/common/errors.py`、`src/dce/mcp/facts_contract.py`、`src/dce/mcp/contracts.py`、`schemas/portainer-query.schema.json`。
- 读取/解析：`src/dce/connectors/portainer.py`、`src/dce/connectors/docker_logs.py`、`src/dce/connectors/http.py`（仅保存 injected transport 供有界异步流复用）。
- 应用/入口：`src/dce/app/facts.py`、`src/dce/mcp/server.py`、`src/dce/cli/__init__.py`。
- 安全投影：`src/dce/security/log_summary.py`；没有新增模型/AI 依赖。
- 测试：`tests/test_service_logs.py`、`tests/test_service_logs_stdio.py`。
- 文档/执行记录：`docs/SCOPED_SERVICE_LOGS.md`、`docs/MCP_FACT_TOOLS.md`、`docs/CURSOR_MCP_SETUP.md`、`docs/DECISIONS_AND_RISKS.md`、`README.md`、`PLANS.md`、`harness/build-log.md`、本报告及 `harness/reports/service-logs-v1.1-summary.json`。

原有工作区包含上一轮验收后的未提交 DCE 改动；这些是 V1.0 基线，不冒充 V1.1 新工作。Project Schema V2、业务项目和既有 `.dce/project.yaml` 不改动。

## 验收结果

| 项目 | 真实执行结果 |
|---|---|
| 新单元/契约/安全 | `pytest tests/test_service_logs.py -q`：96 passed |
| 完整回归 | `pytest -q --tb=short --cov=src/dce --cov-report=term-missing`：323 passed，27.50s；97.63% |
| 原九工具 | 原契约回归、既有 stdio/HTTP 全通过；新增 service_logs 真 stdio/合成 HTTP 测试通过，仍九工具 |
| 类型/静态 | `ruff check .` passed；`mypy src` 52 source files passed |
| 安装/构建 | `uv sync --locked --offline --dev`、`uv build --offline` passed；wheel 1.1.0 隔离导入、版本、日志 Schema passed |
| CLI | 独立临时 Catalog 的 `doctor --mock` passed，三平台 mock；日志 CLI 授权检查通过 |
| 真实日志 | not_verified；无明确日志读取权限证据，未尝试连接，不伪报 403 或真实日志成功 |

测试均为合成身份/日志/凭证；stdio HTTP 只监听本机随机 loopback 端口。初次受限全量运行有 3 个 loopback bind 权限错误；获执行器许可后重跑通过。首轮错误契约不允许 data 附查询上下文的问题已修复为 service_logs 专属扩展，其他操作仍 data=null。首次测试复用历史 calls 的问题已修正。uv 最初受限缓存读取失败，获许可后离线锁包与构建成功；没有把这些失败隐藏或标成成功。

## 已覆盖场景

正常读取、多 Task/stdout/stderr、纳秒/时区/半开窗口、跨 HTTP 与 Docker frame 的 UTF-8、TTY combined、分帧畸形/巨大长度/截断、空/字面关键词无命中/过期未知/明确过期/有限 tail 可能缺失；行/原始字节/双份输出限制；独立授权、Endpoint/Stack/Swarm/namespace/实际 Service ID/版本/并发变化；401/403/404/429/驱动不支持/过滤不支持/普通服务端失败；敏感文本、凭证/个人信息/URL/Header/请求体/恶意指令不进入 Agent；超时/慢流/中断/外部取消/Systemerr/压缩拒绝；运行时 Schema 与导出文件一致、旧九工具回归。

## 剩余限制及权限

1. 需要管理员确认目标测试 Environment、Stack 和 Docker service logs GET 权限，再显式加入 endpoint:stack 日志 grant。现有服务元数据读取成功不代表日志权限。只进行已授权小窗口有限验证，不制造业务事件。
2. Docker service logs 没有 until/关键词过滤；先 since + finite tail，再有限客户端筛选。历史窗口可能被较新 tail 挤出；truncated 或 retention not_verified 不能作为业务事件不存在的证据。
3. 只支持可核对 Task context 的 API >=1.30 与 json-file/journald；TTY 不可恢复原 stdout/stderr，返回 combined。其他 driver、过滤参数拒绝、分帧/上下文不兼容均失败闭合，不改用 SSH/Socket/容器日志绕过。
4. 原文默认全部省略，仅固定事件信号/异常/HTTP 状态/时间/Task 与进程内 HMAC 关联标识。摘要不足时需另行授权人工本地审查；不引入自动根因分析。
5. timeout_seconds 是日志 HTTP 总截止时间；元数据检查沿用既有 Reader 的逐请求 timeout 和有限重试。max_bytes 控制应用接收的原始 payload，HTTP/内核固定预取缓冲不属于精确网络包限流。

实际参数、Schema 链接和可复制 Cursor 示例：[使用契约](../docs/SCOPED_SERVICE_LOGS.md)。真实业务身份只在用户当前会话使用，公共例子保持合成。
