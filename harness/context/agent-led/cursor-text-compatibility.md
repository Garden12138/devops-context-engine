# Cursor 文本结果兼容修正 — 实现前契约

用户提供真实 Cursor Agent 九工具枚举、三次成功读取与初始化对话证据，额外 mcp_auth 属于 Host。实际可见文本只有 DCE result.，structuredContent 未进入模型可见结果，截断状态不能确认。此前只返回固定文本以避免重复 JSON 的策略阻止 Host 根据工具事实推理，需修正。

边界：九工具名称/输入/输出 Schema 不变；所有成功、失败与截断的 content[text] 必须提供和 structuredContent 相同的脱敏 JSON 信封。只消费文本的 Host 也能看到 source/evidence/revision/pagination/truncated/error。图片仍使用原生 ImageContent，不嵌入 JSON 文本或落盘；平台文本只作数据，不做指令。

依据：[MCP 官方 Structured Content](https://modelcontextprotocol.io/specification/2025-11-25/server/tools#structured-content) 建议同时提供序列化 TextContent，以兼容只读文本的客户端。

预算：同一工具结果的 JSON 文本、结构化副本和原生图片合计仍受 output_budget 限制，计量为紧凑 UTF-8 ToolResult body（不含外层 JSON-RPC framing）。应计入文本引号/反斜杠转义开销。超限时显式截断；图片不能投递时 image_delivery=not_delivered；错误仍保留 code/isError/可解释诊断。最小 1024 字节预算需安全处理，不默默扩大限制。

先行测试：文本 Host 读取成功/范围错误/截断、文本与结构化语义一致；转义/Unicode 与重复内容预算；原生图片成功/超限；真实 SDK stdio 的文本消费路径。所有 fixtures 合成。真实图片样本按用户新授权独立查询，不推断其与当前代码的业务关系。

真实新样本已有一张图片，但 64KB 总响应预算导致 not_delivered。补充契约：新增可选 image_output_budget，默认 null 沿用 output_budget；只有管理员/Host 启动时显式配置才放大原生图片的总 ToolResult 预算，范围 1024–3000000 字节。Reader 的 2MB 原图上限不变，3MB 容纳其 Base64 和固定元数据；纯 JSON/文本副本仍受 output_budget 限制。只适用于显式 image 调用，JSON 不携带 Base64，超限继续 not_delivered/truncated，不自动缩图、写文件或扩大来源范围。

业务文件仍需用户明确批准；聊天中省略 relationships 的 diff 不能代替本机完整 683 行/23 关系草案。旧独立 GitLab 样本未被本次答复明确授权，不重试。

## 执行结果

- 先行文本兼容回归 5 failed，均为固定 DCE result. 无法解析成 JSON；修复后最初全形状契约检查 1 failed/38 passed，因为严格计量双副本后较大的旧 Catalog 响应在默认预算明确截断。全形状检查改为显式 64KB，最小预算截断另测；不是放弃旧 Schema。随后 39 passed；显式图片预算补齐后针对性 40 passed。
- 全库 `.venv/bin/pytest -q --cov=src/dce --cov-report=json:/tmp/dce-agent-led-coverage.json --junitxml=/tmp/dce-agent-led-tests.xml --tb=short`：208 passed，0 failed/errors/skipped（18.14s），总体 97.93%、行 98.45%、分支 96.31%；ruff、strict mypy（48 files）通过。最终 wheel 离线构建/隔离安装，实际包的文本错误语义一致与新预算字段通过。
- 真实 stdio SDK：授权图片样本附件 1；旧 64KB 预算 not_delivered/truncated，显式 3MB 图片预算后收到原生 image/png，原图 382396 字节、完整 ToolResult 512314 字节、truncated=false、image_delivery=delivered，文本 JSON 与 structuredContent 相同。仅内存处理，不保存图片；不能据此声称 Cursor 模型已看见。
- Cursor 全局 dce 已备份更新图片 Bug allowlist 与图片预算，其他四服务不变，配置无密码/Token。私有 CURSOR_RECHECK.md 只要求新会话验证文本 JSON 与真实图片接收，不重复用户已提供的九工具/原三次调用。原三次工具状态 ok、无错误码，但截断仍 not_observable；没有事后改记为 false。
- 完整草案仍 683 行/23 关系（22 proposed/1 unresolved/0 confirmed），用户已在 Cursor 核对 18 个本地模块。聊天 diff 的 relationships 只是注释，不能当作完整内容保存。已发出完整文件保存审批请求，未获批准前不写业务目录、不补人工审批字段。

## 模块入口诊断

同一 v1 Token 的真实 Bug 返回 200，模块入口返回 403；在三个有界诊断尝试中先提取固定标志，再核对脱敏的固定错误字段，最终为 Access not allowed。没有错误密码重试、扩大 API 范围、读取日志或保存原始错误响应。登录流程有效，不需用户再次提供 Token。

官方 [www/api.php](https://github.com/easysoft/zentaopms/blob/main/www/api.php) 给出了实际框架路径；[entry.loadController/checkPriv](https://github.com/easysoft/zentaopms/blob/main/framework/api/entry.class.php) 设置模块/方法后独立检查权限，未授权返回同样的 Access not allowed；[v1 modules GET](https://github.com/easysoft/zentaopms/blob/main/api/v1/entries/modules.php) 调用 tree/browse。由此推断，应由实例管理员核对当前账号权限组的 tree/browse 读入口和产品范围。此为官方 main 与实际响应相符的推断，当前实例版本未获确认，不声称已精确验证公司权限配置，不请求管理员 Token 或写权限。

公开源码路径最初尝试 api/v1/entry.class.php 为 404，之后按官方 www/api.php 的 include 找到 framework/api/entry.class.php；这是公开源码查阅，不是公司 API 猜测/探测。当前业务服务/环境/版本关系仍未 confirmed。


收尾验证：工作流文档 2 passed（0.51s）、11 份文档相对链接零缺失、21 个暂存文件私有路径/站点扫描通过，git diff --cached --check 通过；凭证源/真实图片/私有运行数据未入索引。
