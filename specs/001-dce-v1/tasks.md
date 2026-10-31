# DCE V1.0 — 实施任务（Tasks）

> 此清单是执行来源，与 `PLANS.md` 的 T0→T7 阶段保持同步。每项包含验收证据，Code Agent 不得用“已写代码”代替实际测试。

## T0 项目基座

- [ ] T0.1 创建 `pyproject.toml`、`src/dce` 可安装包、`dce --help` CLI。
- [ ] T0.2 配置 `pytest`、`ruff`、类型检查、提交检查（无私有数据）、依赖锁、GitHub Actions 纯离线 CI。
- [ ] T0.3 设计 Pydantic Settings、配置优先级（CLI > env > 配置文件）、`.env.example` 和日志脱敏。
- [ ] T0.4 `doctor --mock`、统一错误码与退出码；测试空 Token、HTTP 未授权等行为。

## T1 三平台只读 Adapter

- [ ] T1.1 ZenTao v1 bug/project/product/attachment 只读：Token 头、内嵌图片认证下载、HTML 纯化、图片 MIME/magic 验证、域名限制；测试有图 `files=[]`。
- [ ] T1.2 GitLab 项目列表分页、Repo Tree/Raw File、Commit、Pipeline/Jobs/Trace，支持自定义分页和 ref。
- [ ] T1.3 Portainer Stacks、StackFile/GitConfig 脱敏、Endpoints/Docker Info/Services，服务标签筛选；空 Namespace 时也正常。
- [ ] T1.4 为每个 Adapter 记录能力探测、版本差异、429/5xx 重试和权限错误，使用本地 Mock HTTP 测试。

## T2 资源发现/解析

- [ ] T2.1 Scopes/scan-run/checkpoints 与速率/分页控制；分页大仓库只读取相关文件路径。
- [ ] T2.2 Maven/Gradle/Go/Node 模块检测；Dockerfile/CI 脚本静态分析，不执行 build。
- [ ] T2.3 解析 GitLab 部署库 Compose Service/Image/环境变量**名称**、image digest/Mutable tag；不同镜像引用去重。
- [ ] T2.4 Portainer Stack GitConfig current ref/StackFile 快照/Swarm Service 快照三方差异；SwarmId 不匹配标记 stale_candidate。
- [ ] T2.5 支持一镜像对多服务、项目包含多模块、一个服务由多模块协同构建等情况。

## T3 Catalog 持久化

- [ ] T3.1 Entity/Edge/Evidence/Snapshot/ScanRun/Review/Audit 基础表、迁移脚本。
- [ ] T3.2 幂等 upsert、唯一键、版本历史、时间维度、软删除。
- [ ] T3.3 已确认映射不被下一次扫描覆盖；检测过期、来源消失与冲突。
- [ ] T3.4 目录查询与服务追踪（正向及反向）。

## T4 Mapping + AI + 人工审核

- [ ] T4.1 证据优先级规则及候选分数，输出证据链与适用版本。
- [ ] T4.2 可配置 AI Provider / Fake Provider，仅发送脱敏白名单摘要；schema 校验，不合规则回退规则结果。
- [ ] T4.3 review accept/reject/override，显式记录 actor/reason；`confirmed` 不允许 AI 自决。
- [ ] T4.4 不确定的业务/源码关系展示多个候选与 `unresolved`，不得阻止已确定技术边形成。

## T5 CLI

- [ ] T5.1 `dce doctor`, `init`, `discover`, `catalog`, `trace`, `mapping suggest/review/verify`。
- [ ] T5.2 `dce bug context`, `pipeline diagnose`, `stack inspect`，支持 `--format json|table` 和输出截断标记。
- [ ] T5.3 安全错误、stderr 日志、非交互 JSON 模式、退出码与帮助文本；参数不接受任意 URL 以防 SSRF。

## T6 MCP

- [ ] T6.1 6 个只读 MCP Tools；schema 明确、结构化输出小于预算，错误分级。
- [ ] T6.2 `stdio` 服务与 CLI 相同 AppServices；`stdout` 无多余文本。
- [ ] T6.3 MCP Inspector 或 Python 客户端离线测试；README 添加 Cursor 连接示例，说明 Grok Bot 是否支持需实测。

## T7 验收

- [ ] T7.1 合成 3 Stack/1 current Swarm/71 vs 78 service/78 current service/5 shared images 的 fixtures。
- [ ] T7.2 模块-镜像-服务多对多、CLI bug context、图片返回 HTML/PNG、CI failure、mapping approval 情况的 E2E。
- [ ] T7.3 运行 `pytest`, lint, typecheck，输出测试报告与覆盖率，修复失败。
- [ ] T7.4 写 `docs/OPERATIONS.md` 的安装、Mock 演示、真实内网只读验收、常见错误、回滚/删除本地数据方法。
- [ ] T7.5 `git diff --check`, 查找 secrets/内网地址、License 和 GitHub 初始化审查；填写 `harness/build-log.md`。

## V1 完成后才讨论的事项

V1.1：Agent MCP 操作体验、摘要压缩；V1.2：CI/MR 构建与任务记录；V2：审核部署/回滚/禅道回写。新需求开新 Spec，不在 T0–T7 偷做。
