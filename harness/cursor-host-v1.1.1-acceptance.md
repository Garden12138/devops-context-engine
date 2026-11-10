# V1.1.1 Cursor Host启动与Schema修复（2026-11-07）

## 结论边界

**2026-11-08当前结论：Cursor Host Gate A PASS（来源：用户真实桌面验收回传）**。版本1.1.1、九工具、service_logs发现、原授权Bug连续两次及测试Stack只读查询均通过。具体验收PID/资源ID仅留本地忽略报告；本轮收尾不重复访问公司平台。独立STDIO结果与桌面验收分别记录。

2026-11-07时桌面调用尚待复验；此前失败、日志证据缺口和独立客户端结果保留为当时事实。进程存活本身仍不作为Host通过依据。

**2026-11-08当时Service Logs Gate B：not_verified**。发现service_logs与元数据查询通过不代表日志权限；当时仍需独立审批日志scope及有限窗口真实只读验收，Host修复阶段未新增权限、未读真实日志。

2026-11-09独立日志验收完成：**Gate B PASS、临时授权REVOKED**；真实GET1次，6条脱敏事件，truncated明确，无已发现越权或敏感泄露。Gate A结论保持。公开结论与真实过期认证剩余缺口见[最终工程收尾摘要](v1.1-final-acceptance.md)，不在Host历史记录中保存日志、实际授权身份或策略。

## 定位

- 当前业务工作区无项目级.cursor/mcp.json；用户级仅一个dce属性，JSONC无语法错误，也未发现原生用户/其他profile的MCP文件。实际窗口仍可能持有旧连接定义。
- 用户级定义是带配置/凭证文件的本地入口；Cursor共享MCP宿主同时运行了旧CLI入口及本地凭证入口。旧CLI未带平台配置/凭证文件。日志中同名dce有多个配置指纹，启动事件与两种进程的启动时间对应；原日志缺逐调用PID/request_id审计，无法追认历史两次请求的精确PID归属。
- Platform configuration is missing来自Settings.platform(None)，先于Adapter/Token获取；与Token过期分类不同。用观测CLI定义、无平台环境及临时Catalog做真正STDIO负例，两次完全复现同一AUTH_FAILED，未发平台请求。
- Portainer源码已经注册service_logs枚举和描述。正/负两条STDIO入口均发布该操作；Cursor展示缺失与当前服务端Schema不一致，需重载旧连接/会话缓存。未为此改Token Manager或业务Schema。

## 修复

- serve_dce_local.py新增--require-platform，可要求三平台完整配置并在缺配置时以脱敏stderr JSON提前退出；不增加授权、不做启动登录。
- 本地入口补--portainer-log-scope，抽取并复用CLI同一验证函数；默认空grant，本轮真实配置没有增加日志授权。
- 保留serverInfo.version=1.1.1，从包版本统一取值。既有工具/结果_meta追加版本、PID、公开Schema摘要、配置平台类别；无新MCP工具、无地址/身份/范围值。预算不足时先省略可选结果_meta，再进行原有数据/图片裁剪，诊断不得挤掉原本可返回的结果。
- 本地入口只向stderr写固定启动/调用审计；request_id关联既有响应文本，避免Host隐藏_meta时失去调用证据。不记录业务参数、头或正文。
- 用户级只改dce：保留绝对路径、凭证来源、全部既有scope与env，仅追加三项--require-platform；写前0600私有备份，其他MCP条目逐项一致。没有新增Bug或日志grant，没有修改业务文件。

## 自动化证据

先行新增10项失败，证实启动检查、共用日志参数及运行身份缺口。实现后首轮24项中最小预算用例暴露可选_meta挤占预算；修复为优先保留原信封/按预算省略诊断，24通过。三平台合成STDIO和service_logs/契约专项116通过。补request_id关联后启动/stdio专项15通过。

最终审阅补1项预算边界非退化用例，将可选诊断移除提前到数据/图片裁剪前，并保持原静态日志计量接口。最终完整回归 **370通过 / 45.69s / 97.25%**；ruff与strict mypy（54文件）通过。Token Manager文件未修改，原357项覆盖继续通过。无真实模型调用、CI、部署、真实图片或运行日志查询。

## 独立真实STDIO证据

完全复用修正后用户级dce的command/args/env及实际工作目录，使用原Catalog；初始化返回1.1.1，九工具发现通过，三平台均configured_not_verified。portainer_query契约2.2且枚举/描述含service_logs，日志授权状态blocked（未授予）。

同一协议会话内，既有授权Bug连续两次、既有测试Stack元数据一次均成功，资源身份检查通过、未截断。初始化、工具Schema、每次结果_meta和stderr审计PID一致；原Catalog计数与配置文件指纹不变。不保存正文、图片、Token或Cookie；具体资源ID、PID、路径与完整安全状态证据只保存在忽略的私有目录。

真实业务读取在补充request_id审计字段前完成；后续仅补固定日志字段，未改变网络/认证/授权行为，以最终合成回归验证该关联，不重复业务读取。桌面历史两次失败保留；后续用户已按[重载方案](../docs/CURSOR_HOST_V1_1_1.md)确认Gate A PASS，不将后续通过追写到旧失败中。

最终入口另以实际STDIO调用一次本地discovery_status：初始化/九工具/结果PID与Schema一致，响应request_id精确匹配stderr审计，零平台网络请求。该本地检查也不冒充Cursor桌面调用。

## 文件范围

| 类别 | 文件 |
|---|---|
| 启动/协议 | scripts/serve_dce_local.py、src/dce/mcp/startup.py（新增）、src/dce/mcp/server.py、src/dce/cli/__init__.py |
| 自动化 | tests/test_mcp_startup.py（新增）、tests/test_agent_e2e.py |
| 契约/接入 | docs/CURSOR_HOST_V1_1_1.md（新增）、docs/AGENT_LED_LOCAL_CREDENTIALS.md、docs/CURSOR_MCP_SETUP.md、docs/DECISIONS_AND_RISKS.md |
| 状态/验收 | README.md、PLANS.md、harness/build-log.md、harness/cursor-host-v1.1.1-acceptance.md（新增） |

用户级MCP配置及0600备份只在本机，未纳入以上14文件。2026-11-08用户授权仅提交本表源码、测试及必要文档，不推送。

## 旧Runtime PID收尾检查

只读检查Cursor工具目录发现：工具JSON保留了正确service_logs枚举，旧PID出现在独立INSTRUCTIONS.md握手说明快照中。DCE源码的runtime仅在进程内通过os.getpid()构建，无Catalog持久化写入/加载路径；不是平台配置或Token状态被旧PID覆盖。

最小修正从可缓存说明移除瞬时PID，保留稳定Schema摘要；实时Tool/Result元数据、request_id审计和九工具Schema不变。新增同一合成Catalog连续两次真实STDIO进程用例，确认稳定说明/Schema、不同进程PID和request_id。不修改Cursor缓存或重启已验收的真实连接。

该新增用例在旧实现上先行失败，确认握手说明确实携带瞬时PID；最小修正后启动/STDIO专项17通过。2026-11-08收尾全量 **371 passed / 31.45s / 97.25%**，原370项继续通过，ruff、strict mypy54文件及git diff --check通过。输入Schema摘要与原独立验收一致，Token Manager/凭证加载器/Schema源文件没有新增修改。提交前14文件人工内容审核、辅助敏感扫描及相对链接检查通过；无企业配置、凭证、真实业务数据或私有诊断入索引。
