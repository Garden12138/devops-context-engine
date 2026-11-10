from collections.abc import Iterator
from typing import Any
from urllib.parse import quote

from dce.common.errors import DceError, ErrorCode
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

    def job_page(
        self,
        project: str,
        *,
        pipeline: str | None = None,
        ref: str | None = None,
        trigger_api: str | None = None,
        page: int = 1,
        limit: int = 20,
        statuses: list[str] | None = None,
        include_retried: bool = False,
    ) -> tuple[list[dict[str, Any]], bool, list[str]]:
        """One upstream page. A local ref filter never changes upstream pagination."""
        if trigger_api not in {None, "bridges", "trigger_jobs"} or trigger_api and not pipeline:
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid trigger query.")
        route = f"/api/v4/projects/{key(project)}"
        route += f"/pipelines/{key(pipeline)}" if pipeline else ""
        route += "/" + (trigger_api or "jobs")
        params: dict[str, Any] = {"page": page, "per_page": limit}
        if statuses:
            params["scope[]"] = statuses
        if include_retried:
            params["include_retried"] = "true"
        response = self.reader.get(route, params=params)
        records = self.reader.decode(response, list)
        cursor = response.headers.get("X-Next-Page")
        more = len(records) >= limit if cursor is None else bool(cursor)
        warnings = []
        if len(records) > limit:
            records, more = records[:limit], True
            warnings.append("UPSTREAM_PAGE_LIMIT_EXCEEDED")
        if cursor and (not cursor.isdigit() or int(cursor) != page + 1):
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid pagination cursor.")
        if ref is not None:
            if any(r.get("ref") is None for r in records):
                warnings.append("JOB_REF_UNAVAILABLE_ON_UPSTREAM_PAGE")
            records = [r for r in records if r.get("ref") == ref]
            warnings.append("BRANCH_FILTER_LOCAL_TO_PROJECT_JOB_PAGE")
        if not records:
            warnings.append("EMPTY_JOB_PAGE_NOT_PROOF_OF_NO_BUILD")
            if pipeline and not trigger_api:
                warnings.append("CHECK_PIPELINE_BRIDGES_AND_JOB_VISIBILITY")
        if trigger_api and any(r.get("downstream_pipeline") for r in records):
            warnings.append("DOWNSTREAM_PIPELINES_NOT_EXPANDED")
        return records, more, warnings

    def trace(self, project: str, job: str) -> str:
        return self.reader.get(f"/api/v4/projects/{key(project)}/jobs/{key(job)}/trace").text
