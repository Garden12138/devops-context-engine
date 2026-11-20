from collections.abc import Iterator
from typing import Any
from urllib.parse import quote

from dce.errors import DceError, ErrorCode
from dce.platforms.http import PlatformClient


def key(value: str) -> str:
    return quote(str(value), safe="")


class GitLab:
    def __init__(self, reader: PlatformClient) -> None:
        self.reader = reader

    def projects(self, group: str | None = None) -> Iterator[dict[str, Any]]:
        path = f"/api/v4/groups/{key(group)}/projects" if group else "/api/v4/projects"
        return self.reader.pages(path)

    def project(self, project: str) -> dict[str, Any]:
        return dict(self.reader.json(f"/api/v4/projects/{key(project)}"))

    def project_by_path(self, path: str) -> dict[str, Any]:
        return self.project(path)

    def branches(self, project_id: int, search: str) -> Iterator[dict[str, Any]]:
        return self.reader.pages(
            f'/api/v4/projects/{project_id}/repository/branches', params={'search': search},
        )

    def token_self(self) -> dict[str, Any] | None:
        try:
            return dict(self.reader.json('/api/v4/personal_access_tokens/self'))
        except DceError as exc:
            if exc.code == ErrorCode.NOT_FOUND:
                return None
            raise

    def raw_file(self, project: str, path: str, ref: str) -> str:
        return self.reader.get(
            f"/api/v4/projects/{key(project)}/repository/files/{key(path)}/raw", params={"ref": ref}
        ).text

    def pipelines(self, project: str, ref: str | None = None, sha: str | None = None
                  ) -> Iterator[dict[str, Any]]:
        return self.reader.pages(
            f"/api/v4/projects/{key(project)}/pipelines",
            params={k: v for k, v in {"ref": ref, "sha": sha}.items() if v is not None}
        )

    def pipeline(self, project: str, pipeline: str) -> dict[str, Any]:
        return dict(self.reader.json(f"/api/v4/projects/{key(project)}/pipelines/{key(pipeline)}"))

    def jobs(self, project: str, pipeline: str) -> Iterator[dict[str, Any]]:
        return self.reader.pages(f"/api/v4/projects/{key(project)}/pipelines/{key(pipeline)}/jobs")

    def trace(self, project: str, job: str) -> str:
        return self.reader.get(f"/api/v4/projects/{key(project)}/jobs/{key(job)}/trace").text

    def bridges(self, project: str, pipeline: str) -> list[dict[str, Any]]:
        return list(self.reader.pages(
            f"/api/v4/projects/{key(project)}/pipelines/{key(pipeline)}/bridges"))

    def jobs_all(self, project: str, pipeline: str) -> list[dict[str, Any]]:
        return list(self.reader.pages(
            f"/api/v4/projects/{key(project)}/pipelines/{key(pipeline)}/jobs",
            params={"per_page": 100}))

    def play(self, project: str, job: str) -> dict[str, Any]:
        return dict(self.reader.decode(self.reader.post(
            f"/api/v4/projects/{key(project)}/jobs/{key(job)}/play"), dict))

    def retry(self, project: str, job: str) -> dict[str, Any]:
        return dict(self.reader.decode(self.reader.post(
            f"/api/v4/projects/{key(project)}/jobs/{key(job)}/retry"), dict))

    def create_pipeline(self, project: str, ref: str) -> dict[str, Any]:
        return dict(self.reader.decode(self.reader.post(
            f"/api/v4/projects/{key(project)}/pipeline", json={"ref": ref}), dict))

    def trace_tail(self, project: str, job: str, lines: int = 200) -> str:
        from dce.redact import redact
        return str(redact("\n".join(self.trace(project, job).splitlines()[-lines:]),
                          self.reader.secrets()))
