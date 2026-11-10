"""Synthetic temporary grants; no company identities, credentials or log requests."""

import json
import time

import pytest

from dce.common.errors import DceError
from dce.common.service_logs import LogControls, timestamp_ns


@pytest.fixture
def policy_file(tmp_path, monkeypatch):
    from dce.security import log_grant

    monkeypatch.setattr(
        log_grant.time, "time_ns", lambda: timestamp_ns("2026-11-01T10:01:00+08:00")
    )
    tmp_path.chmod(0o700)
    p = tmp_path / "grant.json"
    data = {
        "version": 1,
        "grant_id": "a" * 32,
        "source_instance": "unit",
        "endpoint_id": "1",
        "stack_id": "7",
        "stack_name": "demo",
        "namespace": "demo",
        "swarm_id": "swarm1",
        "service_id": "svc1",
        "compose_service": "template",
        "service_name": "demo_template",
        "issued_at": "2027-01-15T08:00:00Z",
        "expires_at": "2027-01-15T08:30:00Z",
    }
    # Values are relative to an explicit synthetic clock, never the real platform clock.
    from datetime import UTC, datetime

    data["issued_at"] = datetime.fromtimestamp(time.time_ns() // 10**9 - 10, UTC).isoformat()
    data["expires_at"] = datetime.fromtimestamp(time.time_ns() // 10**9 + 1800, UTC).isoformat()
    p.write_text(json.dumps(data))
    p.chmod(0o600)
    return p, data


def controls(**updates):
    from datetime import UTC, datetime

    now = time.time_ns() // 10**9
    return LogControls(
        start_time=datetime.fromtimestamp(now - 300, UTC).isoformat(),
        end_time=datetime.fromtimestamp(now, UTC).isoformat(),
        **updates,
    )


def test_private_grant_limits_and_shared_one_use_marker(policy_file):
    from dce.security.log_grant import ServiceLogGrant

    p, _ = policy_file
    a, b = ServiceLogGrant.load(p), ServiceLogGrant.load(p)
    c = controls()
    a.authorize("unit", "1", "7", service_id=None, service_name="template", controls=c)
    assert (c.max_lines, c.max_bytes, c.max_output_bytes, c.timeout_seconds) == (
        20,
        16384,
        8192,
        10,
    )
    assert not a.used()
    a.consume(c)
    assert a.used() and b.used()
    with pytest.raises(DceError) as e:
        b.consume(controls())
    assert e.value.code == "PERMISSION_DENIED"


@pytest.mark.parametrize(
    "selector",
    [
        {"service_name": "ad", "service_id": None},
        {"service_name": None, "service_id": "svc2"},
        {"service_name": None, "service_id": "svc"},
        {"service_name": "demo_template", "service_id": None},
    ],
)
def test_exact_name_and_id_restriction(policy_file, selector):
    from dce.security.log_grant import ServiceLogGrant

    grant = ServiceLogGrant.load(policy_file[0])
    with pytest.raises(DceError):
        grant.authorize("unit", "1", "7", controls=controls(), **selector)
    assert not grant.used()


def test_revocation_is_seen_by_already_loaded_grant(policy_file):
    from dce.security.log_grant import ServiceLogGrant

    p, _ = policy_file
    grant = ServiceLogGrant.load(p)
    p.rename(p.with_suffix(".revoked"))
    with pytest.raises(DceError):
        grant.consume(controls())
    assert not grant.used()


def test_private_file_and_modified_policy_fail_closed(policy_file):
    from dce.security.log_grant import ServiceLogGrant

    p, data = policy_file
    grant = ServiceLogGrant.load(p)
    p.chmod(0o644)
    with pytest.raises(DceError):
        ServiceLogGrant.load(p)
    p.chmod(0o600)
    data["compose_service"] = "ad"
    p.write_text(json.dumps(data))
    with pytest.raises(DceError):
        grant.consume(controls())
    assert not grant.used()


@pytest.mark.parametrize("mode", ["parent_permissions", "symlink", "oversize", "duplicate"])
def test_unsafe_policy_files_fail_closed(policy_file, mode):
    from dce.security.log_grant import ServiceLogGrant

    p, _ = policy_file
    if mode == "parent_permissions":
        p.parent.chmod(0o755)
    elif mode == "symlink":
        target = p.with_suffix(".target")
        p.rename(target)
        p.symlink_to(target)
    elif mode == "oversize":
        p.write_text(" " * 8193)
    else:
        p.write_text('{"version":1,"version":1}')
    with pytest.raises(DceError):
        ServiceLogGrant.load(p)


@pytest.mark.parametrize(
    "updates",
    [
        {"max_uses": 2},
        {"follow": True},
        {"max_window_seconds": 301},
        {"max_lines": 21},
        {"max_bytes": 65537},
        {"max_output_bytes": 8193},
        {"timeout_seconds": 11},
        {"expires_at": "2030-01-01T00:00:00Z"},
        {"issued_at": "2026-11-01T02:00:00"},
        {"service_name": "demo_ad"},
    ],
)
def test_policy_cannot_exceed_temporary_authorization(policy_file, updates):
    from dce.security.log_grant import ServiceLogGrant

    p, data = policy_file
    p.write_text(json.dumps({**data, **updates}))
    with pytest.raises(DceError) as e:
        ServiceLogGrant.load(p)
    assert e.value.code == "INVALID_PAYLOAD"


def test_state_write_failure_is_not_refunded_and_restart_keeps_it_used(policy_file, monkeypatch):
    from dce.security import log_grant

    p, _ = policy_file
    grant = log_grant.ServiceLogGrant.load(p)

    def fail(_):
        raise OSError("synthetic state failure")

    monkeypatch.setattr(log_grant.os, "fsync", fail)
    with pytest.raises(DceError):
        grant.consume(controls())
    assert grant.used()
    restarted = log_grant.ServiceLogGrant.load(p)
    assert not restarted.available()
    with pytest.raises(DceError):
        restarted.consume(controls())
