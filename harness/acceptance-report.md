> 本报告是重构前 V1 的版本/范围证据，不能替代本轮 Agent-led 真实平台或 Host 验收。当前状态见 [agent-led-acceptance.md](agent-led-acceptance.md)。

# DCE V1.0 离线验收报告

本文件保留 2026-11-01 离线基线。后续限定真实只读核验见 [真实报告](live-readonly-report.md)，不覆盖本基线的原始结果和未验证声明。

验证时间：2026-11-01；Python 3.12.11；分支 `work/dce-v1-offline`。

结论：T0–T7 离线范围与全部 P0 通过。真实 ZenTao/GitLab/Portainer、Cursor/Grok 执行器为 `not_verified`。
未触发公司平台写入、构建、部署、推送、合并或公开发布。

## 真实质量证据

- pytest：133 passed，0 failures/errors/skipped；[JUnit](reports/pytest.xml)。主机名已替换为 offline-runner，测试数据全部合成。
- 覆盖率：总体 98.58%（启用分支统计）、行 99.18%、纯分支 96.65%；[完整覆盖率](reports/coverage.json)、[摘要](reports/summary.json)。
- Catalog、MappingService、关系规则、ZenTao、Checkpoint、Stack/Swarm 判定、脱敏模块：纯分支覆盖率均 100%。
- `ruff check .`、`mypy src`（39 files）、`git diff --check` 均 exit 0。
- 真实 CLI 子进程与 MCP ClientSession stdio 集成通过；MCP stdout 仅协议，六工具只读且无审核/部署/触发工具。
- `uv build --offline` 生成 wheel/sdist；wheel 所有 Python 文件与当前源码逐字节一致。
- 独立临时 venv 从 wheel 安装，确认导入路径为 site-packages；迁移、init、2 张 PNG、master Pipeline、6 MCP 工具与 doctor mock 通过。
- 独立安装初始化实测：243 Entity / 335 Edge / 331 Evidence / 6 Snapshot。
- 暂存区与历史敏感模式检查通过；扫描凭证文件名时直接拒绝、不读取内容；仍保留人工发布审查要求。

## P0 验收逐项映射

| AC | 当前证明 | 测试来源 |
|---|---|---|
| 01 | 三 Adapter Mock、逐平台能力与失败隔离、无 Token | test_foundation / test_connector_boundaries |
| 02 | files=[] 的两图通过 Token 获取，安全私有路径与 MCP URI | test_connectors / test_cli_workflow / test_mcp |
| 03 | 200 HTML / SVG / MIME 与 magic 不匹配拒绝 | test_connectors / test_services |
| 04 | master、failed job/trace、missing_make 与 Buildx 分开、只读 GET | test_connectors / test_cli_workflow / test_services |
| 05 | source/deployment repo 分离、独立 ID 与证据 | test_discovery |
| 06 | 多模块→多 Job→多镜像；一个镜像两个运行服务 | test_acceptance_chain / test_parsers / test_mapping_rules |
| 07 | saved 71 / git 78，准确 added 072–078 | test_discovery / test_crawler_platforms |
| 08 | 3 Stack 中 2 stale，Endpoint/Swarm mismatch fail closed | test_discovery |
| 09 | 81 个实际输入中仅匹配 Namespace 的 78 进入业务目录 | test_discovery |
| 10 | 空 Namespace 由实际标签匹配；无标签证据不确认当前 Stack | test_discovery |
| 11 | mutable_tag/version_uncertain，不以 latest 宣称版本相同 | test_parsers / test_discovery |
| 12 | 名称线索仅 candidate；不明确多个 unresolved | test_mapping / test_mapping_rules |
| 13 | confirmed/rejected 审核保留、冲突/过期另报、可撤销 | test_catalog / test_catalog_boundaries |
| 14 | 恶意文本不执行，标记文件未创建，Provider 无原始文本 | test_mcp / test_mapping |
| 15 | HTTP/日志/Catalog/CLI/MCP 脱敏；同源/重定向/大小/资源完整性 | test_connector_boundaries / test_catalog_boundaries / test_mcp_boundaries |
| 16 | 有限 429/503/超时重试、分页循环上限、checkpoint 恢复/损坏/原子失败 | test_connectors / test_crawler / test_final_safety_gates |
| 17 | 无 Provider、--no-ai、超时/异常/无效候选均保留规则，可审核和重跑 | test_mapping / test_mapping_rules / test_mapping_limits |

## REQ / NFR 与阶段交付审计

| 要求 | 实现及当前证据 |
|---|---|
| REQ-01 / T0 | pyproject/uv.lock、CLI、配置 CLI>env>TOML、.env.example、统一错误、doctor、离线 CI、本地提交钩子 |
| REQ-02–04 / T1 | 三平台 Reader；ZenTao 唯一认证 POST，其余 GET；实际 Mock HTTP 契约、错误/认证/图片/分页测试 |
| REQ-05–06 / T2 | Scope、相关文件白名单、固定 commit、节流/分页、私有恢复缓存、静态解析、三类独立快照 |
| REQ-07 / T3 | SQLAlchemy SQLite + Alembic 0001→0002、幂等、历史/有效期/最近验证、ScanRun/Approval/Audit、范围成员 |
| REQ-08 / T4 | 可证实关系与候选分离；Provider 仅 ID/类型摘要；严格 schema 与引用；高风险环境人工确认 |
| REQ-09 / T5 | 全部规定 CLI、JSON/table、预算/分页/安全退出码、真实子进程 smoke |
| REQ-10 / T6 | 六工具 schema、固定 error_code、真实 SDK stdio、共用 AppServices、会话资源授权 |
| REQ-11 / T4–5 | preview 的证据/版本/环境/影响；actor/reason/时间、期望版本；审核不向 MCP 暴露 |
| REQ-12 / 全阶段 | 默认 fixture；live/read_only/scope、HTTPS 与显式 HTTP、只读方法；AI 无原始数据与网络调用 |
| NFR-01 | timeout/有限重试/退避/节流/分页/结构化分类，全由 Mock HTTP 验证 |
| NFR-02 | 重扫无重复图元素；人工确认不覆盖，AI/规则同边幂等 |
| NFR-03 | 统一预算、truncated/omissions/next_action；图片独立受控资源，无 BugContext base64 |
| NFR-04 | schema 迁移、软删除/过期、撤销与版本历史/审计；不支持破坏性 downgrade |
| NFR-05 | 无脚本执行，静态 YAML/XML/模块元数据，恶意文本仅数据 |
| NFR-06 | 凭证环境输入；本地单用户 stdio；私有权限和缓存；未实现共享 HTTP 身份服务（设计明确后续） |
| T7.1–2 | 合成 3 Stack / 1 Swarm / 71 vs 78 / 81 vs 78 / 5 shared images；模块链、图片、CI、审核 E2E |
| T7.3–5 | 质量报告、独立安装、OPERATIONS、隐私/License/GitHub 审查、本地提交；不自动发布 |

## 边界与未验证项

- AC-20 真实平台 smoke 为 P1 / `not_verified`；步骤、最小权限、失败诊断与脱敏要求见 OPERATIONS。
- 101/103 没有完整 saved Service 列表：只保留合成计数与 incomplete，不按计数伪造配置或版本一致性。
- CI include P0 只保留显式引用与 incomplete；递归/merged lint 属 P1。
- 可选 Provider 以 Python 协议注入，含 Noop/Fake；CLI 默认关闭。OpenAI-compatible HTTP 模型客户端与共享鉴权服务属后续扩展。
- 不添加未经所有者批准的开源许可；未创建/修改远端仓库，未 push/merge/release。此发布授权事项不阻塞本地离线 P0。

## 复现

`uv sync --locked --dev` 后，按 OPERATIONS 的离线命令运行。完整质量命令为：

```bash
uv run --offline ruff check .
uv run --offline mypy src
uv run --offline pytest -q --cov=src/dce --cov-report=term-missing
uv run --offline dce doctor --mock
uv run --offline python scripts/check_public_data.py
uv run --offline python scripts/check_public_data.py --history
git diff --check
```
