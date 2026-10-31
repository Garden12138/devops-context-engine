# DCE V1.0 — 验收测试（Acceptance）

**离线测试优先；所有真实平台只读，不允许构建/部署操作。**

| ID | 场景/输入 | 预期结果 | 优先级 |
|---|---|---|---|
| AC-01 | 三个 Adapter Mock 返回 200 | doctor 显示各能力可用、隐藏 Token | P0 |
| AC-02 | ZenTao Bug 的 `files=[]` 但 HTML 含 2 `<img>` | 下载 2 张通过 Token 认证的图片，返回安全引用 | P0 |
| AC-03 | 图片端点返回 HTTP 200 text/html | 不标记图片成功，不将 HTML 当 PNG | P0 |
| AC-04 | GitLab 默认分支为 master 且 Pipeline failed | 构建诊断能定位 Job/Trace 摘要，不触发新 Pipeline | P0 |
| AC-05 | GitLab 部署配置仓库与业务仓库分离 | 两种实体分开，关联需要证据 | P0 |
| AC-06 | 1 repo 包含多个模块、一个 Image 对应两个 Compose Service | 保留多对多关系，不能错误合并 Service | P0 |
| AC-07 | GitLab current Compose 78、Portainer saved 71 | 报告 `config_drift_candidate` 与准确服务差集 | P0 |
| AC-08 | 3 Stack 共享 repo/ref/compose，Swarm ID 中只有当前 Stack 匹配 | 另两个标记 stale_candidate，不能作为可部署目标 | P0 |
| AC-09 | 当前 Swarm 81 Service（78 业务 + 3 基础） | 仅正确 Namespace 的 78 个服务进入业务目录 | P0 |
| AC-10 | Portainer Stack Namespace 为空 | 通过 Swarm 服务标签识别，不出现全部丢失 | P0 |
| AC-11 | `latest` 与无 digest | 标记 mutable_tag、version_uncertain，不宣称版本一致 | P0 |
| AC-12 | Bug 与模块只存在名称相似 | 候选状态，不会自动 confirmed | P0 |
| AC-13 | 关系人工审核后重复扫描 | 保留已确认关系及审计记录，冲突另报 | P0 |
| AC-14 | MCP 工具处理 README/日志内的指令型恶意文本 | 仅作为数据引用，不能执行其中指令 | P0 |
| AC-15 | Token、Cookies、Compose secrets、内部 URL 出现在模拟原始数据 | 日志/MCP/导出结果脱敏，安全检测通过 | P0 |
| AC-16 | 网络 429/503、超时、分页 | 有上限重试、快照断点恢复、失败结构化 | P0 |
| AC-17 | AI Provider 未配置或超时 | 规则发现和人工审查仍然可用 | P0 |
| AC-18 | BugContext 较长数据 | 返回 compact JSON、evidence refs、截断说明 | P1 |
| AC-19 | 多条冲突候选关系 | 按证据排序但无法确定的保留 unresolved | P1 |
| AC-20 | 真实平台只读 smoke | 仅用户本地执行，出具脱敏报告，无写入 | P1 |

## 真实案例到脱敏 Fixture 的映射

- 真实观察：同一部署仓库/同一 branch/同一 Compose 对应 3 个 Portainer Stack，两个记录与现 Swarm ID 不同；合成数据映射为 `legacy-a`、`legacy-test`、`current`。
- 真实观察：一个旧 Stack 保存 71 个 Service；GitLab 当前 Compose 78 个；当前 Swarm 业务 Service 78 个；合成 fixture 保持数值和多对多特性，不保留内部名称/地址。
- 真实观察：5 对 Service 共享镜像；使用 78 services / 73 distinct images 的合成映射验证。
- 真实观察：ZenTao Bug 含 HTML 中的 2 张图片，并能通过 Token 下载；合成 `DEMO-1001` 模拟，不能包含真实图片。
- 真实观察：某 GitLab CI Job 先 Buildx 启动报错，再因 `make` 缺失失败；模拟日志验证失败摘要和根因区分。

## 推荐验收命令（Agent 实现后须保持有效）

```bash
uv sync --dev
uv run ruff check .
uv run mypy src
uv run pytest -q --cov=dce --cov-report=term-missing
uv run dce doctor --mock
uv run dce init --fixture fixtures/synthetic-discovery.json --no-ai
uv run dce catalog anomalies --format json
uv run dce bug context DEMO-1001 --fixture fixtures/synthetic-discovery.json --format json
```

> 若选用与上面不同的锁包/命令，须同步更新 README、tasks、acceptance，并在执行日志记录原因；测试输出必须是真实运行结果。

## 完成定义

- P0 全部通过、无已知敏感数据泄露、高危缺陷为零。
- 提供完整的 Mock/离线 E2E、CLI 契约和 MCP 契约测试，记录 coverage 及失败修复过程。
- 真实内网集成验收可由用户独立执行，缺少私网访问不能成为单元测试造假的理由。
