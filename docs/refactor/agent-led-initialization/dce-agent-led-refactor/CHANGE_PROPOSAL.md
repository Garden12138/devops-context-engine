# 架构改造提案：Agent-led Project Initialization

## 1. 为什么改
原 V1 把资源发现、跨平台关系推理、AI 映射和全局 Service Catalog 放在 DCE 内部。问题是：DCE 内置模型不一定是用户当前最强的 Agent；Cursor/Codex 已掌握当前 workspace、本地源码、Git Remote 和项目配置；公司级全局关系目录容易混淆不同业务项目、仓库和环境；业务关系需要开发者确认，最自然的审核位置就是当前项目的 Agent 对话。DCE 的长期价值应是稳定、模型无关、可复用的平台工具层。

## 2. 新架构
旧：`DCE 全局扫描 → DCE 内部推理 → 全局关系目录 → Agent 查询`
新：`Agent 打开项目 → 读取本地仓库 → 调用 DCE MCP → Agent 分析关系 → 用户审核 → 保存到当前项目`

## 3. 职责边界
### DCE 负责
- 管理三平台连接与凭证读取。
- 提供禅道、GitLab、Portainer 只读 API。
- 统一分页、超时、重试、限流、错误格式和输出预算。
- 返回结构化数据及可追溯证据。
- 返回附件图片、文件、CI 日志等模型可消费内容。
- 提供 Compose/CI/Maven/Node 等确定性结构解析，但只报告文件中存在的事实。
- 提供 MCP Server、必要的 CLI doctor 和调用审计。

### Agent 负责
- 识别当前工作区及其 Git roots。
- 阅读 README、Git Remote、模块定义、CI、Dockerfile、Compose。
- 选择并查询相关禅道项目、GitLab 仓库、Portainer Stack/Endpoint。
- 推理多平台关系，列出证据、冲突和未知项。
- 询问用户确认业务关系及环境。
- 维护当前项目 `.dce/project.yaml`。
- 后续在当前项目内执行 refresh、bug context、service trace、pipeline diagnose。

### 用户负责
确认业务语义、环境归属和不确定关系；决定 `.dce/project.yaml` 是否可提交到私有业务仓库。

## 4. 设计原则
1. Agent 推理，DCE 提供事实。
2. 每次初始化限定在当前 workspace，不扫描全公司无关资源。
3. 项目关系是多对多，不假设 Project=Repo=Module=Image=Service。
4. 事实、推断、未知分开保存。
5. 每条关系必须有 evidence、revision、observed_at 和状态。
6. 只有用户确认后才标记 `confirmed`。
7. 项目间关系隔离。
8. 默认只读；本次不实现触发 CI、写禅道、更新 Stack、部署和删除资源。

## 5. 非目标
DCE 内置 AI Agent/关系推理模型、公司级全局业务关系真相库、Web 管理后台、自动修复代码/创建 MR/构建/部署、自动确认业务映射或推断生产/测试环境。

## 6. 迁移策略
不要重写整个 DCE。先盘点真实代码和现有六个 MCP 工具；保留已验收 Adapter、MCP transport、只读能力、分页、脱敏和输出预算。把关系推理从核心路径解耦。全局 Catalog 先备份并降级为资源缓存/历史数据，不得粗暴删除。旧工具尽量兼容，必要时提供弃用周期。
