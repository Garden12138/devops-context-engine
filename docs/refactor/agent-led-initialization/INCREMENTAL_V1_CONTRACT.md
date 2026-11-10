# Agent-led V1 实际项目缺口增量契约（2026-11-05）

本轮只扩展现有九工具和项目契约，不增加模型/业务关系推理、平台写接口或业务目录写能力。保留既有未提交改动；不 git add/commit/push，不修改业务 project.yaml。实际项目当前 24 proposed/3 unresolved/1 confirmed，只读记录内容指纹，所有 fixtures 使用合成名称。

## A：GitLab Job 事实

- 原 `gitlab_query(operation=jobs, project_id, pipeline_id)` 保持 Pipeline Job 调用方式。新增 `project_jobs`、`branch_jobs`（必填 ref）、`pipeline_bridges`（必填 pipeline_id）。九个 MCP 工具名称不变。
- Project/Branch Job 使用已授权 Project 的 Jobs API；GitLab 的项目 Jobs API 无 ref 过滤参数，branch_jobs 对单个上游页按记录 ref 精确过滤，不伪造服务器 ref 过滤。page/limit/next_page 对应上游 Project Job 页，过滤后空页仍可能有下一页。
- 单次只取一页。校验游标、限制服务端忽略 limit 的过宽响应；权限错误仍为错误，不转成空列表。可按 job_statuses（scope[]）过滤 manual 等状态；默认不排除手动 Job。Pipeline Jobs 可显式 include_retried。
- 触发 Job/下游 Pipeline 是独立事实入口。返回安全的 downstream_pipeline 标识/ref/SHA/status，不自动递归到其他 Project，不扩大 scope；调用方需按来源 ID 明确查询。
- 空 Job 页显式提示不能证明没有构建，建议继续分页、读取 bridges/执行可见性和 CI 定义。CI 定义与执行区分；不把空列表转为业务结论。

API 根据 [GitLab Jobs](https://docs.gitlab.com/api/jobs/) 与 [Pipelines](https://docs.gitlab.com/api/pipelines/) 官方文档核对，实际实例不支持的参数/权限以真实错误记录。

## B：单个 Compose Service

- 新增 `portainer_query(operation=stack_service, stack_id, endpoint_id, service_name)`；与旧 stack_file 共用只读 Adapter，先检查 Stack.EndpointId。
- 服务端读取受限 Stack File 并选中精确 Compose key，再解析目标，避免整份输出预算或无关 service 的无效 image 干扰目标查询。不匹配返回 NOT_FOUND，不以 Swarm Service 名称猜测 Compose key。
- 只返回目标 name/image/build_context/environment_names、安全标签、ports、deploy mode/replicas，以及 Stack/Endpoint/file revision；不返回环境值、auth、command、secrets、原始文件。未知格式明确 incomplete 或错误。
- 文件输入字节/YAML 节点限制仍有效；超过 MCP 输出预算的整份 Compose 不妨碍其中一个小记录返回。只保证保存定义事实，不确认运行环境、镜像版本或 Swarm 归属。

## C：Project Context v2

- 保留 v1 读取、默认 v1 模板和旧节点类型。固定原 JSON Schema 于 schemas/project-v1.schema.json，新 project.schema.json 支持 1/2。新增版本必须显式选择，不在 load/validate 时改写或暗升版本。
- v2 新节点独立描述 source_branch、git_ref、ci_job_definition、ci_job_execution、image_tag、image_digest、deployment_definition、runtime_observation；environment 可提供独立 details。typed details 携带项目/ref/路径/执行 ID/镜像/端点/观察时间，不把同数字跨平台当作相同身份。
- v2 relationship 可独立携带 version_match（not_verified/matched/mismatched/inconclusive），与 proposed/confirmed 等关系状态分开。已匹配/不匹配需具体 digest/完整 commit SHA 和证据，标签相等不能作为版本匹配依据。
- 支持同节点多关系、多分支/环境/版本；相同 type+instance+id 不能携带互相冲突的 details。新 GitLab/Portainer details 必须落在显式项目/端点/Stack scope 内。
- `migrate(project, target_version=2)` 是纯函数，保留所有原关系、证据、审批、备注和状态；不猜测旧 ci_job/container_image 的新语义。CLI migrate 仅向 stdout 输出候选，不写业务文件；拒绝有损降级。

## D：验证边界

基线 208 passed（12.41s）。先行契约/安全测试覆盖新 Job 路由/过滤/分页/手动/bridges/权限/空页、单 Service 大文件/缺失/secret/越界、v1/v2 读取与迁移/审批保留/版本匹配/多环境。完整回归、九工具列表/旧六 Schema、stdio 合成 E2E、ruff/mypy 与 wheel 检查按实际结果记录。

真实验收只在当前已授权业务 Project/Stack 范围，凭证继续由既有显式本机入口处理，不向对话输出。保护业务 project.yaml 字节指纹/HEAD/index；无真实 CI/部署/日志读取。调用示例使用占位符，实际 ID 与私有响应仅留 gitignored 目录。
