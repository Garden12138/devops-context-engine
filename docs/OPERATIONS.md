# 本地安装、离线验收与只读运维

V1 使用 Python 3.12+、uv、SQLite。默认 synthetic fixture，不需要公司网络或凭证。
所有命令从仓库根目录运行；在其他目录启动 MCP 时，使用绝对路径。

## 安装与质量检查

```bash
uv sync --locked --dev
uv run --offline ruff check .
uv run --offline mypy src
uv run --offline pytest -q --cov=src/dce --cov-report=term-missing
uv build --offline
```

首次 sync 仅下载公共依赖，后续检查使用缓存。CI 不注入公司凭证；测试拒绝 IP 网络连接，HTTP 使用 MockTransport，MCP 使用本地 stdio 子进程。
可选启用本地提交检查：`git config --local core.hooksPath .githooks`。
钩子只检查暂存区敏感模式与空白错误，不读取 .env/密钥文件；人工审查仍必需。

## 可复现 Mock 演示

```bash
uv run --offline dce doctor --mock
uv run --offline dce init --fixture fixtures/synthetic-discovery.json --no-ai
uv run --offline dce catalog list --kind service --limit 20 --format json
uv run --offline dce catalog anomalies --format json
uv run --offline dce mapping suggest --offline
uv run --offline dce mapping review
uv run --offline dce bug context DEMO-1001 --fixture fixtures/synthetic-discovery.json
uv run --offline dce pipeline diagnose 1001 2001 --fixture fixtures/synthetic-discovery.json
uv run --offline dce stack inspect 102
```

预期：3 Stack、1 current Swarm、78 业务 Service、73 distinct images，5 组镜像复用。
102 的 saved 71 与 Git current 78 差集为 072–078；101/102 均 stale。
101/103 未提供完整 saved 内容，只保留合成计数与 incomplete，不能伪造版本一致性。
Bug 返回 2 张合成 PNG 的私有缓存路径、模块候选、证据和未确认提示；不会输出 base64。
Pipeline 的缺失 make 为失败根因，Buildx 镜像错误单独列出；不触发任何构建。
列表返回 cursor，下一页通过 `--offset` 指定；超预算显式 truncated/omissions/next_action。

## 人工审核与恢复

```bash
uv run --offline dce mapping review EDGE_UUID
uv run --offline dce mapping review EDGE_UUID --action accept --actor OWNER --reason REASON --expected-version VERSION
uv run --offline dce mapping review EDGE_UUID --action revoke --actor OWNER --reason REASON --expected-version NEW_VERSION
```

将占位值替换为预览结果。accept/reject/override/revoke 均留审计；过期预览会拒绝，须重新获取版本。
环境关联接受另需 `--confirm-environment`；stale 关系必须重新发现。
AI 默认关闭；Python 集成可注入 CandidateProvider/NoopProvider/FakeProvider，只有 ID/类型/证据白名单出域。
CLI 未注册云模型 HTTP 客户端；无 API Key 仍能运行全部核心流程。

## 用户本地真实平台 smoke

以下步骤由具备授权的用户执行。已取得三平台限定元数据、代表性源码项目 live discover、六工具处理与独立 SDK stdio 证据，见 [V1 验收状态](../harness/v1-acceptance-status.md)。更多发现范围、真实附件/Compose/失败日志仍未覆盖；下列通用命令不能整体视为所有外部路径均通过。业务系统页面操作、修复回归与发布执行不属于 DCE V1 验收，无需为此配置浏览器或辅助功能权限。
先通过系统密钥链或受保护进程环境注入 DCE_ZENTAO_URL/TOKEN、DCE_GITLAB_URL/TOKEN、DCE_PORTAINER_URL/TOKEN。
不将 Token 放在 CLI 参数、配置文件或公开报告中；DCE 不自动读取 .env。
使用 GitLab read_api、Portainer 限制 Environment 的只读账号、ZenTao 最小查看权限。
默认拒绝 HTTP；仅授权网络确实要求明文时由用户显式设置 DCE_ALLOW_HTTP=true。
TLS 验证保持开启；默认不继承代理环境，避免凭证发给未授权代理。企业 CA/代理差异应先在本地适配验证。

```bash
uv run dce doctor --live --read-only
uv run dce discover --live --read-only --gitlab-project PROJECT_ID --zentao-project ZENTAO_ID --portainer-endpoint ENDPOINT_ID
uv run dce bug context BUG_ID --live --read-only
uv run dce pipeline diagnose PROJECT_ID PIPELINE_ID --live --read-only
```

也可 `init --live --read-only --scope '{"gitlab_projects":["PROJECT_ID"]}'`；不允许空 scope。
ZenTao product、GitLab group、Portainer stack 均有对应 discover 参数，ID 不跨平台混用。
检查 doctor 能力、分页、主分支、图片 MIME/magic、Endpoint/Swarm/Namespace、三类快照差异。
Stack Status 不代表健康，latest 不代表版本指纹，名称不代表环境。
记录命令/退出码/能力与诊断代码，原始截图、日志、配置、内部地址留在私有区；公开报告只保留脱敏结论。
遇到版本不兼容、权限不足或图片 HTML，停止该资源核验，不升权、不尝试写路由。
Checkpoint 位于 Catalog 同目录 checkpoints/，仅存规范化元数据。重跑同范围会复用已完成 commit，变化版本重读。
失败批次不覆盖已确认映射，完整扫描的来源消失标为过期，其他活跃 scope 保留共享资源。

## MCP

Cursor 桌面版的安装、全局配置、启动、自检和排错见 [Cursor MCP 接入文档](CURSOR_MCP_SETUP.md)。stdio 由宿主管理进程；真实 Catalog、合成演示与实时上游模式分开配置，凭证不写 MCP JSON。

先准备对应模式的 Catalog；真实库不可用 fixture init 覆盖。下面仅为在仓库根目录手动启动合成演示的命令，Cursor 日常使用不需先运行它：

```bash
uv run --offline dce mcp serve --transport stdio --fixture fixtures/synthetic-discovery.json
```

六工具结果在 structuredContent，stdout 仅 JSON-RPC，日志 stderr；不提供审核、部署或 Pipeline 触发工具。
附件仅当前会话注册的 dce://assets 引用可读，校验大小/路径/指纹，不暴露上游 URL。
用户显式开启 live 时还需 --read-only；Bug/流水线分别由 --zentao-bug、--gitlab-project 重复参数限定上游读取。
未授权 ID 在请求前拒绝；Catalog 查询限于当前本地库。共享 HTTP 服务与多人鉴权属于后续版本。
Grok Bot 执行器与实际宿主的实时上游读取仍 not_verified；Cursor 的配置及进程启动证据单列在接入文档。

## 本地备份、回滚与移除数据

先停止 MCP/CLI 写入，用 Python sqlite3 backup API 或 sqlite3 的 .backup 生成 .local/ 下私有备份。
恢复时保持旧文件，使用备份替换 Catalog，并重新运行 doctor/mock 与 catalog 查询。
Schema 只支持 Alembic 前向迁移；不做破坏性 downgrade；审核撤销使用 review revoke。
若要移除本地数据，用户可先创建 private/，把整个 .local/ 移到 private/dce-retired/ 后确认再删除。
这两个目录均 gitignored；不要将备份移动到未忽略目录。移除只影响本机数据，不调用远端接口。

## 常见诊断

- AUTH_FAILED/PERMISSION_DENIED：核对只读 scope，勿自动升权。
- API_INCOMPATIBLE/INVALID_PAYLOAD：核对版本和返回结构，原始响应不进入错误输出。
- UNSAFE_URL：同源/HTTP/重定向边界阻止访问，勿绕过。
- RATE_LIMITED/NETWORK_UNAVAILABLE：有界退避后失败；检查 checkpoint，修复后重跑。
- SNAPSHOT_CONFLICT：不可变证据或审核版本已变化，保留旧快照，重新预览。
- OUTPUT_BUDGET_EXCEEDED：减小页大小或查询单个资源。

## 发布与许可审查

当前只保留本地工作分支，不 push、merge、建公开仓库或发布 Release。
未添加开源许可证：依原仓库发布指南，知识产权/公司授权未确认前不擅自授予许可。
这不影响本地离线验收；公开发布需所有者另行确认许可与历史数据审查。
