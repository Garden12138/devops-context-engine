# DCE 1.2 项目模式：主动初始化，日常只说 Bug ID

本模式通过 `--mode project` 开启，提供十个工具（原九个查询工具 + project_initialize）。默认 legacy 模式保持旧九工具兼容。Project Schema v1/v2 均可使用。

## 配置一次连接

沿用 [本地部署手册](LOCAL_DEPLOYMENT.md) 的非秘密 TOML 和0600凭证文件。升级执行 `uv sync --locked --dev`。下面是终端启动检查命令，不需要任何业务ID、固定工作区或Catalog：

```sh
cd /absolute/path/to/devops-context-engine
.venv/bin/python scripts/serve_dce_local.py \
  --mode project --live --read-only \
  --config "$HOME/.config/dce-trial/connections.toml" \
  --credentials-file "$HOME/.config/dce-trial/credentials.env"
```

STDIO会等待协议输入，Ctrl-C停止。实际使用时由Cursor启动自己的子进程。全局MCP定义示例（替换为实际绝对路径，不在JSON中使用~或$HOME）：

```json
{
  "mcpServers": {
    "dce": {
      "command": "/absolute/path/to/devops-context-engine/.venv/bin/python",
      "args": [
        "/absolute/path/to/devops-context-engine/scripts/serve_dce_local.py",
        "--mode", "project", "--live", "--read-only",
        "--config", "/Users/YOUR_NAME/.config/dce-trial/connections.toml",
        "--credentials-file", "/Users/YOUR_NAME/.config/dce-trial/credentials.env"
      ],
      "env": {"PYTHONUNBUFFERED": "1"}
    }
  }
}
```

项目私有状态默认保存在 `~/.local/state/dce/<工作区路径摘要>/`，可用 `--state-dir` 指定独立目录。目录0700，授权文件0600。凭证仍只在显式本机文件/进程中，Token Manager不持久化Token。DCE不自动修改既有Cursor配置、项目文件或旧缓存。

同一个启动配置可用于不同工作区；每个Host会话分别运行STDIO子进程。优先使用Host的MCP Roots。多个root时Agent请用户选择；没有Roots时Agent传当前工作区绝对路径，首次通过用户确认后才能读取项目上下文。会话中Root改变时拒绝继续查询，需建立新MCP会话，避免串项目。

## 用户主动初始化

连接、打开目录、新建聊天、调用project_context或查询Bug都不会初始化，也不会自动扫描平台。用户明确说：

> 请初始化当前工作区的DevOps关系。先分析本地仓库和模块，再查询必要的平台事实；展示候选、证据和访问范围，让我确认。

Host读取普通源码/构建配置和脱敏Git Remote，向DCE提供发现线索。不能读取.env、密钥、完整私有日志或执行README/CI中的命令。DCE没有内置推理模型，Host负责多对多关系推理。

| 步骤 | 工具/行为 | 结果 |
|---|---|---|
| 选定工作区 | project_context，必要时workspace参数 | uninitialized或已有项目上下文；不访问平台 |
| 开始发现 | project_initialize(begin) | 用户同意后取得30分钟临时发现许可 |
| 查看事实 | project_context分页；三个*_query工具补充 | 候选、来源、revision、观察时间、遗漏 |
| 审核提案 | project_initialize(review) | 显示完整关系与长期范围；返回审核文档和receipt |
| 保存 | Host组装全部文档页、写project.yaml | DCE不写业务工作区 |
| 激活 | project_initialize(complete, receipt) | 复读一致才ready；缺平台时partial |

合成begin参数（真实使用由Agent根据当前工作区/用户线索填写，不是启动参数）：

```json
{
  "operation": "begin",
  "seeds": {
    "gitlab_paths": ["demo/api"],
    "zentao_bug": "DEMO-1001",
    "portainer_search": "demo"
  }
}
```

GitLab路径应由Git Remote解析为namespace/project，平台主机来自既有连接配置；不接受任意上游URL。ZenTao也支持zentao_search，Portainer支持deployment_repositories（无凭证的HTTP/HTTPS仓库URL）。线索不足时Agent向用户询问项目名称或样例Bug，不扫描整个公司。目录查询每页20条、每类最多3页；Portainer无分页列表只读取一次受响应字节上限约束的元数据。超限/权限不足/未找到保留缺口，不推断“不存在”。

临时发现仅允许已定位资源的初始化元数据和有限构建/部署配置片段，不授权Bug正文、图片、CI Trace或服务日志。显式提供的样例Bug只取ID和项目/产品/模块归属，不向Host交付正文。

## 用户确认与保存

支持MCP原生表单时，直接在Host界面确认。否则返回 `approval_url`，Agent展示链接，用户在本机页面审核；只监听127.0.0.1随机端口。页面显示完整范围和提案，10分钟有效，POST/Origin/CSRF防护，一次性提交。提案变化会使旧确认链接/receipt失效。

填写真实审核人和原因；“确认关系ID”输入框可填写逗号分隔的关系ID，留空时关系保持候选。确认资源查询范围不等于确认所有业务关系。服务日志和部署不在此确认范围内。

Browser fallback不会阻塞一次MCP调用10分钟：工具返回awaiting_user_confirmation和URL；用户确认后，Agent以完全相同参数再次调用。不能用工具参数confirmed=true代替用户确认。若原生表单无法容纳完整提案，也使用本机页面，不截断后偷偷批准隐藏范围。

review通过后，结果为awaiting_host_save，返回document、revision、receipt和pagination。Agent按page/limit逐页取得文档（过大时缩小limit），组装完整relationships，保存 `.dce/project.yaml` 后调用complete。receipt只属于当前会话/工作区，有效期10分钟；重启或cancel后需重新审核。文件、Git roots、实例、Scope或文档版本不一致时拒绝激活。

## 日常使用与恢复

新聊天可直接说：

> 请处理Bug DEMO-1002：读取当前项目上下文、缺陷与证据，定位代码并修复、运行本地测试，列出涉及的GitLab项目和Portainer部署资源。不触发CI或部署。

Agent先读取project_context，再用对话中的Bug ID调用zentao_query/bug_context。服务端核对Bug真实Project/Product归属；两类范围同时配置时必须同时匹配。没有可靠归属、跨项目或响应ID不一致时拒绝返回正文；附件/图片使用相同检查。无需给每个Bug改白名单或重启。

GitLab/Portainer参数由Agent从已审核映射填写。Portainer服务按已授权Stack的namespace及当前Swarm过滤，不能借共享Endpoint读取其他Stack服务。声明镜像、Stack保存配置与实际运行服务分开取证；名字相似/latest/服务数量不构成版本或环境确认。

改变project.yaml不会扩大授权。未审核的变更显示changed_pending_review；新关系不得自称confirmed。已有项目收到普通begin会返回already_initialized。只有用户明确提出刷新后，Host才调用begin(refresh=true)重新发现、展示差异、审核和保存。拒绝关系、备注及未变化的已审核关系保持。

## 取消、撤销及独立日志

- project_initialize(cancel)：取消当前临时发现/待保存提案，不删除业务文件，不撤销之前的长期授权。
- project_initialize(revoke)：用户确认后撤销当前项目授权，同机其他进程下一次请求也会拒绝；不会删除project.yaml。
- 同时初始化的两个进程遇到授权版本变化时拒绝覆盖，要求重新审核。
- 日志默认关闭。单独批准后可在project模式追加 `--portainer-log-policy /absolute/private/grant.json`；不添加Stack级pair。策略必须属于已审核项目并精确绑定实例/Endpoint/Stack/Swarm/Service，复用现有短窗口、单次跨进程额度、失败也消费及撤销机制。文件缺失/过期/撤销不会放宽授权，普通元数据查询继续可用。

旧固定ID入口继续在legacy模式使用；project模式拒绝混入旧ID/Stack pair或显式本地凭证入口的单个catalog路径。不会自动把旧全局Catalog的confirmed迁成项目真相。

## 验证边界

自动化用合成平台验证真实SDK STDIO、原生确认回调和本机确认页。真实Cursor桌面Roots/表单/浏览器交互、公司平台兼容权限及真实Token过期恢复需分别实际验收；没有观察到的项目保持not_verified。模式扫描与Host确认不能认证被操作系统管理员控制的客户端，也不能代替企业数据授权。
