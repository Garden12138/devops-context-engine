# Agent 执行日志

状态：OFFLINE_COMPLETE
当前阶段：T0–T7 全部离线验收通过
最后更新时间：2026-11-01

## 里程碑

| 阶段 | 状态 | 提交/验收证据 |
|---|---|---|
| T0 | passed | ca28f8a；Python 3.12.11；pytest 13 passed / coverage (branch enabled) 100%；mypy 10 files；CLI smoke passed |
| T1 | passed | 7719fdc；47 tests / 99.48% coverage (branch enabled)；ruff + mypy + doctor mock |
| T2 | passed | 59724e4；79 tests / 97.41% coverage (branch enabled)；三平台 scoped mock、快照差集、恢复与安全静态解析 |
| T3 | passed | 5839502；93 tests / 97.77% coverage (branch enabled)；Alembic 0001→0002、事务/版本/审核与双向查询 |
| T4 | passed | ae07de1；107 tests / 98.02% coverage (branch enabled)；规则/AI/review/Catalog 关键分支 100% |
| T5 | passed | 1cfcd3c；119 tests / 97.86% coverage (branch enabled)；CLI 全流程/子进程/预算/授权门禁 |
| T6 | passed | 1e5984a；123 tests / 97.93% coverage (branch enabled)；真实 SDK stdio 六工具/资源/错误/注入 |
| T7 | passed | 133 tests；总体 98.58% / 行 99.18% / 纯分支 96.65%；独立 wheel 安装与逐项 P0 报告 |

## 下次继续动作

离线目标已完成。真实平台与 Cursor/Grok 实际执行器仍 not_verified；用户可按 OPERATIONS 独立进行授权只读 smoke。

## T0 执行记录

- 创建本地分支 `work/dce-v1-offline`；初始仅文档，无实现，无已完成阶段。
- `uv sync --python 3.12 --dev` exit 0，生成 uv.lock；仅公共依赖下载。
- `.venv/bin/pytest -q --cov=dce --cov-report=term-missing` exit 0：13 passed，100% 覆盖率（启用分支统计）。
- `.venv/bin/mypy src` exit 0：10 source files。
- `.venv/bin/dce doctor --mock` exit 0：3 平台合成契约，live 均 not_verified。
- 初次 ruff exit 1（测试行过长）；ruff format 修复后 check exit 0。
- `git diff --check` exit 0。真实平台未调用。

## T1 执行记录

- 实现 ZenTao v1 / GitLab REST v4 / Portainer 与 Docker proxy GET；唯一特许 POST 是 ZenTao token 认证且不自动重试。
- HTTP：固定 origin、禁止重定向、timeout、流式字节上限、有限退避、错误分类、分页循环与页数上限。
- 图片：files=[] 内嵌 2 图、Token、MIME+magic、跨域/HTTP/SVG/HTML/超限拒绝；私有目录、原子写、失败清理测试。
- doctor 使用 Adapter；独立能力矩阵、单平台失败隔离；mock 不出网。
- `pytest -q --cov=dce --cov-report=term-missing` exit 0：47 passed，99.48% 覆盖率（启用分支统计）。
- `ruff check .`、`mypy src`（15 files）、`dce doctor --mock`、`git diff --check` exit 0。
- 修复首次检查暴露的闭包 lint 和动态 JSON 类型收窄错误，所有修复后检查通过。
- 外部 API 兼容性 not_verified；未访问内网，未调用业务写接口。

## T2 执行记录

- 静态解析 Maven reactor、Gradle settings、Go work/module、Node workspaces、Dockerfile、CI 显式 include、Compose。
- 禁止执行脚本；大小/节点上限、非法 YAML/XML、alias/动态表达式 incomplete、OCI 引用验证；Compose 仅变量名。
- 显式 scope 的 GitLab/ZenTao/Portainer crawler；固定 commit 读取、相关路径白名单、节流、私有原子 checkpoint。
- 失败状态持久化，已完成仓库复用、commit 变化失效重读；Catalog ScanRun 将在 T3 接入。
- 独立 git_current / portainer_saved / swarm_runtime 快照、来源实例复合身份、版本指纹和证据。
- 合成验收：3 Stack、1 current Swarm、2 stale、78 namespace services、73 images、5 组复用；71→78 差集为 072–078。
- 三平台 Mock HTTP 联合测试验证范围、master、Endpoint/Swarm/标签、快照差异及原始 secrets 不进入 cache。
- HTTP 日志开启 DEBUG 时仍过滤 URL、主机与凭证；图片/写操作拦截回归通过。
- `ruff check .`、`mypy src`（24 files）、`pytest -q --cov=dce --cov-report=term-missing`、`git diff --check` exit 0。
- 最终 79 passed，coverage (branch enabled) 97.41%；外部平台 not_verified。

## T3 执行记录

- SQLAlchemy SQLite Catalog 与打包 Alembic 0001/0002；旧实体/关系版本历史回填测试通过。
- 实体/边/证据/独立快照/ScanRun/Approval/Audit 持久化；完整批次原子导入，失败另记 scan 状态。
- 来源复合键、幂等写入、历史版本、最近校验、有效期；不可变快照/证据冲突与缺失引用回滚。
- Entity 与 Edge 独立 scope 成员；完整扫描来源消失软删除/过期；其他活跃 scope 保护共享资源。
- 审核 accept/reject/revoke/override 保留 actor/reason/timestamp 与 before/after；扫描不能写 confirmed，冲突单独记录。
- 有界分页、双向 trace、证据/版本/审计查询；本地目录 0700/数据库 0600。
- `ruff check .`、`mypy src`（32 files）、`pytest -q --cov=src/dce --cov-report=term-missing`、`git diff --check` exit 0。
- 93 passed，coverage (branch enabled) 97.77%。修复 mypy 动态 SQL 类型注解与关系消失保护分支。
- 覆盖率命令从包名改源码路径：包名过滤会把 Alembic 动态脚本计为未执行；源码路径正确测量迁移。README/tasks/acceptance/CI 已同步。
- 真实外部平台仍 not_verified。

## T4 执行记录

- 规则以显式 module_paths 建立模块→build job 证据；名称相似仅 candidate，线索不足保留多个 unresolved。
- Provider 协议、Noop/Fake、默认关闭；仅 UUID/受控类型/证据 ID 摘要，不发送名称/URL/源码/日志。
- 严格候选 schema/引用/状态校验；超时/异常回退规则，AI 阶段失败持久化，可有限重跑。
- AI/规则同边合并幂等；Mapping scope 不取得实体所有权；候选上限与证据排序。
- 审核预览证据/版本/环境/影响，期望版本原子校验；环境显式确认，stale 不能接受；撤销保留审计。
- `ruff check .`、`mypy src`（36 files）、`pytest -q --cov=src/dce --cov-report=term-missing`、`git diff --check` exit 0。
- 107 passed，coverage (branch enabled) 98.02%；rules、AI、MappingService、Catalog 100% 分支覆盖。
- 无外部 AI 请求，真实平台 not_verified。

## T5 执行记录

- 完整 CLI 命令树与共用 AppServices；默认离线、JSON/table、统一错误、预算截断、全命令帮助。
- init/discover 显式 live/read_only/Scope；MockTransport 测试 CLI 调用路径，无内网请求。
- BugContext 同一 Adapter Token 认证获取两张合成 PNG；摘要/证据/候选/人工状态、附件私有路径。
- 修复拒绝映射被 fixture 回退重新召回的问题；来源实例歧义 fail closed。
- Pipeline 摘要区分 Buildx 与 missing_make，保留 master，不触发 Pipeline。
- Stack 三类快照摘要，stale/unknown health/environment/version；分页/trace 与 review 版本门禁。
- 真实 CLI 子进程 smoke、1024 字节预算、损坏 SQLite/URL/参数安全失败通过。
- `ruff check .`、`mypy src`（37 files）、`pytest -q --cov=src/dce --cov-report=term-missing`、`git diff --check` exit 0。
- 119 passed，coverage (branch enabled) 97.86%；真实平台 not_verified。

## T6 执行记录

- MCP SDK stdio，仅六个只读工具；CLI/MCP 共用 AppServices，严格 schema、固定 error_code。
- 真实 Python ClientSession 子进程完成 initialize/list_tools/六工具/错误/资源读取；stdout 仅协议。
- structuredContent 单份 payload，预留协议预算；discovery_status 压缩为进度/异常计数/待审核数。
- 附件只返回当前会话注册 URI；资源读取验证 SHA256、边界、大小和 symlink，拒绝未知/篡改引用。
- 默认离线，live/read_only 与 Bug/项目 allowlist 显式启用；不注册审核/部署/触发工具。
- 恶意指令文本仅数据，未创建标记文件；URL/Token 脱敏与预算测试通过。
- `ruff check .`、`mypy src`（39 files）、`pytest -q --cov=src/dce --cov-report=term-missing`、`git diff --check` exit 0。
- 123 passed，coverage (branch enabled) 97.93%；README 增加 Cursor 可运行配置，Grok/真实内网 not_verified。

## T7 执行记录

- 按 REQ-01–12 / NFR-01–06 / AC-01–17 / T0–T7 逐项审计，证据写入 acceptance-report.md。
- 合成多模块/Job/镜像/运行服务链补齐并 E2E；Node glob 只认 package 根；缺 Namespace 证据不能确认当前 Stack。
- 补测并修复平台子路径、畸形附件 URL、损坏/原子失败 checkpoint、Catalog 入库/审核二次脱敏。
- 本地 pre-commit 已启用 .githooks；index blob、凭证文件名拒绝、私网地址/主机与历史扫描；从不打开凭证文件。
- ruff check . / mypy src（39 files）/ git diff --check exit 0。
- 最终 pytest -q --cov=src/dce --cov-report=term-missing --cov-report=json:harness/reports/coverage.json --junitxml=harness/reports/pytest.xml exit 0：133 passed、0 failures/errors/skipped。
- 覆盖率口径更正：早期日志的百分比是启用分支统计的总体值，已改正称谓；最终总体 98.58%、行 99.18%、纯分支 96.65%。命名安全/状态/关系模块的纯分支 100%，详见 reports/summary.json。
- JUnit 主机名脱敏为 offline-runner，完整 coverage 与 JUnit/摘要已保留；测试始终合成，autouse 禁止 IP socket。
- uv build --offline exit 0，wheel/sdist 成功；wheel Python 源文件逐字节匹配，独立临时 venv 安装迁移/243实体/335边/331证据/6快照/双图/6工具/doctor mock 成功。
- OPERATIONS 安装/Mock/用户本地 smoke/恢复/移除指南完成；Cursor 配置有效，Grok 与真实平台 not_verified。
- License/GitHub 审查：不擅自授予许可，不创建远端、不 push/merge/release；不影响本地离线 P0。
- 最后行为核对补齐 live init/discover 入库后的本地规则生成（无新增平台请求）；重新完整运行 133 tests 通过。
- 最后报告整理的 EOF 空行由 diff --check 发现并修正。
- 补齐 AI 候选独立 ai_candidate 快照与脱敏 rationale Evidence；无效输出不留伪证据、重复候选幂等；再次完整 133 tests 通过。
- T7 由本地提交 test: certify offline V1 acceptance and operations 保存；提交钩子再次执行暂存区检查。

## 真实案例只读验证尝试（2026-11-02，未完成）

- 边界：按用户提供的 14 个 Bug、5 组组件与最终闭环限定核验；不执行公司构建、部署、审核通过或回调，不读取凭证文件、真实图片、私有日志或原始 Compose。
- `.venv/bin/dce doctor --live --read-only` exit 2：ZenTao/GitLab/Portainer 均 `AUTH_FAILED` / `Platform configuration is missing.`；请求在配置检查处停止，无平台响应或网络成功证据。
- 注意该命令本次 JSON 顶层 `status` 为 `ok`，但三平台均错误且退出码为 2；不得将顶层字段当作连通验收通过。
- 只读核对 5 个实际本地仓库：模块标记存在；2 条案例明确指定的本地目标分支包含 feature HEAD。此项仅证明本地提交包含关系，不能证明每个 Bug 已修复或远端/构建/部署状态。
- 案例和本地版本仅写入 gitignored 私有目录 `.local/live-validation/`。报告断言通过：14 个去重 Bug、5 个顺序组件、2 条本地证据关系、模块标记存在；所有远端与功能结果保持 `not_verified`。未把真实案例加入 fixtures，也未伪造 API 响应。
- 未执行现有 HTTP 远端查询：按 SECURITY 已请求明确确认；安全凭证注入方式、测试入口和环境/Stack/Service 范围待补充。
- 发现现有 `discover` 仅采集默认分支；指定部署 ref 需独立核对，不能以默认分支扫描结果冒充。
- 本轮没有产品代码或架构变化，不重跑离线测试替代真实验收；本地文档检查结果另记于下。
- `git diff --check` exit 0；`git check-ignore` 确认两个案例文件均被忽略；暂存前 `scripts/check_public_data.py` exit 0（暂存后另由提交钩子检查）。

## 真实案例只读验证接续（2026-11-02，Git 远端已验证）

- 读取用户填写的非密钥私有定位表：人工明确测试环境与 Endpoint/Stack；GitLab HTTP 只读已允许。平台 API 凭证未进入当前进程、聊天或文件。
- 首次 `git ls-remote` 在沙箱内网络失败；按环境要求申请沙箱外只读执行后成功，没有绕过网络权限。
- 对五个限定仓库查询指定远端 refs 全部 exit 0；两个用户明确指定的目标分支，均用真实远端 SHA 与本地已有 Git 对象证实包含相应远端 feature HEAD。没有 fetch、checkout、push 或触发 CI。
- 另记录默认分支与指定分支的差异，以及一个前端远端 HEAD 已不在本地对象库的情况：缺少对象时 ancestry 保留 `not_verified`，不把默认分支当作部署分支或伪称完成全部版本验证。
- 远端 SHA、来源实例指纹与本次时间戳仅存 gitignored 私有目录；未将真实名称、地址、ID 或版本写入公开报告。
- 为后续 API 证据准备私有本机运行入口：交互式 `getpass`；拒绝非终端和不隐藏输入的回退；凭证仅存在进程内。HTTP 逐平台确认；跨 GitLab origin 在传凭证前拒绝；GET 仅限 Bug 元数据、指定仓库/ref/pipeline 元数据及所选 Endpoint/Stack/Swarm 标签。
- 不获取图片、源码 raw、job trace 或 StackFile，不执行业务测试脚本、不调用构建/部署/审核/回调。运行报告 0600、目录 0700；错误和部分成功保留诊断，不标记功能通过。
- 本机入口的 9 项合成安全检查通过（unittest，0.006s）；表单路径/API 基址/目标选择器检查通过；私有脚本 ruff 通过。此结果独立于已验收的 133 项产品测试，不能充当真实 API 成功证据。
- 已向用户提供本机终端运行命令，等待其不回显输入只读 API 凭证。GitLab REST、ZenTao、Portainer、运行版本和业务功能仍为 `not_verified`。

## 首轮 API 实跑与失败诊断（2026-11-02，未通过）

- 用户完成本机输入后取得真实 API 报告：GitLab、Portainer 为 `NETWORK_UNAVAILABLE`；ZenTao 首个限定 Bug 返回 `AUTH_FAILED`，其余 Bug 按边界停止，全部功能与部署版本仍 `not_verified`。三平台 HTTP 均由用户在运行时明确授权。
- 凭证仅在已退出的用户进程中存在，未存文件，当前执行器不能恢复其值或自动重放认证请求。
- 在已授权执行器做不带凭证的 TCP 与 GET 诊断：三平台均 TCP connected；直连 GitLab 返回 JSON 404，ZenTao/Portainer 返回 JSON 401。对现有本机回环代理的无凭证对照结果相同。未读取响应正文、未发送任何认证信息；不能据此归因于代理，也不能把私有项目无凭证 404 当作项目不存在。
- 用户终端的首轮异常已被 Reader 归并为固定网络错误，原始异常不可恢复；因此网络失败根因尚未确定。未擅自切换代理、关闭 TLS、换认证头或升权。
- 补强私有入口：同一终端先对精确 API 路径做无凭证预检，连接失败时不再要求输入 Token；异常诊断仅记录固定类别、类型和 errno，不记录原始消息/URL/请求头/正文。去除凭证首尾空白并拒绝内部空白、控制字符与非 ASCII，未经证据不声称首轮失败由输入格式引起。
- 新增本地请求协议错误、超时、拒绝连接、权限拒绝、凭证输入、失败预检不获取凭证、预检 401 后正常认证等检查；私有 unittest 共 14 项通过，ruff 通过。没有修改产品代码，也没有用离线检查冒充真实通过。
- 官方 REST v1 认证说明核对：https://www.zentao.net/book/api/1397.html 及 https://www.zentao.net/book/api/664.html；当前路径和 `Token` 头符合说明，首轮 401 只能确认认证被拒绝，不能认定具体过期或权限原因。已询问用户凭证获取渠道，不索取值。
- 历史 API 报告保持原样；无凭证诊断存独立 `network-check` 报告，避免与认证 API 报告混淆。等待用户运行加强入口后继续定位；未执行任何业务写入。

## 第二轮 API 结果与 HTTP 修复（2026-11-02，部分验证）

- 真实 Portainer 认证成功，所选 Endpoint/Stack 的 Swarm ID 及实际 Namespace 标签一致；属于限定资源的 `observed_verified`，不代表服务副本健康、修复版本已部署或业务功能通过。原始资源标识与服务摘要仅保留在私有目录。
- GitLab 同终端无凭证预检有 JSON 响应，认证请求下层为 `DecodingError`；不再归咎于网络或 Token 可用性。用合成 gzip、deflate、嵌套编码与分页响应复现本地 Reader 重复解压缺陷：修复前 5 failed / 1 passed，修复后 6 passed。
- Reader 继续用解码后的正文执行大小上限，缓冲为 Response 前删除上游内容编码、内容长度与分块传输头，保留 MIME/分页头。坏压缩数据按 `INVALID_PAYLOAD` 失败且不重试，真正网络异常仍维持原有限重试。
- 用户说明禅道 Token 来自 v1 登录；官方源码示例返回 session_id()。具体部署版本/有效期未验证，不把 401 直接断定为过期，也不切换 v2。
- 唯一登录 POST 不再附带已有 Token：先用扩展的认证测试观察 1 failed，再修复至通过；现有不重试登录测试继续通过。私有入口新增一次现取 v1 Token 的本机账号/密码输入，不把秘密放进 argv、文件或报告；密码保留原有空格/Unicode。用户选择此模式并明确同意 HTTP 认证后才发送登录请求。
- 已支持只重试 GitLab/ZenTao，保留 Portainer 历史成功快照，不再次索取其凭证。合成检查覆盖登录 POST 后限定 GET、认证失败不重试、不读取 Bug、密码保真、无敏感报告及平台选择；私有 unittest 19 passed，ruff passed。
- 产品最终检查：139 passed（11.69s），0 failures/skipped；总体覆盖率 98.58%、行 99.19%、分支 96.66%；ruff、strict mypy（39 files）、git diff --check exit 0。摘要见 reports/http-encoding-summary.json；完整本次报告位于 gitignored 私有目录，历史基线报告未覆盖。
- 确认本机运行入口加载工作区修复后的 Reader。GitLab 修复后真实请求及 ZenTao 即时登录还需用户输入本机凭证；未伪称通过。业务页面、调度器、审核通过及回调均未执行。

## 第三轮 API 与真实元数据本地集成（2026-11-02，限定范围通过）

- 用户重跑选择 GitLab/ZenTao 的本机入口：GitLab 五个仓库的 project/ref/commit/有限 pipeline 元数据全部读取成功；两个用户明确目标分支的当前 SHA 流水线均 success。修复后的 Reader 已通过真实 REST 复验，无需更换 GitLab Token。
- ZenTao 一次 v1 登录后立刻读取十四个 Bug 全部成功；只记录字段白名单，不存 Token/密码。前轮 401 的确切失效原因与会话有效期仍不作断言。
- 保留上一轮 Portainer 成功快照；汇总分别列出两轮采集时间，不声称形成当前同步部署快照。三个前端仍只有默认分支观测；manual 和有限查询未命中当前 SHA 均不被当作部署失败或构建不存在。
- 在 gitignored 私有目录，以实际响应白名单元数据和用户案例期望分别建 Snapshot/Evidence；未经过 synthetic fixture 加载器，也未模拟 API 响应。来源实例/资源种类/外部 ID 分离；Bug→仓库只保留 candidate。
- 实跑 Catalog 两次导入：185 Entity / 213 Edge / 213 Evidence / 8 Snapshot，第二次元素数量不变。198 条直接观测、15 条 candidate，无自动 confirmed，证据引用有效。
- 真实 DCE CLI 子进程：两页 Bug 列表无重复；service trace 有观测关系；mapping verify 无缺失证据；stack inspect 保留 version_match=not_verified。五次 exit 0、未截断且满足默认输出预算。
- 私有案例报告和 JSON 汇总已更新；真实名称、ID、SHA、digest 和采集时间仅存私有区。公开结论见 live-readonly-report.md。此轮无产品代码变化，不以重复离线 pytest 冒充新的真实测试。
- 尚未执行完整 live discover、实际 Agent MCP Host、源码 commit→构建镜像→Service 指纹链、页面请求/调度器/审核/回调功能回归。未执行公司业务写入；原有本地工作分支继续保存脱敏记录。

## 第二阶段部署与页面验收启动（2026-11-03，进行中）

- 用户授权继续验收，限定原测试环境和五个组件；保持业务只读，未保存模板、审核通过、触发回调、构建或部署。
- 按 plugin-management 检查浏览器能力：发现未连接的云端工具，未找到适合本机内网窗口的已连接工具，不发起云端连接。采用已安装本机 computer-use/browser-use 技能；两次 doctor 均 ready=false、accessibility=false、screen_recording=true。未绕过缺失权限，已请求人工开启。
- 不带凭证 GET 指定业务入口：同源 301 后 200 HTML；记录正文摘要和同源静态资源路径，不保存 HTML、不访问图片。这不等于页面功能验收通过。
- 只在本机对已定位仓库的受限 CI/Dockerfile 做静态元数据分析，未执行其中脚本或读取 .env。三个前端声明 dist 构建产物；本轮所需 commit/revision 标记未观察到，未按名称补造版本关系。
- 准备私有第二阶段入口：GitLab job-ID 单文件产物与部署 JS/CSS 字节摘要比较；限定 ref/pipeline/job/逻辑请求数和解码后字节；不保存源码、不下载 archive/trace。作业 SHA 不一致不取产物，多 commit 同产物不声称唯一来源。
- 运行侧再校验用户目标 Endpoint/Stack/Swarm/Namespace；名称匹配仅候选。仅针对当前 endpoint Node 的任务容器取 Image/Health 白名单；不执行 exec、不跨未验证节点路由，不把远端服务与本机缓存镜像混为一谈。
- 新 13 项合成部署检查 passed（0.031s）；原私有入口 19 项检查 passed；ruff passed。原私有入口补充传播 not_verified，避免 API 内层失败被包装为通过；无产品代码更改，未重跑全库 pytest 充当新真实证据。
- 已提供需本机不回显输入 GitLab/Portainer 凭证的实际运行命令，等待部署证据报告；同时请求三个前端的人工部署分支。真实版本与业务结果继续 not_verified。脱敏进展见 phase2-readonly-progress.md，真实数据与代码仅在 gitignored 私有目录。

## 风险与边界

离线 P0 无未解决阻塞。三平台限定元数据及捕获数据的 Catalog/CLI 已验证；完整真实平台链路、部署/功能与实际 Agent 接入仍未完成。P1 递归 CI include、云模型 HTTP 插件和共享鉴权服务为后续扩展，不虚报完成。
