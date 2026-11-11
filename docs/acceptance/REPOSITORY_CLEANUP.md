# 仓库文件整顿记录

日期：2026-11-11。盘点基于干净快照 `2748c7b`，230 个跟踪文件；初始工作区无未提交修改。保留既有目录，避免无功能收益的大量移动。

## 盘点边界

以 Git 文件表与引用搜索盘点全部源码、测试、docs、harness、fixtures、scripts、schemas、prompts、examples。缓存只检查名称、类型和计数；不读取内容。`.git`、`.local`、`.venv`、`.dce`、private、凭证/用户配置目录不进入递归扫描，现有 worktree 不删除。

| 类别 | 跟踪文件数 | 处理 |
|---|---:|---|
| (root) | 9 | 核对用途并保留有效交付 |
| .githooks | 1 | 核对用途并保留有效交付 |
| .github | 1 | 核对用途并保留有效交付 |
| docs | 42 | 核对用途并保留有效交付 |
| examples | 7 | 核对用途并保留有效交付 |
| fixtures | 2 | 核对用途并保留有效交付 |
| harness | 51 | 核对用途并保留有效交付 |
| prompts | 10 | 核对用途并保留有效交付 |
| schemas | 3 | 核对用途并保留有效交付 |
| scripts | 4 | 核对用途并保留有效交付 |
| specs | 4 | 核对用途并保留有效交付 |
| src | 55 | 核对用途并保留有效交付 |
| tests | 41 | 核对用途并保留有效交付 |

## 删除清单

| 文件/生成目录 | 删除原因 | 是否被引用 | 处理结果 |
|---|---|---|---|
| `.pytest_cache`（5 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `dist`（3 个文件） | 过期构建产物 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `.ruff_cache`（8 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `.mypy_cache`（3 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `.DS_Store`（1 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `.coverage`（1 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `tests/__pycache__`（41 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `docs/.DS_Store`（1 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `docs/refactor/.DS_Store`（1 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `docs/refactor/agent-led-initialization/.DS_Store`（1 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/__pycache__`（1 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/connectors/__pycache__`（7 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/parsers/__pycache__`（2 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/app/__pycache__`（5 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/security/__pycache__`（5 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/catalog/__pycache__`（4 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/catalog/migrations/__pycache__`（1 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/catalog/migrations/versions/__pycache__`（3 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/graph/__pycache__`（3 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/discovery/__pycache__`（5 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/mcp/__pycache__`（5 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/cli/__pycache__`（1 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/project/__pycache__`（4 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/common/__pycache__`（5 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `src/dce/ai/__pycache__`（2 个文件） | 可再生缓存/本地系统元数据 | 无正式依赖；Git 未跟踪 | 已定点删除 |
| `harness/reports/coverage.json` | 旧 133 用例基线的原始覆盖率明细，体积大且含旧绝对路径 | 历史验收链接与 build-log 命令引用，无程序读取；链接已改为移除说明 | 删除；历史摘要保留，新报告替代当前入口 |
| `harness/reports/pytest.xml` | 同期原始 JUnit 中间产物 | 历史验收链接与 build-log 命令引用，无程序读取；链接已改为移除说明 | 删除；不删除任何测试 |

共清理 25 个未跟踪生成路径（含 118 个文件）及 2 个跟踪原始报告。未删除任何正式源码、测试、有效 fixture、Schema 或 Prompt。验收产生的新缓存不属于初始清理，最终再次定点检查；验收编排自身产物存独立临时目录并自动移除。

## 重要保留项

| 路径 | 保留理由 |
|---|---|
| `harness/*acceptance*.md`、`harness/reports/*summary.json` | 各版本时间点的脱敏历史证据，不能用新报告改写历史 |
| `harness/context/`、`harness/build-log.md` | 阶段决策、失败诊断及续跑依据；被文档和 Prompt 引用 |
| `docs/refactor/agent-led-initialization/` | 已完成重构的契约/决策/资料包，PROMPTS 和测试仍引用 |
| `prompts/agent-led/` | 当前初始化、审核、刷新、定位操作入口；测试校验内容 |
| `prompts/CODEX_LONG_TASK.md` 等旧 Prompt | 原 T0–T7 实施/恢复上下文，仍有引用，作为历史兼容保留 |
| `schemas/project-v1.schema.json`、v2 与 Portainer Schema | 兼容、迁移和运行时 Schema 回归依赖 |
| `src/dce/ai`、Catalog/mapping、旧六 MCP 工具 | 显式 legacy 功能及旧消费者兼容，已有测试，不能判为无用代码 |
| `scripts/check_mcp_stdio.py` | 历史 Catalog smoke，仍有指南引用；新版统一验收不依赖其过时 revision 断言 |
| `.local`、`.dce`、实际凭证和用户配置 | 用户数据和私有诊断，完全保留，不作为缓存 |

## 待确认/历史限制

旧文档与资料包存在相似内容但各自承担审计/提示词契约，未凭重复文本删除。旧 `check_mcp_stdio.py` 的 revision 断言已按运行时契约修正，并校验合法有界截断必须披露遗漏及下一步；统一验收执行它，避免保留失效入口。未发现需要删除的无引用业务实现。对用户私有目录不做内容判断，清理统计不包含它们。

安全处理：全部生成路径删除前确认非 symlink、不是 Git 跟踪内容、且不位于保护根；没有使用 git clean/reset。旧原始报告可从干净候选恢复；历史 build-log 中命令为原时点事实，不代表文件仍是当前验收产物。

## 最终验收后再生缓存收尾

以下仅删除本轮运行重新生成的缓存；不是新增业务文件。每项再次排除 symlink/Git 跟踪路径，不进入保护目录。

| 文件/目录 | 原因 | 引用 | 结果 |
|---|---|---|---|
| `.pytest_cache`（5 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `.ruff_cache`（5 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `tests/__pycache__`（2 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `scripts/__pycache__`（3 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/__pycache__`（1 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/connectors/__pycache__`（7 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/parsers/__pycache__`（2 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/app/__pycache__`（5 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/security/__pycache__`（4 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/catalog/__pycache__`（4 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/catalog/migrations/__pycache__`（1 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/catalog/migrations/versions/__pycache__`（3 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/graph/__pycache__`（3 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/discovery/__pycache__`（5 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/mcp/__pycache__`（5 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/cli/__pycache__`（1 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/common/__pycache__`（5 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |
| `src/dce/ai/__pycache__`（2 文件） | 本轮验证生成、可再生 | 无正式依赖 | 已删除 |

收尾共 18 个生成路径、63 文件；与初始清理有路径重叠，不能相加为唯一文件数。受保护目录未处理。
