import fnmatch
import re
from functools import partial
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dce.common.errors import DceError, ErrorCode
from dce.connectors.gitlab import GitLab
from dce.connectors.portainer import Portainer
from dce.connectors.zentao import ZenTao
from dce.discovery.checkpoint import Checkpoint
from dce.discovery.fixture import Builder
from dce.discovery.snapshots import compare_services, stack_runtime
from dce.graph.model import DiscoveryResult, Edge, fingerprint
from dce.parsers.metadata import ci, compose, dockerfile, modules, safe_path


class ScanScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gitlab_projects: list[str] = Field(default_factory=list)
    gitlab_groups: list[str] = Field(default_factory=list)
    zentao_projects: list[str] = Field(default_factory=list)
    zentao_products: list[str] = Field(default_factory=list)
    portainer_endpoints: list[str] = Field(default_factory=list)
    portainer_stacks: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def explicit_scope(self) -> "ScanScope":
        fields = self.model_dump().values()
        if not any(fields):
            raise ValueError("explicit scan scope required")
        for values in fields:
            if any(not re.fullmatch(r"[\w./-]{1,200}", value) or ".." in value for value in values):
                raise ValueError("scope requires controlled resource IDs")
        return self


MODULE_FILES = {
    "pom.xml",
    "settings.gradle",
    "settings.gradle.kts",
    "go.work",
    "go.mod",
    "package.json",
}


def origin_key(url: str) -> str:
    parsed = urlsplit(url)
    return fingerprint([parsed.scheme.lower(), parsed.hostname, parsed.port])


def relevant(path: str) -> bool:
    name = PurePosixPath(path).name
    return safe_path(path) and (
        name in MODULE_FILES
        or name == "Dockerfile"
        or name.startswith("Dockerfile.")
        or name == ".gitlab-ci.yml"
        or ("compose" in name.lower() and name.endswith((".yaml", ".yml")))
    )


def merge(results: list[DiscoveryResult]) -> DiscoveryResult:
    result = DiscoveryResult()
    result.entities = list({e.id: e for r in results for e in r.entities}.values())
    result.snapshots = list({s.id: s for r in results for s in r.snapshots}.values())
    result.evidence = list({e.id: e for r in results for e in r.evidence}.values())
    edges: dict[str, Edge] = {}
    for item in results:
        for edge in item.edges:
            if edge.id in edges:
                edge = edge.model_copy(
                    update={
                        "evidence_ids": sorted(set(edges[edge.id].evidence_ids + edge.evidence_ids))
                    }
                )
            edges[edge.id] = edge
        result.anomalies.extend(item.anomalies)
        result.warnings.extend(item.warnings)
    result.edges = list(edges.values())
    return result


class Crawler:
    def __init__(
        self,
        scope: ScanScope,
        checkpoint: Checkpoint,
        *,
        gitlab: GitLab | None = None,
        portainer: Portainer | None = None,
        zentao: ZenTao | None = None,
    ) -> None:
        self.scope = scope
        self.checkpoint = checkpoint
        self.gitlab = gitlab
        self.portainer = portainer
        self.zentao = zentao

    def run(self) -> DiscoveryResult:
        try:
            return self._run()
        except DceError as exc:
            self.checkpoint.state["status"] = "failed"
            self.checkpoint.state["error_code"] = exc.code.value
            self.checkpoint.save()
            raise
        except (KeyError, TypeError, ValueError, AttributeError):
            self.checkpoint.state["status"] = "failed"
            self.checkpoint.state["error_code"] = ErrorCode.INVALID_PAYLOAD.value
            self.checkpoint.save()
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid discovery payload.") from None

    def _run(self) -> DiscoveryResult:
        results = []
        if self.scope.gitlab_projects or self.scope.gitlab_groups:
            if self.gitlab is None:
                raise DceError(ErrorCode.AUTH_FAILED, "GitLab adapter is required for scope.")
            projects = set(self.scope.gitlab_projects)
            for group in self.scope.gitlab_groups:
                projects.update(str(p["id"]) for p in self.gitlab.projects(group))
            for project in sorted(projects):
                metadata = self.gitlab.project(project)
                ref = metadata.get("default_branch")
                if not isinstance(ref, str) or not ref:
                    raise DceError(ErrorCode.API_INCOMPATIBLE, "Project default branch is missing.")
                commit = self.gitlab.commit(project, ref).get("id")
                if not isinstance(commit, str) or not commit:
                    raise DceError(ErrorCode.API_INCOMPATIBLE, "Git commit ID is missing.")
                version = fingerprint([commit, metadata.get("path_with_namespace"), ref])
                source = self.gitlab.reader.config.instance_id
                results.append(
                    self.checkpoint.resource(
                        f"{source}:repository:{project}",
                        version,
                        partial(self.repository, project, metadata, commit),
                    )
                )
        if self.scope.portainer_stacks or self.scope.portainer_endpoints:
            if self.portainer is None:
                raise DceError(ErrorCode.AUTH_FAILED, "Portainer adapter is required for scope.")
            stacks = {}
            if self.scope.portainer_endpoints:
                stacks = {
                    str(s["Id"]): s
                    for s in self.portainer.stacks()
                    if str(s.get("EndpointId")) in self.scope.portainer_endpoints
                }
            for stack_id in self.scope.portainer_stacks:
                stacks[stack_id] = self.portainer.stack(stack_id)
            for stack in stacks.values():
                results.append(self.runtime(stack))
        if self.scope.zentao_projects or self.scope.zentao_products:
            if self.zentao is None:
                raise DceError(ErrorCode.AUTH_FAILED, "ZenTao adapter is required for scope.")
            results.append(self.business())
        result = merge(results)
        # Compare declarations only when repository identity AND declared ref/path agree.
        for stack_entity in (e for e in result.entities if e.kind == "stack"):
            attrs = stack_entity.attributes
            for snapshot in (s for s in result.snapshots if s.kind == "git_current"):
                metadata = snapshot.metadata
                if (
                    attrs.get("repository_path") != metadata.get("repository_path")
                    or attrs.get("repository_origin") != metadata.get("repository_origin")
                    or attrs.get("ref", "").removeprefix("refs/heads/") != metadata.get("ref")
                    or attrs.get("config_path") != metadata.get("path")
                ):
                    continue
                for saved in (
                    s
                    for s in result.snapshots
                    if s.resource_key == stack_entity.id and s.kind == "portainer_saved"
                ):
                    diff = compare_services(metadata["services"], saved.metadata["services"])
                    if diff["status"] == "config_drift_candidate":
                        result.anomalies.append(
                            {
                                "stack_id": stack_entity.id,
                                **diff,
                                "snapshot_ids": [snapshot.id, saved.id],
                            }
                        )
        self.checkpoint.complete()
        return result

    def repository(self, project: str, metadata: dict[str, Any], commit: str) -> DiscoveryResult:
        assert self.gitlab is not None
        gitlab = self.gitlab
        source = gitlab.reader.config.instance_id
        b = Builder()
        repo = b.entity(
            source,
            "repository",
            project,
            role="source",
            path=metadata.get("path_with_namespace", str(project)),
            default_branch=metadata["default_branch"],
            commit=commit,
        )
        tree = list(gitlab.tree(project, commit))
        files = [str(item["path"]) for item in tree if item.get("type") == "blob"]
        for path in sorted(set(path for path in files if relevant(path))):
            text = gitlab.raw_file(project, path, commit)
            name = PurePosixPath(path).name
            if name in MODULE_FILES:
                parsed = modules(path, text)
                snapshot = b.snapshot(
                    source,
                    f"{repo.id}:{path}",
                    "repository",
                    {"commit": commit, "path": path, "parsed": parsed},
                )
                for module in parsed["modules"]:
                    full = str(PurePosixPath(path).parent / module)
                    matches = [full]
                    if "*" in full:
                        matches = sorted(
                            {
                                str(PurePosixPath(f).parent)
                                for f in files
                                if fnmatch.fnmatch(str(PurePosixPath(f).parent), full)
                            }
                        )
                    for module_path in matches:
                        entity = b.entity(
                            source, "module", f"{project}:{module_path}", path=module_path
                        )
                        b.link(
                            repo, entity, "contains_module", snapshot, f"{path}/modules/{module}"
                        )
            elif "compose" in name.lower():
                parsed = compose(text)
                repo.attributes["role"] = "deployment"
                snapshot = b.snapshot(
                    source,
                    f"{repo.id}:{path}",
                    "git_current",
                    {
                        "commit": commit,
                        "ref": metadata["default_branch"],
                        "path": path,
                        "repository_path": metadata.get("path_with_namespace"),
                        "repository_origin": origin_key(gitlab.reader.config.base_url),
                        **parsed,
                    },
                )
                for service in parsed["services"]:
                    entity = b.entity(
                        source,
                        "compose_service",
                        f"{project}:{path}:{service['name']}",
                        name=service["name"],
                        environment_names=service["environment_names"],
                    )
                    b.link(repo, entity, "declares_service", snapshot, f"{path}/{service['name']}")
                    if service["image"]:
                        img = b.image_entity(service["image"]["reference"])
                        b.link(
                            entity,
                            img,
                            "declares_image",
                            snapshot,
                            f"{path}/{service['name']}/image",
                        )
            else:
                parsed = ci(text) if name == ".gitlab-ci.yml" else dockerfile(text)
                snapshot = b.snapshot(
                    source,
                    f"{repo.id}:{path}",
                    "repository",
                    {"commit": commit, "path": path, "parsed": parsed},
                )
                if name == ".gitlab-ci.yml":
                    for job in parsed["jobs"]:
                        entity = b.entity(
                            source,
                            "build_job",
                            f"{project}:{path}:{job['name']}",
                            name=job["name"],
                            stage=job["stage"],
                            module_paths=job["module_paths"],
                            dockerfiles=job["dockerfiles"],
                        )
                        b.link(
                            repo, entity, "declares_build_job", snapshot, f"{path}/{job['name']}"
                        )
                        for reference in job["images"]:
                            img = b.image_entity(reference)
                            b.link(
                                entity,
                                img,
                                "declares_build_image",
                                snapshot,
                                f"{path}/{job['name']}/image/{fingerprint(reference)[:16]}",
                            )
            if parsed["incomplete"]:
                b.result.warnings.append(f"INCOMPLETE:{snapshot.id}")
        return b.finish()

    def runtime(self, stack: dict[str, Any]) -> DiscoveryResult:
        assert self.portainer is not None
        adapter = self.portainer
        source = adapter.reader.config.instance_id
        if not stack.get("EndpointId"):
            raise DceError(ErrorCode.API_INCOMPATIBLE, "Stack EndpointId is missing.")
        endpoint_id = str(stack["EndpointId"])
        info = adapter.docker_info(endpoint_id)
        endpoint = {"Id": endpoint_id, **info}
        services = adapter.services(endpoint_id)
        observation = stack_runtime(stack, endpoint, services)
        saved = compose(adapter.stack_file(str(stack["Id"]), endpoint_id))
        b = Builder()

        git = stack.get("GitConfig", {})
        repo_path = urlsplit(git.get("URL", "")).path.lstrip("/").removesuffix(".git")
        entity = b.entity(
            source,
            "stack",
            stack["Id"],
            name=stack.get("Name"),
            endpoint_id=endpoint_id,
            state=observation["status"],
            environment="unresolved",
            health="unknown",
            repository_path=repo_path,
            repository_origin=origin_key(git.get("URL", "")),
            ref=git.get("ReferenceName", ""),
            config_path=git.get("ConfigFilePath", ""),
        )
        snapshot = b.snapshot(source, entity.id, "portainer_saved", saved)
        endpoint_entity = b.entity(source, "endpoint", endpoint_id)
        b.link(endpoint_entity, entity, "records_stack", snapshot, "EndpointId")
        if observation["status"] == "stale_candidate":
            b.result.anomalies.append({"stack_id": entity.id, "status": "stale_candidate"})
        else:
            safe_services = []
            for item in observation["services"]:
                spec = item.get("Spec", {})
                reference = spec.get("TaskTemplate", {}).get("ContainerSpec", {}).get("Image")
                if not isinstance(reference, str) or not item.get("ID"):
                    b.result.warnings.append(f"INCOMPLETE_SERVICE:{entity.id}")
                    continue
                safe_services.append(
                    {
                        "id": item["ID"],
                        "name": spec.get("Name"),
                        "image": reference,
                        "namespace": observation["namespace"],
                    }
                )
            runtime = b.snapshot(
                source,
                entity.id,
                "swarm_runtime",
                {"services": safe_services, "swarm_id": info["Swarm"].get("Cluster", {}).get("ID")},
            )
            swarm = b.entity(
                source,
                "swarm",
                str(info["Swarm"].get("Cluster", {}).get("ID")),
                endpoint_id=endpoint_id,
            )
            b.link(endpoint_entity, swarm, "observes_swarm", runtime, "DockerInfo/Swarm/Cluster/ID")
            b.link(swarm, entity, "observes_stack_namespace", runtime, "Services/Labels/Namespace")
            for item in safe_services:
                service = b.entity(
                    source,
                    "service",
                    f"{endpoint_id}:{item['id']}",
                    name=item["name"],
                    namespace=item["namespace"],
                    health="unknown",
                )
                b.link(entity, service, "runs_service", runtime, f"Services/{item['id']}/Labels")
                img = b.image_entity(item["image"])
                b.link(
                    service,
                    img,
                    "observes_image_reference",
                    runtime,
                    f"Services/{item['id']}/Image",
                )
        if saved["incomplete"]:
            b.result.warnings.append(f"INCOMPLETE:{snapshot.id}")
        result = b.finish()
        version = fingerprint([stack, saved, info, services])
        return self.checkpoint.resource(f"{source}:stack:{stack['Id']}", version, lambda: result)

    def business(self) -> DiscoveryResult:
        assert self.zentao is not None
        adapter = self.zentao
        source = adapter.reader.config.instance_id
        b = Builder()
        for parent_kind, scopes, entity_kind in (
            ("projects", self.scope.zentao_projects, "business_project"),
            ("products", self.scope.zentao_products, "product"),
        ):
            for parent_id in scopes:
                resource = adapter.resource(parent_kind, parent_id)
                parent = b.entity(
                    source, entity_kind, parent_id, name=str(resource.get("name", ""))
                )
                bugs = list(adapter.resources("bugs", parent_id, parent_kind=parent_kind))
                safe_bugs = [
                    {"id": str(bug["id"]), "title": str(bug.get("title", ""))[:500]} for bug in bugs
                ]
                snapshot = b.snapshot(source, parent.id, "business", {"bugs": safe_bugs})
                for bug in safe_bugs:
                    # Bug HTML/attachments stay out of discovery snapshots; fetched on demand.
                    entity = b.entity(source, "bug", bug["id"], title=bug["title"])
                    b.link(
                        parent,
                        entity,
                        "contains_bug",
                        snapshot,
                        f"{parent_kind}/{parent_id}/{bug['id']}",
                    )
        result = b.finish()
        version = fingerprint([e.model_dump() for e in result.entities])
        return self.checkpoint.resource(f"{source}:business", version, lambda: result)
