> 历史 V1 兼容文档。当前业务关系推理与 project.yaml 归 Host，默认 DCE 核心不调用语义 Mapping；参见 [Agent-led 工作流](AGENT_LED_WORKFLOW.md)。旧实现保留作缓存/历史兼容。

# 平台适配器与自动发现实施细则

## 1. 共同接口

Reader protocol（伪代码）：

```python
class SourceReader(Protocol):
    async def probe(self) -> CapabilityReport: ...
    async def list_resources(self, scope: ScanScope, cursor: str | None) -> Page[Resource]: ...
    async def get_resource(self, key: ResourceKey) -> Resource: ...
```

所有 SourceReader 需要 `allowlisted_base_url`、传输超时、rate-limit、分页、请求 ID、可撤销凭证源及模拟传输。Adapter 不允许创建/更新/删除任何外部资源。`httpx` 的 `trust_env` 应按用户代理与公司网络策略配置，不能悄悄全局禁用企业代理或 CA 验证。

HTTP 压缩响应契约：Reader 的大小上限按 `iter_bytes()` 解码后的字节计算。将流缓冲为新 Response 时，删除上游 `Content-Encoding`、`Content-Length` 和 `Transfer-Encoding`，让新 Response 按实际正文生成长度；保留 MIME、分页等业务头，避免已解压内容被再次解压。损坏的压缩正文返回 `INVALID_PAYLOAD` 且不重试；真正的传输异常仍按有界网络重试处理。合成测试须覆盖 gzip/deflate、分页头、解压后大小限制和损坏压缩数据；真实接口成功需独立实跑证明。

## 2. 禅道（ZenTao REST v1）

已验证的 v1 使用 `POST /api.php/v1/tokens`（获取 Token）、`GET /api.php/v1/bugs/{id}` 和 `Token: <token>`。系统需避免记录登录密码，即使刷新 Token 也不能输出。Bug steps 通常为 HTML，图片可能嵌入 `src=".../file-read-xxx.png"`，且 `files=[]`。图片端点在 HTTP 200 时可能返回 `text/html`；必须带 Token 再读取并做 MIME/字节校验。

登录只请求 v1 tokens，不附带已有 Token、不重试登录 POST；取得的临时 Token 用于随后同源的只读请求。账号/密码只由用户本机不回显输入；报告不保留认证响应、Token 或密码。401 只证明认证被拒绝，不据此推定有效期，不自动切换到 v2 或反复登录。

安全实践：
- 通过 HTML 解析器提取图片，而非依赖正则做 HTML 语法分析。
- 只允许已配置的禅道域名和前缀下载；屏蔽访问 metadata/IP/任意用户构造 URL 以防 SSRF。
- 图片大小及数量限制；缓存目录权限 0700；仅本地 file handle 或需要鉴权的资源 ID，绝不输出大图 base64。
- 原始 HTML 脱除 script/style/event handler，`img` 转为可引用 asset；所有文本按非可信数据处理。
- 项目/产品/模块发现遵循 API 权限与版本能力报告，v1 不具备的接口不猜测、不使用网页点击兜底。

## 3. GitLab REST v4

最低只读能力：`GET /api/v4/projects`、`/projects/:id`、`repository/tree`、`repository/files/:file_path/raw?ref=...`、`repository/commits/:sha`、`pipelines`、`pipelines/:pid/jobs`、`jobs/:jid/trace`。

注意：
- `project id` 可以是数字或 URL 编码路径；`/` 需编码为 `%2F`。
- 需要正确处理 API Pagination Links/headers、GitLab Self-Managed 旧版本的字段与端点差异。
- 确定仓库默认分支，而非假定 main；扫描 CI 的 `include` 仅限同一项目和允许组，递归深度受限。
- CI `script` 是**字符串数据**，静态解析显式 `docker build/tag/push`, `make`, `buildx` 关系；不要执行脚本；动态变量解析不到时标记 unknown。
- GitLab CI 失败日志应先截取错误上下文并脱敏，不直接发送全部日志给模型。
- 业务仓库与 `devops/deployment` 等部署仓库必须分别建实体，不能通过 Stack 的 GitConfig.URL 认定其为业务代码来源。

## 4. Portainer + Docker Swarm

已验证可读：`GET /api/stacks`、`/api/stacks/{id}`、`/api/stacks/{id}/file`、`/api/endpoints/{id}/docker/info`、`/api/endpoints/{id}/docker/services`。

安全和关联：
- 剔除响应中 `GitConfig.Authentication`、Env values、RegistryPassword、RepositoryPassword、API keys 等，避免将原始响应落盘。
- `Type:1` 可以按 Swarm Stack 处理，但保留类型判断，不将所有 Portainer 当 Swarm。
- 读取 `/docker/info` 中 `Swarm.Cluster.ID`，与 Stack `SwarmId` 比较。
- `Stack.Namespace` 可能为空；使用运行 Service 的 `Spec.Labels["com.docker.stack.namespace"]` 和 `Spec.Name` 分组。
- `/docker/services` 返回的是 Service 定义而不是“正在健康运行的副本数”。健康检查需进一步只读 Tasks/replica 数据，V1 可标记尚未验证。
- `Status:1` 仅作为 Portainer 状态字段存储，不能代表部署健康。
- GitConfig 中 `ConfigHash` 可能与 Commit 有关联，但先验证 GitLab 存在对应 ref/commit，再建立版本边。不能直接把它当成本次运行镜像 SHA。

## 5. 解析器优先级

1. Docker image/CI/Compose 中的 **完全相等 OCI image repository** 作为强证据；Tag 是可变条件，digest 更可信。
2. `Dockerfile` + CI build context + Maven module artifact 或 Go/Node 构建目录作为次强证据。
3. `pom.xml` modules、`settings.gradle` includes、`go.work`、`package.json workspaces` 等结构识别为 Module，不自动当成独立运行服务。
4. `README`/文件夹命名/禅道功能名称仅作为模糊候选。

## 6. 增量同步策略

- `ScanScope` 必须显式控制项目/组/端点以及扫描深度，默认不会全量扫完整 GitLab。
- GitLab 以 default_ref -> latest commit、ETag（若支持）比对，未变则复用 Snapshot。
- Portainer 以 Stack metadata/GitConfig/当前 Swarm ID 和 Service 列表的 fingerprint 判定变化。
- 禅道以 Bug updated_at/项目列表等权限可见字段增量；缺字段时按扫描 TTL。
- 增量任务可重试，但已审核关系只被标记 `needs_revalidation`，不能被覆盖或静默删除。

## 7. 只读验证实例

由用户本地单独配置 Token，运行：

```bash
# 默认使用模拟服务
dce doctor --mock
dce discover --fixture fixtures/synthetic-discovery.json

# 只有获得明确允许后，才在企业内网执行：
dce doctor --live --read-only
dce discover --live --read-only --gitlab-project <ID> --portainer-stack <ID>
```

不能在 GitHub Actions 里连接公司的私有网络；没有真实凭证也必须能完成全部单测。
