# 项目关系日常维护提示词

```text
请基于当前项目 `.dce/project.yaml` 和 DCE MCP 维护本项目 DevOps 关系。

先读取现有关系，不覆盖人工备注和 confirmed 关系。按我的请求执行 refresh / verify / bug-context / pipeline-diagnose / service-trace。

1. 只查询当前项目已确认或明确候选的资源。
2. 对照 evidence、revision、observed_at。
3. 新关系先 proposed。
4. 证据变化标记 stale/conflicted，不静默覆盖。
5. 用户确认后才更新为 confirmed。
6. 修改 YAML 前展示 diff。
7. 不调用平台写操作、不触发构建和部署。
8. 输出事实、推断、未知。
9. Bug 图片必须确认 Image Content 实际送达模型。
10. Service Trace 必须逐段提供代码、CI、Image、Compose、Stack、Swarm Service 证据。
```
