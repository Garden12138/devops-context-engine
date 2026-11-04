# 显式本地凭证入口与禅道 v1 登录

默认 `dce` 仍只读进程环境/非秘密 TOML，不自动加载 `.env`。用户明确提供本机凭证文件时，可使用独立启动入口 [serve_dce_local.py](../scripts/serve_dce_local.py)。凭证只由本机进程解析，不进入 MCP 参数、project.yaml、日志或持久化报告。

```text
/absolute/path/to/repo/.venv/bin/python /absolute/path/to/repo/scripts/serve_dce_local.py --config /absolute/private/connections.toml --credentials-file /absolute/private/.env --catalog /absolute/private/cache.sqlite3 --live --read-only --zentao-bug <authorized-id> --gitlab-project <authorized-id-or-path> --portainer-endpoint <authorized-id>
```

这是固定只读 stdio MCP 入口，scope 参数可重复，空范围拒绝。Host 的 command 使用虚拟环境 Python 的入口路径，不能把 Python 符号链接解析成全局解释器路径。Host args 填脚本及上述参数，stdout 只传 MCP，启动失败仅在 stderr 返回固定错误。

连接地址和实例别名来自 [connections.example.toml](../examples/connections.example.toml) 的私有副本。站点地址不能从 Token 推断；HTTP 默认拒绝，只有显式放行配置时可用。只保留当前需要接入的平台段。凭证别名映射：

| 本机字段 | 用途 |
|---|---|
| ZEN_USER / DCE_ZENTAO_ACCOUNT | 禅道 v1 account |
| ZEN_PASSWORD / DCE_ZENTAO_PASSWORD | 禅道 v1 password |
| GITLAB_TOKEN | DCE_GITLAB_TOKEN |
| PORTAINER_API_KEY | DCE_PORTAINER_TOKEN |
| DCE_ZENTAO_TOKEN | 已有 v1 Token；无账号密码输入时可直接使用 |

账号密码必须成对；存在时每次启动通过已有 Adapter 调用一次 v1 `/api.php/v1/tokens`，认证不附旧 Token、不自动重试密码，之后只使用返回的临时 Token。Token 不写回凭证文件；会话失效返回 AUTH_FAILED，修正/重新启动 MCP 后再登录。账号密码不进入子进程 argv，也不导出为 DCE Settings 字段。

凭证文件必须为受保护常规文件（0600），拒绝 symlink、超出 64 KiB、重复 key、别名冲突和无效格式。只处理已知变量；按字面值解析，保留密码内容，不运行 shell、不插值 `${...}`。未知变量不进入 DCE 配置。`--live --read-only` 缺失时不会打开凭证文件或登录。默认 Settings 的无 dotenv 行为有回归保护。

此入口通过合成 v1 认证和 MCP stdio 测试，不代表当前公司认证已成功。真实地址/权限/Host 仍按 [本轮验收](../harness/agent-led-acceptance.md) 分开记录。首次连接前需提供明确业务工作区、非秘密地址配置和授权资源范围。
