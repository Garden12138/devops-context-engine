import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from dce.cli import app
from dce.common.errors import DceError
from dce.project.context import load_project, refresh, template, validate_text
from dce.project.model import ProjectContext


def evidence():
    return {
        "kind": "platform_observation",
        "source": "g",
        "locator": "synthetic-read",
        "observed_at": "2026-11-05T00:00:00Z",
        "revision": "a" * 40,
        "summary": "Synthetic direct fact, not a business decision.",
    }


def legacy():
    document = template("demo")
    document["scope"] = {
        "gitlab": {"instance": "g", "projects": ["repo"]},
        "portainer": {"instance": "p", "endpoints": ["e"], "stacks": ["s"]},
    }
    for index, status in enumerate(
        ("proposed", "confirmed", "rejected", "stale", "conflicted", "unresolved")
    ):
        document["relationships"].append(
            {
                "id": f"r{index}",
                "from": {"type": "gitlab_project", "instance": "g", "id": "repo"},
                "relation": "related_to",
                "to": {"type": "ci_job", "instance": "g", "id": str(index)},
                "status": status,
                "confidence": 0.8,
                "evidence": [evidence()],
                "approved_by": "human-owner" if status == "confirmed" else None,
                "approved_at": "2026-11-05T01:00:00Z" if status == "confirmed" else None,
                "notes": "retain every review and note",
            }
        )
    return document


def parse(document):
    return validate_text(yaml.safe_dump(document))


def test_explicit_pure_migration_preserves_every_legacy_relationship(tmp_path: Path):
    from dce.project.context import migrate

    document = legacy()
    workspace = tmp_path / "business"
    (workspace / ".dce").mkdir(parents=True)
    file = workspace / ".dce/project.yaml"
    file.write_text(yaml.safe_dump(document))
    original = file.read_bytes()
    old = load_project(workspace)
    assert old.schema_version == 1
    Draft202012Validator(json.loads(Path("schemas/project-v1.schema.json").read_text())).validate(
        old.model_dump(mode="json", by_alias=True)
    )
    upgraded = migrate(old)
    assert upgraded.schema_version == 2
    assert old.schema_version == 1 and file.read_bytes() == original
    assert upgraded.relationships == old.relationships
    assert upgraded.metadata == old.metadata and upgraded.scope == old.scope
    assert all(r.to.type == "ci_job" for r in upgraded.relationships)
    assert migrate(upgraded) == upgraded
    with pytest.raises(DceError):
        migrate(upgraded, target_version=1)
    result = CliRunner().invoke(app, ["project", "migrate", str(workspace)])
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["schema_version"] == 2 and len(output["relationships"]) == 6
    assert file.read_bytes() == original
    assert (
        json.loads(
            CliRunner().invoke(app, ["project", "template", "--schema-version", "2"]).stdout
        )["schema_version"]
        == 2
    )


def qualified(kind, instance, identifier, **details):
    return {
        "type": kind,
        "instance": instance,
        "id": identifier,
        "details": {"kind": kind, **details},
    }


def expanded():
    data = legacy()
    data["schema_version"] = 2
    pairs = [
        ("source_branch", "g", "branch-a", {"project_id": "repo", "ref": "topic-a"}),
        ("git_ref", "g", "tag-a", {"project_id": "repo", "ref": "v1", "ref_kind": "tag"}),
        (
            "ci_job_definition",
            "g",
            "definition-a",
            {"project_id": "repo", "ref": "topic-a", "path": ".gitlab-ci.yml", "job_name": "build"},
        ),
        (
            "ci_job_execution",
            "g",
            "execution-a",
            {
                "project_id": "repo",
                "pipeline_id": "q",
                "job_id": "j",
                "ref": "topic-a",
                "sha": "a" * 40,
                "status": "manual",
            },
        ),
        ("image_tag", "p", "tag-image", {"repository": "demo/image", "tag": "latest"}),
        (
            "image_digest",
            "p",
            "digest-image",
            {"repository": "demo/image", "digest": "sha256:" + "b" * 64},
        ),
        (
            "deployment_definition",
            "p",
            "definition-deploy",
            {"endpoint_id": "e", "stack_id": "s", "service_name": "api", "file_revision": "c" * 64},
        ),
        (
            "runtime_observation",
            "p",
            "runtime-a",
            {
                "endpoint_id": "e",
                "service_id": "runtime-service",
                "observed_at": "2026-11-05T00:00:00Z",
                "image": "demo/image:latest",
            },
        ),
        ("environment", "demo", "environment-a", {"name": "Unreviewed environment A"}),
    ]
    for index, (kind, instance, identifier, details) in enumerate(pairs):
        rel = copy.deepcopy(data["relationships"][0])
        rel.update(id=f"new-{index}", to=qualified(kind, instance, identifier, **details))
        data["relationships"].append(rel)
    return data


def test_v2_independent_concepts_and_multiple_branches_environments_versions():
    document = expanded()
    second = copy.deepcopy(document["relationships"][6])
    second["id"] = "other-branch"
    second["to"]["id"] = "branch-b"
    second["to"]["details"]["ref"] = "topic-b"
    document["relationships"].append(second)
    second_environment = copy.deepcopy(document["relationships"][-2])
    second_environment["id"] = "other-environment"
    second_environment["to"]["id"] = "environment-b"
    second_environment["to"]["details"]["name"] = "Unreviewed environment B"
    document["relationships"].append(second_environment)
    model = parse(document)
    Draft202012Validator(ProjectContext.model_json_schema()).validate(
        model.model_dump(mode="json", by_alias=True)
    )
    assert parse(model.model_dump(mode="json", by_alias=True)) == model
    assert model.schema_version == 2
    assert sum(r.status == "confirmed" for r in model.relationships) == 1


def test_new_details_scope_identity_and_v1_boundaries_are_strict():
    for mutate in (
        lambda d: d.update(schema_version=1),
        lambda d: d["relationships"][6]["to"]["details"].update(project_id="foreign"),
        lambda d: d["relationships"][12]["to"]["details"].update(stack_id="foreign"),
        lambda d: d["relationships"][6]["to"].pop("details"),
        lambda d: d["relationships"][8]["to"]["details"].update(path="../private"),
        lambda d: d["relationships"][13]["to"]["details"].update(observed_at="2026-11-05T00:00:00"),
    ):
        document = expanded()
        mutate(document)
        with pytest.raises(DceError):
            parse(document)
    duplicate = expanded()
    other = copy.deepcopy(duplicate["relationships"][6])
    other["id"] = "same-node-conflicting-ref"
    other["to"]["details"]["ref"] = "different"
    duplicate["relationships"].append(other)
    with pytest.raises(DceError):
        parse(duplicate)
    missing_details = expanded()
    missing_details["relationships"][6]["to"].pop("details")
    assert not Draft202012Validator(ProjectContext.model_json_schema()).is_valid(missing_details)
    wrong_kind = expanded()
    wrong_kind["relationships"][6]["to"]["type"] = "git_ref"
    with pytest.raises(DceError):
        parse(wrong_kind)
    foreign_endpoint = expanded()
    foreign_endpoint["relationships"][13]["to"]["details"]["endpoint_id"] = "foreign"
    with pytest.raises(DceError):
        parse(foreign_endpoint)


def test_version_match_is_independent_requires_immutable_identity_and_evidence():
    document = expanded()
    comparison = {
        "status": "matched",
        "basis": "image_digest",
        "expected": "sha256:" + "b" * 64,
        "observed": "sha256:" + "b" * 64,
        "evidence": [evidence()],
    }
    document["relationships"][0]["version_match"] = comparison
    model = parse(document)
    assert model.relationships[0].status == "proposed"
    assert model.relationships[0].version_match.status == "matched"
    invalid_tag = copy.deepcopy(document)
    invalid_tag["relationships"][0]["version_match"].update(expected="latest", observed="latest")
    assert not Draft202012Validator(ProjectContext.model_json_schema()).is_valid(invalid_tag)
    for update in (
        {"evidence": []},
        {"expected": "latest", "observed": "latest"},
        {"observed": "sha256:" + "c" * 64},
        {"basis": "image_tag"},
    ):
        invalid = copy.deepcopy(document)
        invalid["relationships"][0]["version_match"].update(update)
        with pytest.raises(DceError):
            parse(invalid)
    changed = model.relationships[1].model_copy(deep=True)
    changed.version_match = model.relationships[0].version_match.model_copy(deep=True)
    result = refresh(model, [model.relationships[0], changed, *model.relationships[2:]])
    assert result.relationships[1].status == "stale"
    assert result.relationships[1].approved_by == "human-owner"
    assert result.relationships[1].version_match.status == "matched"
    observation = result.relationships[1].model_copy(deep=True)
    observation.version_match.evidence[0].observed_at = datetime(2026, 11, 6, tzinfo=UTC)
    same_facts = refresh(result, [result.relationships[0], observation, *result.relationships[2:]])
    assert same_facts.relationships[1].status == "stale"
    assert same_facts.relationships[1].version_match.status == "matched"
    comparison.update(status="mismatched", basis="commit_sha", expected="a" * 40, observed="b" * 40)
    document["relationships"][0]["version_match"] = comparison
    assert parse(document).relationships[0].version_match.status == "mismatched"
