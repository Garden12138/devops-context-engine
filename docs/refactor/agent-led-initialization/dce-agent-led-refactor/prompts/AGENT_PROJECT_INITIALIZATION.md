# 在 Cursor/Codex 真实业务项目中执行初始化

在 Cursor/Codex 打开目标业务项目根目录，确认 DCE MCP 已连接后使用：

```text
请使用已经连接的 DCE MCP，为当前打开的工作区初始化项目级 DevOps 上下文。

原则：由你（当前 Agent）负责分析和推理；DCE 只作为禅道、GitLab、Portainer 的数据和证据提供工具；关系只属于当前工作区，不做公司级全局扫描；先分析本地项目，再按证据查询平台；不确定时问我，不得猜测或自动确认；本次只读，不修改平台、不触发 CI、不部署。

1. 理解本地项目：识别 workspace、所有 Git roots、Git Remote（脱敏）、branch、README、技术栈、模块、Dockerfile、Makefile、CI YAML、Compose。
2. 检查 DCE：检查三个平台连接和只读能力，不输出 Token。
3. 发现候选：优先用本地 Git Remote 精确匹配 GitLab；按业务描述/我提供的 Bug ID 查询 ZenTao；根据 CI 镜像、部署仓库 URL、Compose 线索查询 Portainer/Swarm。只查当前项目相关候选。
4. 建立关系：分析 ZenTao Project/Module/Bug ↔ GitLab Project/Code Module ↔ CI/Image ↔ Compose Service ↔ Portainer Stack/Swarm Service。
5. 每条关系区分 API/配置事实、AI 推断、未知和冲突，并提供来源、locator、revision、observed_at。
6. 输出审核表：来源 | 关系 | 目标 | 状态 | 证据 | 风险/未知 | 是否需要我确认。
7. 对不确定的业务关系和环境归属逐项询问。允许 unresolved。
8. 我确认后，创建/更新当前项目 `.dce/project.yaml`。confirmed 必须有 evidence、approved_by、approved_at。写入前展示 diff。
9. 不写 Token/密码/API Key，不复制完整日志/图片/secret。写入后做 schema validation 并重新读取。
10. 总结已确认、候选、冲突、未知、权限缺口和文件位置。

不要为了显示初始化成功而虚构关系，可以以 partially_initialized 结束。
```

## 已知样本注意
仅作线索，必须重新核验：ZenTao Project 28/Product 13/Bug 4314；GitLab `devops/portainer` 是部署配置仓库候选，不等于业务源码仓库；Stack 31 曾匹配当前 Swarm；Stack 19/21 曾不匹配；`link-forge` Project 314 不得自动绑定 Bug 4314。
