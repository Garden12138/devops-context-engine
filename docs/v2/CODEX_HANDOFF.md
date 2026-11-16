# 交给 Codex 的执行提示

## 怎么用（给 andy）

1. 在 Codex 中打开本仓库目录，切到 `feature/v2-bugfix-loop` 分支。权限选“工作区可写 + 需要时询问”（CLI 为 `codex --sandbox workspace-write --ask-for-approval on-request`）。只有 M0 的 `uv lock` / `uv sync` 需要联网，Codex 会来问。
2. **每个里程碑新开一个 Codex 会话**，把第 2 节中对应里程碑的代码块整块复制粘贴进去。不要一次让它做多个里程碑。
3. 里程碑完成后，按 Codex 最后给出的清单，在 Cursor 里做 `06-验收标准.md` 中对应的现场验收（M0 不需要）。通过后再开下一个里程碑。
4. 中途中断、验收失败、回答它的“待确认”问题、发现它跑偏时，用第 3 节的提示。

第 1 节是写给 Codex 的通用规则，每个里程碑的提示都会让它先读这一节。你不需要单独粘贴第 1 节。

---

## 1. 通用执行规则（Codex 每次都要遵守）

### 1.1 阅读顺序

1. `AGENTS.md`
2. 本文件第 1 节
3. `docs/v2/README.md`、`01-诊断与重构决策.md`、`02-需求规格.md`
4. `docs/v2/03-架构设计.md`、`04-工具契约.md`
5. `docs/v2/05-实施计划.md` 的“全局约束”“文件结构总表”，以及本次里程碑那一节
6. `docs/v2/06-验收标准.md` 中本次里程碑对应的现场验收
7. `docs/v2/progress.md`（M0 之后存在）和 `git log --oneline -20`

### 1.2 执行方式

1. 严格按 05 中的任务顺序执行。每个任务：先写测试 → 实现 → `uv run pytest -q`、`uv run ruff check .`、`uv run mypy` 全部通过 → 单独提交（Conventional Commits）→ 在 `docs/v2/progress.md` 加一行。
2. `progress.md` 每行格式：`| 日期 | 任务 | 提交短 SHA | 测试数 / 覆盖率 | 现场验收 | 偏差或备注 |`。现场验收一栏由用户验收后填写，你填 `—`。
3. 05 和 03/04 里给出的文件路径、函数名、参数、错误码、工具名、返回字段，是跨任务的约定，不要改名。确实需要改时，同时修改所有引用的文档，并在提交说明里写明原因。
4. 设计文档（02/03/04）与计划（05）冲突时以设计文档为准。发现设计本身有问题时，先停下来说明问题和建议，不要自己另起炉灶。
5. 每完成一个任务，用三到五行汇报：做了什么、测试结果、当前非测试代码行数（`find src -name '*.py' -exec cat {} + | wc -l`）、与计划的偏差。
6. 里程碑全部完成后：汇总本里程碑的提交列表和测试结果；把 06 中对应现场验收整理成用户可以直接照做的清单（要创建或修改的文件、要在 Cursor 里说的话、每步看什么算通过）；然后停止，不要开始下一个里程碑。

### 1.3 必须先停下来问用户的情况

- 需要联网（`uv lock`、`uv sync`、`uv add`），或需要新增 05 列表之外的依赖。
- 需要访问真实的禅道、GitLab、Portainer，或读写业务工作区（路径见 `.local/v2/field-facts.md`）。开发阶段不需要做这些，真实验证由用户在现场验收中完成。
- 文档有矛盾、缺信息，或你认为设计有问题。把问题写进 `progress.md` 的“待确认”一节，编号，然后停下。
- 非测试代码行数超出第 1.6 节预算的 20% 以上。
- 想增加计划之外的工具、命令、配置项、返回字段或错误码。

### 1.4 明确禁止（1.x 就是因为这些变得不可用的）

- 不要添加审批 Broker、本机审批网页、CSRF、receipt、hash 往返校验、TTL 许可、MCP Roots 协商、关系状态机（proposed/confirmed/stale…）、证据账本、通用平台查询工具、日志授权文件。
- 不要把多种失败折叠成一句笼统的错误信息。每个错误都要说明：哪个平台、哪个资源、上游状态码、判断出的原因、下一步怎么做。
- 不要写验收报告、证据清单、阶段总结文档。`docs/v2/` 下只允许存在：`README.md`、`01`–`08` 编号文档、`CODEX_HANDOFF.md`、`progress.md`。
- 不要在工具描述、文档、错误信息里写否定式免责声明（例如“这不代表……”“不能据此推断……”）。只写做什么、需要什么前置条件、出错了下一步怎么办。
- 不要从 tag `v1.2.0-final` 整块恢复旧代码。只迁移 05 中点名保留的模块。
- 测试不得访问网络：HTTP 一律用 `httpx.MockTransport`，git 一律用 `tmp_path` 下的 bare 仓库和 clone。
- 仓库内（代码、测试夹具、文档、示例）只能出现合成名字：仓库用 `demo-*`，主机用 `*.example.invalid`。你可以读 `.local/v2/field-facts.md` 了解真实 CI 和部署的写法，但不得把其中任何真实名字、地址、ID、账号写进仓库。
- 不要读取或输出 `~/.config/dce/`、任何 `.env` 或凭证文件的内容。
- git：不要 push，不要建 MR，不要改其他分支；代码和测试里不得出现 `--force`/`-f` 推送。

### 1.5 现场验收发现真实平台行为与设计不符时

以实测为准：修改 03/04 中对应的章节，同步修改测试的期望值（测试数据仍用合成名字），在提交说明里写“根据现场验收调整：<一句话说明>”，并在 `progress.md` 备注列写明。

### 1.6 非测试代码行数预算（统计 `src/`）

| 里程碑结束时 | 预算（行） |
|---|---|
| M0 | 1800 |
| M1 | 3500 |
| M2 | 4500 |
| M3 | 5400 |
| M4 | 5900 |
| M5 | 6500 |

持续明显超出预算，通常意味着开始过度设计。此时对照第 1.4 节自查，再决定是否停下来问。

---

## 2. 里程碑提示（每个里程碑新开会话，整块粘贴）

### M0 清场与骨架

```text
你在 devops-context-engine 仓库（当前工作目录）的 feature/v2-bugfix-loop 分支上工作，执行 DCE 2.0 的里程碑 M0（清场与骨架）。

1. 先按 docs/v2/CODEX_HANDOFF.md 第 1.1 节的顺序阅读文档，并遵守第 1 节全部规则。
2. 按 docs/v2/05-实施计划.md 的 T0.1 → T0.2 → T0.3 执行，每个任务一个提交。
3. 本里程碑要点：
   - 本地 tag：git tag v1.2.0-final fa3573f。只建 tag，不推送。
   - 删除范围以 T0.1 为准。删除前用 git ls-files 列出将删除的路径，与 T0.1 逐项核对；有不在 T0.1 列表里的文件，停下来问我。
   - 保留并迁移的模块：http、zentao_auth、zentao、gitlab、portainer、docker_logs、redact、errors、config 与 local_credentials（合并为 settings.py）。迁移时去掉对已删除模块（catalog、project、log_grant 等）的引用。
   - Portainer 迁移时，service_logs 去掉日志授权文件参数（ServiceLogGrant）；1.x 的 Stack/Swarm 校验逻辑可以保留，M4 时再按 03 第 6.4 节调整。
   - settings.py 的配置错误要具体（见 05 的 T1.1 用例）。T0.2 只做到保留原有测试通过，具体报错在 T1.1 完成。
   - uv lock 需要联网，先问我。
   - 创建 docs/v2/progress.md（表头和“待确认”一节）。
4. 完成标准：uv run pytest -q、uv run ruff check .、uv run mypy 全部通过；uv run dce --version 输出 2.0.0；scripts/check_public_data.py 通过。
5. 按第 1.2 节汇报，并附：删除的目录列表、保留模块的新路径、非测试代码行数。M0 没有现场验收，请提醒我检查删除范围的 diff。然后停止，不要开始 M1。
```

### M1 配置、扫描、自检

```text
你在 devops-context-engine 仓库（当前工作目录）的 feature/v2-bugfix-loop 分支上工作，执行 DCE 2.0 的里程碑 M1（配置、扫描、自检）。

1. 先按 docs/v2/CODEX_HANDOFF.md 第 1.1 节的顺序阅读文档，并遵守第 1 节全部规则。检查 progress.md：M0 未完成，或有未答复的“待确认”，就停下来告诉我。
2. 按 05 的 T1.1 → T1.8 执行，每个任务一个提交。
3. 本里程碑要点：
   - CI 解析严格按 03 第 5.1 节：支持 extends（多层、深度合并）、变量优先级、$VAR 与 ${VAR}、脚本里的 export、rules 中的分支条件、trigger 子流水线、compile/build 通过 needs 配对、去掉开头未定义的 registry 变量。不要复用旧 parsers/metadata.py 的 ci()。
   - 测试夹具按 05 的 T1.3 写成合成文件，覆盖三种形态（模板加子流水线的 Maven 多模块、直接 job 的前端、只发布 jar 的库）和一个未知表达式反例。可以参考 .local/v2/field-facts.md 里真实 CI 的结构，但名字一律用 demo-*。
   - scan 用 ruamel.yaml 写出带注释的 dce.yaml：不确定处写 “# TODO(确认): 原因”；已有 dce.yaml 时只写 dce.proposed.yaml 和差异，绝不覆盖。
   - workspace 定位按 03 第 3.4 节，不调用 MCP roots/list。
   - doctor 的检查项 id 与 04 第 1 节一致；除 portainer.write、zentao.resolve 两项固定 warn 外，每项都有 pass 和 fail 测试；两项固定 warn 各测试状态及首次使用验证提示。
   - mcp_server.py 注册全部 12 个工具，未实现的返回 NOT_IMPLEMENTED；text content 与 structuredContent 内容相同。
4. 完成标准：全部测试通过；workspace、loop、platforms 覆盖率 ≥ 80%；tests/test_mcp_stdio.py 能列出 12 个工具并调用 dce_status。
5. 按第 1.2 节汇报。最后把 06 的“共同前置”和 R1 整理成我在 Cursor 里可以直接照做的清单，包括：
   ~/.config/dce/connections.toml 的内容；凭证文件需要哪些键（只写键名）；业务工作区 .cursor/mcp.json 的完整内容（用本机实际的 .venv/bin/dce 路径；业务工作区路径从 .local/v2/field-facts.md 读取，只写在给我的回复里，不写进仓库）；要删除的全局 dce 配置；要说的话；每步看什么算通过。
   然后停止，不要开始 M2。
```

### M2 缺陷读取与部署计划

```text
你在 devops-context-engine 仓库（当前工作目录）的 feature/v2-bugfix-loop 分支上工作，执行 DCE 2.0 的里程碑 M2（缺陷读取与部署计划）。

1. 先按 docs/v2/CODEX_HANDOFF.md 第 1.1 节的顺序阅读文档，并遵守第 1 节全部规则。检查 progress.md：M1 的现场验收 R1 没有标 PASS，或有未答复的“待确认”，就停下来告诉我。
2. 按 05 的 T2.1 → T2.5 执行，每个任务一个提交。
3. 本里程碑要点：
   - bug_get 先校验产品，不符时不解析正文、不下载图片（测试断言 MockTransport 没收到图片请求）。图片作为 MCP ImageContent 返回，默认最多 6 张。
   - 缺陷历史字段（actions）真实格式未确认：有就整理，没有就返回空列表并加 HISTORY_UNAVAILABLE 警告，不要猜字段。
   - 运行记录按 03 第 4 节：原子写、文件锁、events 只追加。
   - 部署计划按 03 第 6.1 节的 9 个步骤，警告码与 04 第 5 节一致；summary 表格的列与 03 第 6.1 节完全一致。
   - git 操作全部用 subprocess 列表参数、shell=False、GIT_TERMINAL_PROMPT=0、超时；测试用 tests/gitfixture.py 的本地 bare 仓库。
4. 完成标准：全部测试通过；覆盖率 ≥ 80%；stdio 测试能调用 deploy_plan（只用 git 夹具）。
5. 按第 1.2 节汇报。最后把 06 的 R2 整理成我可以直接照做的清单（要说的话、预期结果、怎么对照历史的“打包部署顺序表”）。然后停止，不要开始 M3。
```

### M3 合并与构建

```text
你在 devops-context-engine 仓库（当前工作目录）的 feature/v2-bugfix-loop 分支上工作，执行 DCE 2.0 的里程碑 M3（合并与构建）。

1. 先按 docs/v2/CODEX_HANDOFF.md 第 1.1 节的顺序阅读文档，并遵守第 1 节全部规则。检查 progress.md：R2 没有标 PASS，或有未答复的“待确认”，就停下来告诉我。
2. 按 05 的 T3.1 → T3.5 执行，每个任务一个提交。
3. 本里程碑要点：
   - 写接口白名单严格等于 03 第 7.1 节的 7 条，写在 platforms/http.py；不在白名单的请求在发出前抛 PERMISSION_DENIED。写请求不重试。
   - guard.py 的每个检查都要有正反例；不符时 message 写明是哪一项不符。
   - 合并只在 .dce/tmp 下的临时 detached worktree 中进行，不切换用户当前检出的分支，不改用户工作副本。冲突时 abort 并删除临时 worktree。push 永远是普通推送。测试要断言用户工作副本的 HEAD 不变，以及调用记录中没有 --force/-f。
   - merge_to_test 在 gates.merge == always 时要求 approved_by_user=true。
   - ci_build 可以重复调用，只处理需要动作的 job（03 第 6.3 节第 4 步）；ci_status 只读，测试断言它只发 GET。
   - 只 play 计划内的 job；job 缺失时每仓库每个 run 最多新建一次流水线。
   - 轮询用可注入的时钟，测试里不真正 sleep。
4. 完成标准：全部测试通过；覆盖率 ≥ 80%。
5. 按第 1.2 节汇报。最后把 06 的 R3 整理成我可以直接照做的清单（怎么挑一个小缺陷、G2 时 Agent 应展示什么、Cursor 弹窗确认、在 GitLab 上核对什么）。然后停止，不要开始 M4。
```

### M4 部署与核验

```text
你在 devops-context-engine 仓库（当前工作目录）的 feature/v2-bugfix-loop 分支上工作，执行 DCE 2.0 的里程碑 M4（部署与核验）。

1. 先按 docs/v2/CODEX_HANDOFF.md 第 1.1 节的顺序阅读文档，并遵守第 1 节全部规则。检查 progress.md：R3 没有标 PASS，或有未答复的“待确认”，就停下来告诉我。
2. 按 05 的 T4.1 → T4.3 执行，每个任务一个提交。
3. 本里程碑要点：
   - 部署前置条件：build 成功且不是旧构建；不满足的服务标 skipped 且不发写请求，全部跳过时返回 PRECONDITION_FAILED（03 第 6.4 节）。
   - 守卫：集群 ID、stack namespace、镜像仓库路径、endpoint 都必须与配置一致。
   - 首选 PUT /api/endpoints/{id}/forceupdateservice（PullImage=true，X-Registry-Auth 为 base64 的 {"registryId": N}）；返回 404/405 时回退到 docker service update（ForceUpdate+1、去掉 @sha256、带 version）。两条路径都要测试。
   - 判定 converged/updating/failed/digest_unverified 按 03 第 6.4 节；日志复用 docker_logs.py 并脱敏，不需要日志授权文件。
4. 完成标准：全部测试通过；覆盖率 ≥ 80%。
5. 按第 1.2 节汇报。最后把 06 的 R4 整理成我可以直接照做的清单（含“构建未完成时部署应被跳过”的负向验证，以及在 Portainer 页面核对什么）。然后停止，不要开始 M5。
```

### M5 验证、记录、禅道与 Playbook

```text
你在 devops-context-engine 仓库（当前工作目录）的 feature/v2-bugfix-loop 分支上工作，执行 DCE 2.0 的里程碑 M5（验证、记录、禅道与 Playbook）。

1. 先按 docs/v2/CODEX_HANDOFF.md 第 1.1 节的顺序阅读文档（本次还要读 docs/v2/07-Playbook.md），并遵守第 1 节全部规则。检查 progress.md：R4 没有标 PASS，或有未答复的“待确认”，就停下来告诉我。
2. 按 05 的 T5.1 → T5.5 执行，每个任务一个提交。
3. 本里程碑要点：
   - bug_resolve 的前置条件、请求体、备注模板、复读确认严格按 03 第 6.5 节；只开放 resolve，不实现 close。
   - run_update 的 evidence 路径必须在工作区内且文件存在；record.commit 必须能在 records 仓库中找到。
   - skills/dce-bugfix-loop/SKILL.md 和 record-template.md 从 07 原样拷贝，不要改写内容；dce install-skill 已存在时先显示差异，加 --force 才覆盖。
   - docs/v2/08-使用指南.md 不超过 200 行。
   - 删除临时的 NOT_IMPLEMENTED 错误码，确认 12 个工具都已实现。
4. 完成标准：全部测试通过；覆盖率 ≥ 80%；非测试代码不超过 6500 行。
5. 按第 1.2 节汇报。最后把 06 的 R5 整理成我可以直接照做的清单（安装 Skill 的两条命令、新对话里要说的话、各确认点我该看什么、结束后在禅道和修复记录里核对什么、如何验证新会话能恢复 run）。然后停止。
```

---

## 3. 其他场景提示

### 中途接续（上一个 Codex 会话中断）

```text
你在 devops-context-engine 仓库（当前工作目录）的 feature/v2-bugfix-loop 分支上继续 DCE 2.0 的里程碑 M<N>，上一个会话中途中断了。

1. 按 docs/v2/CODEX_HANDOFF.md 第 1.1 节阅读文档，遵守第 1 节全部规则。
2. 查看 docs/v2/progress.md、git log --oneline -20、git status，判断 M<N> 最后完成的是哪个任务。
3. 有未提交的改动时：如果属于下一个任务，并且补完后测试能通过，就完成它再提交；否则 git stash，并告诉我 stash 里有什么。
4. 从下一个未完成的任务继续，规则与第 2 节中 M<N> 的提示相同。完成整个里程碑后按第 1.2 节第 6 条汇报并停止。
```

### 现场验收失败后修复

```text
DCE 2.0 现场验收 R<N> 没有通过。在 feature/v2-bugfix-loop 分支上处理，遵守 docs/v2/CODEX_HANDOFF.md 第 1 节全部规则。

现象：<粘贴我看到的现象，以及哪一步失败>
DCE 返回：<粘贴工具返回的 JSON 或 CLI 输出；把其中的真实主机名、IP 和账号换成占位符>

1. 先判断原因属于哪一类：代码缺陷、文档与真实平台行为不符、我的配置问题。说明判断依据。
2. 代码缺陷：先用合成数据写一个能复现的失败测试，再修复，单独提交。
3. 文档与真实平台行为不符：按第 1.5 节处理。
4. 我的配置问题：告诉我具体怎么改，不要改代码。
5. 修复后在 progress.md 记一行，告诉我如何重做 R<N> 中失败的那几步。不要进入下一个里程碑。
```

### 回复“待确认”问题

```text
对 docs/v2/progress.md 中“待确认”第 <编号> 条的答复：<答复内容>

把答复原样记录在该条下面，标记为已答复。答复需要修改设计文档时，先修改对应章节并单独提交（docs: ...），再继续当前里程碑的任务。
```

### 跑偏纠正

```text
你最近的提交 <短 SHA> <简述做了什么>，这超出了 docs/v2 的范围（或违反了 docs/v2/CODEX_HANDOFF.md 第 1.4 节 / AGENTS.md 第 <N> 条）。

用 git revert 撤销该提交，然后对照 docs/v2/05-实施计划.md 中当前任务的定义重新实现，只做定义里写的内容。完成后按第 1.2 节汇报。
```

---

## 4. 给 andy 的提示

- 开发阶段（M0–M5 的编码）不需要访问公司平台，也不会产生任何真实写操作。真实的合并、构建、部署、禅道操作只发生在你做的现场验收里：R3 起会真实合并和构建，R4 起会真实更新测试环境服务，R5 会真实把一个缺陷标为“已解决”。
- 每个里程碑结束时看三样：`progress.md` 的新行、非测试代码行数是否在第 1.6 节预算内、有没有新出现的“待确认”。
- 出现以下迹象说明它开始走 1.x 的老路，直接用“跑偏纠正”提示：新增了 approval、receipt、evidence、proposed/confirmed、not_verified 之类的概念；工具描述里出现大段免责声明；`docs/v2/` 下出现计划外的报告文件。
- 现场验收的真实细节（真实名字、地址、截图）记在本机 `.local/v2/acceptance-notes.md`，`progress.md` 里只写 PASS/FAIL 和不含真实名称的简短说明。
