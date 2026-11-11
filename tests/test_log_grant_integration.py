"""All services, grants and logs are synthetic; real logs must never be used here."""

import asyncio
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from test_log_grant import policy_file as policy_file
from test_service_logs import ARGS, END, START, LogStream, query, record
from test_service_logs import logs as logs

from dce.common.errors import DceError
from dce.common.service_logs import timestamp_ns
from dce.mcp.startup import load_log_policy
from dce.security.log_grant import ServiceLogGrant


@pytest.fixture
def restricted(logs, policy_file):
    app, state = logs
    grant = ServiceLogGrant.load(policy_file[0])
    app.fact_scope.portainer_log_policy = grant
    return app, state, grant


def log_calls(state):
    return [r for r in state["calls"] if r.url.path.endswith("/logs")]


@pytest.mark.parametrize("by_id", [False, True])
def test_exact_service_both_selectors_caps_and_one_use(restricted, by_id):
    app, state, grant = restricted
    changes = {"service_name": None, "service_id": "svc1"} if by_id else {}
    response = query(
        (app, state),
        max_lines=500,
        max_bytes=262144,
        max_output_bytes=16384,
        timeout_seconds=15,
        **changes,
    )
    assert not response.isError
    q = record(response)["query"]
    assert (q["max_lines"], q["max_bytes"], q["max_output_bytes"], q["timeout_seconds"]) == (
        20,
        16384,
        8192,
        10,
    )
    assert q["follow"] is False and grant.used()
    assert log_calls(state)[0].url.params["tail"] == "20"
    assert log_calls(state)[0].url.params["follow"] == "false"
    assert len(response.model_dump_json(by_alias=True, exclude_none=True).encode()) <= 8192
    before = len(state["calls"])
    denied = query((app, state), **changes)
    assert denied.isError and denied.structuredContent["error"]["code"] == "PERMISSION_DENIED"
    assert len(log_calls(state)) == 1 and len(state["calls"]) == before
    tools = {t.name: t for t in asyncio.run(app.list_tools())}
    assert tools["portainer_query"].meta["dce"]["service_logs"]["availability"] == "blocked"


@pytest.mark.parametrize(
    "changes",
    [
        {"service_name": "ad"},
        {"service_name": "demo_template"},
        {"service_name": None, "service_id": "svc2"},
        {"service_name": None, "service_id": "svc"},
        {"stack_id": "8"},
        {"endpoint_id": "2"},
        {"instance": "other"},
        {"start_time": "2026-11-01T09:55:59+08:00"},
        {"start_time": "2026-11-01T09:00:00+08:00", "end_time": "2026-11-01T09:01:00+08:00"},
        {"end_time": "2026-11-01T10:01:01+08:00"},
        {"follow": True},
        {"follow": False},
        {"portainer_log_policy": None},
    ],
)
def test_out_of_scope_denied_before_any_remote_request(restricted, changes):
    app, state, grant = restricted
    app.fact_scope.portainer_endpoints.add("2")
    app.fact_scope.portainer_stacks.add("8")
    app.fact_scope.portainer_log_scopes |= {("2", "7"), ("1", "8")}
    response = query((app, state), **changes)
    assert response.isError
    assert response.structuredContent["error"]["code"] in {"PERMISSION_DENIED", "INVALID_PAYLOAD"}
    assert state["calls"] == [] and not grant.used()


def test_no_pair_scope_has_zero_log_calls(restricted):
    app, state, grant = restricted
    app.fact_scope.portainer_log_scopes.clear()
    assert query((app, state)).isError
    assert state["calls"] == [] and not grant.used()


@pytest.mark.parametrize(
    "mismatch", ["swarm_pin", "stack_name", "service_name", "recreated_id", "namespace"]
)
def test_remote_identity_must_match_pin_before_log_request(restricted, mismatch):
    app, state, grant = restricted
    if mismatch == "swarm_pin":
        state["stack"]["SwarmId"] = "swarm2"
        state["info"]["Swarm"]["Cluster"]["ID"] = "swarm2"
    elif mismatch == "stack_name":
        state["stack"].update(Name="other", Namespace="demo")
    elif mismatch == "service_name":
        state["service"]["Spec"]["Name"] = "demo_template_extra"
    elif mismatch == "recreated_id":
        state["service"]["ID"] = "svc2"
    else:
        state["service"]["Spec"]["Labels"]["com.docker.stack.namespace"] = "other"
    response = (
        query((app, state), service_name=None, service_id="svc1")
        if mismatch == "service_name"
        else query((app, state))
    )
    assert response.isError and not log_calls(state) and not grant.used()


def test_revocation_and_expiry_block_without_remote_reads(restricted, policy_file, monkeypatch):
    app, state, grant = restricted
    p, _ = policy_file
    original = time.time_ns()
    monkeypatch.setattr(time, "time_ns", lambda: original + 4000 * 10**9)
    assert query((app, state)).isError and not state["calls"]
    monkeypatch.setattr(time, "time_ns", lambda: original)
    p.rename(p.with_suffix(".revoked"))
    assert query((app, state)).isError and not state["calls"] and not grant.used()


def test_rolling_window_rechecked_at_dispatch(restricted, monkeypatch):
    app, state, _ = restricted
    now = timestamp_ns(END)
    clock = [now]
    monkeypatch.setattr(time, "time_ns", lambda: clock[0])
    transport = app.services.transports["portainer"]

    def handle(request):
        response = transport.handle_request(request)
        if request.url.path.endswith("/version"):
            clock[0] += 5 * 10**9
        return response

    app.services.transports["portainer"] = httpx.MockTransport(handle)
    start = datetime.fromtimestamp(now // 10**9 - 300, UTC).isoformat()
    response = query((app, state), start_time=start)
    assert not response.isError
    q = record(response)["query"]
    assert timestamp_ns(q["start_time"]) == clock[0] - 300 * 10**9
    assert log_calls(state)[0].url.params["since"] == str(clock[0] // 10**9 - 300)
    assert timestamp_ns(q["end_time"]) - timestamp_ns(q["start_time"]) <= 300 * 10**9
    assert q["follow"] is False and len(log_calls(state)) == 1


def test_docker_since_rounds_inward_for_subsecond_grant(restricted, monkeypatch):
    app, state, _ = restricted
    now = timestamp_ns(END) + 123_456_789
    monkeypatch.setattr(time, "time_ns", lambda: now)
    response = query((app, state), start_time="2026-11-01T09:56:00.123456789+08:00")
    assert not response.isError
    since = int(log_calls(state)[0].url.params["since"]) * 10**9
    assert now - 300 * 10**9 <= since < now - 299 * 10**9


def test_log_http_failure_consumes_unique_attempt(restricted):
    app, state, grant = restricted
    state["status"] = 403
    assert query((app, state)).isError and grant.used()
    assert query((app, state)).isError
    assert len(log_calls(state)) == 1


@pytest.mark.parametrize("failure", [httpx.ReadTimeout("fixture"), httpx.ReadError("fixture")])
def test_stream_failure_spends_once_and_closes(restricted, failure):
    app, state, grant = restricted
    state["stream"] = LogStream([], failure=failure)
    assert query((app, state)).isError and grant.used() and state["stream"].closed
    assert query((app, state)).isError and len(log_calls(state)) == 1


def test_cancelled_log_read_spends_once_and_closes(restricted):
    app, state, grant = restricted
    state["stream"] = LogStream([b"x"], delay=10)

    async def cancel():
        task = asyncio.create_task(app.call_tool("portainer_query", ARGS))
        while not log_calls(state):
            await asyncio.sleep(0)
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel())
    assert state["stream"].closed and grant.used()
    assert query((app, state)).isError and len(log_calls(state)) == 1


def test_policy_output_budget_is_enforced(restricted, policy_file):
    app, state, _ = restricted
    p, data = policy_file
    data["max_output_bytes"] = 4096
    p.write_text(json.dumps(data))
    app.fact_scope.portainer_log_policy = ServiceLogGrant.load(p)
    result = query((app, state), max_output_bytes=16384)
    assert len(result.model_dump_json(by_alias=True, exclude_none=True).encode()) <= 4096


def test_policy_and_pair_constraints_are_both_required(policy_file):
    p, _ = policy_file
    for scopes in [set(), {("1", "8")}, {("1", "7"), ("1", "8")}]:
        with pytest.raises(DceError):
            load_log_policy(p, scopes)
    assert load_log_policy(p, {("1", "7")}) is not None


def test_single_use_is_atomic_across_processes(policy_file):
    p, _ = policy_file
    now = time.time_ns()
    code = """
import sys
from pathlib import Path
import dce.security.log_grant as module
from dce.common.service_logs import LogControls
from dce.common.errors import DceError
module.time.time_ns=lambda:int(sys.argv[2])
grant=module.ServiceLogGrant.load(Path(sys.argv[1]))
try:
    grant.consume(LogControls(start_time=sys.argv[3],end_time=sys.argv[4]))
except DceError:
    sys.exit(2)
"""
    command = [str(Path(".venv/bin/python").absolute()), "-c", code, str(p), str(now), START, END]
    children = [
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(5)
    ]
    codes = []
    for child in children:
        child.communicate(timeout=20)
        codes.append(child.returncode)
    assert codes.count(0) == 1 and codes.count(2) == 4
