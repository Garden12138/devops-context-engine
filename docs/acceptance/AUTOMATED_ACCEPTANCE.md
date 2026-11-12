# DCE 本次自动化验收

结论：**PASS**（仅离线本地验收）。

执行时间：2026-11-12T10:45:56.234684+00:00 至 2026-11-12T10:47:00.656229+00:00。
Git HEAD：`43633a980a4201e660b7dd241f069046c3084592`；执行时 dirty：`False`。
实现 SHA256：`b718d75306d117c372222c2d092bbe00c50a336313b83df5529bd562bdf7968b`。
Python：3.12.11；系统：macOS-26.5.1-arm64-arm-64bit。

复现：`uv run --offline python scripts/run_acceptance.py`。首次准备依赖使用 `uv sync --locked --dev`；验收期间仅允许本机合成服务。

| 阶段 | 状态 | 退出码 | 秒 | 实际命令/检查 |
|---|---|---|---|---|
| python_compatibility | PASS | — | — | `in-process check` |
| uv_version | PASS | 0 | 0.007 | `uv --version` |
| lock_consistency | PASS | 0 | 0.013 | `uv lock --check --offline` |
| locked_dependency_install | PASS | 0 | 0.013 | `uv sync --locked --offline --dev` |
| ruff | PASS | 0 | 0.038 | `/Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/python3 -m ruff check .` |
| mypy | PASS | 0 | 4.212 | `/Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/python3 -m mypy --strict src/dce` |
| pytest | PASS | 0 | 47.083 | `/Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/python3 -m pytest -q --tb=short -p pytest_cov.plugin -o cache_dir=/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/pytest-cache --basetemp=/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/pytest-tmp --cov=src/dce --cov-report=term --cov-report=json:/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/coverage.json --junitxml=/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/pytest.xml` |
| synthetic_cli_init | PASS | 0 | 0.5 | `/Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/dce --catalog /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/synthetic-catalog.sqlite3 init --fixture /Users/cengjiada/Documents/github/devops-context-engine/fixtures/synthetic-discovery.json --no-ai` |
| catalog_stdio_checker | PASS | 0 | 0.981 | `/Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/python3 scripts/check_mcp_stdio.py --catalog /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/synthetic-catalog.sqlite3` |
| index_safety | PASS | 0 | 1.48 | `/Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/python3 scripts/check_public_data.py` |
| working_tree_safety | PASS | — | — | `in-process check` |
| diff_whitespace | PASS | 0 | 0.008 | `git diff --check` |
| wheel_build | PASS | 0 | 0.227 | `uv build --wheel --offline --out-dir /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/dist` |
| isolated_venv | PASS | 0 | 0.011 | `uv venv --offline --python /Users/cengjiada/Documents/github/devops-context-engine/.venv/bin/python3 /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/installed` |
| locked_runtime_export | PASS | 0 | 0.013 | `uv export --frozen --offline --no-dev --no-emit-project --format requirements-txt --output-file /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/runtime-requirements.txt` |
| isolated_locked_dependencies | PASS | 0 | 0.083 | `uv sync --locked --offline --no-dev --no-install-project --python /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/installed/bin/python` |
| isolated_wheel_install | PASS | 0 | 0.048 | `uv pip install --offline --python /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/installed/bin/python --no-deps /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/dist/devops_context_engine-1.2.0-py3-none-any.whl` |
| installed_cli_help | PASS | 0 | 5.199 | `/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/installed/bin/dce --help` |
| installed_cli_doctor | PASS | 0 | 0.875 | `/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/installed/bin/dce --catalog /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/doctor.sqlite3 doctor --mock` |
| installed_wheel_mcp | PASS | 0 | 3.322 | `/var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/installed/bin/python /var/folders/tc/48w0b8390_q9xhrvc2v_mv580000gn/T/dce-acceptance-dpxxjcf5/wheel_smoke.py` |

测试：468 总计，468 通过，0 失败，0 跳过；通过率 100.0%；覆盖率 93.79%。

| 功能分类（用例可重叠） | 状态 | 通过/总数 |
|---|---|---|
| agent_initialization | PASS | 96/96 |
| mcp | PASS | 65/65 |
| zentao | PASS | 68/68 |
| service_logs | PASS | 152/152 |
| security | PASS | 302/302 |
| cursor_stdio_simulation | PASS | 25/25 |

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
