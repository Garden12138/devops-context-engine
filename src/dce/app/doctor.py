from typing import Any


def mock_doctor() -> dict[str, Any]:
    """T0 contract; adapter-backed capability probes are added in T1."""
    return {
        "mode": "offline-fixture",
        "platforms": {
            name: {
                "status": "ok",
                "verification": "mock",
                "read_only": True,
                "capabilities": ["fixture_contract"],
                "live_status": "not_verified",
            }
            for name in ("zentao", "gitlab", "portainer")
        },
    }
