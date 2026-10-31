# GitHub 建仓建议与开源发布方案

## 1. 仓库名称

**首选**：`devops-context-engine`，简称 DCE。理由：强调“研发上下文 + 多平台关联”，而不局限于单一平台 MCP，适合未来加入 Jenkins、Kubernetes、Jira 等 Adapter。

备选：`agent-devops-context`（更凸显 Agent 用途）、`devops-service-catalog`（更凸显目录）。不推荐 `zentao-gitlab-portainer-bot`，名字过于平台绑定。

建议仓库定位：**AI-ready DevOps context and service mapping engine for self-hosted development stacks.**

推荐 GitHub Description（英文，可直接复制）：

> AI-ready DevOps context engine that discovers and maps issues, code modules, CI pipelines, container images, and deployed services across self-hosted tools.

推荐中文介绍：

> 面向 AI Coding Agent 的研发环境自动发现、可信项目关联与缺陷交付上下文引擎，支持禅道、GitLab、Portainer。

建议 Topics：`devops`, `mcp`, `ai-agent`, `gitlab`, `portainer`, `zentao`, `service-catalog`, `developer-tools`, `python`, `docker-swarm`。

## 2. 仓库可见性——**建议先 private，脱敏后再决定 public**

公司平台地址、项目结构、镜像 Registry、缺陷截图、配置等属于企业内部信息；即使 Token 已删除也可能泄漏内部拓扑与代码信息。

- 初期使用 `Garden12138/devops-context-engine`（建议先 Private）。
- 公开前彻底审查所有 commit 的历史（包括被删除的内容），不要以为删除工作树文件就足够。
- 公开版本仅保留开源代码、完全合成的 fixtures、泛化示例；真实公司适配参数由 `.env`/私有配置在本地管理。
- 若用公司代码/相关文档作为开发输入，先确认公司对外开源授权，不能将公司源代码或专有内部资料直接发布。
- 开源许可建议 Apache-2.0（含专利授权，利于企业采用）；如果有公司知识产权限制，先不开源、暂不添加许可，征得同意后再补。

## 3. 初始设置

手动 UI：GitHub → New repository → `devops-context-engine` → Private → 不勾选自动添加 README（本包已含 README）→ Create。

也可本地进入解压后的包根目录：

```bash
# 先确保工作树中仅有已脱敏内容
git init -b main
git add .
git diff --cached --stat
git diff --cached --check
# 在确认内容不敏感后提交
git commit -m "docs: bootstrap DCE v1 specifications"

# 已安装并登录 gh 时；先保持 Private
gh repo create Garden12138/devops-context-engine \
  --private --source=. --remote=origin --push \
  --description "AI-ready DevOps context engine for self-hosted development stacks"

# 再创建实现分支（Codex/Cursor 也会按提示在干净仓库创建）
git switch -c feat/dce-v1-core
```

**注意**：`--push` 会立即上传提交，必须提前完成敏感数据检查。若希望保守，先使用 `gh repo create ... --private --source=. --remote=origin`，待手工审查后再 push。

## 4. 分支与协作

- `main`：稳定基线，保护分支（PR + checks 后合并）。
- `feat/dce-v1-core`：从 Spec 实现 V1 的主开发分支；阶段完成后用 PR 合并。
- 后续如有多名开发者：`feat/adapters-*`、`feat/catalog-*`、`feat/mcp-*` 分工，尽量避免共享单一工作分支。
- 里程碑：`v1.0-discovery-catalog`、`v1.1-mcp-context`、`v1.2-ci-workflow`、`v2.0-delivery-loop`；正式 tag 在测试通过后创建。
- Labels：`type:feature`, `type:bug`, `type:security`, `component:connector`, `component:catalog`, `component:mapping`, `component:mcp`, `priority:P0`。

## 5. GitHub 设置

- 仓库设置中开启 GitHub Issues / Discussions（可选）；设置 Security Policy、Dependabot 和 secret scanning（按计划支持）。
- 为 `main` 创建 Ruleset：PR 审核、测试通过、阻止 force push 与删除；依 GitHub 计划权益配置。
- CI 只运行合成 fixtures 单元测试/静态分析，**不注入公司内网 Token、不连接公司网络**。
- 设置 `CODEOWNERS` 和 PR 模板，后续可自动生成；版本许可与公开范围需先确认。
- 因为 GitHub 上的项目规划词汇“Project”也可指看板，当前建议先新建 **Repository**，后期才建 GitHub Projects 看板。

## 6. 推荐首个 Release

不要立即发布 `v1.0.0`。先以 `0.1.0-alpha` 标记本地 Mock/Fixture 运行的 Alpha；正式 `v1.0.0` 必须满足 Spec 全部 P0、明确公开数据清单与实际只读验收（按权限）。
