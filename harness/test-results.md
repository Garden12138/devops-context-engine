
- 2026-11-04 T0: 审计完成：harness/refactor-audit.md；先核对六工具、三 Adapter、Mapping/AI/Catalog，定义新契约/失败/测试。基线 .venv/bin/pytest -q：144 passed（7.52s），exit 0。下一步 T1 默认调用路径解耦；真实新版能力 not_verified。

- 2026-11-04 T1: 默认初始化/发现和 Bug fixture fallback 的语义推理已移出；确定性 Module→CI 保留，旧 mapping CLI 与 init --legacy-mapping 可用。首次回归 3 failed/142 passed，诊断为技术事实被混放在 Mapping 与旧 ai_status 兼容字段；拆分修复后 pytest 145 passed（7.54s），ruff/mypy exit 0。下一步 T2 范围事实查询。
