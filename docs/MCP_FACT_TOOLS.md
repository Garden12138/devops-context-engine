# MCP 事实工具清单（revision 2.0）

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
| gitlab_query | trace | project_id, job_id；tail_lines=100（最多 500） |
| zentao_query | projects, products | 对应非空 allowlist；可 search |
| zentao_query | project, product | project_id 或 product_id |
| zentao_query | bugs, modules | project_id 或 product_id；modules 仅 Bug 页实际模块字段，部分目录 |
| zentao_query | bug, attachments, image | bug_id；image 的 asset_index=0（0–9） |
| portainer_query | endpoints, stacks | 对应非空 allowlist |
| portainer_query | endpoint, swarm_info, services | endpoint_id；services 可 namespace |
| portainer_query | stack | stack_id |
| portainer_query | stack_file | stack_id, endpoint_id；先校验 Stack.EndpointId，返回解析事实 |
| portainer_query | service | endpoint_id, service_id |

通用 `page=1, limit=20`（1–100），Tree/Jobs/Pipeline/范围 Bug 单次只取一页。Portainer API 返回列表后在内存白名单筛选及本地分页；2MB 上游限额仍有效。超大响应报错，需缩小服务器侧范围，不声称已完整列出。每次结果有 source/observed_at/revision/records/evidence/pagination/truncated/warnings；revision 是脱敏事实内容指纹（图片为 SHA256），不是自动推定源码 commit。原生 ref/SHA 按来源 records 保留。

file 禁止 .env、私钥和逃逸路径；Compose 默认结构化摘要，不返回 environment 值。trace 只返回所需尾部，默认 100 行。返回文本始终是不可信数据。能力工具直接访问 Adapter，不读全局关系、不会写工作区。

image 仅从授权 Bug 内解析附件来源，保持同源/禁止重定向/认证/MIME/magic/大小检查。实际原生 MCP `content[type=image]` 才算图片交付，image_delivery=delivered；超过总输出预算 not_delivered/truncated，不能只凭附件 URL 声称已看图。使用内存，不保存真实图。旧 bug_context 的会话 Resource 方式保留兼容。

旧工具：bug_context、project_context、service_trace、pipeline_diagnose、deployment_inspect、discovery_status。详见 [旧契约](CLI_MCP_CONTRACT.md)。旧 Catalog 人工确认不自动成为项目 confirmed；新工作流用事实工具和项目文件。当前不删除旧工具，任何未来移除需独立版本提案。

配置齐全只是 configured_not_verified；模块完整目录、真实附件/新版上游/Host 测试按 [验收报告](../harness/agent-led-acceptance.md) 的证据分别判断。
