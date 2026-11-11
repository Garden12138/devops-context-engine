# 决策记录（ADR）与风险清单

## ADR-001：先做可验证服务目录，不先做自动部署

原因：初次研究已发现相同 GitOps 仓库与文件对应多个历史/current Stack；自动部署前若只凭名称推断极易选错环境。V1 仅 read-only。

## ADR-002：SQLite + Edge 表，而不是立即 Neo4j

原因：单用户初期需求和数据量可控，关系和证据可用关系数据库表达；后续增长才考虑图数据库。

## ADR-003：AI 不能作为唯一可信来源

原因：业务语义与源码名称可能高度相关却不真实对应；直接技术证据和人工确认必须独立存在。

## ADR-004：同时存 Git current、Portainer saved、Swarm runtime 三种快照

原因：用户实际环境中三者可能不同步；配置声明 != 已部署事实。

## ADR-005：CLI/MCP 共用业务内核

原因：减少维护成本；让 Codex/Cursor 与 Grok Bot 不必实现两套映射。MCP v1 不对外暴露写操作。

## ADR-006：T0 工具链与配置输入

选择 Python 3.12、uv.lock、ruff、strict mypy、pytest（含分支覆盖率）。
配置优先级 CLI > 环境 > 显式 TOML；不隐式加载 .env，不接受文件内凭证。
原因：避免默认扫描读取本地秘密；环境错误仅返回固定诊断，避免验证器原样输出凭证。
HTTP 需要显式放行；所有 live 操作仍须 --live --read-only 与后续范围约束。

## ADR-007：只读 HTTP 与图片缓存

固定请求源，禁重定向；唯一认证 POST 不附带旧 Token、不重试；429/网关故障和网络错误有限重试。
GitConfig 只留声明字段并清除 URL 凭证/查询；StackFile 和原始 trace 仅供内存解析。
图片缓存使用来源实例+资源引用标识、内容 SHA256、私有目录与原子写。
所有平台兼容性以本地 Mock HTTP 契约证明，真实 API 单独标记 not_verified。

## ADR-008：静态解析与恢复边界

不执行 YAML、CI、Dockerfile 或模块脚本；无法静态解析的值为 incomplete。
扫描以 commit 固定仓库读取，缓存只存规范化白名单；重启复用已完成资源，变化版本重读。
三种部署快照独立保留；只有来源、仓库路径、ref、配置路径匹配才比较声明。
Namespace 标签与 Endpoint/Swarm ID 同时验证；不由名称判断环境或部署版本。

## ADR-009：Catalog 审核状态与扫描观测分离

使用 SQLAlchemy + SQLite 与打包 Alembic 前向迁移；人工决定独立于 observed_status。
所有变更保留历史和 Audit；不可变快照冲突回滚整个批次，ScanRun 单独保留失败记录。
Entity/Edge 记录各 scope 活跃成员，来源消失不误删其他范围资源；人工确认保留但标明 stale/conflict。
不支持破坏性 schema downgrade；恢复使用本地备份，V1 不做任何远端操作。

## ADR-010：AI 候选与人工审核权限分离

默认关闭，provider 可注入；只传 UUID/受控类型/证据 ID，禁止原始私有文本。
结果严格 schema 校验且仅候选；有限超时不自动无限重试，失败可追溯并不影响规则。
CLI 审核要求 actor/reason/期望版本，环境另行确认；MCP 不暴露审核 API。

## ADR-011：CLI 与工具共享应用服务

AppServices 统一 scope、BugContext、Pipeline、Stack 和图查询；入口只处理参数、格式和错误。
固定 JSON envelope，UTF-8 字节上限保守控制 token；附件只返回私有缓存路径/受控引用。
默认 fixture；真实扫描需显式 live/read_only 与 scope，所有平台请求仍只读。

## ADR-012：MCP 协议与资源授权

使用 SDK 低层 Server，统一参数校验失败为固定 error_code；stdio stdout 仅协议帧。
六工具共用服务层，无审核/写工具；structuredContent 不重复大文本。
附件引用仅在当前会话注册，读取重新验证路径/大小/指纹；live 上游访问需显式 allowlist。

## ADR-013：离线完成与真实平台核验分离

以合成 HTTP、真实 CLI/MCP 子进程、迁移及独立 wheel 安装证明离线 P0。
不把 Mock 的成功等同公司接口/部署事实；没有真实证据的范围与 Agent 执行器明确 not_verified。已取得的限定真实证据单列来源、时间和边界，不扩展为完整部署或业务验收。
覆盖率区分行、纯分支与组合总体；报告移除框架自动写入的本机主机名。
暂存区与历史扫描不读取凭证文件；许可证/公开发布按所有者另行授权，不自动发布。

部署产物验收把实际资源字节相等记录为观测证据；同一产物可能对应多个 commit，不能自动推定唯一来源。名称候选、远端节点未核验和缺失 GUI 权限各自保持不确定状态，不扩大为业务功能通过。

用户给出的业务 Bug 仅用于提供真实 DCE 输入。V1 验收不包含业务系统页面点击、修复回归、审核/回调或发布执行，也不以 GUI 权限作为门槛。临时核验脚本的额外观察与产品已实现能力分开，未实跑的产品路径保留 not_verified。

## ADR-014：缓冲解码后的 HTTP 响应，不重复应用传输编码

真实验证暴露出 `DecodingError` 被归为网络错误的诊断缺口。Reader 已通过 `iter_bytes()` 解码响应，缓冲后的 Response 必须移除原始内容编码、长度与分块传输头，保留 MIME/分页头；大小上限继续约束解码后的正文。损坏编码属于 `INVALID_PAYLOAD`，不应按网络异常重复请求。修复用合成压缩字节流回归证明，不将合成通过替代真实平台复验，不关闭压缩、代理或 TLS 防护来掩盖问题。

## ADR-015：Cursor 由本地 stdio 管理进程，真实 Catalog 与演示数据分离

Cursor 使用 DCE 虚拟环境入口和 Catalog 的绝对路径启动子进程，不假定宿主的 PATH、工作目录或交互终端；V1 不新增监听端口或后台网络服务。
无常驻上游凭证时，接入已授权真实元数据的独立 Catalog 副本，显式 `--live --read-only` 并保持 Bug/Project allowlist 为空。四类 Catalog 工具读取保存快照，另外两类返回 PERMISSION_DENIED，不以合成 Bug/流水线替代真实结果。六个工具可见不代表六类真实上游访问均已启用。
Cursor 配置不包含凭证、envFile 或 HTTP 放行；实时读取需另行提供受保护的进程环境与明确范围。禅道会话失效须安全重新认证，不能承诺自动续期。
标准 SDK 检查只输出状态/计数，不输出内部名称、资源 ID、工具正文或原始错误；缺失库、协议错误、预算超限、读取改变数量应失败。SDK 握手与 Cursor 实际激活分别记录，不能互相替代。

## ADR-016：MCP 必须通过发布契约说明能力与当前会话条件

Cursor 的真实能力检查暴露描述模板化、无业务 data Schema、互斥参数只在运行时检查的问题。保持六个只读工具，独立定义输入/输出模型并发布完整 envelope、错误及截断约束；部署的两种结果分支均建模，未知动态平台字段只允许出现在 attributes/summary 等显式元数据容器。
描述明确平台/来源，`_meta.dce` 提供 contract_revision=1.1 和配置可判定的 availability/blockers；枚举时不调用平台、不泄露地址/凭证/allowlist ID。配置就绪用 configured_not_verified，不声称认证已通过。Catalog 数据是否真实及是否过期由证据判断，不能由 live 标志或 ready 推断。
响应 snapshot_at 的旧命名保留兼容，公开其生成时间语义；部署快照添加已有 observed_at。无实时 Portainer 查询、健康或版本验证时保留 unknown/unresolved/not_verified，不通过描述扩张产品能力。Schema 用真实服务返回的成功/错误/截断正反例及 SDK stdio 验证，仍与实际宿主缓存、业务调用及平台验收分别记录。

## 当前风险登记

| ID | 风险 | 后果 | 缓解 |
|---|---|---|---|
| R1 | 越权读取内部项目 | 数据泄露 | 最小权限、扫描 Scope、审计、禁自动遍历全部项目 |
| R2 | 真实凭证入 git | 严重安全事故 | .gitignore、secret scan、外部 Keychain、合成 fixtures |
| R3 | 历史 Stack 被判定当前环境 | 错误部署 | Endpoint/Swarm ID/Namespace 检查 + 人工环境确认 |
| R4 | `latest` 镜像版本不明确 | 错误回滚/误判 | digest/SHA 对应关系；缺失则 uncertain |
| R5 | AI 幻觉建立项目关系 | 修改错误仓库 | 证据分级、候选复核、禁止自动批准 |
| R6 | YAML/CI 动态配置难解析 | 漏掉构建模块 | 标注 incomplete、能力边界和人工补充 |
| R7 | AI prompt injection | 执行不可信命令 | 输入白名单、tool-only 许可、不可执行外部文本 |
| R8 | 外部云模型传输内网数据 | 合规与隐私问题 | 默认 AI off、本地模型优先、按数据策略批准 |
| R9 | Portainer/ZenTao 版本差异 | 接口异常 | Probe/Capability matrix、fixture contract、错误码 |
| R10 | 长任务 Agent 中断 | 半成品和误报完成 | 阶段小提交、build-log、复跑提示词、离线测试 |
| R11 | 显式 HTTP 内网 API | Token 泄露风险 | 网络隔离、TLS 优先、allow_http 显式风险接受 |

## ADR-017：Agent-led 能力路径与旧语义 Mapping 解耦

默认 initialize/discover 只抽取来源文件可验证的事实，Module→CI 显式路径匹配独立为 technical_facts；不调用 MappingService 或任何模型。bug_context 不再按 fixture 临时生成语义映射。旧六工具仍可读取历史图，旧 mapping suggest/review 与 init --legacy-mapping 显式兼容；不把旧库当项目关系真相。Host Agent 负责当前 workspace 推理与人类审核。

## ADR-018：有范围的事实查询与原生图片交付

保留旧六工具，新增 zentao_query/gitlab_query/portainer_query，参数由各自 Schema 枚举，instance 与启动 allowlist 双重限制；查询不触达 Mapping/Catalog。项目/产品搜索只访问允许 ID，不全公司枚举；Tree/Jobs/Pipeline 单页，日志尾部、文件行窗口、输出遗漏明确。Stack File 只返回 Compose 事实，Swarm Service 不返回 Container Env/Registry Auth，Stack/Swarm 来源分开。
图片从已授权 Bug 取得同源附件，经 MIME/magic 与大小限制后直接在内存返回 MCP ImageContent；预算不足标 not_delivered，不缓存真实图片。旧 Resource 交付保留兼容。
禅道 v1 官方资料未核实完整模块列表路由；modules 返回指定项目/产品 Bug 页实际 module 字段，强制 PARTIAL_MODULE_INVENTORY_FROM_BUG_PAGE，不宣称完整模块目录或已在真实实例验证。
路由依据：[GitLab Repositories API](https://docs.gitlab.com/api/repositories/)、[禅道 v1 配置](https://www.zentao.net/book/api/1397.html)、[Portainer API](https://docs.portainer.io/api/access)。文档支持路由设计，不证明实际实例兼容或权限。

## ADR-019：项目关系契约与纯刷新

schema_version=1 的 project.yaml 由 Host 写入，DCE 提供 Schema、模板 stdout、指定工作区只读校验和纯 refresh 函数。节点强制 type/instance/id；示例 implemented_by 与关系枚举均兼容。confirmed 需非空证据、带时区人工审批，已知 Agent 身份不能审批；文件元数据无法认证真实人类身份，Host 必须以真实用户对话为准。
拒绝重复 YAML key、alias/anchor、超限、不安全路径、secret key/value、带凭证 URL、跨 instance/scope。刷新保留审批/备注/拒绝，新关系 proposed；来源变化 stale/冲突 conflicted，DCE 不写业务目录。JSON Schema 与运行时校验同时发布，安全和来源范围的交叉字段约束以运行时校验为准。

## ADR-020：备份后降级全局关系权威

旧库升级 head 前先 SQLite backup/quick_check，失败不迁移；0003 只新增角色元数据，保留所有旧实体、边、证据、审批及历史，不导入业务 workspace。备份 0700/0600，拒绝 symlink，限定执行时长。0001 固定历史表清单，防止引用最新 metadata 使未来表提前创建。旧工具/CLI 兼容，本轮不删除；真实库需显式指定且停止同库旧进程后迁移。Host 使用旧图只做历史取证，必须当前项目重新审核。

## ADR-021：按已核对的 v1 模块入口补齐产品模块树

官方 apiv1.php 明确注册 /modules，entries/modules.php 的 GET 以 type/id 读取模块树；tree/model.php 的 getProductStructure/getDataStructure 返回对象及 children。原先 config/routes.php 404 不代表当前源码没有模块入口。此结论来自官方公开源码，不是公司实例成功证据。

新增 zentao_query(module_tree)，仅允许明确授权 Product ID 和 bug/story/case/product 类型；Project/Execution ID 不可替代 Product ID，任务模块不开放。旧 modules 的 Bug 页部分清单保持兼容。树只保留实际节点字段和层级父 ID，先搜索再本地分页，限制节点数/深度/上游字节；畸形、重复、越 root 和不支持接口安全失败，绝不静默回退后声称完整。DCE 不做业务关系推断。

依据：[官方 v1 路由](https://github.com/easysoft/zentaopms/blob/main/config/apiv1.php)、[GET 参数/返回](https://github.com/easysoft/zentaopms/blob/main/api/v1/entries/modules.php)、[树结构](https://github.com/easysoft/zentaopms/blob/main/module/tree/model.php)。实际版本/权限仍 not_verified，需取得授权配置后实测。


## ADR-022：用户明确凭证源时显式加载，保留默认无 dotenv

用户恢复接续后明确凭证位于本机 .env，禅道需 v1 账号密码换 Token。独立本地 MCP 入口处理该输入，默认 CLI/Settings 不自动读取 dotenv；环境通过参数注入，不修改父进程。解析器不 source/执行/插值，严格文件模式/体积/重复/别名检查；账号密码、Token 和三平台 URL 别名映射至 DCE 字段。显式进程配置优先于本机文件与 TOML，允许用实际观察到的同源应用入口修正安装包欢迎页地址；不自动推测 API 路径。v1 认证仅启动时一次，不附旧 Token，不重试密码，不持久化临时 Token，失败固定诊断保持 stdout 协议纯净。公开记录不含真实路径、资源名称或凭证，业务根目录画像和候选项目文档只保留私有区。连接地址缺失不能从凭证猜测，需要非秘密配置。

## ADR-023：文本 Host 兼容与显式原生图片预算

真实 Cursor Agent 已能枚举九工具并发起三平台调用，但只看见 DCE result.，无法消费 structuredContent 中的事实。九工具统一在 TextContent 返回相同的序列化 JSON，兼容只消费文本的 Host；Schema、名称和只读边界保持不变。按实际 UTF-8 ToolResult body 同时计量两份 JSON 与转义，超限明确遗漏，大 Catalog 查询需适当提高预算或缩小范围。

真实授权图片超过旧 64KB 总预算。新增可选 image_output_budget（默认 null，最大 3MB），只在显式配置后用于原生图片总响应；文本/结构化元数据仍受 output_budget 限制，Reader 的 2MB 原图上限不变。Base64 不进入 JSON 文本、不自动缩图、不落盘、不扩大 Bug scope。合成与真实 SDK 均验证；SDK 收到图片不等于真实 Host 模型看见，验收仍分别记录。

## ADR-024：增量 Job/单服务事实与显式项目 Schema v2

保留原 Pipeline jobs 与九工具名称，新增 Project/Branch Job 和触发 Job 单页读取；Branch 是本地精确过滤，分页保持上游坐标，空页明确不能证明没有构建。下游标识返回 Host，DCE 不递归扩 scope、不执行业务推理。单 Compose Service 在服务端选择后解析/预算；安全字段白名单和输入上限保留，畸形环境条目/Job 嵌套字段不允许夹带敏感配置。

项目 v1 默认行为/读取与静态 Schema 保留，新概念显式使用 v2 typed details。CI 定义/执行、tag/digest、保存定义/运行观察与环境/版本比较独立，不能由分支名或 latest 推断确认。迁移是纯函数/CLI stdout 预览，不重新解释旧节点，不修改业务文件，审批/证据/状态/备注语义保持。实际项目当前 24 proposed/3 unresolved/1 confirmed 在本轮按内容指纹保护。详细边界和验证见 docs/AGENT_LED_INCREMENTAL_V1.md 与 harness/incremental-v1-acceptance.md。


## ADR-025：限定服务日志采用独立授权、有界流和固定词汇投影

元数据只读范围不自动授予日志权限；新增 endpoint:stack 日志 pair，仍同时要求原 allowlist。先比对 Stack/Endpoint/当前 Swarm、Service 实际 ID 和 namespace label，再通过 Portainer Docker proxy GET 日志，最后复核版本。没有 Docker Socket、SSH、写 API 或新服务。

官方服务日志没有 until/关键词过滤，因此使用 since + finite tail，再在原始 payload 上限和 asyncio 总截止时间内有限过滤；拒绝 follow、压缩和不支持的必要参数，不重试日志 GET。解析 Docker stdcopy、Task context、纳秒时间、UTF-8、TTY 与 Systemerr。tail、读取中断、未知保留期和真正已读无匹配分别表达，不能由空结果推断过期或权限。

任意文本的正则脱敏不能保证移除个人信息；默认完全省略自由文本，只输出固定事件词汇、常见异常、HTTP 状态和进程内随机密钥 HMAC 关联摘要。日志内容永远没有指令权。错误仅 service_logs 可携带查询上下文，其他操作保持原契约；双份 MCP 输出裁剪后重新计算 revision。Project Schema V2、九工具、Host 推理职责保持。

版本 1.1.0 / Portainer 契约 2.2；323 合成测试通过，97.63%，真实日志 not_verified。详细约束、官方来源和权限缺口见 [Scoped Service Logs](SCOPED_SERVICE_LOGS.md) 与 [验收](../harness/service-logs-v1.1-acceptance.md)。

## ADR-026：禅道v1认证恢复采用懒登录、single-flight及失败熔断

本地scope拒绝必须发生在网络和登录之前；不能将权限错误当作失效而扩大allowlist。复用显式本地凭证加载，进程内Manager绑定同一instance/base_url，首次授权GET再登录；不增加凭证来源、磁盘Token或猜测TTL。锁与generation使并发失效共享一次登录，迟到旧请求不能覆盖新Token。仅严格401/403 JSON失效信号允许重放同一路径/参数GET一次；普通403、网络、HTML和跳转不用于推测过期。登录POST不重试，失败及刷新后仍失效锁存到重启，降低账号锁定风险。

外部MCP错误枚举/结构保持，AUTH_EXPIRED、AUTH_REFRESH_FAILED通过固定错误message区分；网络外部code仍NETWORK_UNAVAILABLE。禅道传输诊断整体省略，避免未知Set-Cookie泄漏；本次使用的两代Token与账号密码参与业务输出脱敏，Cookie不带入GET。Settings私有属性不序列化Manager，deep copy共享同一连接锁。默认直接Token模式保持但无密码时无法刷新。

完整合成357通过、97.62%；真实单个既有授权资源的登录/缓存/独立进程读取通过；真实过期恢复、真实并发及Cursor实际重载后调用不冒充已验证。见 [契约](ZENTAO_AUTH_RECOVERY.md) 与 [验收](../harness/zentao-auth-v1.1.1-acceptance.md)。

## ADR-027：Host启动要求与请求身份使用既有MCP协议

同名MCP的多个窗口/配置指纹可能引用不同启动定义；包版本/PID存活不足以证明当前Agent的工具调用进入正确连接。保留显式凭证入口，以--require-platform在STDIO前验证所需连接存在，不新增凭证源或授权，也不改变合法单平台/旧Catalog入口。日志grant由CLI与本地入口共用校验，能力发现独立于权限。

使用既有初始化serverInfo.version及Tool/CallToolResult._meta追加运行版本/PID/公开输入Schema摘要/平台类别，不新增查询工具或业务字段。预算不足时先省略可选诊断，再执行原有数据/图片裁剪；不挤占原本可返回的结果。仅本地入口启用固定stderr审计，既有request_id将调用关联到进程，不记录参数、上游正文、URL或scope值。历史无审计不推造逐调用归属；独立STDIO、桌面重载、真实Agent调用分别验收。

用户级仅改dce条目，先私有备份，保留其他MCP与全部授权；不通过全局杀进程或反复临时改配置代替目标窗口重载。实际桌面复验保留外部边界。详见[契约](CURSOR_HOST_V1_1_1.md)及[验收](../harness/cursor-host-v1.1.1-acceptance.md)。

2026-11-08收尾：用户确认Gate A PASS；检查发现旧PID来自Host缓存的INSTRUCTIONS.md。握手说明改为仅保留稳定Schema摘要及实时身份查验方法，避免缓存文件声称当前PID；Tool/Result实时元数据和request_id审计不变，DCE不持久化或回读该PID。跨进程/同Catalog回归保证说明稳定、实时身份更新。Gate B仍not_verified，权限边界不变。

## ADR-028：Gate B采用精确身份与持久单次标记的临时日志策略

原Endpoint:Stack日志grant覆盖整个Stack，不能满足单服务一次性授权。保留兼容参数，两个启动入口追加可选的绝对路径策略，要求日志pair与策略pair恰好一致。策略固定来源实例、Stack/Endpoint、namespace/Swarm及完整Service ID/名称；Compose key和ID两种输入都在远程请求前校验，远端元数据必须再次完整匹配。其他工具、平台scope、凭证源、MCP九工具及业务Project Schema不变。

每次检查私有文件、摘要、TTL及消费标记；日志GET之前通过O_EXCL原子预占共享额度，跨进程/重启最多一次派发尝试，失败/取消不返还。撤销文件使旧进程后续调用拒绝；本地有权限的管理员仍可管理文件，这不是跨主机授权服务。最长300秒滚动窗口在派发前再次求交集，整数since向内取整，有限行数/字节/超时及既有脱敏摘要保持。完整格式、失败处理和撤销顺序见[预检契约](GATE_B_PREFLIGHT.md)。

本轮仅配置及预检：426项回归通过，97.24%，ruff/strict mypy55文件通过。真实调用限目标元数据GET与STDIO初始化/枚举；真实service_logs为0，Gate A不重跑，不能将READY写成Gate B PASS。真实策略、用户配置备份与READY报告均保持在忽略的本地受保护目录，不提交。

2026-11-09最终验收：后续独立授权执行阶段已完成真实日志GET1次、6条脱敏事件，truncated明确，Gate B PASS；临时授权REVOKED，未发现越权或敏感泄露。早期预检的0次记录保持当时事实。正式收尾426项回归通过，禅道真实Token过期恢复仍not_verified；见[最终脱敏摘要](../harness/v1.1-final-acceptance.md)。没有将策略、实际身份或日志纳入Git。

## ADR-029：公开候选从已审核基线重建快照，保留原验收分支

仅在旧分支HEAD删除真实样本，不能消除祖先中的原文。独立候选以已检查的main为父提交，导入完整可运行快照，对资料包README、两份关联提示词、验收说明和历史凭证入口记录做泛化；不在公开文档复述实际业务身份或凭证文件操作观察。原本地验收分支及私有证据不重写，已公开旧feature历史不自动处理。

功能源码、测试、Schema和锁定依赖保持逐字节一致，候选在独立环境重跑426项回归。公开审核覆盖候选的全部可达历史，不以增量扫描或普通秘密检测代替人工内容审查。新候选是不同的发布提交，须以新的SHA和范围审核后再推送；不自动创建PR、Tag或Release，不修改main。


## ADR-030：本地产品分支由干净快照整合

本轮选择main 078962e为不可变基线（无Tag），功能来源2748c7b独立干净候选。逐字节核对运行代码/测试/Schema/锁后从main创建临时分支导入快照，不merge旧38个开发提交，避免重新引入旧敏感祖先。main、所有Tag、独立候选分支及现有worktree保留。旧开发分支删除前核对祖先/差异并制作仅本机0600 bundle及恢复验证；不删除远端引用，不把私有备份提交。无法判断独有代码时保留该分支。

为遵守AGENTS要求，实施前创建本地临时分支，小批次提交；交付完成后再最终命名feature/upgrade-chatgpt及清理旧分支。报告执行HEAD和后续保存报告的HEAD分别标注，用实现摘要核对被测代码，避免自引用提交哈希。

## ADR-031：本地验收使用新证据和独立安装

统一runner清除DCE/业务凭证及代理环境，Python子进程限制loopback，uv命令强制offline。每次新临时目录，JUnit/coverage缺失或损坏失败闭合，失败/跳过不标PASS，命令超时终止进程组。分类来自本次完整测试集，可重叠不相加；人工Host/真实平台项始终分开。

隔离依赖安装直接消费uv.lock并指定独立UV_PROJECT_ENVIRONMENT；不依赖可能缺少的requirements解析索引，不复制现有site-packages。新Wheel装入后从源码目录外验证CLI与STDIO，断言dce导入路径在新venv内。当前包仍1.1.1，Schema/授权不因产品整理改变。首次联网准备缓存与本轮完全离线验收分开；其他Python版本未执行不宣称通过。
