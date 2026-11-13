# MCP 事实工具清单（Portainer revision 2.2，其余 2.1）

DCE 暴露九工具。原六名称/参数/输出 Schema 保留兼容，关系部分是历史线索。三平台实例/凭证由已有 Settings 的安全进程环境/非秘密 TOML 配置读取；不自动加载 .env。`dce doctor --live --read-only` 独立检查三平台，失败不阻塞其他平台；MCP 枚举只报告配置条件，不进行认证探测。

已实现启动参数（用实际绝对路径和已授权 ID 替换占位符，不在命令中放凭证）：

```text
/absolute/path/.venv/bin/dce --config /absolute/path/connections.toml --catalog /absolute/path/cache.sqlite3 mcp serve --transport stdio --live --read-only --gitlab-project <id> --zentao-project <id> --zentao-product <id> --zentao-bug <id> --portainer-endpoint <id> --portainer-stack <id>
```

这些范围参数可重复；空范围拒绝相应读取。每次参数 `instance` 必须与配置一致；一个服务进程每平台配置一个实例，多实例启动独立 MCP Server。项目/产品搜索只读取允许 ID，再本地筛选，不能扫描无关项目。

| 工具 | operation | 必要的范围/参数 |
|---|---|---|
| gitlab_query | projects | 非空 Project allowlist；可 search |
| gitlab_query | project | project_id |
| gitlab_query | tree | project_id, ref；path 可选，单层目录 |
| gitlab_query | file | project_id, ref, path；start_line=1, tail_lines=100 |
| gitlab_query | commit | project_id, ref |
| gitlab_query | pipelines | project_id；ref 可选 |
| gitlab_query | pipeline, jobs | project_id, pipeline_id |
| gitlab_query | project_jobs | project_id；可 job_statuses；page/limit 为 Project Job 页 |
| gitlab_query | branch_jobs | project_id, ref；对 Project Job 单页本地精确筛选；空页可能仍有下一页 |
| gitlab_query | pipeline_bridges | project_id, pipeline_id；仅查询触发 Job/下游 ID，不递归扩 scope |
| gitlab_query | trace | project_id, job_id；tail_lines=100（最多 500） |
| zentao_query | projects, products | 对应非空 allowlist；可 search |
| zentao_query | project, product | project_id 或 product_id |
| zentao_query | module_tree | product_id（不能用 Project/Execution ID）；module_type=bug/story/case/product，默认 bug；search 后本地 page/limit |
| zentao_query | bugs, modules | project_id 或 product_id；modules 仅 Bug 页实际模块字段，部分目录 |
| zentao_query | bug, attachments, image | bug_id；image 的 asset_index=0（0–9） |
| portainer_query | endpoints, stacks | 对应非空 allowlist |
| portainer_query | endpoint, swarm_info, services | endpoint_id；services 可 namespace |
| portainer_query | stack | stack_id |
| portainer_query | stack_file | stack_id, endpoint_id；先校验 Stack.EndpointId，返回解析事实 |
| portainer_query | stack_service | stack_id, endpoint_id, service_name；服务端选择精确 Compose key 后输出安全字段 |
| portainer_query | service | endpoint_id, service_id |
| portainer_query | service_logs | endpoint_id, stack_id, service_name 或 service_id（二选一）, start_time, end_time；独立启动日志授权，有限 lines/bytes/deadline |

V1.1 日志能力的实际参数 Schema、安全投影、错误/空结果/过期边界和 Cursor 配置见 [Scoped Service Logs](SCOPED_SERVICE_LOGS.md)。必须额外设置 `--portainer-log-scope ENDPOINT_ID:STACK_ID`；旧元数据范围不自动开放私有日志。follow 禁止，日志 GET 不重试；原九工具及调用仍兼容。

独立模块树使用官方 v1 `GET /modules?id=<Product ID>&type=<module_type>`；保留实际节点字段和 children 层级，屏蔽 URL/owner，最多 10000 节点、深度 30。接口不支持/权限失败时返回错误，不以部分 Bug 清单冒充完整目录。此路线由 [官方路由与 GET 实现](https://github.com/easysoft/zentaopms/blob/main/api/v1/entries/modules.php) 核对，真实实例仍 not_verified。

通用 `page=1, limit=20`（1–100），Tree/Jobs/Pipeline/范围 Bug 单次只取一页。Portainer API 返回列表后在内存白名单筛选及本地分页；2MB 上游限额仍有效。超大响应报错，需缩小服务器侧范围，不声称已完整列出。每次结果有 source/observed_at/revision/records/evidence/pagination/truncated/warnings；revision 是脱敏事实内容指纹（图片为 SHA256），不是自动推定源码 commit。原生 ref/SHA 按来源 records 保留。

事实工具的完整证据对象在 `data.evidence`；信封顶层 `evidence` 沿用旧工具的 evidence ID 数组，事实调用可为空。Host 判断证据应读取 `data.evidence`，不能因兼容字段为空就声称没有证据。

file 禁止 .env、私钥和逃逸路径；Compose 默认结构化摘要，不返回 environment 值。trace 只返回所需尾部，默认 100 行。返回文本始终是不可信数据。能力工具直接访问 Adapter，不读全局关系、不会写工作区。

image 仅从授权 Bug 内解析附件来源，保持同源/禁止重定向/认证/MIME/magic/大小检查。实际原生 MCP `content[type=image]` 才算图片交付，image_delivery=delivered；超过总输出预算 not_delivered/truncated，不能只凭附件 URL 声称已看图。使用内存，不保存真实图。旧 bug_context 的会话 Resource 方式保留兼容。

九工具均同时提供相同的结构化 JSON 和文本 JSON 信封，Host 不转发 structuredContent 时仍可看到 source/evidence/pagination/truncated/error。两份 JSON（含转义）共同受 output_budget 约束。较大图片可在受保护的启动配置中显式设置 `image_output_budget` 或 `DCE_IMAGE_OUTPUT_BUDGET`（最大 3000000 字节）；默认未设置时沿用 output_budget。文本元数据预算和 Reader 的 2MB 原图限制不变，Base64 只在原生 ImageContent 中。协议发送成功与真实 Host 模型收到图片分别验收。

旧工具：bug_context、project_context、service_trace、pipeline_diagnose、deployment_inspect、discovery_status。详见 [旧契约](CLI_MCP_CONTRACT.md)。旧 Catalog 人工确认不自动成为项目 confirmed；新工作流用事实工具和项目文件。当前不删除旧工具，任何未来移除需独立版本提案。

配置齐全只是 configured_not_verified；模块完整目录、真实附件/新版上游/Host 测试按 [验收报告](../harness/agent-led-acceptance.md) 的证据分别判断。

增量 Job/单 Service 的分页语义、空结果和手动/下游处理、调用 JSON、v1→v2 只读迁移见 [增量使用说明](AGENT_LED_INCREMENTAL_V1.md) 和 [本轮增量验收](../harness/incremental-v1-acceptance.md)。原 jobs 仍按 Pipeline 查询；Project/Branch 使用新 operation，不把空列表判为没有构建。


用户明确使用本机 .env 和禅道 v1 账号密码时，采用 [显式本地凭证入口](AGENT_LED_LOCAL_CREDENTIALS.md)；默认 dce 不自动加载 .env，不能直接把旧变量名当作已注入的 DCE 进程配置。
