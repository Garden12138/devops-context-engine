# Agent 协作协议（DCE 2.0，Codex / Cursor 通用）

1. 当前目标是 DCE 2.0「缺陷闭环」。先读 `docs/v2/README.md`，按 `docs/v2/05-实施计划.md` 的里程碑顺序实施。1.x 的代码和文档已废弃（本地 tag `v1.2.0-final`），不要参考或恢复。
2. 范围以 `docs/v2/02-需求规格.md`、`03-架构设计.md`、`04-工具契约.md` 为准，不实现文档以外的功能。文档有矛盾或不清楚时，停下来，写进 `docs/v2/progress.md` 的“待确认”一节，并告诉用户。
3. 禁止添加：审批 Broker、本机审批网页、receipt、hash 往返校验、MCP Roots 协商、关系状态机（proposed/confirmed 等）、通用平台查询工具、日志授权文件。人工确认靠 Playbook 和宿主自带的工具调用确认。
4. 平台写操作只允许 03 第 7.1 节的白名单，目标必须通过 `loop/guard.py`。git 永不 force push，合并目标永不匹配 `master`、`main`、`release*`、`prod*`、`uat*`。
5. 本仓库可能公开：只用合成数据（主机用 `*.example.invalid`），不提交私有 IP、真实仓库名、服务名、账号、Token、`.env`、截图。真实环境事实只放在 `.local/`（已 gitignore）。
6. 不读取、不输出凭证文件内容。测试不访问网络：HTTP 用 `httpx.MockTransport`，git 用临时目录里的本地仓库。
7. 先写测试再实现。一个任务一个本地提交（Conventional Commits）。不 push、不建 MR、不改其他分支。
8. 每个任务都运行 `uv run pytest -q`、`uv run ruff check .`、`uv run mypy`，结果写一行到 `docs/v2/progress.md`。里程碑结束时，提示用户做 `docs/v2/06-验收标准.md` 中对应的现场验收；现场验收通过前，不开始下一个里程碑。
9. 错误信息必须具体：哪个平台、哪个资源、上游状态码、判断出的原因、下一步怎么做。禁止把不同故障折叠成同一句笼统的话。
10. 给用户的回复保持简短：做了什么、测试结果、下一步。不要写长篇治理或验收报告。
