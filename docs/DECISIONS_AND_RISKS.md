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

固定请求源，禁重定向；唯一认证 POST 不重试；429/网关故障和网络错误有限重试。
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

## 风险登记

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
