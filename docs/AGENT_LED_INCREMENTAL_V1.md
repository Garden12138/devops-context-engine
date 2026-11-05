# Agent-led V1：Job、单服务和项目 Schema 增量

本轮扩展三个事实工具的 operation 和项目 Schema，九个 MCP 工具名称不变，旧六工具契约仍为 1.1，事实工具 revision 为 2.1。DCE 返回事实；分支、业务、环境和部署版本关系由 Host 根据证据判断。业务项目文件不自动迁移或写入。

## GitLab：定义与执行、项目与分支

| operation | 参数 | 来源及边界 |
|---|---|---|
| `project_jobs` | project_id, page, limit | 单页 Project Job 实例；不接受 ref/pipeline_id |
| `branch_jobs` | project_id, ref, page, limit | 对单个 Project Job 上游页按 Job.ref 精确过滤 |
| `jobs`（保持原用法） | project_id, pipeline_id | 指定 Pipeline 的普通 Job；可 include_retried |
| `pipeline_bridges` | project_id, pipeline_id | 指定 Pipeline 的触发 Job 与安全 downstream_pipeline 标识 |
| `file`（已有） | project_id, ref, path | CI 文件的静态定义；不同于 Job 实例 |

`job_statuses` 可传 `['manual']` 等状态，转换成 scope[]；默认不排除 manual。手动 Job 是已创建的实例，状态不表示已执行完成。401/403 为错误，不转成空列表。重试 Job 只在 `jobs` 的 include_retried=true 时显式包含。

GitLab 项目 Jobs API 没有 ref 过滤参数，branch_jobs 不向上游发送虚假的 ref 过滤：page/limit/next_page 对应 **上游 Project Job 页**。当前页无匹配且 more_available=true 时，继续同一 ref 的下一页。大项目可先用 pipelines/ref 定位，再按 Pipeline 查询。分页采用 offset page，错误/过宽响应/异常游标均显式处理。

普通 Job 空页返回 EMPTY_JOB_PAGE_NOT_PROOF_OF_NO_BUILD，Pipeline 空页另提示检查 bridges。触发 Job 单独查询，返回下游 Project/Pipeline ID、ref/SHA/status；不递归扩大 scope。Host 核对下游项目仍在已授权范围后，再单独查询其 Job。

`pipeline_bridges` 默认 GET `/bridges`，保持旧实例兼容。当前官方文档标明 19.2 起改名 `/trigger_jobs`，需时显式传 `trigger_api='trigger_jobs'`；不会遇到权限错误就尝试其他路由。以上均是 GET 列表，不触发任何执行。[GitLab 官方 Jobs API](https://docs.gitlab.com/api/jobs/)

调用示例（均为合成坐标，替换为已授权实值）：

```json
{"instance":"gitlab","operation":"project_jobs","project_id":"example/service","page":1,"limit":3,"job_statuses":["manual"]}
```

```json
{"instance":"gitlab","operation":"branch_jobs","project_id":"example/service","ref":"topic-a","page":1,"limit":3}
```

```json
{"instance":"gitlab","operation":"jobs","project_id":"example/service","pipeline_id":"pipeline-a","include_retried":true,"page":1,"limit":3}
```

```json
{"instance":"gitlab","operation":"pipeline_bridges","project_id":"example/service","pipeline_id":"pipeline-a","page":1,"limit":3}
```

工具都是 `gitlab_query`。执行标识与 CI Job Definition 名称分开保存；空页不能否定源码中存在构建定义，也不能否定下游执行。

## Portainer：只读一个保存的 Compose Service

工具 `portainer_query`：

```json
{"instance":"portainer","operation":"stack_service","stack_id":"stack-a","endpoint_id":"endpoint-a","service_name":"api"}
```

service_name 是实际 Compose key。服务端先校验 Stack.EndpointId，受限读取 Stack File，按该 key 选中后才解析/编码目标；不解析无关服务的 image，不把整份原文输出。缺失返回 NOT_FOUND，越界/Endpoint 不匹配直接拒绝。Reader 2MB、元数据 1MB/YAML 节点限制仍保留，不为大文件关闭安全边界。

返回 name、image（tag/digest/mutable 标记）、build_context、environment_names、白名单标签、端口和 deploy mode/replicas，以及 stack_id/endpoint_id/stack_file_revision 和统一 evidence。环境值、command、auth、secrets、完整原文不返回。不能安全解析的目标字段标 incomplete；未解析 YAML alias 显式报错。

该操作只描述保存的部署定义。运行事实仍读取 services/service/swarm_info；保存定义与运行观察分开，不由服务名或数量相等推断环境、健康或版本一致。

## Project Context：v1 保持、v2 显式选择

[当前 Schema](../schemas/project.schema.json) 同时支持 1/2；[原 v1 Schema](../schemas/project-v1.schema.json) 固定保留。旧 v1 可原样读取，序列化不添加新的空字段；默认模板仍为 v1。需要新概念时显式选 v2：

```sh
.venv/bin/dce project template --workspace-id example-workspace --schema-version 2
.venv/bin/dce project migrate /absolute/business/workspace
.venv/bin/dce project validate /absolute/business/workspace
```

migrate **只向 stdout 输出候选 JSON**，不创建、覆盖或提交业务文件；程序接口 `dce.project.context.migrate(project)` 同样是纯函数。解析后的模型仅升级 schema_version，输出可规范化格式/默认字段；保留所有关系、证据、审批、状态和备注；旧 ci_job/container_image 不被猜成新类型。拒绝有损降级，Host 后续应用候选仍需展示 diff 并取得相应授权。

| Node.type / details.kind | details 必要标识 |
|---|---|
| source_branch | project_id, ref；可带观察到的 commit_sha |
| git_ref | project_id, ref, ref_kind（branch/tag/commit） |
| ci_job_definition | project_id, ref, path, job_name |
| ci_job_execution | project_id, pipeline_id, job_id；ref/SHA/status 可选 |
| image_tag | repository, tag |
| image_digest | repository, digest |
| deployment_definition | endpoint_id, stack_id, service_name；file_revision 可选 |
| runtime_observation | endpoint_id, service_id, observed_at（带时区） |
| environment | name；已有旧 environment 节点仍可无 details |

新节点需对应的 typed details，相同 type/instance/id 不能携带冲突的细节；项目/端点/Stack 坐标仍需落在显式 scope 内；project_id 与 scope 使用相同的已授权标识（数字或 namespace/path），不自动猜测互换。多分支、多环境、多版本各自使用独立身份和关系，可多对多；没有环境名称推断规则。

示例节点：

```json
{"type":"ci_job_definition","instance":"gitlab","id":"build:topic-a","details":{"kind":"ci_job_definition","project_id":"example/service","ref":"topic-a","path":".gitlab-ci.yml","job_name":"build"}}
```

relationship 可独立携带 version_match，状态为 not_verified/matched/mismatched/inconclusive，和 proposed/confirmed 等审批状态分开。matched/mismatched 必须有 evidence、image_digest 或完整 commit_sha 及 expected/observed；标签比较不是依据。结构/格式由 JSON Schema 检查，范围、身份冲突、审批和比较结果还需运行时校验。`latest` 不产生版本确认。

[完整合成 v2 示例](../examples/project-context/project-v2.yaml) 可用当前校验器读取。刷新保留审批/拒绝/备注，版本比较证据变化也会使已有关系 stale/conflicted；仅观察时间变化不使相同比较失效。

## 使用与证据

已有 Cursor 连接需在 MCP 页面将 dce 服务开关关闭再开启一次，并新建会话加载新参数。九工具名称保持不变。本轮真实验收为独立 SDK stdio，不能代替未观察到的 Cursor 新 operation 调用；原有 Cursor Host 验收保留其版本/时间边界。

验收结果见 [增量报告](../harness/incremental-v1-acceptance.md)。当前项目带实际 Pipeline ID 和 Compose key 的可复制示例只保留本机 `.local/agent-led/incremental-v1/MCP_CALLS.md`，不包含凭证。业务关系文件在本轮只读，24 proposed/3 unresolved/1 confirmed 全部保留，不写入 v2。
