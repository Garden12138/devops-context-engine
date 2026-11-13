# V1.1.1 禅道认证稳定性验收（2026-11-06）

## 诊断与实现

修复前：显式本地入口只在启动时登录一次，Reader 持有固定 Token；没有过期后重新登录路径。本地 MCP Bug/instance/resource scope 先于上游读取，scope 拒绝不能归因于 Token。当前 Cursor 的非授权 Bug 拒绝已按真实启动配置核对，精确值仅存 gitignored 私有诊断，不进入公共文档或 fixtures。历史 NETWORK_UNAVAILABLE 没有足够证据认定为 Token 过期，保留未知。

先定义 [契约/错误分类](../docs/ZENTAO_AUTH_RECOVERY.md)，再增加进程内 Token Manager：复用既有凭证加载，首次授权 GET 懒登录；缓存、single-flight、generation 保护、明确认证失效后的原 GET 一次重放。登录失败/刷新后仍失效会熔断到重启；无固定 TTL、无磁盘 Token、无 scope 扩大。Reader 对禅道整体省略传输诊断并清除 Cookie，业务结果以本次使用的旧/新 Token 及账号密码脱敏。错误正文16KiB上限，超限按HTTP状态处理而不猜测过期。

新增模块 `connectors/zentao_auth.py`；修改 Reader、Settings 私有运行属性、显式 local_settings、事实输出与旧 bug_context/pipeline 的脱敏接线。包/MCP server version 为1.1.1；九工具名称、输入/输出 Schema、错误枚举、Project Schema V2 与 Portainer 契约2.2保持。

本轮23个文件：

| 分组 | 文件 |
|---|---|
| 认证/传输 | src/dce/connectors/zentao_auth.py（新增）、src/dce/connectors/http.py、src/dce/security/local_credentials.py |
| 状态/脱敏接线 | src/dce/common/config.py、src/dce/security/redact.py、src/dce/app/facts.py、src/dce/app/services.py |
| 版本 | pyproject.toml、uv.lock、src/dce/__init__.py、src/dce/mcp/server.py |
| 测试 | tests/test_zentao_auth.py（新增）、tests/test_local_credentials.py、tests/test_agent_e2e.py |
| 契约/使用/安全 | docs/ZENTAO_AUTH_RECOVERY.md（新增）、docs/AGENT_LED_LOCAL_CREDENTIALS.md、docs/CURSOR_MCP_SETUP.md、docs/SECURITY.md、docs/DECISIONS_AND_RISKS.md |
| 计划/验收 | README.md、PLANS.md、harness/build-log.md、harness/zentao-auth-v1.1.1-acceptance.md（新增） |

## 自动化证据

- `.venv/bin/pytest -q --tb=short --cov=src/dce --cov-report=term-missing`：**357 passed / 27.20s / 97.62%**，无失败、错误或跳过；原V1.1基线323项保持，净增34项。
- 专项：新增33个合成认证用例；原 stdio 认证 E2E 参数化，新增1个过期恢复场景。专项先行37 passed，再补并发失败/两代秘密/原生图片/有界错误等；中间44 passed，最终全量357通过。
- 覆盖首次登录、缓存复用、401/403精确分类、参数不变的一次重放、二次失效停止、密码错误/锁定/网络登录失败、并发首次登录与并发刷新一次、旧generation失败、scope零网络、跨源/跨连接拒绝、直接Token模式、有界错误正文、Token/密码/Cookie不泄漏、九工具 Schema、图片及 service_logs 回归。
- `ruff check .` 与 strict `mypy src/dce`（53文件）通过。
- `uv sync --locked --offline --dev`、`uv build --offline`通过，wheel/sdist为1.1.1；隔离wheel验证与提交前检查另记 build-log。
- HTTP测试全部使用Mock或本机loopback合成平台；无模型调用、CI、业务构建或部署。

## 真实只读证据

使用当前Cursor显式配置与既有凭证加载器，精确选择一个已授权且此前成功的Bug。独立临时Catalog，不打开或备份真实Catalog；HTTP guard只允许该Bug GET和v1认证POST，禁其他路径/查询，网络重试设0、单请求超时最多10秒。只保留时间、状态、计数及布尔检查，不保存响应正文、图片、URL、账号、Token或Cookie。

| 检查 | 真实观察 |
|---|---|
| 未授权Bug的本地拒绝 | PERMISSION_DENIED；零网络、零登录；未向上游查询 |
| 同一已授权Bug的无Token有界GET | 401；命中严格JSON认证失效规则 |
| 首次授权调用登录 | POST 201 |
| 连续读取与缓存复用 | GET 200两次；仅一次登录 |
| 独立新进程 | 新POST 201、GET 200一次 |
| 输出敏感值检查 | 账号、密码、当前Token均未出现在MCP返回中 |

真实总计：认证POST两次、成功GET三次、无凭证认证探针GET一次。所有调用都在原精确授权范围内。没有使真实Token失效、撤销会话、修改权限或触发业务事件。实际Token过期后的恢复、真实并发、实例未出现的403失效变体仍 **not_verified**，由合成测试验证其逻辑。实际Cursor窗口未重载，不把SDK handler/独立进程验证称作Cursor Agent实测。

## 剩余限制与使用

默认入口仍不隐式读dotenv；直接Token模式没有账号密码可刷新。没有可信到期元数据就不主动定时续期；多进程独立登录。登录网络故障也锁存，需检查后重启，避免密码不确定性下重复提交。未知认证响应保守失败，不扩展为猜测登录。

Cursor保持原配置和scope，重启dce子进程后即可启用；版本应为1.1.1，新会话枚举九工具再查询既有授权Bug。新增Bug需人工单独审批精确allowlist，Project/Product授权不替代精确Bug入口。无业务项目修改、权限修改、GitHub推送或真实日志查询。
