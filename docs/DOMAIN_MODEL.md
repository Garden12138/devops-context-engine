> 历史 V1 兼容文档。当前业务关系推理与 project.yaml 归 Host，默认 DCE 核心不调用语义 Mapping；参见 [Agent-led 工作流](AGENT_LED_WORKFLOW.md)。旧实现保留作缓存/历史兼容。

# 领域模型、关联语义和数据字典

## 1. 实体清单

| 领域 | 实体 | 主键约束/核心字段 |
|---|---|---|
| 平台 | SourceInstance | `id`, `type`, `base_url_hash`, `capabilities`；不可明文存秘钥 |
| 业务 | ZenProduct / ZenProject / ZenModule / ZenBug | `instance_id + type + external_id`；ZenTao 项目、产品、模块相互独立 |
| 源码 | GitRepository / CodeModule / SourcePath | gitlab project ID、namespace/path、commit、语言、模块根目录 |
| 构建 | Pipeline / CIJob / BuildTarget / OCIImage | project+pipeline/job ID、ref、sha、registry/repository/tag/digest |
| 部署配置 | DeployRepository / ComposeSnapshot / ComposeService | repo+commit(or hash)+path+service；变量只存键名，默认不存值 |
| 运行 | PortainerEndpoint / SwarmCluster / StackRecord / RuntimeService / Environment | endpoint、Swarm ID、Stack id、namespace、Docker Service ID、replicas |
| 关系管理 | Edge / Evidence / Review / ScanRun / Snapshot / Audit | status、source、target、证据版本、时间、actor、action |

**跨平台资源不能使用裸数字作为全局 ID。** 例如禅道 Project 28 与 GitLab Project 28 不应混淆；Stack ID 也仅在 Portainer 实例内唯一。

## 2. 建议 SQLite 表

```text
source_instances(id, kind, base_url_fingerprint, capabilities_json, created_at)
entities(id, instance_id, kind, external_id, canonical_key UNIQUE, attrs_redacted_json, first_seen_at, last_seen_at)
scan_runs(id, scope_json, mode, state, started_at, finished_at, checkpoint_json, errors_json)
snapshots(id, scan_run_id, entity_id, source_ref, commit_sha, etag_or_hash, observed_at, content_fingerprint, summary_json)
evidence(id, source_instance_id, source_uri_redacted, source_kind, snapshot_id, rule_id, fingerprint, summary, observed_at)
edges(id, from_entity_id, to_entity_id, relation_kind, environment_id NULL, status, discovery_method, confidence NULL, valid_from, valid_to NULL, last_verified_at)
edge_evidence(edge_id, evidence_id, strength, PRIMARY KEY(edge_id,evidence_id))
reviews(id, edge_id, decision, reviewer, reason, reviewed_at, previous_status, new_status)
audit_events(id, actor, action, target_id, sanitized_details_json, created_at)
```

建议索引：`entities(canonical_key)`，`edges(from_entity_id,relation_kind,status)`，`edges(to_entity_id,status)`，`snapshots(entity_id,observed_at DESC)`，`evidence(fingerprint)`。

可用 `canonical_key = {instance-uuid}/{kind}/{external_id}`，长路径经过 URL 规范化并保留原始外部 ID。V1 以多态实体表加 edges 避免过多专表，后续访问高频字段可优化成显式表。

## 3. 关系类型（示例）

- `belongs_to_project`: Bug → ZenProject
- `classifies`: ZenModule → Bug/feature（业务关系）
- `implemented_by`: ZenModule/feature → CodeModule（语义关系，需要确认）
- `part_of_repository`: CodeModule → GitRepository
- `built_by`: BuildTarget/OCIImage → CIJob
- `produces_image`: CodeModule/BuildTarget → OCIImage（需 CI/Dockerfile 证据）
- `declared_in`: ComposeService → ComposeSnapshot
- `uses_image`: ComposeService → OCIImage（部署配置事实）
- `realized_as`: ComposeService → RuntimeService（需 Name/namespace/stack/matching cluster）
- `managed_by_stack`: RuntimeService → StackRecord（当前集群证据）
- `runs_in`: RuntimeService → Environment
- `configured_from`: StackRecord → DeployRepository/ComposeSnapshot

### 示例：共享镜像

`CodeModule-M → Image-X → ComposeService-A + ComposeService-B → RuntimeService-A/B`。两条 Service 使用不同环境变量或启动参数也必须保持身份独立。

## 4. 状态机

建议边状态：

```text
candidate -> reviewed_confirmed
          -> reviewed_rejected
observed_verified -> stale_candidate / conflict / superseded
reviewed_confirmed -> needs_revalidation -> reviewed_confirmed / conflict
unresolved （未产生可用关系）
```

- `observed_verified` 只表示某个 *时间/快照范围内* 已验证的技术事实；不等于永久正确。
- `reviewed_confirmed` 指人工确认的语义/部署归属关系；任何自动重扫不得悄悄改为另一个 target。
- `stale_candidate` 例如 Stack 对应 SwarmId 与当前 Endpoint 的 Cluster ID 不匹配，并不是“已经确定废弃”。
- `confidence` 只用于候选排序，不是事实真伪概率或高风险自动审批凭据。

## 5. 版本和差异

需保存至少三类来源快照：

1. `git_compose_snapshot`：GitLab repo / commit / Compose file / parsed Service/Image；默认分支内容会变。
2. `portainer_saved_snapshot`：StackFile 当前 Portainer 保存文本的脱敏结构 + ConfigHash；ConfigHash 是否是合法 Commit 必须再向 GitLab 询证。
3. `swarm_runtime_snapshot`：Docker `/info` 当前 Cluster ID + `/services` Namespace/Name/Image Digest/replica desired/actual（若有）。

比较结果按 `source -> expected -> observed` 展示 `missing`, `extra`, `image_mismatch`, `mutable_tag`, `stack_cluster_mismatch`, `unknown`。不要用数量相同来推断每个 Service 一致。

## 6. 最小序列化示例

```json
{
  "relation_id": "edge-example-1",
  "from": "gitlab:example:compose:service-001",
  "to": "docker:example:swarm:service-001",
  "type": "realized_as",
  "status": "observed_verified",
  "environment": "env-review-required",
  "evidence_ids": ["ev-01", "ev-02"],
  "snapshot_at": "2026-10-31T00:00:00Z",
  "last_verified_at": "2026-10-31T00:00:00Z"
}
```

所有 ID 都是合成示例；不应持久保存真实 Token、数据库密码、完整 CI variables、完整敏感 StackFile。
