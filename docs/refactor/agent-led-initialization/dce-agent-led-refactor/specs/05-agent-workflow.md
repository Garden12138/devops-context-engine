# 05 — Agent 项目初始化和维护流程

## 触发
在 Cursor/Codex 打开目标业务项目后，用户说：
“请使用 DCE MCP 为当前工作区初始化项目级 DevOps 关系。先分析本地项目，再按证据查询三个平台；不确定时问我。不要执行写入、构建或部署。”

## 阶段 A：理解本地项目
读取 workspace、所有 Git root、Git Remote（脱敏）、branch、README、语言、Maven/Gradle/Go/Node 模块、Dockerfile、Makefile、CI YAML、Compose。形成项目画像和候选资源线索。

## 阶段 B：检查 DCE
检查三平台连接、权限、附件/图片、日志、Stack File 能力。某平台不可用时继续其他平台并记录阻塞。

## 阶段 C：按证据查询
- GitLab：优先用本地 Git Remote 精确匹配，再读取必要的项目元数据、Tree、CI、Dockerfile。
- ZenTao：根据业务描述/用户提供 Bug ID 查询 Product/Project/Module；候选不唯一时询问。
- Portainer：根据 CI 镜像、部署仓库 URL、Compose 文件定位 Stack/Endpoint/Swarm/Service。
- 不全量扫描无关资源。

## 阶段 D：关系分析
技术链：`GitLab Project → CI Job → Image → Compose Service → Portainer Stack → Swarm Service`
业务链：`ZenTao Project/Module/Bug ↔ GitLab Project/Code Module`
每条关系记录证据、revision、观察时间、状态、推断理由和冲突。

## 阶段 E：用户审核
输出：来源 | 关系 | 目标 | 状态 | 证据 | 风险/未知 | 是否需确认。业务映射和环境归属不明确时必须询问。允许 unresolved。

## 阶段 F：持久化
用户确认后创建/更新 `.dce/project.yaml`；写入前展示 diff；confirmed 必须有审核元数据；不存密钥；写入后 schema validate 并重新读取验证。

## 阶段 G：完成报告
输出已确认关系、候选关系、冲突、未知项、调用工具、权限缺口、文件位置和是否建议提交 Git。可部分完成，不得为了“初始化成功”而编造关系。

## 日常维护
refresh：重新读取已关联资源，对比 revision 和事实变化。
bug-context：读取 Bug/附件，结合当前项目已确认映射定位代码。
service-trace：逐段展示代码→CI→Image→Compose→Stack→Swarm Service 证据。
pipeline-diagnose：读取失败 Job Trace，区分日志事实与模型推断。
所有新关系先 proposed，证据冲突标记 stale/conflicted。
