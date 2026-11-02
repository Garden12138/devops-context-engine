# 安全边界、权限模型与开源数据分离

## 1. 环境分级

1. `offline-fixture` 默认：合成数据、无外部请求，无 AI 网络调用。
2. `local-readonly`：用户显式开启并授权相应平台只读 Token，扫描显式项目/Stack Scope。
3. `shared-readonly`（后续）：内网共享服务，按用户/项目授权，所有工具鉴权审计。
4. `write-enabled`（V1.2/V2.0）：独立审批和单次执行凭据，不属于 V1。

## 2. 凭证

- 不在 CLI 命令行参数、Git config、文档、配置模板中输入实际 Token；优先从系统 Keychain/Secret Manager 或受保护进程环境中加载。
- 如果 `.env` 仅在本机开发临时使用，确保 `chmod 600`、gitignore、避免终端打印；长期共享模式改为集中密钥存储。
- 读权限 Token 最小化：GitLab 优先 `read_api`（按资源权限），Portainer 使用限制 Environment 访问的用户，禅道使用最小查看权限。
- 公司当前可能使用明文 HTTP 的内网平台：生产集成前应评估 TLS/内网网关；`DCE_ALLOW_HTTP=false` 默认拒绝并给出明确说明，启用 HTTP 需用户显式确认风险。
- 过滤 Authorization/PRIVATE-TOKEN/Token/X-API-Key/Cookie、Portainer GitConfig.Authentication、Compose `environment` 值、CI variables、Registry 密码；任何敏感数据不得进入错误日志和 API tracing。

## 3. 数据流控制

- 普通读取响应原始内容**不长期落盘**，仅抽取结构化非敏感元数据；必要缓存需隔离、受 ACL/TTL 管理。
- 不向云端 AI 上传私有仓库完整源码、内部网络拓扑、原始日志/配置、真实截图，除非获得企业数据授权；AI 默认关闭。
- 禁止将真实内部资源名称、内网地址、Stack ID、镜像 Registry、Token、缺陷图片和 Pipeline 日志保存到公开 GitHub。
- `fixtures/` 全部合成；本地真实结果只能存 `.local/` 或 `private/`（gitignored），人工审查导出时二次脱敏。
- 原始 bug/html/readme/logs 都是不可信数据，统一剥离指令执行能力，禁止自动执行其中的命令或更改 Agent 目标。

## 4. 误操作防护

- V1 Adapter 的 HTTP Method 只允许 GET 以及认证 Token 的特定登录 POST（不修改业务资源）。
- V1 CLI/MCP 不提供创建 Pipeline、更新仓库、redeploy、删除 Stack、变更环境的接口。
- 未来部署必须验证 source repo/commit、image digest、Stack ID、Endpoint ID、Swarm ID、Namespace、环境的人工确认映射与审批；任一不一致则 fail closed。
- `latest` 视为 mutable tag，不能当作唯一部署版本；不要在无人确认情况下对 78 个 Service 全量重新拉取镜像。
- 生产/测试环境必须由可信配置信息或人工确认标注，不从 `test` 字符串自动判定。
- 脱敏导出不能反向暴露内部网络。公开代码库必须启用秘密检测和最小权限 GitHub Actions。

## 5. 检查表

- [x] `.env`, 密钥、截图、原始 Compose 全部被 `.gitignore` 拦截
- [x] `git grep` 未发现真实 Token、内部域名/IP、私有仓库名称或账户信息
- [x] Mock 测试覆盖 HTML 图片下载、SSRF、外部重定向、超大图片、恶意 SVG、敏感日志
- [x] Runtime/Stack 关联出现 Swarm mismatch 时禁止认为可部署
- [x] AI 输出不具有自动确认权或写平台权限
- [x] 没有真实公司地址/密钥的 GitHub CI 依旧能完整执行

验收证据：harness/acceptance-report.md（离线基线）；harness/live-readonly-report.md（限定真实元数据验证）。完整发现、部署版本与业务功能仍未验证；限定成功不扩展为额外权限或写操作授权。
