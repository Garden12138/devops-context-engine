"""Reproducible offline product acceptance; never load local business configuration."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {
    "agent_initialization": {
        "test_agent_boundary",
        "test_agent_workflow",
        "test_agent_e2e",
        "test_project_context",
        "test_project_v2",
        "test_discovery",
        "test_crawler",
        "test_parsers",
        "test_mapping",
        "test_mapping_rules",
        "test_catalog",
        "test_acceptance_chain",
    },
    "mcp": {
        "test_mcp",
        "test_mcp_boundaries",
        "test_mcp_contracts",
        "test_facts",
        "test_agent_e2e",
        "test_incremental_stdio",
        "test_service_logs_stdio",
        "test_log_grant_stdio",
        "test_mcp_startup",
    },
    "zentao": {"test_zentao_auth", "test_local_credentials", "test_connectors", "test_agent_e2e"},
    "service_logs": {
        "test_service_logs",
        "test_service_logs_stdio",
        "test_log_grant",
        "test_log_grant_integration",
        "test_log_grant_stdio",
    },
    "security": {
        "test_final_safety_gates",
        "test_connector_boundaries",
        "test_catalog_boundaries",
        "test_mcp_boundaries",
        "test_local_credentials",
        "test_public_data_check",
        "test_project_context",
        "test_service_logs",
        "test_log_grant",
        "test_log_grant_integration",
        "test_log_grant_stdio",
        "test_facts",
        "test_zentao_auth",
    },
    "cursor_stdio_simulation": {
        "test_agent_e2e",
        "test_mcp_startup",
        "test_incremental_stdio",
        "test_log_grant_stdio",
        "test_service_logs_stdio",
        "test_mcp",
    },
}

# Loaded by Python children, including MCP servers launched by the SDK. No external DNS.
NETWORK_GUARD = """import ipaddress
import socket
_connect = socket.socket.connect
_connect_ex = socket.socket.connect_ex
_getaddrinfo = socket.getaddrinfo
def _allowed(host):
    if host in ("localhost", b"localhost", None):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
def _check(address):
    if isinstance(address, tuple) and not _allowed(address[0]):
        raise PermissionError("offline acceptance permits loopback only")
def connect(self, address):
    _check(address)
    return _connect(self, address)
def connect_ex(self, address):
    _check(address)
    return _connect_ex(self, address)
def getaddrinfo(host, *args, **kwargs):
    if not _allowed(host):
        raise PermissionError("offline acceptance blocks external DNS")
    return _getaddrinfo(host, *args, **kwargs)
socket.socket.connect = connect
socket.socket.connect_ex = connect_ex
socket.getaddrinfo = getaddrinfo
"""

WHEEL_SMOKE = """import asyncio, json, os, sys
from pathlib import Path
from importlib.metadata import version
import dce
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
expected = {"bug_context", "project_context", "service_trace", "pipeline_diagnose",
            "deployment_inspect", "discovery_status", "zentao_query", "gitlab_query",
            "portainer_query"}
assert Path(dce.__file__).is_relative_to(Path(sys.prefix))
async def smoke():
    p = StdioServerParameters(command=str(Path(sys.prefix)/"bin/dce"),
        args=["--catalog", str(Path.cwd()/"wheel-cache.sqlite3"), "mcp", "serve"],
        env=dict(os.environ), cwd=str(Path.cwd()))
    async with stdio_client(p) as (read, write):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            assert info.serverInfo.version == version("devops-context-engine")
            tools = (await session.list_tools()).tools
            assert {t.name for t in tools} == expected
            for _ in range(2):
                result = await session.call_tool("discovery_status", {})
                assert not result.isError and result.structuredContent["status"] == "ok"
            result = await session.call_tool("bug_context", {"bug_id":"outside"})
            assert result.isError
    print(json.dumps({"version": info.serverInfo.version, "tools": len(tools),
                      "wheel_import": True, "repeated_calls": 2, "scope_denied": True}))
asyncio.run(smoke())
"""


def command_result(
    name: str,
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int = 300,
) -> tuple[dict, str]:
    """Kill the process group on deadline so MCP grandchildren cannot remain running."""
    start = time.monotonic()
    result = {"name": name, "command": shlex.join(command), "status": "FAIL", "exit_code": None}
    output = ""
    try:
        with subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        ) as proc:
            try:
                output, _ = proc.communicate(timeout=timeout)
                result.update(
                    exit_code=proc.returncode, status="PASS" if proc.returncode == 0 else "FAIL"
                )
                if proc.returncode:
                    result["reason"] = (
                        "Command returned nonzero; see failure test IDs if available."
                    )
                    if any(
                        s in output.lower()
                        for s in (
                            "not found in cache",
                            "network connectivity is disabled",
                            "no cached",
                            "operation not permitted",
                            "permission denied",
                        )
                    ):
                        result.update(
                            status="BLOCKED", reason="Offline cache or OS access unavailable."
                        )
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
                result.update(status="BLOCKED", reason="Deadline exceeded; process group stopped.")
    except OSError as exc:
        result.update(status="BLOCKED", reason=f"Command unavailable ({type(exc).__name__}).")
    result["duration_seconds"] = round(time.monotonic() - start, 3)
    return result, output


def parse_junit(path: Path) -> dict:
    """Absent/invalid evidence must fail closed, including collection errors."""
    root = ET.parse(path).getroot()
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("Invalid JUnit root")
    cases = []
    for case in root.iter("testcase"):
        status = (
            "FAIL"
            if case.find("failure") is not None or case.find("error") is not None
            else "NOT_RUN"
            if case.find("skipped") is not None
            else "PASS"
        )
        item = {
            "id": case.get("classname", "") + "::" + case.get("name", ""),
            "module": case.get("classname", "").split(".")[-1],
            "status": status,
        }
        if status == "FAIL":
            failure = case.find("failure")
            if failure is None:
                failure = case.find("error")
            message = failure.get("message", "Test assertion/collection failed.")
            # Bounded JUnit reason from synthetic tests; never include captured logs/tracebacks.
            message = re.sub(r"https?://\S+", "<url>", message)
            item["reason"] = message.replace(str(ROOT), "<workspace>").replace("\n", " ")[:400]
        cases.append(item)
    if not cases:
        raise ValueError("No test cases")
    return summarize_cases(cases) | {"cases": cases}


def summarize_cases(cases: list[dict]) -> dict:
    total = len(cases)
    passed = sum(c["status"] == "PASS" for c in cases)
    failed = sum(c["status"] == "FAIL" for c in cases)
    skipped = total - passed - failed
    return {
        "status": "FAIL" if failed else "NOT_RUN" if skipped or not total else "PASS",
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": round(passed / total * 100, 2) if total else 0,
        "failed_tests": [c["id"] for c in cases if c["status"] == "FAIL"],
        "failures": [
            {"id": c["id"], "reason": c.get("reason", "Test failed.")}
            for c in cases
            if c["status"] == "FAIL"
        ],
    }


def implementation_digest(root: Path) -> str:
    digest = hashlib.sha256()
    paths = [
        p
        for prefix in ("src", "tests", "scripts", "schemas", "prompts")
        for p in (root / prefix).rglob("*")
        if p.is_file() and not p.is_symlink() and "__pycache__" not in p.parts
    ]
    paths += [root / "pyproject.toml", root / "uv.lock"]
    for path in sorted(paths):
        digest.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def source_safety(root: Path) -> dict:
    """Read only Git-visible source; reject private paths before opening any content."""
    from check_public_data import PATTERNS, PRIVATE_ADDRESS, PRIVATE_HOST

    names = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=root,
        )
        .decode()
        .split("\0")
    )
    failures = []
    for name in sorted(set(filter(None, names))):
        p = Path(name)
        if (
            p.name.startswith(".env")
            and p.name != ".env.example"
            or p.suffix in {".key", ".pem", ".p12"}
            or p.parts[0] in {"private", ".local", ".dce"}
        ):
            failures.append(name)
            continue
        path = root / p
        if not path.exists():
            continue  # Explicit tracked deletion.
        if path.is_symlink():
            failures.append(name)
            continue
        payload = path.read_bytes()
        if (
            any(pattern.search(payload) for pattern in PATTERNS)
            or p.parts[0] not in {"tests", "fixtures"}
            and (PRIVATE_ADDRESS.search(payload) or PRIVATE_HOST.search(payload))
        ):
            failures.append(name)
    return {
        "name": "working_tree_safety",
        "status": "FAIL" if failures else "PASS",
        "checked_files": len(set(filter(None, names))),
        "failed_paths": failures,
        "limitation": "Pattern scan plus protected-path exclusion; manual review remains required.",
    }


def write_reports(summary: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    rows = [
        "# DCE 本次自动化验收",
        "",
        f"结论：**{summary['status']}**（仅离线本地验收）。",
        "",
        f"执行时间：{summary['started_at']} 至 {summary['finished_at']}。",
        f"Git HEAD：`{summary['git_commit']}`；执行时 dirty：`{summary['git_dirty']}`。",
        f"实现 SHA256：`{summary['implementation_sha256']}`。",
        f"Python：{summary['python']}；系统：{summary['platform']}。",
        "",
        "复现：`uv run --offline python scripts/run_acceptance.py`。首次准备依赖使用 "
        "`uv sync --locked --dev`；验收期间仅允许本机合成服务。",
        "",
        "| 阶段 | 状态 | 退出码 | 秒 | 实际命令/检查 |",
        "|---|---|---|---|---|",
    ]
    for s in summary["stages"]:
        rows.append(
            f"| {s['name']} | {s['status']} | {s.get('exit_code', '—')} | "
            f"{s.get('duration_seconds', '—')} | `{s.get('command', 'in-process check')}` |"
        )
        if s.get("reason"):
            rows.append(f"\n{s['name']}：{s['reason']}\n")
    t = summary["tests"]
    rows += [
        "",
        f"测试：{t.get('total', 0)} 总计，{t.get('passed', 0)} 通过，"
        f"{t.get('failed', 0)} 失败，{t.get('skipped', 0)} 跳过；"
        f"通过率 {t.get('pass_rate', 0)}%；覆盖率 {summary.get('coverage_percent')}%。",
        "",
        "| 功能分类（用例可重叠） | 状态 | 通过/总数 |",
        "|---|---|---|",
    ]
    for name, group in summary["functional_acceptance"].items():
        rows.append(f"| {name} | {group['status']} | {group['passed']}/{group['total']} |")
    if t.get("failed_tests"):
        rows += ["", "失败用例及合成断言原因：", ""] + [
            f"- `{f['id']}`：{f['reason']}" for f in t["failures"]
        ]
    rows += [
        "",
        "依赖精确版本见同目录 [JSON](acceptance-summary.json) 的 dependencies。"
        "命令使用的临时路径每轮不同，原始临时产物运行后删除；本报告只由本轮新产物生成。",
        "",
        "Git HEAD 是执行时提交；随后保存报告的提交不冒充被测提交。"
        "实现摘要覆盖 src/tests/scripts/schemas/prompts 与 pyproject.toml/uv.lock，"
        "可核对最终提交中的实现是否变化。",
        "",
        "| 外部/人工现场项目 | 本轮状态 |",
        "|---|---|",
    ]
    rows += [f"| {name} | NOT_RUN / not_verified |" for name in summary["not_verified"]]
    rows += [
        "",
        "历史 Gate A/B 结果见 harness 原日期报告，本轮没有重跑真实平台。"
        "Mock Token 恢复、合成 Host 审批数据和本地 SDK 成功不等于真实现场验收。",
        "",
    ]
    for name, content in (
        ("acceptance-summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n"),
        ("AUTOMATED_ACCEPTANCE.md", "\n".join(rows)),
    ):
        target = output / name
        if target.is_symlink():
            raise ValueError("Refusing symlink report destination")
        temporary = output / (name + ".tmp")
        with temporary.open("x") as stream:
            stream.write(content)
        temporary.replace(target)


def acceptance_environment(environ: Mapping[str, str]) -> dict[str, str]:
    # Deliberately omit business credentials, DCE variables, proxies, PYTHONPATH and user config.
    # setup-uv prepares a non-default cache; offline build children must use that same cache.
    allowed = ("PATH", "TMPDIR", "SYSTEMROOT", "LANG", "UV_CACHE_DIR")
    env = {k: environ[k] for k in allowed if k in environ}
    env.update(
        UV_OFFLINE="true",
        UV_PYTHON_DOWNLOADS="never",
        PYTHONDONTWRITEBYTECODE="1",
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        NO_COLOR="1",
    )
    return env


def run(output: Path) -> int:
    started = datetime.now(UTC).isoformat()
    stages: list[dict] = []
    test_data: dict = {"status": "NOT_RUN"}
    coverage = None
    env = acceptance_environment(os.environ)
    git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    git_dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
    with tempfile.TemporaryDirectory(prefix="dce-acceptance-") as tmp:
        work = Path(tmp)
        guard = work / "guard"
        guard.mkdir()
        (guard / "sitecustomize.py").write_text(NETWORK_GUARD)
        env.update(
            PYTHONPATH=str(guard),
            COVERAGE_FILE=str(work / ".coverage"),
            MYPY_CACHE_DIR=str(work / "mypy"),
            RUFF_CACHE_DIR=str(work / "ruff"),
        )

        def execute(
            name: str,
            command: list[str],
            *,
            cwd: Path = ROOT,
            timeout: int = 300,
            extra_env: dict[str, str] | None = None,
        ) -> dict:
            print(f"Running {name} ...", flush=True)
            result, output_text = command_result(
                name, command, cwd=cwd, env=env | (extra_env or {}), timeout=timeout
            )
            if extra_env:
                result["environment_overrides"] = extra_env
            if name == "uv_version" and result["status"] == "PASS":
                result["version"] = output_text.strip()
            if name in {"catalog_stdio_checker", "installed_wheel_mcp"}:
                try:
                    evidence = json.loads(output_text.strip().splitlines()[-1])
                    result["evidence"] = {
                        k: v
                        for k, v in evidence.items()
                        if k
                        in {
                            "server_version",
                            "tool_count",
                            "complete_reads",
                            "truncated_reads",
                            "scope_denials",
                            "unknown_write_denied",
                            "catalog_counts_unchanged",
                            "version",
                            "tools",
                            "wheel_import",
                            "repeated_calls",
                            "scope_denied",
                        }
                    }
                except (ValueError, IndexError):
                    pass  # Exit status remains authoritative; no raw output enters the report.
            stages.append(result)
            print(f"  {result['status']}", flush=True)
            return result

        def skip(name: str) -> None:
            stages.append({"name": name, "status": "NOT_RUN", "reason": "Prerequisite failed."})

        stages.append(
            {
                "name": "python_compatibility",
                "status": "PASS" if sys.version_info >= (3, 12) else "BLOCKED",
                "requires_python": ">=3.12",
                "verified": platform.python_version(),
                "limitation": "Only this interpreter/platform executed; no full version matrix.",
            }
        )
        execute("uv_version", ["uv", "--version"])
        execute("lock_consistency", ["uv", "lock", "--check", "--offline"])
        sync = execute(
            "locked_dependency_install", ["uv", "sync", "--locked", "--offline", "--dev"]
        )
        if sync["status"] == "PASS":
            execute("ruff", [sys.executable, "-m", "ruff", "check", "."])
            execute("mypy", [sys.executable, "-m", "mypy", "--strict", "src/dce"])
            xml = work / "pytest.xml"
            cov = work / "coverage.json"
            tests = execute(
                "pytest",
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "--tb=short",
                    "-p",
                    "pytest_cov.plugin",
                    "-o",
                    "cache_dir=" + str(work / "pytest-cache"),
                    "--basetemp=" + str(work / "pytest-tmp"),
                    "--cov=src/dce",
                    "--cov-report=term",
                    "--cov-report=json:" + str(cov),
                    "--junitxml=" + str(xml),
                ],
                timeout=600,
            )
            try:
                test_data = parse_junit(xml)
                coverage = json.loads(cov.read_text())["totals"]["percent_covered"]
                if not isinstance(coverage, (int, float)) or not 0 <= coverage <= 100:
                    raise ValueError("Invalid coverage")
                coverage = round(coverage, 2)
                threshold = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"][
                    "coverage"
                ]["report"]["fail_under"]
                if test_data["status"] != "PASS" or coverage < threshold:
                    tests.update(
                        status="FAIL", reason="Failed/skipped cases or insufficient coverage."
                    )
            except (OSError, ValueError, KeyError, TypeError, ET.ParseError):
                tests.update(
                    status="FAIL", reason="Fresh JUnit/coverage evidence missing or invalid."
                )
        else:
            for name in ("ruff", "mypy", "pytest"):
                skip(name)
        if sync["status"] == "PASS":
            demo_catalog = work / "synthetic-catalog.sqlite3"
            demo = execute(
                "synthetic_cli_init",
                [
                    str(ROOT / ".venv/bin/dce"),
                    "--catalog",
                    str(demo_catalog),
                    "init",
                    "--fixture",
                    str(ROOT / "fixtures/synthetic-discovery.json"),
                    "--no-ai",
                ],
            )
            if demo["status"] == "PASS":
                execute(
                    "catalog_stdio_checker",
                    [sys.executable, "scripts/check_mcp_stdio.py", "--catalog", str(demo_catalog)],
                    timeout=90,
                )
            else:
                skip("catalog_stdio_checker")
        else:
            skip("synthetic_cli_init")
            skip("catalog_stdio_checker")
        execute("index_safety", [sys.executable, "scripts/check_public_data.py"])
        stages.append(source_safety(ROOT))
        execute("diff_whitespace", ["git", "diff", "--check"])
        build = execute(
            "wheel_build", ["uv", "build", "--wheel", "--offline", "--out-dir", str(work / "dist")]
        )
        wheels = list((work / "dist").glob("*.whl"))
        if build["status"] == "PASS" and len(wheels) == 1:
            build["artifact"] = {
                "filename": wheels[0].name,
                "sha256": hashlib.sha256(wheels[0].read_bytes()).hexdigest(),
                "bytes": wheels[0].stat().st_size,
            }
            venv = work / "installed"
            created = execute(
                "isolated_venv", ["uv", "venv", "--offline", "--python", sys.executable, str(venv)]
            )
            requirements = work / "runtime-requirements.txt"
            exported = execute(
                "locked_runtime_export",
                [
                    "uv",
                    "export",
                    "--frozen",
                    "--offline",
                    "--no-dev",
                    "--no-emit-project",
                    "--format",
                    "requirements-txt",
                    "--output-file",
                    str(requirements),
                ],
            )
            if created["status"] == exported["status"] == "PASS":
                python = str(venv / "bin/python")
                installed = execute(
                    "isolated_locked_dependencies",
                    [
                        "uv",
                        "sync",
                        "--locked",
                        "--offline",
                        "--no-dev",
                        "--no-install-project",
                        "--python",
                        python,
                    ],
                    extra_env={"UV_PROJECT_ENVIRONMENT": str(venv)},
                )
                wheel = execute(
                    "isolated_wheel_install",
                    [
                        "uv",
                        "pip",
                        "install",
                        "--offline",
                        "--python",
                        python,
                        "--no-deps",
                        str(wheels[0]),
                    ],
                )
                if installed["status"] == wheel["status"] == "PASS":
                    execute("installed_cli_help", [str(venv / "bin/dce"), "--help"], cwd=work)
                    execute(
                        "installed_cli_doctor",
                        [
                            str(venv / "bin/dce"),
                            "--catalog",
                            str(work / "doctor.sqlite3"),
                            "doctor",
                            "--mock",
                        ],
                        cwd=work,
                    )
                    smoke = work / "wheel_smoke.py"
                    smoke.write_text(WHEEL_SMOKE)
                    execute("installed_wheel_mcp", [python, str(smoke)], cwd=work, timeout=60)
                else:
                    for name in (
                        "installed_cli_help",
                        "installed_cli_doctor",
                        "installed_wheel_mcp",
                    ):
                        skip(name)
            else:
                skip("isolated_install_and_smoke")
        else:
            if build["status"] == "PASS":
                build.update(status="FAIL", reason="Expected exactly one newly built Wheel.")
            skip("isolated_install_and_smoke")
    cases = test_data.pop("cases", [])
    groups = {
        name: summarize_cases([c for c in cases if c["module"] in modules])
        for name, modules in GROUPS.items()
    }
    # Sources are installed editable by the lock sync, so metadata describes this run's environment.
    dependencies = {
        d.metadata["Name"]: d.version
        for d in importlib.metadata.distributions()
        if d.metadata.get("Name")
    }
    status = (
        "FAIL"
        if any(s["status"] == "FAIL" for s in stages)
        else "BLOCKED"
        if any(s["status"] != "PASS" for s in stages)
        else "PASS"
    )
    summary = {
        "schema_version": 1,
        "status": status,
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "implementation_sha256": implementation_digest(ROOT),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": dict(sorted(dependencies.items())),
        "stages": stages,
        "tests": test_data,
        "coverage_percent": coverage,
        "functional_acceptance": groups,
        "network": "loopback-only Python; uv offline",
        "not_verified": [
            "Cursor desktop Host reload and model-visible images",
            "Real company platform APIs in this run",
            "Real ZenTao Token expiry recovery",
            "Real log permissions/retention in a newly installed environment",
            "Actual human approval and model relationship inference quality",
            "Other Python versions and operating systems",
        ],
    }
    write_reports(summary, output)
    print(f"Acceptance {status}: {output / 'AUTOMATED_ACCEPTANCE.md'}", flush=True)
    return 0 if status == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/acceptance")
    args = parser.parse_args()
    return run(args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
