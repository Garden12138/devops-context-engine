# Agent-led initialization T0 audit — 2026-11-04

基线 commit: 6fd0a90；本地分支 refactor/agent-led-project-init。工作树初始仅有用户提供的未跟踪重构规格；未删除代码。提案实际位置为 docs/refactor/agent-led-initialization/dce-agent-led-refactor/，根层路径不存在；以实际提案和 specs/01–07 为准。

## 真实六工具（revision 1.1）

全部注册于 src/dce/mcp/contracts.py，运行于 mcp/server.py；严格输入、显式输出 envelope/error/truncation Schema，stdio/readOnlyHint，未暴露写工具。

| 名称 | 参数 | 实现 / 输出 | 测试 |
|---|---|---|---|
| bug_context | bug_id, include_assets=false | AppServices.bug_context；ZenTao live 或 fixture，BugData；隐式查询全局模块映射；图片仅 dce:// Resource | test_mcp*, test_services, test_connector* |
| project_context | source, project_key, depth=2 | Catalog source-instance 查 repository/business_project 与 graph；ProjectData | test_mcp*, test_services |
| service_trace | service_key, direction=both, max_depth=2 | 全局 Catalog trace；TraceData | test_mcp*, test_catalog* |
| pipeline_diagnose | project_key, pipeline_id | GitLab project/pipeline/jobs/失败 trace；PipelineData；存在 missing_make 硬编码诊断 | test_mcp*, test_services |
| deployment_inspect | stack_key 或 service_key（互斥） | Catalog Stack snapshots/trace，health unknown/environment unresolved/version not_verified | test_mcp*, test_services |
| discovery_status | scan_id 可选 | Catalog scan history/pending reviews；DiscoveryData | test_mcp*, test_services |

## Adapter / 缺口

- Reader：GET 与特定禅道认证 POST，禁止重定向/越源，超时、2MB 解压后限额、有限重试、分页、脱敏日志；保留。当前分页 iterator 不适合单页 MCP 查询，补有界单页接口。
- ZenTao：projects/products 列表/详情、范围 Bug、Bug HTML/附件源解析、认证图片下载 MIME+magic、0700/0600 缓存；缺 modules、独立附件查询和 MCP ImageContent。
- GitLab：projects/group/projects、project、recursive tree、ref file、commit、pipelines、pipeline、jobs、trace 均已有；缺 MCP 直接入口、单页/path/ref/tail 控制。
- Portainer：stacks/stack/file、endpoints、docker_info、namespace services 已有；缺 MCP 直接入口与 service detail。safe_stack 已去 GitConfig.Authentication；服务原文含 env，直接输出前必须白名单过滤。Stack File 默认只出确定性解析摘要。
- 所有缺口的新接口先合成 HTTP 契约测试；版本依赖真实调用前均 not_verified，不把文档路由当作真实权限成功。

## 关系引擎、AI、Catalog

- graph/rules.suggestions：镜像引用等技术事实与 business/module 名称语义候选混合。
- app/services.initialize/discover 隐式调用 MappingService.suggest；bug_context._bug_modules 还会 fixture fallback suggestions。必须从默认核心移出；旧命令显式兼容。
- app/mapping + ai/provider：候选验证、Provider 超时、人工审核；无真实模型实现，已有 Fake/Noop；保留历史兼容，但默认能力层不调用。
- Catalog SQLite schema v2：entities/edges/evidence/snapshots/scans/approvals/audit/history/members，带迁移和人工状态保护；不可删除。先 SQLite backup，再标记 resource_cache_and_history，旧 graph 返回保留状态且声明历史，不自动导入任何业务 workspace。
- 当前已有真实证据仅覆盖旧版限定元数据；Cursor 启动和 SDK stdio 不等于 Host Agent 调用。真实图片/新版 modules/trace/Stack File/真实 Host 初始化仍 not_verified。

## 新边界、失败处理、测试契约（实现前）

1. 新事实查询直接 Adapter，不依赖 Catalog/Mapping/模型；显式 instance 和启动 allowlist，跨项目 fail closed；只读 scope 搜索不全公司枚举。保留旧六名称、参数、输出兼容并标历史。
2. 单页结构返回 source/observed_at/revision/pagination/truncated/warnings/evidence，错误复用 DceError，预算遗漏必须显式；来源资源文本永远 untrusted。
3. 图片通过当前 Bug 范围内来源、认证、MIME/magic、完整性后返回 ImageContent；未交付必须明示。离线传输成功不能冒充真实 Bug 图片已达模型。
4. project.yaml 仅纯 Schema/读取校验/refresh 计算/模板 stdout；DCE 不写业务工作区。节点需 type+instance+id，关系 ID 限当前 workspace，多对多；confirmed 需 evidence+人工审批元数据。缺字段/跨 scope/秘密/路径逃逸/不合法 YAML 拒绝。
5. refresh 保留人工备注/拒绝/审核，证据变化 stale/conflicted，新关系 proposed；不把高 confidence 当确认。校验器不证明实际人类身份，由 Host 保证真实对话审批。
6. Catalog 迁移用 backup API，原库不覆盖、备份校验完整性/计数；保留旧表、工具与 CLI。旧审核不自动成为项目 confirmed。
7. 阶段测试覆盖：解耦、三平台分页与范围、图片协议、Schema/refresh/隔离/多对多、stdio 离线 E2E、迁移回滚、安全/预算；真实路径和 Host 有独立矩阵，不能用 mock 计作通过。
