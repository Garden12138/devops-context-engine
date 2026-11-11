# 04 — DCE MCP 能力契约

## 定位
MCP Server 是数据与证据工具箱，不是关系推理 Agent。

## 兼容要求
改造前先盘点当前六个 MCP 工具的真实名称、参数/返回 Schema、实现与测试。保留已验收工具，按能力缺口补充；不得照文档示例机械重命名或删除。

## 必要能力域
### ZenTao
项目/产品/模块搜索；Bug 详情；附件元数据；附件实际内容。图片优先 MCP Image Content，不能只返回 URL 并声称模型已看图。

### GitLab
项目搜索/详情；Repository Tree；指定 ref/commit 文件；Commit；Pipeline；Jobs；Job Trace。支持分页、路径过滤、日志截断标记。

### Portainer / Docker
Endpoint；Stack 列表/详情/Stack File；Docker Info/Swarm ID；Service 列表/详情；image、labels、replicas；必要时 Task 状态。

### 确定性事实解析
可解析 Compose service/image/labels/deploy/ports，CI job/stage/image/script，Maven/Gradle/Go/Node 模块。但只返回来源文件中可验证的事实，不做业务关系推理。

## 返回结果要求
尽量包含 `data`, `source`, `observed_at`, `revision`, `pagination`, `truncated`, `warnings`。MCP Image/Resource 按协议原生返回。

## 输出预算
- Tree 支持路径过滤和分页。
- 日志默认摘要/尾部，支持按需扩大。
- Compose 默认结构化摘要，必要时再读完整文件。
- 大附件避免转成巨型 Base64 文本。
- 返回明确说明数据是否截断。

## 安全
- 本次所有工具只读。
- 不新增触发 Pipeline、创建 MR、写禅道、更新 Stack、部署、删除资源工具。
- 凭证不进入输出。
- STDIO stdout 只用于 MCP 协议，日志写 stderr。
