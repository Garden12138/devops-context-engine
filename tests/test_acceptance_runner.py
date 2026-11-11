"""Prevent false-positive acceptance reports and unsafe offline execution."""

import importlib.util
import os
import subprocess
import sys

import pytest

spec = importlib.util.spec_from_file_location("acceptance", "scripts/run_acceptance.py")
assert spec and spec.loader
acceptance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance)


def test_failed_and_missing_commands_cannot_pass(tmp_path):
    result, output = acceptance.command_result(
        "failed",
        [sys.executable, "-c", "import os;print(os.environ['SYNTHETIC_DIAGNOSTIC']);exit(7)"],
        cwd=tmp_path,
        env={**os.environ, "SYNTHETIC_DIAGNOSTIC": "synthetic failure"},
    )
    assert result["status"] == "FAIL" and result["exit_code"] == 7
    assert "synthetic failure" in output and "synthetic failure" not in str(result)
    result, _ = acceptance.command_result(
        "missing",
        [str(tmp_path / "missing-executable")],
        cwd=tmp_path,
        env=dict(os.environ),
    )
    assert result["status"] == "BLOCKED" and result["exit_code"] is None


def test_deadline_stops_command_group(tmp_path):
    result, _ = acceptance.command_result(
        "deadline",
        [sys.executable, "-c", "import time;time.sleep(30)"],
        cwd=tmp_path,
        env=dict(os.environ),
        timeout=1,
    )
    assert result["status"] == "BLOCKED" and result["duration_seconds"] < 10


def test_missing_or_invalid_evidence_cannot_reuse_old_results(tmp_path):
    path = tmp_path / "pytest.xml"
    with pytest.raises(OSError):
        acceptance.parse_junit(path)
    path.write_text("<testsuites/>")
    with pytest.raises(ValueError):
        acceptance.parse_junit(path)
    path.write_text(
        "<testsuites><testsuite><testcase classname='test_demo' name='ok'/>"
        "<testcase classname='test_demo' name='failure'>"
        "<failure message='expected bounded output'/></testcase>"
        "<testcase classname='test_demo' name='collection'><error/></testcase>"
        "<testcase classname='test_demo' name='skip'><skipped/></testcase>"
        "</testsuite></testsuites>"
    )
    result = acceptance.parse_junit(path)
    assert (result["total"], result["passed"], result["failed"], result["skipped"]) == (4, 1, 2, 1)
    assert result["status"] == "FAIL" and result["pass_rate"] == 25
    assert "test_demo::collection" in result["failed_tests"]
    assert result["failures"][0]["reason"] == "expected bounded output"
    assert acceptance.summarize_cases([{"status": "NOT_RUN"}])["status"] == "NOT_RUN"


def test_guard_blocks_nonloopback_even_in_child_process(tmp_path):
    guard = tmp_path / "sitecustomize.py"
    guard.write_text(acceptance.NETWORK_GUARD)
    result = subprocess.run(
        [sys.executable, "-c", "import socket;socket.getaddrinfo('example.invalid',443)"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
    )
    assert result.returncode and b"offline acceptance blocks external DNS" in result.stderr
    result = subprocess.run(
        [sys.executable, "-c", "import socket;socket.socket().connect(('203.0.113.1',443))"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
    )
    assert result.returncode and b"offline acceptance permits loopback only" in result.stderr
    result = subprocess.run(
        [sys.executable, "-c", "import socket;assert socket.getaddrinfo('127.0.0.1',443)"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
    )
    assert result.returncode == 0


def test_impl_digest_changes_when_code_changes_and_ignores_cache(tmp_path):
    for directory in ("src", "tests", "scripts", "schemas", "prompts"):
        (tmp_path / directory).mkdir()
    (tmp_path / "pyproject.toml").write_text("synthetic")
    (tmp_path / "uv.lock").write_text("synthetic")
    before = acceptance.implementation_digest(tmp_path)
    (tmp_path / "src/demo.py").write_text("changed")
    after = acceptance.implementation_digest(tmp_path)
    assert before != after
    (tmp_path / "src/__pycache__").mkdir()
    (tmp_path / "src/__pycache__/demo.pyc").write_bytes(b"ignored")
    assert after == acceptance.implementation_digest(tmp_path)


def test_offline_child_uses_prepared_cache_without_inheriting_credentials(tmp_path):
    cache = tmp_path / "prepared-cache"
    cache.mkdir()
    (cache / "ready").write_text("synthetic-build-dependency")
    env = acceptance.acceptance_environment(
        {
            **os.environ,
            "UV_CACHE_DIR": str(cache),
            "DCE_ZENTAO_TOKEN": "synthetic-business-secret",
            "GITHUB_TOKEN": "synthetic-host-secret",
            "HTTP_PROXY": "https://proxy.example.invalid",
        }
    )
    code = (
        "import os;from pathlib import Path;"
        "assert (Path(os.environ['UV_CACHE_DIR'])/'ready').read_text()"
        " == 'synthetic-build-dependency';"
        "assert os.environ['UV_OFFLINE'] == 'true';"
        "assert not any(k in os.environ for k in "
        "('DCE_ZENTAO_TOKEN','GITHUB_TOKEN','HTTP_PROXY'))"
    )
    result, _ = acceptance.command_result(
        "prepared_cache",
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=env,
    )
    assert result["status"] == "PASS"
