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

## 风险登记

## ADR-006：T0 工具链与配置输入

选择 Python 3.12、uv.lock、ruff、strict mypy、pytest（含分支覆盖率）。
配置优先级 CLI > 环境 > 显式 TOML；不隐式加载 .env，不接受文件内凭证。
原因：避免默认扫描读取本地秘密；环境错误仅返回固定诊断，避免验证器原样输出凭证。
HTTP 需要显式放行；所有 live 操作仍须 --live --read-only 与后续范围约束。

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
