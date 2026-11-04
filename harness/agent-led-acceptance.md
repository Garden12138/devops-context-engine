# Agent-led 重构验收 — 2026-11-04

结论：**本地实现与离线验证通过；整体真实验收未完成。** T2 独立产品模块树现已补齐离线实现并核对官方 v1 路由，真实实例兼容性及 T6 的真实平台/图片/Agent Host 和指定业务项目初始化为 `not_verified`。不将旧 V1 成功、SDK 客户端或合成 HTTP 等同本次真实 Host 通过。

依据：实际位于 docs/refactor/agent-led-initialization/dce-agent-led-refactor/ 的 CHANGE_PROPOSAL 与 specs/01–07；根 AGENTS/GOALS/PLANS、旧验收仅作历史证据。T0 基线 6fd0a90（144 tests）；本地阶段提交保留，未 push/merge。审计见 [refactor-audit.md](refactor-audit.md)，全部命令与修复过程见 [build-log.md](build-log.md)、[test-results.md](test-results.md)。

| 阶段 | 交付 | 判定 |
|---|---|---|
| T0 | 六工具真实 Schema/实现/测试、Adapter、Mapping/AI/Catalog 审计；先定义边界/失败/测试 | passed |
| T1 | 默认初始化/发现/Bug fallback 不调用语义推理，确定性 Module→CI 保留；显式 legacy 入口兼容 | passed |
| T2 | 三事实工具，保留旧六；三平台 scope/instance、分页/ref/path/日志窗口、证据/预算、原生图片 | offline passed；新增 module_tree 独立产品树，旧 modules 部分清单兼容；真实新版接口 not_verified |
| T3 | 项目 Schema/模板/只读校验/纯 refresh，六状态、人工审批、隔离、多对多、拒绝保留 | offline passed |
| T4 | 六 Agent 工作流、实际工具说明、SDK smoke；Host 负责对话/推理/diff/文件写入 | offline passed；真实 Host 流程 not_verified |
| T5 | SQLite backup/quick_check 后迁移 0003 角色；所有旧关系、审批和历史保留；回滚说明 | offline passed；未选择/迁移用户真实旧库 |
| T6 | 单元/契约/CLI/stdio/本机合成 HTTP E2E/图片/安全/隔离；真实预检记录 | offline passed；外部 P0 pending |
| T7 | README/GOALS/PLANS、迁移/清单/工作流、安全/ADR、harness 与续跑 | documentation ready；不宣告整体完成 |

## 实跑结果

- `.venv/bin/pytest -q --cov=src/dce --cov-report=term-missing --cov-report=json:/tmp/dce-agent-led-coverage.json --junitxml=/tmp/dce-agent-led-tests.xml --tb=short`：**191 passed，0 failed，0 errors，0 skipped，15.94s**。
- 总体覆盖率 **98.18%**；行 **98.73%**，分支 **96.48%**，高于 75% 门槛；新增 MCP 事实输入契约模块 100%。安全/状态关键场景见下表。
- `.venv/bin/ruff check .`、`.venv/bin/mypy src`（47 files）、`git diff --check`、索引公共数据扫描 exit 0。最终暂存扫描在 T7 提交前另记。
- `uv build --wheel --offline --out-dir /tmp/dce-agent-led-dist`：成功；wheel 安装到 `/tmp` 隔离路径，实际从安装包导入，项目模板/Schema 与 0003 迁移/角色检查通过。不触发公司构建或部署。
- `check_agent_led_mcp.py --help`、项目 CLI/help/模板/schema/校验通过；真实新版 SDK smoke 尚未执行。已提供不输出 ID/正文/凭证的范围检查入口。

本机 HTTP E2E 第一次因沙箱禁止 socket bind 失败，经执行器放行后只绑定 loopback 随机端口通过；wheel 首次因 uv 缓存读取限制停止，经执行器放行离线缓存后通过。没有绕过 TLS/SSRF/范围限制。迁移首轮暴露旧 0001 动态 metadata 表清单问题，修复后 19 项迁移/Catalog/CLI 检查通过。

## 离线 P0 证据

| 场景 | 测试/证据 | 状态 |
|---|---|---|
| 三平台所有新增 operation / Schema / source/revision/观察时间 | test_facts.py，含 26 类 operation 组合 | passed（合成） |
| instance/Project/Bug/Endpoint/Stack 范围、空 scope、不允许秘密路径 | test_facts.py，拒绝发生在打开 Reader 前 | passed |
| Tree 单页、ref/path、cursor 检验、trace tail、输出遗漏 | test_facts.py、旧 Reader/预算测试 | passed |
| 同源图片/HTML 假图/越源/大小/原生 ImageContent/总预算 | test_facts.py、test_agent_e2e.py、旧 connector/MCP tests | passed（合成） |
| Swarm/Stack 独立来源、env/auth 过滤、非典型文件名 Compose | test_facts.py，历史 mismatch 和 current/saved/runtime 旧用例保留 | passed（合成） |
| confirmed 需证据与人工元数据，confidence 不批准 | test_project_context.py | passed |
| 六状态、新关系 proposed、审批/备注/拒绝保留、变化 stale/conflicted | test_project_context.py | passed |
| 双 workspace / 来源实例 ID / 同数字跨平台 / 多对多 | test_project_context.py、test_agent_e2e.py、旧链路用例 | passed |
| YAML 注入/重复 key/alias/体积/secret/路径和 symlink 逃逸 | test_project_context.py、旧安全测试 | passed |
| 模型无关、默认无 Mapping/AI 调用、事实读取不改 Catalog | test_agent_boundary.py、test_facts.py | passed |
| 旧六工具/CLI 保留，旧库先备份，审批历史不变 | test_mcp*.py、test_catalog_migration.py、test_cli_workflow.py | passed |
| MCP stdio→HTTPTransport→三平台合成读取、原生图片、Host harness 写文件 | test_agent_e2e.py | passed；不是实际 Agent Host |
| 调用审计只含已知工具名/状态/错误码 | test_facts.py；无参数/正文/密钥 | passed |

## 外部 P0 缺口与真实证据

实际运行 `.venv/bin/dce doctor --live --read-only`：exit **2**，ZenTao/GitLab/Portainer 均 `AUTH_FAILED`，原因固定诊断 `Platform configuration is missing.`，`live_status=not_verified`；未发送平台请求。仅检查六个相应进程变量是否存在，均 false，未打印值；未读取 .env、Token 文件、私有日志或真实附件缓存。当前工具集合无 DCE MCP；用户尚未提供指定业务 workspace，已异步询问。

| 必须补验 | 当前判定 | 下一步 |
|---|---|---|
| 新版三平台真实只读查询 | not_verified | 受保护子进程环境加载配置；用户给明确授权 scope |
| 完整 ZenTao 产品模块树 | implemented offline / live not_verified | 新 module_tree 按官方 v1 /modules GET 契约实现，搜索后本地分页；真实实例按产品 scope 补验，不能把项目 ID 当产品/执行 ID |
| 指定真实 Bug 图片到模型 | not_verified | 在真实 Host 观察 tools/call 的 MCP ImageContent；URL/Resource/SDK 布尔摘要不能代替 |
| 至少一个真实 Cursor/Codex connect/list/三次真实 calls | not_verified | 重载实际 Host 新进程与会话，按工具清单枚举九工具并记录调用 |
| 当前业务项目初始化与维护 | not_verified | 指定 workspace；Host 执行提示词、展示候选/diff、人工确认或明确 unresolved、写后校验/复读 |
| 指定 Stack Swarm mismatch、三来源 Compose/namespace 数量、Stack File、Pipeline/Job 可访问性 | not_verified | 在当前授权范围重读；历史数字不作当前事实，过期明确不可用 |
| 指定 GitLab 项目与 Bug 关系 | unresolved | 无业务证据，不假设相关；仅用户审核后 confirmed |
| 真实旧库迁移 | not_verified | 指定安全私有库，停旧进程，先备份再打开新版本 |

没有项目/环境被自动确认，没有业务仓库文件被 DCE 写入，没有真实平台写入、构建、部署、push 或 merge。机器摘要见 [agent-led-summary.json](reports/agent-led-summary.json)。

## 接续

按 [续跑提示词](../prompts/agent-led/resume.md)，从缺失外部条件补验继续，无需重做离线阶段。需要目标业务工作区绝对路径、非秘密连接配置/授权范围及可调用 DCE 的真实 Host；凭证只进入本机受保护进程环境，不发聊天或写入项目 YAML。未满足这些完成标准前保留 goal 未完成。


## 模块能力接续（2026-11-04）

官方 [路由注册](https://github.com/easysoft/zentaopms/blob/main/config/apiv1.php)、[模块入口](https://github.com/easysoft/zentaopms/blob/main/api/v1/entries/modules.php) 和 [产品树结构实现](https://github.com/easysoft/zentaopms/blob/main/module/tree/model.php) 已核对，之前 config/routes.php 404 不代表没有 API。新 module_tree 保留完整产品树的实际节点字段/层级，支持本地搜索后分页，深度/节点/字节预算和范围检查；旧模块部分清单不被冒充为完整。新增回归先观察到缺少 operation 的失败，实施后针对性 69 passed（2.71s），真实 stdio/本机 HTTP E2E 1 passed（1.39s）。测试数据全部合成，真实版本与权限依旧 not_verified。


## Goal 阻塞审计

当前状态 blocked，整体未完成。相同的连接配置/真实 Host/业务工作区缺失已连续三轮复核，见 [逐项审计](context/agent-led/blocked-audit.md)。本轮无代码变更，未重复 pytest 或无配置认证；191 项通过的证据保持原采集时间与范围。取得明确业务工作区、授权非秘密配置/范围以及真实 Host 后从外部验收接续。
