# 真实验收接续资料

代码与离线验证已完成。下一步从一个明确业务项目开始，不重新扫描公司全部资源。

先提供业务工作区绝对路径和一句项目用途；多仓库可提供它们的共同目录。不能用 DCE 本身的仓库路径替代业务项目。

后续资料可分次回复：

| 信息 | 回复内容 |
|---|---|
| Host | Cursor 或 Codex；是否已经能看到 dce |
| 连接 | 不含凭证的 TOML 配置文件绝对路径；没有则回复未配置；说明是否必须用 HTTP |
| 样本范围 | 是否沿用提案中的独立查询样本；或给替换范围。项目、Bug、Stack 的关系仍待证据，不预设相关 |
| 未知 ID | ZenTao Project/Product、Pipeline/Job 所属 GitLab Project 不清楚可写待查，不必猜 |

无配置时使用 [实际配置模板](../examples/connections.example.toml)，复制到安全的本地私有目录并填写站点根地址和实例别名；不加 Token 字段。只保留要接入的平台段。凭证仅进入受保护的 DCE 子进程环境：DCE_ZENTAO_TOKEN、DCE_GITLAB_TOKEN、DCE_PORTAINER_TOKEN。不要发送到聊天；用户明确提供 .env 时，由显式本机入口加载，Agent 不把正文读入对话。实际进程 URL 覆盖变量为 DCE_ZENTAO_URL、DCE_GITLAB_URL、DCE_PORTAINER_URL。

账号密码换禅道 v1 Token 的入口见 [本地凭证说明](AGENT_LED_LOCAL_CREDENTIALS.md)。指定文件也支持 ZEN_URL、GITLAB_URL、PORTAINER_URL；显式进程 DCE_* 配置优先于该文件和 TOML。

配置与范围明确后，先核对 workspace/Git roots 和最少平台事实，再准备实际 Host MCP 启动配置。Host 展示候选与文件 diff，用户确认后维护 .dce/project.yaml。真实 Host 至少三次读取、真实图片 ImageContent 到模型，以及人工确认或明确 unresolved 的证据分别记录。SDK smoke 与旧 Cursor 启动记录不能代替这几项。

当前不需要提供 Token、密码、.env 内容、完整 Compose、私有日志、业务页面账号或部署权限。详细步骤见 [Host 工作流](AGENT_LED_WORKFLOW.md) 与 [工具清单](MCP_FACT_TOOLS.md)。
