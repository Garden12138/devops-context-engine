# 显式本地凭证入口与禅道 v1 登录

默认 `dce` 仍只读进程环境/非秘密 TOML，不自动加载 `.env`。用户明确提供本机凭证文件时，可使用独立启动入口 [serve_dce_local.py](../scripts/serve_dce_local.py)。凭证只由本机进程解析，不进入 MCP 参数、project.yaml、日志或持久化报告。

```text
/absolute/path/to/repo/.venv/bin/python /absolute/path/to/repo/scripts/serve_dce_local.py --config /absolute/private/connections.toml --credentials-file /absolute/private/.env --catalog /absolute/private/cache.sqlite3 --live --read-only --zentao-bug <authorized-id> --gitlab-project <authorized-id-or-path> --portainer-endpoint <authorized-id>
```

这是固定只读 stdio MCP 入口，scope 参数可重复，空范围拒绝。Host 的 command 使用虚拟环境 Python 的入口路径，不能把 Python 符号链接解析成全局解释器路径。Host args 填脚本及上述参数，stdout 只传 MCP，启动失败仅在 stderr 返回固定错误。

需要三平台的当前Cursor定义另加 `--require-platform zentao --require-platform gitlab --require-platform portainer`，缺连接时在STDIO前停止，不做网络探测或新增授权。此入口也支持独立的 `--portainer-log-scope ENDPOINT:STACK`，但默认不授予，且必须已有对应元数据scope及人工日志读取授权。本地入口成功启动/调用的固定审计写stderr，不含业务参数；用既有request_id对照PID和Schema。详见 [Host修复与重载](CURSOR_HOST_V1_1_1.md)。

连接地址和实例别名可来自 [connections.example.toml](../examples/connections.example.toml) 的私有副本，也支持用户明确指定文件中的 URL 别名。优先级为显式进程 `DCE_*` 环境、指定本机文件、TOML；同一文件的别名与规范字段冲突时拒绝。站点地址不能从 Token 推断；HTTP 默认拒绝，只有显式放行配置时可用。只保留当前需要接入的平台段。字段映射：

| 本机字段 | 用途 |
|---|---|
| ZEN_URL | DCE_ZENTAO_URL |
| GITLAB_URL | DCE_GITLAB_URL |
| PORTAINER_URL | DCE_PORTAINER_URL |
| ZEN_USER / DCE_ZENTAO_ACCOUNT | 禅道 v1 account |
| ZEN_PASSWORD / DCE_ZENTAO_PASSWORD | 禅道 v1 password |
| GITLAB_TOKEN | DCE_GITLAB_TOKEN |
| PORTAINER_API_KEY | DCE_PORTAINER_TOKEN |
| DCE_ZENTAO_TOKEN | 已有 v1 Token；无账号密码输入时可直接使用 |

账号密码必须成对；V1.1.1 起，启动只建立进程内 Token Manager，第一次通过本地授权的禅道读取才经已有 Adapter 调用 v1 `/api.php/v1/tokens`。认证不附旧 Token/Cookie、不自动重试密码，成功后缓存临时 Token。明确的认证失效仅重新登录并重放原 GET 一次；并发失效共享一次登录，普通 403、网络错误及本地 scope 拒绝不触发刷新。没有可信有效期就不猜测 TTL。登录失败或刷新后仍失效会停止登录，修正后重启 MCP。Token 不写回文件；账号密码不进入子进程 argv 或公开 Settings 字段。只有直接 Token、没有账号密码时，失效仍需人工更新并重启。详见 [认证恢复契约与错误分类](ZENTAO_AUTH_RECOVERY.md)。

凭证文件必须为受保护常规文件（0600），拒绝 symlink、超出 64 KiB、重复 key、别名冲突和无效格式。只处理已知变量；按字面值解析，保留密码内容，不运行 shell、不插值 `${...}`。未知变量不进入 DCE 配置。`--live --read-only` 缺失时不会打开凭证文件或登录。默认 Settings 的无 dotenv 行为有回归保护。

禅道 URL 必须指向实际应用根，安装包欢迎页不等于应用入口。若认证路由 404，先区分站点入口与 API 版本；仅按实际观察到的同源链接核对，不枚举猜测路径。核实的应用 URL 可用显式进程 `DCE_ZENTAO_URL` 覆盖，避免修改原凭证文件。不会自动跟随带认证的跨源入口。

此入口已通过合成 v1 认证、MCP stdio 测试和本轮真实 v1 登录/限定读取；接口权限、真实图片及实际 Agent Host 按 [本轮验收](../harness/agent-led-acceptance.md) 分开记录。首次连接仍需明确业务工作区和授权资源范围。

图片可通过非秘密 TOML `image_output_budget` 或进程 `DCE_IMAGE_OUTPUT_BUDGET` 显式扩大原生图片结果预算（最大 3000000 字节）；不扩大文本 JSON/元数据预算，不改变 2MB 原图读取上限，也不扩大授权 Bug 范围。未配置时保持原预算。账号密码换 Token 能读取某些 v1 资源，不等于所有 v1 入口均可访问；同 Token 的 Bug 200、模块入口 403 应分别记录，不重新索取密码或直接要求管理员权限。

本轮模块入口的脱敏错误为 `Access not allowed`。官方 v1 [模块 GET](https://github.com/easysoft/zentaopms/blob/main/api/v1/entries/modules.php) 调用 tree/browse；[loadController 与 checkPriv](https://github.com/easysoft/zentaopms/blob/main/framework/api/entry.class.php) 对该方法单独检查权限并返回同样的 403。由此推断需核对账号权限组的 tree/browse 入口及产品范围；这是独立方法权限，不说明 Token 登录错误，也未证明当前实例版本与官方 main 相同。可让实例管理员核对读入口，无需把管理员 Token 提供给 DCE。
