# DCE 本次自动化验收

结论：**PASS**（仅离线本地验收）。

执行时间：2026-11-11T02:55:00.853797+00:00 至 2026-11-11T02:55:55.171111+00:00。
Git HEAD：`508bf9054ebd32f311823828eed361a47da1419f`；执行时 dirty：`True`。
实现 SHA256：`c10f4a0d504eca421e4400c11c8c332f6e626d808884c147262adbe9e967d867`。
Python：3.12.11；系统：macOS-26.5.1-arm64-arm-64bit。

复现：`uv run --offline python scripts/run_acceptance.py`。首次准备依赖使用 `uv sync --locked --dev`；验收期间仅允许本机合成服务。

| 阶段 | 状态 | 退出码 | 秒 | 实际命令/检查 |
|---|---|---|---|---|
| python_compatibility | PASS | — | — | `in-process check` |
| uv_version | PASS | 0 | 0.008 | `uv --version` |
| lock_consistency | PASS | 0 | 0.014 | `uv lock --check --offline` |
| locked_dependency_install | PASS | 0 | 0.013 | `uv sync --locked --offline --dev` |
| ruff | PASS | 0 | 0.04 | `/Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/python3 -m ruff check .` |
| mypy | PASS | 0 | 4.143 | `/Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/python3 -m mypy --strict src/dce` |
| pytest | PASS | 0 | 37.805 | `/Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/python3 -m pytest -q --tb=short -p pytest_cov.plugin -o cache_dir=/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/pytest-cache --basetemp=/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/pytest-tmp --cov=src/dce --cov-report=term --cov-report=json:/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/coverage.json --junitxml=/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/pytest.xml` |
| synthetic_cli_init | PASS | 0 | 0.554 | `/Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/dce --catalog /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/synthetic-catalog.sqlite3 init --fixture /Users/cengjiada/Documents/github/devops-context-engine/fixtures/synthetic-discovery.json --no-ai` |
| catalog_stdio_checker | PASS | 0 | 1.007 | `/Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/python3 scripts/check_mcp_stdio.py --catalog /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/synthetic-catalog.sqlite3` |
| index_safety | PASS | 0 | 1.636 | `/Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/python3 scripts/check_public_data.py` |
| working_tree_safety | PASS | — | — | `in-process check` |
| diff_whitespace | PASS | 0 | 0.01 | `git diff --check` |
| wheel_build | PASS | 0 | 0.242 | `uv build --wheel --offline --out-dir /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/dist` |
| isolated_venv | PASS | 0 | 0.013 | `uv venv --offline --python /Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/python3 /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/installed` |
| locked_runtime_export | PASS | 0 | 0.014 | `uv export --frozen --offline --no-dev --no-emit-project --format requirements-txt --output-file /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/runtime-requirements.txt` |
| isolated_locked_dependencies | PASS | 0 | 0.135 | `uv sync --locked --offline --no-dev --no-install-project --python /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/installed/bin/python` |
| isolated_wheel_install | PASS | 0 | 0.046 | `uv pip install --offline --python /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/installed/bin/python --no-deps /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/dist/devops_context_engine-1.1.1-py3-none-any.whl` |
| installed_cli_help | PASS | 0 | 5.217 | `/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/installed/bin/dce --help` |
| installed_cli_doctor | PASS | 0 | 0.893 | `/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/installed/bin/dce --catalog /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/doctor.sqlite3 doctor --mock` |
| installed_wheel_mcp | PASS | 0 | 2.231 | `/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/installed/bin/python /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-xrdi18qt/wheel_smoke.py` |

测试：432 总计，432 通过，0 失败，0 跳过；通过率 100.0%；覆盖率 97.24%。

| 功能分类（用例可重叠） | 状态 | 通过/总数 |
|---|---|---|
| agent_initialization | PASS | 65/65 |
| mcp | PASS | 63/63 |
| zentao | PASS | 68/68 |
| service_logs | PASS | 152/152 |
| security | PASS | 273/273 |
| cursor_stdio_simulation | PASS | 23/23 |

依赖精确版本见同目录 [JSON](acceptance-summary.json) 的 dependencies。命令使用的临时路径每轮不同，原始临时产物运行后删除；本报告只由本轮新产物生成。

Git HEAD 是执行时提交；随后保存报告的提交不冒充被测提交。实现摘要覆盖 src/tests/scripts/schemas/prompts 与 pyproject.toml/uv.lock，可核对最终提交中的实现是否变化。

| 外部/人工现场项目 | 本轮状态 |
|---|---|
| Cursor desktop Host reload and model-visible images | NOT_RUN / not_verified |
| Real company platform APIs in this run | NOT_RUN / not_verified |
| Real ZenTao Token expiry recovery | NOT_RUN / not_verified |
| Real log permissions/retention in a newly installed environment | NOT_RUN / not_verified |
| Actual human approval and model relationship inference quality | NOT_RUN / not_verified |
| Other Python versions and operating systems | NOT_RUN / not_verified |

历史 Gate A/B 结果见 harness 原日期报告，本轮没有重跑真实平台。Mock Token 恢复、合成 Host 审批数据和本地 SDK 成功不等于真实现场验收。
