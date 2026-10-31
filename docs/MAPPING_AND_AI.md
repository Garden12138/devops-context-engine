# AI 关联推理、证据评级与人工审核

## 1. 为什么不全交给大模型

模型可以理解禅道业务名称，但单凭 `模板管理`、`module-template`、`service-template` 名字可能误配。规则推导技术事实更可靠；AI 的职责是：把不明确的业务语义和代码模块联系起来，输出**候选关系 + 可核验证据 + 不确定性**。

## 2. 两阶段关联流水线

### 第一阶段（无需 AI）

- 仓库结构 → 模块：由构建清单生成。
- CI 构建目标 → Image：由 Dockerfile、CI 构建配置解析；动态变量为未解析。
- Image → ComposeService：由 `image:` 字段构成 `observed_verified @ config_snapshot`。
- ComposeService → RuntimeService：必须经 endpoint、stack、namespace、ServiceName、SwarmId 辅助验证；不能凭数量相同确认。
- 发现 GitLab master/Portainer saved/Swarm running 三份快照差异并给出明确报告。

### 第二阶段（可选 AI）

- 对待解决的 `ZenTao feature -> CodeModule`、跨仓库业务组件等进行候选推断。
- 入模仅包含授权范围内的脱敏名称、描述、目录摘要、CI/Compose 元数据、特定 Bug 描述；必要时进一步请求源码摘录，不能默认把所有源码送外部模型。
- 输出严格 JSON Schema：`source_key`, `candidate_targets`, `evidence_ids`, `reason`, `counter_evidence`, `confidence_band`, `requires_review`。
- 无据可依返回空候选；禁止模型伪造 GitLab Ref、部署服务或审批人。

## 3. 候选分层

| 类别 | 例子 | 结果 |
|---|---|---|
| Direct | CI 明确推送 Image，与 Compose `image:` 相等 | 建立指定快照的技术关系 |
| Corroborating | Dockerfile 路径、模块 artifact、镜像名称一致 | 候选增强，须检查动态 CI |
| Semantic | Bug 描述“5G消息”与模块名 `5gmc` 相似 | AI 候选，人工审核 |
| Negative | SwarmId 与当前 Cluster 不匹配 | 不允许选为当前运行部署关系 |

不定义“置信度高于 0.9 即自动批准”。评分只能排序，不能替代证据和审批。

## 4. 审核协议

`dce mapping review` 对每条候选展示：

- 关联左端、右端和所涉环境；来源时间及 Commit/Digest。
- 证据原始系统可追溯的**脱敏引用**（若有权限可由本地 CLI 查看）。
- 反证/冲突，包括旧 Swarm、同名多个服务、多个镜像、复用关系。
- 操作：`accept`, `reject`, `override`, `defer`；默认 defer。
- 审核记录 actor、reason、timestamp、原状态、目标状态；变更后可再次审核，不可物理删除历史。

**安全边界**：`mapping approve` 是本地显式人工动作或受身份验证的审核 API，普通 MCP/Agent 不提供此工具。AI 输出永不直接写 `confirmed`。

## 5. 输入安全与成本控制

- 不可信输入中若出现“忽略上面指令”“执行命令”等文本，作为字符串证据保存，不在 Tool 执行环境解释。
- Model Input Builder 对字段进行 allowlist 与 2k/4k/8k 等可配置 token 预算，减少冗余日志和代码。
- 先召回高置信直接关系，再针对缺口调用 AI；依据扫描 fingerprint 缓存推断结果。
- 本地/公司批准模型优先；不配置 AI 时全部 V1 技术能力继续可用。
- 模型泄漏/外部访问风险由 Provider Policy 拦截；所有入模对象记录数据类别及合规审批状态。

## 6. 示例（全部合成）

```json
{
  "source": "zentao:demo:feature:template-management",
  "candidates": [
    {
      "target": "gitlab:demo:module:front-template",
      "confidence_band": "medium",
      "evidence_ids": ["evidence-path-12", "evidence-readme-01"],
      "reason": "界面路径与业务描述吻合，但调用关系尚未验证",
      "counter_evidence": ["同仓库存在另一个模板模块"],
      "requires_review": true
    }
  ],
  "status": "candidate"
}
```
