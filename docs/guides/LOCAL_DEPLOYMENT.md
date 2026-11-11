# macOS 本地部署与 Cursor 接入

适用交付：本地 `feature/upgrade-chatgpt`，包版本 **1.1.1**。DCE 运行方式是 Python CLI 和 Cursor 启动的 STDIO 子进程，无需 Docker、开放端口或后台 Web 服务。真实公司连接由用户本地配置；本轮验收完全离线。

## 1. 环境与代码准备

`pyproject.toml` 要求 Python >=3.12；本机实际验收 Python 3.12.11、uv 0.6.10、macOS arm64，精确依赖见 [本次摘要](../acceptance/acceptance-summary.json)。其他解释器/系统没有在本轮实测。需要 Git、uv；有 Homebrew 的 Mac 可准备：

```sh
brew install uv
git --version
uv --version
uv python install 3.12
```

安装 uv/Python 和首次依赖下载需要公网包源；验收命令本身强制离线。不要将下载失败解释为产品功能失败，先完成依赖准备。

统一使用 `feature/upgrade-chatgpt` 分支。首次从 GitHub 获取：

```sh
git clone --single-branch --branch feature/upgrade-chatgpt https://github.com/Garden12138/devops-context-engine.git /absolute/path/to/dce-local-trial
cd /absolute/path/to/dce-local-trial
uv sync --locked --dev --python 3.12
uv run --offline dce doctor --mock
```

使用现有交付仓库：

```sh
cd /absolute/path/to/devops-context-engine
git status --short
git switch feature/upgrade-chatgpt
uv sync --locked --dev --python 3.12
uv run --offline dce --help
uv run --offline dce doctor --mock
uv run --offline python scripts/run_acceptance.py
```

切换前若有未提交文件，先保存到自己的本地分支，不要 reset/clean。`uv sync` 自动建立 `.venv`，不需要手动 activate。

在同一 Mac 全新安装到另一个目录，可从本地交付仓库克隆。`--no-local` 避免本地优化复制/硬链接整个旧对象库，只传选定干净分支的可达对象：

```sh
git clone --no-local --single-branch --branch feature/upgrade-chatgpt /absolute/path/to/devops-context-engine /absolute/path/to/dce-local-trial
cd /absolute/path/to/dce-local-trial
uv sync --locked --dev --python 3.12
uv run --offline python scripts/run_acceptance.py
```

跨 Mac 搬运时，在原仓库创建仅含干净交付分支和 main 的本机 bundle，传输到另一台 Mac 后安装：

```sh
git bundle create /absolute/private/dce-local-trial.bundle main feature/upgrade-chatgpt
git bundle verify /absolute/private/dce-local-trial.bundle
git clone --branch feature/upgrade-chatgpt /absolute/private/dce-local-trial.bundle /absolute/path/to/dce-local-trial
```

远端仓库地址是 `https://github.com/Garden12138/devops-context-engine.git`。使用上面明确选择 `feature/upgrade-chatgpt` 的克隆命令；默认 main 仍是保留的旧基线。勿复制整个 `.local` 或旧历史备份作为安装包。

## 2. 无凭证体验

使用新的临时 Catalog，不触碰已有缓存：

```sh
DCE_TRIAL_DIR=$(mktemp -d /tmp/dce-trial.XXXXXX)
uv run --offline dce --catalog "$DCE_TRIAL_DIR/catalog.sqlite3" init --fixture fixtures/synthetic-discovery.json --no-ai
uv run --offline dce --catalog "$DCE_TRIAL_DIR/catalog.sqlite3" catalog anomalies
uv run --offline dce --catalog "$DCE_TRIAL_DIR/catalog.sqlite3" bug context DEMO-1001 --fixture fixtures/synthetic-discovery.json
uv run --offline python scripts/check_mcp_stdio.py --catalog "$DCE_TRIAL_DIR/catalog.sqlite3"
```

大合成 Catalog 的旧工具图查询可能按预算截断；checker 分别报告完整/截断读取并检查 omissions/next_action，不把截断当完整数据。默认 init 只采资源，关系语义由 Host 处理；显式旧演示才使用 `init --legacy-mapping`/`mapping suggest --offline`。合成结果不证明真实权限或部署状态。

## 3. 连接配置与凭证

推荐把本次试用配置放到自己新建的私有目录，例如 `~/.config/dce-trial`，不要写入仓库。以下命令创建目录/空文件，不清空现有文件：

```sh
umask 077
mkdir -p ~/.config/dce-trial
chmod 700 ~/.config/dce-trial
touch ~/.config/dce-trial/connections.toml
touch ~/.config/dce-trial/credentials.env
chmod 600 ~/.config/dce-trial/connections.toml ~/.config/dce-trial/credentials.env
```

用本机编辑器填入配置；不把真实凭证发给 Agent、放进聊天、命令参数或 Git。可以从 [非秘密连接模板](../../examples/connections.example.toml) 手动复制适用平台段：

```toml
allow_http = false
ai_enabled = false
output_budget = 16000

[zentao]
instance_id = "company-zentao"
base_url = "https://zentao.example.invalid"

[gitlab]
instance_id = "company-gitlab"
base_url = "https://gitlab.example.invalid"

[portainer]
instance_id = "company-portainer"
base_url = "https://portainer.example.invalid"
```

地址使用应用根，ZenTao 不要填安装包欢迎页、`/tokens` 或具体 Bug 页面。Portainer Endpoint ID 是另一个启动 Scope 参数，不是 base_url。一个进程每平台一个 instance；多个来源实例用独立 MCP 配置项。

凭证文件仅填写当前需要的平台；下面全是占位符：

```dotenv
DCE_ZENTAO_ACCOUNT=YOUR_ACCOUNT
DCE_ZENTAO_PASSWORD=YOUR_PASSWORD
DCE_GITLAB_TOKEN=YOUR_READ_API_TOKEN
DCE_PORTAINER_TOKEN=YOUR_SCOPED_API_KEY
```

ZenTao 支持账号+密码换取 REST v1 Token；也可仅用 `DCE_ZENTAO_TOKEN=YOUR_V1_TOKEN`。账号密码必须成对；Token 首读登录后只在内存缓存，明确失效时单次共享刷新/重放；直接 Token 模式失效要人工更新。真实过期恢复尚未现场验证。GitLab 使用限定项目的 read_api 权限，Portainer 使用限定 Environment 的只读权限；认证成功不等于所有方法都有权限。

独立入口支持 `ZEN_USER`/`ZEN_PASSWORD`、`GITLAB_TOKEN`、`PORTAINER_API_KEY` 等别名，完整列表与优先级见 [凭证契约](../AGENT_LED_LOCAL_CREDENTIALS.md)。同一文件别名冲突、重复 key、symlink、权限过宽或 >64 KiB 会拒绝。字面解析不执行 shell，不插值 `${...}`。默认 `dce` 不自动读取 dotenv。

优先级为显式 `DCE_*` 进程环境 > 明确指定文件 > 非秘密 TOML；Cursor 通常不继承交互 shell 的 export，因此推荐下面的显式文件入口。HTTP 默认拒绝；只有用户确认网络边界后才能在私有 TOML 显式 `allow_http=true`。不应为修复 403 自动扩大权限。

## 4. Scope 与 Cursor 配置

Scope 必须来自用户授权，并非 Agent 按同数字 ID 猜测。示例均为合成 ID：ZenTao Project 101/Product 201/Bug DEMO-1001、GitLab Project 301、Portainer Endpoint 1/Stack 7。替换为实际已批准 ID 后再启用。

编辑现有 `~/.cursor/mcp.json` 前自行保留私有备份，只追加/更新 `mcpServers.dce`，保留其他服务器。JSON 不支持注释，也不会展开 `~`、`$HOME` 或环境变量引用；下列所有路径必须替换为本机绝对路径：

```json
{
  "mcpServers": {
    "dce": {
      "command": "/absolute/path/to/devops-context-engine/.venv/bin/python",
      "args": [
        "/absolute/path/to/devops-context-engine/scripts/serve_dce_local.py",
        "--config", "/Users/YOUR_NAME/.config/dce-trial/connections.toml",
        "--credentials-file", "/Users/YOUR_NAME/.config/dce-trial/credentials.env",
        "--catalog", "/Users/YOUR_NAME/.config/dce-trial/catalog.sqlite3",
        "--live", "--read-only",
        "--require-platform", "zentao",
        "--require-platform", "gitlab",
        "--require-platform", "portainer",
        "--zentao-project", "101",
        "--zentao-product", "201",
        "--zentao-bug", "DEMO-1001",
        "--gitlab-project", "301",
        "--portainer-endpoint", "1",
        "--portainer-stack", "7"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

只连接部分平台时，删除未使用的 TOML 段、对应 `--require-platform` 与 Scope 参数。scope 可重复；空 allowlist 拒绝相关读取。`project.yaml` 中的 Scope 不会自动扩大 MCP 启动授权。默认无日志 grant。

必须保留 `.venv/bin/python` 入口路径，不要把符号链接解析成全局 Python。验证脚本参数：

```sh
.venv/bin/python scripts/serve_dce_local.py --help
.venv/bin/dce mcp serve --help
.venv/bin/python -c 'from importlib.metadata import version; print(version("devops-context-engine"))'
```

Cursor 中关闭再开启 DCE MCP 连接，必要时重载窗口/新会话。让 Agent 枚举工具，应有九个：bug_context、project_context、discovery_status、deployment_inspect、pipeline_diagnose、service_trace、gitlab_query、portainer_query、zentao_query。

初始化版本应为 1.1.1，Portainer revision 2.2，其余事实工具 2.1、兼容工具 1.1。握手说明保持稳定；实际调用 runtime 中的 PID/request_id 与 stderr 审计用于识别当前进程（预算太小时诊断字段可能省略）。工具可见不证明上游权限。先调用一个已授权资源，并检查 status/error、来源 instance、revision、observed_at、truncated/omissions。桌面按钮名称随 Cursor 版本变化，本轮只自动化验证 SDK STDIO，没有实测当前桌面 UI。

也可仅用受保护进程环境启动 `.venv/bin/dce --config ... --catalog ... mcp serve --transport stdio --live --read-only ...`；账号密码模式与显式文件加载使用脚本入口。STDIO 等待协议输入时终端无提示是正常现象，不能向 stdout 加调试 print。

## 5. 日志默认关闭与单次授权

普通配置不得加日志参数。用户单独批准精确服务日志读取后：

1. 先用已授权的 portainer_query stack/swarm_info/service 只读核对 Endpoint、Stack ID/Name、Swarm ID、namespace、完整 Service ID/Name、Compose key。不能靠服务名前缀或 test 字符串猜环境。
2. 在专用 0700 目录用本机编辑器创建 0600 `service-log-grant.json`。完整字段用 [Gate B 合成格式](../GATE_B_PREFLIGHT.md)；替换准确身份，生成新的 grant_id，issued_at/expires_at 带时区且 TTL <=1 小时。示例旧日期已过期，不能直接当授权。
3. 只在该次 MCP 配置追加 `--portainer-log-scope 1:7` 与 `--portainer-log-policy /absolute/private/service-log-grant.json`，保留原元数据 Scope。单独 pair 是较宽的 Stack 级兼容授权，不满足精确单次需求。
4. 重载后按 [用户教程 12](USER_GUIDE.md#12-查询限定服务日志) 查询一个服务，窗口 <=300 秒且不在未来，最多20行、16KiB原始读取/8KiB输出/10秒。代码固定 follow=false，日志 GET 不重试。
5. 同一策略文件的进程共享 `.log-grant-<grant_id>.used` 原子额度；失败、超时、取消也消耗，禁止删除标记再试。
6. 读取后把本次策略文件重命名为私有 `.revoked`（不要覆盖既有文件），保留 used 标记；删除此次新增的两个 MCP 日志参数，重载。原路径消失会使仍在运行的旧进程立即拒绝日志。撤销参数前若直接重载，启动失败是安全拒绝，不会回退为宽授权。

不生成真实授权文件、不修改真实配置是本轮执行边界；上面是用户未来的本机操作说明。日志输出只含固定事件/统计，空/截断不能证明业务没发生；保留期默认 not_verified。

## 6. 更新、重新安装、构建和停止

后续本地开发统一在 `feature/upgrade-chatgpt`。更新前停用 Cursor 的 DCE 连接并保存当前改动，确认新的本地提交后：

```sh
git status --short
git switch feature/upgrade-chatgpt
uv sync --locked --dev
uv run --offline python scripts/run_acceptance.py
```

需要同步 GitHub 的已推送更新时，先保留本地改动并运行 `git pull --ff-only origin feature/upgrade-chatgpt`；发生分叉先审查差异，不强制覆盖。重新安装包可 `uv sync --locked --dev --reinstall-package devops-context-engine`；完整重装优先采用第 1 节的全新目录，保留旧凭证/业务文件/Catalog，避免直接删除 `.venv` 或 `.local`。

构建并在新环境安装 Wheel：

```sh
uv build --wheel --offline --out-dir /absolute/new-build-output
uv venv --python 3.12 /absolute/new-trial-venv
uv pip install --python /absolute/new-trial-venv/bin/python /absolute/new-build-output/devops_context_engine-1.1.1-py3-none-any.whl
/absolute/new-trial-venv/bin/dce --help
```

单独 pip 安装可能按包约束选择其他依赖版本；严格锁定依赖的全隔离安装已由一键验收中的 `uv sync --locked --offline --no-dev --no-install-project` + 独立 `UV_PROJECT_ENVIRONMENT` 执行。缺缓存时如实 BLOCKED。不要用全局 site-packages 冒充隔离安装。

停止：在 Cursor 停用 DCE MCP；手动终端服务用 Ctrl-C。无守护服务需卸载。升级旧 Catalog 前停用所有访问同库进程，按 [迁移/备份手册](../AGENT_LED_MIGRATION.md) 保留私有 SQLite backup；不要删除业务 `.dce` 作为“重装”。

## 7. 排错

| 现象 | 检查与处理 |
|---|---|
| uv offline 缺缓存 | 首次运行 `uv sync --locked --dev` 准备包；构建后端也需缓存。保留 BLOCKED 结果，勿跳过构建 |
| ModuleNotFoundError | 使用仓库 `.venv/bin/python`，运行 uv sync，核对 Wheel 环境与源目录隔离 |
| MCP 连接失败 | 查 stderr 的固定错误；绝对路径、0600、平台必需项、Scope、参数在 --help 中是否存在 |
| 九工具/版本仍旧 | 关闭旧连接并重载；核对 command 指向当前安装；用 runtime 而非缓存说明 PID 判断 |
| AUTH_FAILED/AUTH_EXPIRED | 分清账号密码或直接 Token 模式；不循环重试密码，修正私有文件后重启 |
| 普通 403/module_tree 拒绝 | 核对产品 ID 和方法查看权限；不把方法权限误判为 Token 过期 |
| PERMISSION_DENIED | 核对 instance 与启动 allowlist；项目 YAML 不会授权；日志需独立 pair+精确策略 |
| NOT_FOUND | 核对平台资源 ID/应用根与版本；不枚举未授权项目或猜路由 |
| 空页/输出不全 | 查 pagination、truncated、omissions；缩小范围或翻页，不能直接判“不存在” |
| 日志已用/过期/撤销 | 保留消费证据，停止读取；需要新的人工授权，不删除标记恢复额度 |

使用入口：[用户手册](USER_GUIDE.md)；边界：[安全文档](../SECURITY.md)；当前验收：[报告](../acceptance/AUTOMATED_ACCEPTANCE.md)。
