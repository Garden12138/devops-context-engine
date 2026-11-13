# 测试执行记录

最新：2026-11-05 A–D 增量最终 226 passed / 97.63%；九工具兼容、当前 Project/Stack 真实 SDK 只读验收通过。业务文件未修改，不暂存或提交；新增 Cursor operation 的实际会话调用未观察。见 incremental-v1-acceptance.md；此前完整模块权限与旧独立样本属于历史全样本验收范围。

- 2026-11-04 T0: 审计完成：harness/refactor-audit.md；先核对六工具、三 Adapter、Mapping/AI/Catalog，定义新契约/失败/测试。基线 .venv/bin/pytest -q：144 passed（7.52s），exit 0。下一步 T1 默认调用路径解耦；真实新版能力 not_verified。

- 2026-11-04 T1: 默认初始化/发现和 Bug fixture fallback 的语义推理已移出；确定性 Module→CI 保留，旧 mapping CLI 与 init --legacy-mapping 可用。首次回归 3 failed/142 passed，诊断为技术事实被混放在 Mapping 与旧 ai_status 兼容字段；拆分修复后 pytest 145 passed（7.54s），ruff/mypy exit 0。下一步 T2 范围事实查询。

- 2026-11-04 T2: 新增三个独立事实工具（共九工具），涵盖三平台已有读取、服务详情、分页/ref/path/日志窗口/证据与原生 ImageContent；只读 scope 和输出预算可测，旧六契约保留。针对性 Adapter/HTTP/MCP 54 passed（3.11s），ruff/mypy exit 0；随后图片总预算修正的 facts/contract 回归另记。modules 仅提供 Bug 页实测字段的部分目录，真实图片/模块完整路由与新版上游调用 not_verified；等待目标业务 workspace/连接范围，不读取秘密文件。

- 2026-11-04 T2-budget: 补充图片协议总字节预算后 facts/MCP 契约 8 passed（1.84s），exit 0；ImageContent 与结构化内容共同受预算限制。T2 实现完成，模块完整目录/真实上游/真实 Host 验收仍 not_verified，不计 P0 全部完成。

- 2026-11-04 T3: 已实现 schema_version=1、模板/JSON Schema、指定 workspace 只读校验和纯 refresh：六状态、evidence/人工审批、instance/scope、多对多、拒绝保留、变化 stale/conflicted、秘密/重复 YAML/路径隔离。project/model 与 boundary 14 passed（0.65s），ruff/strict mypy exit 0。DCE 无业务文件写接口，真实工作区初始化待目标输入。

- 2026-11-04 T4: 已提供 initialize/refresh/review/bug-context/service-trace/pipeline-diagnose 六提示词、MCP 实际参数清单、Host 协议，更新 SDK 检查兼容九工具。事实工具条件必填参数同步发布 JSON Schema；工作流/facts/MCP 契约 10 passed（1.99s），ruff passed，strict mypy 修正动态 JSON Schema 类型后 passed（45 files）。真实 Host 调用尚无证据，not_verified。

- 2026-11-04 T5: SQLite 0003 增加 cache/history 角色，所有旧表/边/审批/历史保留；旧库升级前 online backup+quick_check，失败阻止迁移；新增 catalog backup/status，迁移与回滚指南。首次 19 failed 根因是旧 0001 动态建表提前创建角色表，固定历史表集合后 Catalog/CLI 19 passed（1.60s），ruff/mypy exit 0。合成旧库证实备份版本、0600、行数、审批/历史及二次打开幂等；未改动真实旧库。

- 2026-11-04 T6: 完整离线回归 pytest 185 passed/0 failed/0 skipped（15.65s）；总体覆盖率 98.21%、行 98.77%、分支 96.44%；ruff/strict mypy（47 files）/diff/index secret scan passed。标准 stdio→真实 HTTPTransport→本机合成三平台 E2E、原生 ImageContent、双 workspace、审批/拒绝、多对多、迁移和安全边界通过；local wheel 离线打包与隔离导入/Schema/迁移通过。默认沙箱 socket bind/uv cache 受限，经执行器允许后验证，非公司平台操作。真实 doctor exit 2，三平台 AUTH_FAILED/configuration_missing，0 平台请求；当前 Host 未挂 DCE、目标业务 workspace 未提供。T6 外部 P0 not_verified，整体未验收完成；不以旧报告或合成 SDK 替代。新增安全只读 SDK smoke 入口供连接就绪后复验，绝不声称真实 Host 已通过。

- 2026-11-04 T6-followup: 最终代码审查补强：上游忽略 page limit 时强制单页宽度与显式遗漏；JSON 格式 Compose 同样只返回事实；畸形 Swarm Cluster/Service labels 安全失败。针对性 58 passed（1.41s）；最终全库 187 passed/0 failures/errors/skipped（15.70s），总体覆盖率 98.15%、详见机器摘要；ruff/strict mypy passed。重建最终 wheel 并隔离安装，Schema/0003 角色/九工具枚举通过。外部缺口未变，不宣告整体完成。

- 2026-11-04 T7: README/GOALS/PLANS、九工具清单、迁移回滚、安全/运维、Host 六工作流和续跑、ADR 与验收矩阵已同步，旧 V1 文档明确历史范围。当前测试 187 passed、覆盖率 98.15%；文档契约/项目校验 16 passed（0.50s），ruff/strict mypy/diff/新文档相对链接检查通过。真实新版三平台/图片/Host/指定业务 workspace 与完整模块目录仍 pending/not_verified；无真实平台写、构建、部署或业务文件写入。T7 文档交付就绪，整体未验收完成；接续条件和证据见 harness/agent-led-acceptance.md 与 prompts/agent-led/resume.md。

- 2026-11-04 T2-modules-verified: Goal 接续第二轮完成实际推进：核对官方 apiv1.php、modulesEntry GET 和 getProductStructure/getDataStructure，新增 Product scope 的 module_tree，完整树搜索后本地分页、字段白名单、节点/深度/2MB 限额；禁止以 Project/Execution ID 替代 Product ID，旧 modules 部分清单兼容。先行测试 2 failed/1 passed 证实缺口；实现后 QueryParams 与 dict 的测试断言类型差异导致 1 failed，修正断言后针对性 69 passed（2.71s），stdio/本机合成 HTTP 1 passed（1.39s）。最终全库 191 passed/0 failed/errors/skipped（15.94s），总体覆盖率 98.18%；ZenTao Adapter 与事实输入契约 100%。ruff/strict mypy/最终 wheel 隔离安装/九工具与迁移检查通过。官方主分支源码不代表当前公司版本；真实平台/图片/Host/指定业务 workspace 仍 not_verified，缺配置与工作区的阻塞重复第 2 个 goal turn，未达 blocked 审计门槛且本轮有实际进展，goal 保持 active。

## Goal 第三轮阻塞审计（2026-11-04）

当前代码 075212a，初始工作树干净；本轮仅审计提案/验收/代码状态与连接条件。进程中六项平台 URL/凭证变量均缺失、当前工具集合无 DCE、用户未指定业务 workspace；相同阻塞已连续三轮。本轮未发平台请求、未重复 pytest 或 doctor、无新代码测试结果；保留 191 passed/98.18% 基线。逐项审计和恢复输入见 context/agent-led/blocked-audit.md，goal 将设 blocked，绝不设 complete。

- 2026-11-04 resumed-local-intake: 用户明确业务工作区、凭证源与禅道 v1 登录方式，并更换真实缺陷样本。Host 只读核对 20 Git roots、18 根模块清单、17 CI/Dockerfile，私有首层模块关系提议 18 条、confirmed 0，Schema 校验通过；未写业务目录。显式 dotenv/v1 MCP 启动入口已实现，默认不加载 dotenv；文件模式、无插值/执行、别名/重复/冲突、单次登录/无重试/不附旧 Token/父环境隔离/stdio 安全检查通过。先行 5 failed 证实缺口；测试启动 Python resolve 丢失 venv 修复后基础/安全 20 passed，stdio 合成 E2E 2 passed。最终 pytest 199 passed/0 failures/errors/skips（17.71s），总体覆盖率 98.09%，ruff/strict mypy（48 files）与最终 wheel 隔离检查通过。真实凭证只检查变量名并将模式收紧到 0600，正文/值未进入对话或日志，未执行真实登录。三平台地址和实际 Host 仍待用户回复；原 blocked 审计仅历史，不立即沿用旧计数再次标记阻塞。


## 2026-11-04 resumed-http-cursor

用户补齐 HTTP 地址并选择 Cursor；新增 URL 别名/显式进程覆盖回归后 pytest 201 passed/0 failed/errors/skipped（18.38s），覆盖率 98.09%（行 98.64%、分支 96.39%），ruff/strict mypy（48 files）与最终 wheel 隔离导入/Schema/0003 角色通过。安装验证首次把 /tmp 与 /private/tmp 路径当作不同，规范化比较后通过。真实 v1 认证 201、Bug 200；标准 SDK 九工具、27 次三平台成功只读 calls（ZenTao 4/GitLab 4/Portainer 19）及一次模块树 403，输出 Schema 均校验。指定 Bug 无附件/内联图片，module 未分配；三 Stack File 63/71/78，实际 Service label 的运行 namespace 八页 78 个唯一 ID，不合并来源或自动确认。真实 Catalog 副本先备份迁移并保留 191/219/219/11，原库不改；全局 Cursor dce 已备份更新且其他四服务保留。23 条私有关系草案（22 proposed/1 unresolved/0 confirmed）和具体 diff ready，Schema/纯 refresh passed，未写业务目录。旧独立 GitLab 固定编号补验被自动审批在执行前拒绝（本轮读取范围未明确授权），移除后只按已配置范围执行；旧样本/其 GitLab Compose 保持 not_verified。真实 Cursor Agent 对话/初始化审核、业务文件落地、含图样本、模块只读权限和旧样本范围仍待补。详见 context/agent-led/resumed-http-cursor.md；无业务写/构建/部署/push/merge。


提交前检查：工作流/项目校验/本地凭证回归 25 passed（1.10s），10 份文档相对链接检查通过，git diff --cached --check 与 15 个暂存文件的私有路径/站点扫描通过；.env/.local/private 未入索引。真实 Catalog 原有 11 张业务表计数全部与副本一致，两库 quick_check=ok。


## 2026-11-04 cursor-text-compatibility

用户回传 Cursor 九个 DCE 工具（另有宿主 mcp_auth）、三次实际成功调用与初始化对话；旧文本仅 DCE result.、结构化信封不可见，原三次 truncated 保持 not_observable。先行 5 failed 复现文本缺陷，九工具改为相同 JSON 文本/structuredContent；预算计量双副本/转义。全形状契约改显式 64KB并保留最小预算检查后 39 passed；新增默认关闭的独立图片总预算（最大 3MB，文本预算/Reader 2MB/来源 scope 不变）后针对性 40 passed。最终全库 208 passed/0 failed/errors/skipped（18.14s），覆盖率 97.93%（行 98.45%、分支 96.31%），ruff/strict mypy（48 files）/最终 wheel 隔离检查通过。真实授权新图片经 stdio 返回原生 PNG，原图 382396 字节、ToolResult 512314 字节、truncated=false、文本与结构化相同，无图片落盘；Cursor 模型接收仍待复验。已备份更新 Cursor 的授权图片样本与显式预算，其他四服务不变。模块接口同 Token Bug 200、模块 403 Access not allowed；官方 v1 modules→tree/browse→checkPriv 源码与该错误相符，推断需核对单独读入口/产品范围，实际实例版本未确认，不索取新 Token或绕过权限。完整683行/23关系草案的保存批准已提出，聊天省略片段不写业务目录，confirmed仍0。旧独立GitLab范围未获本轮明确授权，不重试。详见 context/agent-led/cursor-text-compatibility.md。


收尾验证：工作流文档 2 passed（0.51s）、11 份文档相对链接零缺失、21 个暂存文件私有路径/站点扫描通过，git diff --cached --check 通过；凭证源/真实图片/私有运行数据未入索引。


## 2026-11-04 clarification-of-host-restart-and-project-save

用户询问“关开 dce”和文件审批含义，尚未批准业务文件保存。已将私有复验提示词与接入文档改为明确步骤：Cursor Customize→MCPs，关闭再开启 dce 服务开关，等待工具列表后新建 Agent 会话；按官方页面核对。补充项目草案/diff/最终 YAML/规格各自作用和 23 条关系摘要，明确只申请新增业务项目记录，保存不把 proposed/unresolved 改为 confirmed；审批来源为规格 05 阶段 F。仅文案变更，不重跑平台或全库回归，208 tests 基线保留；diff check 通过，业务目录仍未写。

文档工作流检查：2 passed（0.57s）；未运行真实平台读取或改写业务工作区。


## 2026-11-04 cursor-recheck-and-approved-save

用户回传 Cursor 修复后两次实际调用：JSON 文本信封可见，Bug 信封/data.truncated 均 false、data.evidence 1（兼容顶层为空）；原生 PNG 实际进入模型，delivered/truncated=false，未保存或转录。用户明确批准完整文件保存并要求不要提交。Host 将与批准 diff 逐字匹配的 683 行/22451 字节草案只创建为业务 .dce/project.yaml，拒绝覆盖/symlink；23 关系保持 22 proposed/1 unresolved/0 confirmed，审批字段全空。真实 CLI validate exit 0、load_project 复读/字节一致/roots 在 workspace 内通过，业务 Git HEAD/index 前后不变，文件 untracked。本轮无 git add/commit/push、真实平台调用或产品代码修改；208 passed/97.93% 保留既有基线，不重复全库测试。更新记录与文档仅本地未提交。核心初始化闭环；完整模块树403、旧独立GitLab范围/Compose仍未验证，严格全样本验收不虚报完成。详见 context/agent-led/cursor-recheck-and-approved-save.md。


收尾：目标业务文件另经独立 JSON Schema 校验通过；文档工作流 2 passed（0.79s），8 份文档相对链接零缺失，11 个公开工作区文件私有路径/站点扫描通过，git diff --check 通过。DCE HEAD 未变、暂存区为空；没有 git add/commit/push。


## 2026-11-05 incremental-v1-implementation

2026-11-05 增量 A–C：实现前契约见 docs/refactor/agent-led-initialization/INCREMENTAL_V1_CONTRACT.md。现有未提交记录保留且不提交。基线208 passed（12.41s）；事实能力先行6 failed/3 passed复现缺口，新增project_jobs/branch_jobs/pipeline_bridges与stack_service后针对性42 passed（6.81s）。Schema v2先行3 failed/1 passed；新增typed details、独立version_match与纯迁移，旧v1输出省略新空字段以满足冻结原Schema；旧“版本2无效”负例改为版本3，针对性29 passed（1.71s）。阶段全库221 passed（13.35s），ruff/strict mypy49 files通过。当前真实业务文件只读核对28关系24proposed/3unresolved/1confirmed，迁移预览除schema_version外全字段一致，原文件指纹不变。后续补stdio增量E2E、真实限定只读、完整覆盖率和调用示例；尚未声称增量真实验收通过。


## 2026-11-05 incremental-v1-final-verification

增量 A–D 完成。新增 stdio→本机合成 HTTP E2E 1 passed（1.45s），九工具名称/旧六工具1.1/事实工具2.1、双份信封一致、分页与预算边界通过。收尾安全审查补强畸形 environment 名称和 Job 标量字段；中间因服务名变量覆盖出现 3 failed/223 passed，修正后针对性17 passed（1.48s），最终全库 `.venv/bin/pytest -q --cov=src/dce --cov-report=json:/tmp/dce-incremental-v1-coverage.json --junitxml=/tmp/dce-incremental-v1-tests.xml --tb=short`：226 passed、0 failures/errors/skipped（23.08s），总体97.63%（行98.27%、分支95.72%）。`ruff check .`、strict mypy（49 files）通过，最终 wheel 重建/隔离安装验证实际包的新details模块、v1/v2纯迁移、精确服务名和九工具通过；文档工作流2 passed（0.54s）。

真实当前授权范围使用标准 SDK stdio；最终验收选取21次 status=ok（初轮20次、修复后精确服务名复核1次），另2次中间复核留痕，不充当最终版本证据。各分支本次选取的3条上游Pipeline普通Jobs均空，但各有1条bridge；Host核对同项目后显式查询观察到的下游，各2条Jobs。Project/manual首页各3条；两次分支过滤页为空但上游仍有下一页。相同8192字节预算，整Stack截断，目标单服务3634字节、truncated=false、incomplete=false且服务名精确相等。未自动扩展下游、未读私有日志、未保存原始Compose、未请求禅道、未触发CI或部署。不能将空Jobs认定没有构建，也不据此推定分支/环境/版本业务关系。

业务v1文件前后指纹不变，28关系仍24 proposed/3 unresolved/1 confirmed；v2仅在私有目录预览，解析模型除版本外全部值一致，审批/证据/备注保留。本轮没有git add/commit/push，保留此前未提交改动。实际调用JSON保存在gitignored私有目录，公开例子全部合成。新版Cursor operation尚未观察，需重载dce连接后使用；SDK证据不冒充Cursor证据。完整报告 incremental-v1-acceptance.md，机器结果 reports/incremental-v1-summary.json。

收尾独立检查：业务v1、纯迁移v2、两份公开project示例均通过运行时及JSON Schema校验，28条关系/审批/证据/备注保持；17份改动Markdown的70条相对链接有效，35个公开改动文件新增内容的私有路径/主机/项目坐标扫描通过。工作流文档2 passed（0.55s），ruff/strict mypy49 files/diff check通过；DCE索引为空、HEAD未变，业务文件最终指纹与本轮基线一致。
