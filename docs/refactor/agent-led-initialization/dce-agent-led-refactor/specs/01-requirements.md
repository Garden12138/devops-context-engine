# 01 — 需求规格

## 目标
使 Agent 在用户指定的业务项目中，通过 DCE MCP 获取三平台事实，自主完成该项目的关系初始化、人工审核和持续维护。DCE 不承担业务关系推理。

## 功能需求
- FR01：独立检查 ZenTao/GitLab/Portainer 连接和只读权限。
- FR02：ZenTao 项目/产品/模块/Bug/附件查询；图片须实际返回 MCP Image Content 或明确标记未交付。
- FR03：GitLab Project/Repository Tree/File/Commit/Pipeline/Jobs/Job Trace 查询；支持 ref、分页和截断标记。
- FR04：Portainer Endpoint/Stack/Stack File/Swarm Info/Service 查询；区分 Stack 状态、Swarm Service 存在和应用健康。
- FR05：可提供 Compose/CI/模块结构的确定性解析，但不能输出未经证据支持的跨平台业务结论。
- FR06：Agent 从当前 workspace 开始，按项目范围查询平台候选资源。
- FR07：Agent 生成带证据的多对多候选关系，向用户澄清歧义。
- FR08：确认后写入当前项目 `.dce/project.yaml`，不存凭证。
- FR09：后续在当前项目内 refresh、verify、bug-context、service-trace、pipeline-diagnose。
- FR10：项目关系隔离；不同 workspace 不互相污染。

## 非功能要求
默认只读；不回显凭证；MCP STDIO stdout 仅传协议消息；超时/分页/限流/部分失败明确表达；大结果支持过滤和按需读取；不绑定模型供应商；关系证据包含来源、资源 ID、revision 和观察时间。
