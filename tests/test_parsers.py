import pytest

from dce.common.errors import DceError
from dce.parsers.metadata import ci, compose, dockerfile, image, modules


def test_module_formats() -> None:
    assert modules(
        "pom.xml",
        '<project xmlns="urn:maven"><modules><module>api</module>'
        "<module>common</module></modules></project>",
    )["modules"] == ["api", "common"]
    assert modules("settings.gradle.kts", 'include(":api", ":common:core")')["modules"] == [
        "api",
        "common/core",
    ]
    assert modules("go.work", "go 1.23\nuse (\n ./api\n ./common\n)\n")["modules"] == [
        "api",
        "common",
    ]
    assert modules("go.mod", "module example.invalid/demo\ngo 1.23")["modules"] == ["."]
    assert modules("package.json", '{"workspaces":{"packages":["apps/*","lib"]}}')["modules"] == [
        "apps/*",
        "lib",
    ]


def test_compose_names_only_and_multi_service_image() -> None:
    result = compose("""services:
  first:
    image: registry.example.invalid/app:latest
    environment: {PASSWORD: synthetic-secret}
  second:
    image: registry.example.invalid/app:latest
    environment: [TOKEN=synthetic-secret, PORT]
""")
    assert "synthetic-secret" not in str(result)
    assert len(result["services"]) == 2
    assert result["services"][0]["environment_names"] == ["PASSWORD"]
    assert result["services"][1]["environment_names"] == ["PORT", "TOKEN"]
    assert result["services"][0]["image"] == result["services"][1]["image"]


def test_image_versions() -> None:
    mutable = image("registry.example.invalid:5000/app:latest")
    assert mutable["repository"] == "registry.example.invalid:5000/app"
    assert mutable["tag"] == "latest"
    assert mutable["mutable_tag"] and mutable["version_uncertain"]
    pinned = image("repo/app:v1@sha256:" + "a" * 64)
    assert pinned["digest"] == "sha256:" + "a" * 64
    assert not pinned["mutable_tag"]
    assert image("repo/app")["tag"] == "latest"
    assert image("${REGISTRY}/app:${TAG}")["incomplete"]


def test_ci_static_evidence_and_includes() -> None:
    result = ci("""include:
  - local: /ci/build.yml
  - project: demo/build
    file: ci.yml
    ref: master
  - remote: https://remote.example.invalid/ci.yml
build:
  stage: build
  script:
    - docker build -f api/Dockerfile -t demo/api:v1 api
    - mvn -pl api,common package
  variables:
    SECRET: synthetic-secret
""")
    assert result["incomplete"]
    assert len(result["includes"]) == 3
    assert result["jobs"][0]["images"] == ["demo/api:v1"]
    assert result["jobs"][0]["module_paths"] == ["api", "common"]
    assert "synthetic-secret" not in str(result)
    assert "docker build" not in str(result)


def test_dockerfile_static_only() -> None:
    result = dockerfile("""FROM alpine:3 AS builder
COPY api/target/app.jar common/target/lib.jar /opt/
RUN echo ignored
FROM builder
COPY --from=builder /opt/ /app/
""")
    assert result["base_images"] == ["alpine:3"]
    assert result["copy_sources"] == ["api/target/app.jar", "common/target/lib.jar"]
    assert "echo" not in str(result)


@pytest.mark.parametrize("text", ["services: !!python/object:os.system {}", "[invalid", "- list"])
def test_invalid_yaml(text: str) -> None:
    with pytest.raises(DceError):
        compose(text)


def test_incomplete_dynamic_metadata() -> None:
    assert compose("services:\n  one:\n    extends: base\n")["incomplete"]
    assert compose("services:\n  one: &shared\n    image: app\n  two: *shared")["incomplete"]
    assert modules("settings.gradle", "include(moduleNames)")["incomplete"]
    with pytest.raises(DceError):
        modules("pom.xml", '<!DOCTYPE x [<!ENTITY evil SYSTEM "file:///etc/passwd">]><project/>')
    with pytest.raises(DceError):
        modules("package.json", "not-json")
