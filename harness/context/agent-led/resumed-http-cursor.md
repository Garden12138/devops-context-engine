# HTTP / Cursor 真实验收接续 — 2026-11-04

用户补齐三平台地址（明确在本机 .env）、全部 HTTP、实际 Host 为 Cursor。业务 workspace 和缺陷样本沿用最新输入。只由显式本机程序处理已授权文件，值不输出；真实路径、URL、名称和 ID 只在 gitignored 私有目录。以前缺地址/Host 选择的 blocked 审计是历史状态。

## 实现边界与验证

新增 ZEN_URL/GITLAB_URL/PORTAINER_URL 别名；同文件冲突仍拒绝，显式进程 DCE_* 优先于本机文件与 TOML。默认 CLI 无 dotenv；不修改父环境、不 source/插值、不增加自动探路。补充别名/冲突/应用 URL 覆盖两项测试，针对性 9 passed。

全库 pytest 201 passed，0 failed/errors/skipped（18.38s）；总体覆盖率 98.09%，行 98.64%，分支 96.39%。ruff、strict mypy（48 files）通过。最终离线 wheel 构建/临时安装成功，-S 与显式依赖路径核验实际安装包导入、别名、模板/Schema/0003 角色通过。验证脚本首次使用字符串路径前缀将 /tmp 与其 macOS 规范路径 /private/tmp 当作不同，修正规范路径比较后通过，产品无需变更。

## 实际连接与诊断

默认沙箱首次网络不可用；执行器批准限定只读后收到真实响应。禅道给定站点是安装包欢迎页，原认证路由 404。先以无认证 GET 核对实际页面，再仅按观察到的同源链接定位应用；进程覆盖应用 URL 后 v1 认证 201、Bug 200。没有猜测应用目录、执行 HTML/平台指令、修改 .env 或重试错误密码。

标准 MCP SDK 对新启动器实际枚举九工具，三轮合计 27 次成功 tools/call：ZenTao 4、GitLab 4、Portainer 19，输出均过发布 Schema。另一次 module_tree 返回 PERMISSION_DENIED/403，未重试/绕过。SDK 是协议证据，非 Cursor Agent 对话证据。

- ZenTao：Bug、Project、Product 和附件元数据成功。原始形态只做内存计数：files=0、inline images=0、resolved sources=0；module=0 表示未分配，Host scope 已规范成 null，源事实保留原值。真实图片不能从这个样本验收。
- GitLab：按工作区真实 remote 精确查询一个项目，读取 Tree、Commit、实际存在的 CI 文件；不执行脚本、不推断 Bug 归属。
- Portainer：Endpoint/Swarm Info、授权三 Stack 元数据与保存文件、实际服务列表/详情成功。两份 Stack SwarmId 不匹配、另一份匹配当前集群。三份保存 Compose 解析为 63/71/78 个服务。根据保存 Stack 元数据作过一次 namespace 查询，结果 0，保留其来源；另从实际 Service label 得到运行 namespace，8 页共 78 个唯一 ID，无重复、完整结束。健康 unknown、环境 unresolved、版本 not_verified。保存配置、运行 label 与 GitLab 文件是不同事实，不因数量相等确认一致。

接口只用 GET 加禅道 v1 认证 POST；无真实业务写/构建/部署。原始 Compose 仅内存解析，不落盘；未请求私有日志，真实图片未下载/保存。

## 自动审批拒绝及安全收缩

原补验脚本含提案旧独立 GitLab 项目/流水线/Job 固定编号；执行前被自动审批拒绝，理由为这些编号的当前读取范围未明确授权且存在硬编码约束。该命令没有执行。不绕过拒绝：删除全部旧编号及对应请求，复用已有 Cursor allowlist、实际 Git remote/Bug/Stack 元数据后，剩余真实读取获准执行。旧独立样本、GitLab Compose 和其流水线/Job 保持 not_verified；需明确范围后再查元数据，不请求私有日志。

## Catalog / Cursor / 项目草案

真实旧 Catalog 用 SQLite backup 复制到私有验收库，再自动创建迁移前备份并升级 0003。191 实体、219 边、219 证据、11 快照保留，角色 resource_cache_and_history，原库不改；旧业务关系未导入项目 confirmed。

全局 Cursor JSONC 只替换 dce，先创建受保护本机备份，其他四服务对象保持不变；command 保留虚拟环境 Python 入口（不 resolve 到系统解释器），凭证文件仅作为路径参数，配置无 Token/密码。启动参数只包括授权来源范围。Cursor 已打开目标工作区；进程观察仅作启动旁证。CLI 状态 unauthenticated，list-tools 未读到该条目；不读取桌面 Token/日志或把进程启动当作 Agent 成功。已生成私有 CURSOR_ACCEPTANCE.md，请用户在桌面新对话运行并回传脱敏工具状态。

工作区 20 Git roots，私有项目草案 18 条本地模块结构关系、1 条精确 remote 身份提议、3 条独立 Swarm 候选、1 条 Bug↔工作区 unresolved，共 22 proposed/1 unresolved/0 confirmed。所有关系有 evidence/观察时间/revision，人工审批为空。Schema 与对同一草案的纯 refresh 校验通过，新增文件具体 diff 已备好，未写业务目录。按规格 05 阶段 F，Host 展示 diff、用户批准后保存/复读；不会替用户批准关系。

## 待补

真实 Cursor Agent 枚举/三次调用和初始化对话；人工审核与业务文件落地；含图的授权 Bug；模块树只读权限；旧独立 GitLab 元数据范围。当前三平台地址/凭证源/业务路径/Host 选择已知，不再重复索取。整体未完成，不复用旧报告虚报通过。


提交前检查：工作流/项目校验/本地凭证回归 25 passed（1.10s），10 份文档相对链接检查通过，git diff --cached --check 与 15 个暂存文件的私有路径/站点扫描通过；.env/.local/private 未入索引。真实 Catalog 原有 11 张业务表计数全部与副本一致，两库 quick_check=ok。
