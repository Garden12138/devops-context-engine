# DCE V1.0 — 需求规格（Requirements）

**状态：Ready for implementation** · **优先级 P0/P1** · **基线日期：2026-10-31**

## 1. 背景与用户故事

公司内网运行禅道、GitLab、Portainer。Cursor / Grok Bot 在修复 Bug 时反复使用浏览器，不可靠且消耗 token。业务项目可能跨多个 GitLab 仓库，一个仓库包含多个源码 Module；部署采用独立的 GitLab DevOps 仓库 + Compose + Portainer/Swarm；一个镜像可复用到多个 Service。

1. 开发者输入 `dce bug context <bugId>`，得到可靠缺陷、复现步骤、可访问截图和候选源码模块，不需浏览器。
2. 项目负责人运行 `dce init`，系统扫描授权范围并生成关系候选，提交人工审核；以后同样的关系不必重复调查。
3. 运维能分辨 GitLab 分支当前配置、Portainer 保存配置、Docker Swarm 实际服务之间的差异，不因历史 Stack 误部署。
4. AI Agent 使用少量结构化 MCP Tools 获得最小必要信息，不获得管理员权限。

## 2. 功能需求

### P0 — 基础能力

- REQ-01 配置验证：三平台地址/Token 从外部安全输入，`dce doctor` 逐一检查连接、权限、API 返回结构，隐藏敏感值；连接失败不阻塞其余平台。
- REQ-02 ZenTao：支持经过验证的 REST v1 `tokens`/`bugs/{id}`、`Token` 认证、`steps` HTML 清理与 `img src` 抽取；同域允许列表下的图片先用 Token 下载，验证 MIME/文件签名、大小上限；`files=[]` 时也处理内嵌图片。兼容 v2 属扩展，不默认假定可用。
- REQ-03 GitLab：发现可访问项目（分页）、Repository Tree、指定 Ref/Commit 下的文件、CI YAML、Pipeline/Jobs/Trace（只读）；识别 `master` 不是 `main` 的场景；区分业务代码与部署配置仓库。
- REQ-04 Portainer：Stack 列表与详情、保存的 StackFile、GitConfig（剔除认证信息）；Endpoint 的 `/docker/info`、`/docker/services`；按 Namespace 标签识别实际 Service，比较 `SwarmId` 与当前集群 ID，匹配失败标记 `stale_candidate`。
- REQ-05 Discovery：支持 GitLab Group/Project、ZenTao Product/Project、Portainer Endpoint/Stack 的显式扫描范围；迭代分页、断点恢复、节流、幂等写入，扫描差异可追溯。
- REQ-06 源码/部署解析：优先支持 Maven reactor、多模块 Gradle、Go workspace/module、Node workspaces、Dockerfile、`.gitlab-ci.yml`（含显式 include 引用）；解析 YAML 只看安全元数据和受限字段，不能执行脚本。
- REQ-07 图谱存储：Entity、Edge、Evidence、Snapshot、ScanRun、Approval、Audit；复合键含 source-instance、resource-type、external-id；所有确认关系保留来源、版本、有效期/最近校验、审计记录。
- REQ-08 关联：规则产生直接证据，AI 仅可输出候选与依据；高风险环境关联必须人工确认；允许一个源码仓库多模块、多镜像，一镜像多服务、多 Stack/环境，不得强行一对一。
- REQ-09 CLI：提供 doctor/init/discover/catalog/mapping/trace/bug context/pipeline diagnose/stack inspect 等，默认 JSON 或人类可读；有分页和输出大小限制；可用 `--no-ai` 完成核心工作。
- REQ-10 MCP：至少提供 `bug_context`、`project_context`、`service_trace`、`pipeline_diagnose`、`deployment_inspect`、`discovery_status` 六个 **只读** Tools。工具失败时返回机器可读 `error_code` 和诊断，不丢出秘密。
- REQ-11 审核：CLI review 显示候选、证据、状态、涉及环境与影响范围；确认/拒绝/覆盖是人的受控动作，记录 actor、reason、timestamp。不得向普通 MCP Agent 暴露审核确认工具。
- REQ-12 安全：默认 Fixture/Mock；真实内网扫描需显式 `--live --read-only` 与 scope 限定；HTTPS 优先；HTTP 只在显式放行；严禁将文件原始内容/内网地址/Token 送入外部 AI Provider 或公开仓库。

### P1 — 增强

- REQ-13 支持 GitLab CI `include` 递归解析（固定深度、禁止跨允许范围访问），必要时读取已解析的 GitLab CI lint/merged 配置（若当前版本支持且权限允许）。
- REQ-14 业务关系模型可按项目存本地人工别名、负责人备注、文档索引，提高初始化后的准确性。
- REQ-15 审核终端支持批量拒绝、候选排序和对比历史关系，且变更有审计。
- REQ-16 AI 推理插件兼容 OpenAI-compatible API，离线模型配置；用户可以完全禁用；异步任务可恢复，无无限重试。
- REQ-17 可导出脱敏的发现报告（JSON/Markdown），包含已知/候选/过期/冲突关系。

## 3. 明确不做

- 不要求全量读取所有公司仓库源码；不自动克隆/扫描不在范围内的项目。
- 不开发 Web 管理后台；不强依赖 Neo4j/向量数据库/云服务。
- 不自动创建 MR、不触发 build、不变更 Git 仓库、不更新 Stack、不执行 Docker 控制、不更新禅道状态。
- 不凭 `Status:1` 判断 Service 健康，不凭 Stack 名称 `test` 判断环境，不凭 `latest` 判定真实版本。

## 4. 非功能要求

- NFR-01：所有 API 调用有明确 timeout、有限重试（仅幂等只读）、分页、rate-limit/backoff、错误分类。
- NFR-02：同一快照重复导入不产生重复实体/关系；重复扫描不会丢失已确认的人工映射。
- NFR-03：输出大小有上限；单次 BugContext 输出摘要 + 图像受控引用，不直接塞入大尺寸 base64。
- NFR-04：数据库 schema 带版本迁移；删除/反悔审核支持软删除和历史审计。
- NFR-05：输出对 AI 输入中的提示注入不敏感；来自日志、Bug HTML、README 的文本永不获得工具执行权。
- NFR-06：线上凭证只存环境/系统密钥链；服务端统一身份授权；开发库不保存敏感配置或真实快照。

## 5. V1 演示流程

1. `dce doctor --mock`：三个 Adapter 模拟连接成功。
2. `dce init --fixture fixtures/synthetic-discovery.json --no-ai`：入库 3 个 Stack 记录、1 个当前 Swarm、78 个实际 Service 和历史配置差异。
3. `dce catalog anomalies`：识别两个 Swarm mismatch 的 Stack、一个当前 Stack、`latest` 不可作为部署指纹。
4. `dce mapping suggest --offline`：输出规则确认与业务候选，显示证据；AI 关闭也不影响规则发现。
5. `dce mapping review`：模拟人工确认并能复查确认人/版本。
6. `dce bug context DEMO-1001 --fixture`：得到描述、两张本地图片引用、候选模块、依据和未确认提示。
7. MCP Inspector 或自动化客户端调用六个只读工具，验证与 CLI 共享服务层。

## 6. 后续版本

- V1.1：加强 MCP 与上下文压缩、AI Coding Agent 对接与缺陷定位体验。
- V1.2：在具备安全审批的条件下实现分支/MR/CI 构建任务跟踪；修复代码仍由 Coding Agent 负责。
- V2.0：受控测试部署、Swarm/镜像版本核对、健康检查、回滚、禅道回写、审计；生产部署需独立审批链。
