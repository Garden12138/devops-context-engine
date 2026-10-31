# 本地开发、验收与运维指南

本文件在 V1 实施后由 Agent 补充可运行命令，当前提供预期操作协议。

## 1. 前提

- macOS 或 Linux，Python 3.12+，uv（或项目确认的 pip 工具链）、git。
- 本地执行 Mock 不需要公司网络和 Token；线上只读验证需要 VPN/内网可达性及已授权的 read-only 凭证。
- 不推荐在公用服务器存储个人 PAT；不要使用公司运维管理员 Key 测试。

## 2. 预计操作

```bash
uv sync --dev
uv run pytest -q
uv run dce doctor --mock
uv run dce init --fixture fixtures/synthetic-discovery.json --no-ai
uv run dce catalog anomalies --format json
uv run dce mapping suggest --no-ai
uv run dce bug context DEMO-1001 --fixture fixtures/synthetic-discovery.json
```

本包是 specs，以上命令在生成代码并实现入口后才会可执行。不要把它误认为当前已经验证通过。

## 3. 私有网络配置

- 从 `.env.example` 复制到未提交的 `.env`；推荐通过 macOS Keychain 或会话环境导入凭证，不在仓库留存。
- 先 `dce doctor --live --read-only`，成功后 `dce discover --live --read-only --scope ...`；指定项目/Stack 范围。
- 通过显式 `NO_PROXY` 或代码层 proxy allowlist 确保内网直连，需遵守公司网络策略。不要禁用 HTTPS 证书验证；如使用企业 CA，传入证书链。

## 4. 常见错误

| 错误 | 处理 |
|---|---|
| ZenTao HTTP 200 HTML 图片 | 携 `Token` 请求，检查 MIME 和 PNG magic；仍为 HTML 则检查权限/会话 |
| GitLab 401/403 | 看 Token scope 与项目授权；不要自动升权 |
| GitLab 404 | 检查项目 ID 或 URL 编码路径、默认分支、文件路径 |
| Portainer Stack `Status=1` 无 Service | 校验 Endpoint current Swarm ID、Stack SwarmId 和 Namespace 标签 |
| Compose 78 vs saved 71 | 解释三类快照的时间差与配置漂移；不自动 redeploy |
| Tag `latest` | 使用 digest 和构建 SHA 追踪，若缺失则不确定 |
| AI 服务不可用 | 规则解析继续，候选保持 unresolved |

## 5. 变更恢复

- Catalog 本地修改前备份 SQLite，保持 migration 向前兼容；清理本地私有缓存需用户操作，不能在自动扫描时清空已审核历史。
- 若发现错误关系，`mapping review` 撤销/替换并保留审计事件；不要直接删除历史快照。
- 在 CI 安全失败后只记录失败摘要，不自动触发重试构建或部署。

## 6. V2 部署预检（非 V1 操作）

未来必须校验目标 Environment 的授权、Pipeline 成功、镜像 digest、Stack `SwarmId` 与当前 Cluster ID、准确的 Service/namespace、可回滚版本；请求单独审批。拒绝条件：历史 Stack、无确认业务映射、生产环境无审批、只有 `latest` 且无法识别精确镜像版本。
