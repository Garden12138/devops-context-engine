import copy
import json

import pytest
import yaml
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from dce.cli import app
from dce.common.errors import DceError
from dce.project.context import load_project, refresh, template, validate_text
from dce.project.model import ProjectContext


@pytest.fixture
def document():
    data = template("demo")
    data["scope"] = {
        "zentao": {"instance": "z-one", "projects": ["1"], "products": [], "bugs": []},
        "gitlab": {"instance": "g-one", "projects": ["1", "2"]},
    }
    data["relationships"] = [
        {
            "id": "r1",
            "from": {"type": "zentao_project", "instance": "z-one", "id": "1"},
            "relation": "implemented_by",
            "to": {"type": "gitlab_project", "instance": "g-one", "id": "1"},
            "status": "proposed",
            "confidence": 0.99,
            "evidence": [
                {
                    "kind": "agent_analysis",
                    "source": "demo",
                    "locator": "README.md",
                    "observed_at": "2026-11-04T00:00:00Z",
                    "revision": "abc",
                    "summary": "synthetic candidate",
                }
            ],
            "approved_by": None,
            "approved_at": None,
            "notes": "keep human note",
        }
    ]
    return data


def validate(data):
    return validate_text(yaml.safe_dump(data), workspace_id="demo")


def test_schema_roundtrip_multi_many_and_distinct_instances(document):
    extra = copy.deepcopy(document["relationships"][0])
    extra["id"] = "r2"
    extra["to"]["id"] = "2"
    document["relationships"].append(extra)
    model = validate(document)
    assert len(model.relationships) == 2
    Draft202012Validator(ProjectContext.model_json_schema()).validate(
        model.model_dump(by_alias=True, mode="json")
    )
    assert model.relationships[0].from_.id == model.relationships[0].to.id
    assert model.relationships[0].from_.instance != model.relationships[0].to.instance
    assert validate(model.model_dump(by_alias=True, mode="json")) == model


def test_confirmed_requires_evidence_and_human_metadata(document):
    rel = document["relationships"][0]
    rel["status"] = "confirmed"
    for update in (
        {},
        {"approved_by": "owner"},
        {"approved_by": "codex", "approved_at": "2026-11-04T01:00:00Z"},
        {"approved_by": "owner", "approved_at": "2026-11-04T01:00:00"},
    ):
        candidate = copy.deepcopy(document)
        candidate["relationships"][0].update(update)
        with pytest.raises(DceError):
            validate(candidate)
    rel.update(approved_by="human-owner", approved_at="2026-11-04T01:00:00Z")
    assert validate(document).relationships[0].status == "confirmed"
    rel["evidence"] = []
    with pytest.raises(DceError):
        validate(document)


def test_refresh_preserves_approval_rejection_notes_and_flags_change(document):
    document["relationships"][0].update(
        status="confirmed", approved_by="owner", approved_at="2026-11-04T01:00:00Z"
    )
    project = validate(document)
    unchanged = refresh(project, project.relationships)
    assert unchanged.relationships[0].status == "confirmed"
    assert unchanged.relationships[0].approved_by == "owner"
    changed = project.relationships[0].model_copy(deep=True)
    changed.evidence[0].revision = "new-revision"
    result = refresh(project, [changed])
    assert result.relationships[0].status == "stale"
    assert result.relationships[0].notes == "keep human note"
    assert result.relationships[0].approved_by == "owner"
    changed.to.id = "2"
    assert refresh(project, [changed]).relationships[0].status == "conflicted"
    project.relationships[0].status = "rejected"
    assert refresh(project, [changed]).relationships[0].status == "rejected"
    assert refresh(project, []).relationships[0].status == "rejected"
    changed.id = "new"
    result = refresh(project, [changed])
    assert result.relationships[1].status == "proposed"
    assert result.relationships[1].approved_by is None
    with pytest.raises(DceError):
        refresh(project, [changed, changed])


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(token="never-store"),
        lambda d: d["relationships"][0].update(notes="password=never-store"),
        lambda d: d["workspace"]["roots"][0].update(
            remote_url="https://user:pass@example.invalid/a"
        ),
        lambda d: d["workspace"]["roots"][0].update(path="../escape"),
        lambda d: d["relationships"][0]["to"].update(instance="g-other"),
        lambda d: d["relationships"][0]["to"].update(id="foreign-project"),
        lambda d: d["relationships"].append(copy.deepcopy(d["relationships"][0])),
        lambda d: d.update(schema_version=2),
    ],
)
def test_reject_secrets_scope_escape_and_duplicate_ids(document, mutate):
    mutate(document)
    with pytest.raises(DceError) as error:
        validate(document)
    assert "never-store" not in error.value.message


def test_safe_yaml_and_workspace_isolation(tmp_path, document):
    for text in (
        "a: &x [*x]",
        "schema_version: 1\nschema_version: 1",
        "!!python/object/apply:os.system [echo bad]",
        "a: " + "x" * 1_000_000,
    ):
        with pytest.raises(DceError):
            validate_text(text)
    for name in ("one", "two"):
        path = tmp_path / name / ".dce"
        path.mkdir(parents=True)
        data = copy.deepcopy(document)
        data["workspace"]["id"] = name
        (path / "project.yaml").write_text(yaml.safe_dump(data))
    a = load_project(tmp_path / "one", workspace_id="one")
    b = load_project(tmp_path / "two", workspace_id="two")
    a.relationships[0].status = "rejected"
    assert b.relationships[0].status == "proposed"
    with pytest.raises(DceError):
        load_project(tmp_path / "two", workspace_id="one")
    path = tmp_path / "one" / ".dce" / "project.yaml"
    path.unlink()
    path.symlink_to(tmp_path / "two" / ".dce" / "project.yaml")
    with pytest.raises(DceError):
        load_project(tmp_path / "one")


def test_cli_template_schema_validate_never_writes(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["project", "template", "--workspace-id", "demo"])
    assert result.exit_code == 0
    document = json.loads(result.stdout)
    path = tmp_path / ".dce"
    path.mkdir()
    (path / "project.yaml").write_text(yaml.safe_dump(document))
    before = (path / "project.yaml").read_bytes()
    result = runner.invoke(app, ["project", "validate", str(tmp_path), "--workspace-id", "demo"])
    assert result.exit_code == 0 and json.loads(result.stdout)["data"]["valid"]
    assert (path / "project.yaml").read_bytes() == before
    result = runner.invoke(app, ["project", "schema"])
    assert result.exit_code == 0 and "$defs" in json.loads(result.stdout)
    result = runner.invoke(app, ["project", "validate", str(tmp_path), "--workspace-id", "other"])
    assert result.exit_code == 2


def test_unknown_local_instance_and_escaping_git_root_are_rejected(tmp_path, document):
    for node in (
        {"type": "code_module", "instance": "unknown", "id": "api"},
        {"type": "swarm_service", "instance": "unscoped", "id": "service"},
    ):
        document["relationships"][0]["to"] = node
        with pytest.raises(DceError):
            validate(document)
    document["relationships"][0]["to"] = {"type": "code_module", "instance": "demo", "id": "api"}
    assert validate(document)
    root = tmp_path / "workspace"
    (root / ".dce").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)
    document["workspace"]["roots"][0]["path"] = "linked"
    (root / ".dce" / "project.yaml").write_text(yaml.safe_dump(document))
    with pytest.raises(DceError):
        load_project(root)
