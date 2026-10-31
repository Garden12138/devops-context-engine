from collections.abc import Iterator
from typing import Any
from urllib.parse import quote

from dce.connectors.http import Reader


def key(value: str) -> str:
    return quote(str(value), safe="")


class GitLab:
    def __init__(self, reader: Reader) -> None:
        self.reader = reader

    def projects(self, group: str | None = None) -> Iterator[dict[str, Any]]:
        path = f"/api/v4/groups/{key(group)}/projects" if group else "/api/v4/projects"
        return self.reader.pages(path)

    def project(self, project: str) -> dict[str, Any]:
        return dict(self.reader.json(f"/api/v4/projects/{key(project)}"))

    def tree(self, project: str, ref: str, path: str = "") -> Iterator[dict[str, Any]]:
        return self.reader.pages(
            f"/api/v4/projects/{key(project)}/repository/tree",
            params={"ref": ref, "path": path, "recursive": "true"},
        )

    def raw_file(self, project: str, path: str, ref: str) -> str:
        return self.reader.get(
            f"/api/v4/projects/{key(project)}/repository/files/{key(path)}/raw", params={"ref": ref}
        ).text

    def commit(self, project: str, ref: str) -> dict[str, Any]:
        return dict(
            self.reader.json(f"/api/v4/projects/{key(project)}/repository/commits/{key(ref)}")
        )

    def pipelines(self, project: str, ref: str | None = None) -> Iterator[dict[str, Any]]:
        return self.reader.pages(
            f"/api/v4/projects/{key(project)}/pipelines", params={"ref": ref} if ref else None
        )

    def pipeline(self, project: str, pipeline: str) -> dict[str, Any]:
        return dict(self.reader.json(f"/api/v4/projects/{key(project)}/pipelines/{key(pipeline)}"))

    def jobs(self, project: str, pipeline: str) -> Iterator[dict[str, Any]]:
        return self.reader.pages(f"/api/v4/projects/{key(project)}/pipelines/{key(pipeline)}/jobs")

    def trace(self, project: str, job: str) -> str:
        return self.reader.get(f"/api/v4/projects/{key(project)}/jobs/{key(job)}/trace").text
