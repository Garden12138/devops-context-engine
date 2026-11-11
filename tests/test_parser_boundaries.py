import pytest

from dce.common.errors import DceError
from dce.parsers.metadata import MAX_METADATA_BYTES, ci, compose, dockerfile, image, modules


def test_metadata_bounds_and_empty_values() -> None:
    with pytest.raises(DceError, match="size"):
        compose("a" * (MAX_METADATA_BYTES + 1))
    with pytest.raises(DceError, match="node"):
        compose("services:\n" + "  name: one\n" * 13000)
    assert compose("")["services"] == []
    with pytest.raises(DceError):
        compose("services: []")
    assert compose("services:\n  invalid: text")["incomplete"]
    assert compose("services:\n  one:\n    environment: bad")["incomplete"]
    assert compose("services:\n  one:\n    image: app\n    build: /absolute")["incomplete"]


@pytest.mark.parametrize("reference", ["https://host/app", "user:password@host/app", "bad image"])
def test_image_credential_and_syntax_rejected(reference: str) -> None:
    with pytest.raises(DceError):
        image(reference)


def test_module_boundaries() -> None:
    assert modules("pom.xml", "<project><modules><module>../bad</module></modules></project>")[
        "incomplete"
    ]
    assert modules("unknown", "ignored")["incomplete"]
    assert modules("go.mod", "go 1.23")["incomplete"]
    assert modules("settings.gradle", '/* ignored */\ninclude ":one" // ignored')["modules"] == [
        "one"
    ]
    assert modules("go.work", 'go 1.23\nuse "./api"\n')["modules"] == ["api"]
    assert modules("package.json", '{"workspaces":["lib"]}')["modules"] == ["lib"]
    for text in ("[]", '{"workspaces":1}', '{"workspaces":[1]}'):
        with pytest.raises(DceError):
            modules("package.json", text)


def test_dockerfile_copy_formats_and_incomplete() -> None:
    parsed = dockerfile('FROM alpine:3\nCOPY ["api/app.jar", "common/lib.jar", "/opt/"]\n')
    assert parsed["copy_sources"] == ["api/app.jar", "common/lib.jar"]
    assert dockerfile('COPY ["malformed"\n')["incomplete"]
    assert dockerfile("COPY [1, 2]\n")["incomplete"]
    assert dockerfile("ADD https://example.invalid/file /opt/")["incomplete"]
    assert dockerfile('COPY "unterminated\n')["incomplete"]
    assert dockerfile("FROM ${BASE}\n")["incomplete"]
    assert dockerfile("# comment\n\n")["base_images"] == []


def test_ci_dynamic_and_secret_remote_reference() -> None:
    parsed = ci("include: 'ci/local.yml'\nbuild:\n  script: 'docker build -t app:${TAG} .'\n")
    assert parsed["incomplete"] and parsed["jobs"][0]["images"] == []
    parsed = ci("include:\n  remote: https://user:password@example.invalid/a?token=private\n")
    assert "password" not in str(parsed) and "private" not in str(parsed)
    assert ci("include: 1\nbuild:\n  script: 1")["incomplete"]
    assert ci("build:\n  script: [1]")["incomplete"]
