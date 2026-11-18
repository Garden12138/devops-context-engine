"""Plan-scoped CI actions and read-only polling with an injectable clock."""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from dce.errors import DceError, ErrorCode
from dce.loop.guard import check_branch, check_job, check_pipeline_ref, require
from dce.loop.runs import Run, append_event, save_run
from dce.output import success
from dce.platforms.gitlab import GitLab
from dce.workspace.config import DceConfig, Repo


class Clock(Protocol):
    def monotonic(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


INFRA = re.compile(
    r'Cannot connect to the Docker daemon|TLS handshake timeout|i/o timeout|'
    r'context deadline exceeded|no basic auth credentials|pull access denied|'
    r'toomanyrequests|runner system failure|ERROR: Job failed \(system failure\)|'
    r'no space left on device', re.I)
CODE = re.compile(r'BUILD FAILURE|COMPILATION ERROR|npm ERR!|ERR_PNPM|error TS\d+|'
                  r'Module not found|SyntaxError', re.I)
DIGEST = re.compile(r'(?m)digest:\s*(sha256:[0-9a-f]{64})')
FAILED = {'failed', 'canceled'}


def _selection(cfg: DceConfig, run: Run, items: list[str] | None) -> list[dict[str, Any]]:
    planned: list[dict[str, Any]] = run.get('plan', {}).get('items', [])
    requested = set(items) if items is not None else {i['id'] for i in planned}
    unknown = requested - {i['id'] for i in planned}
    require(not unknown, f"GitLab run {run['run_id']}", 'items', sorted(unknown),
            [i['id'] for i in planned])
    selected = [i for i in planned if i['id'] in requested]
    if not selected:
        raise DceError(ErrorCode.PRECONDITION_FAILED, 'GitLab CI: run 中没有所选计划条目。',
                       '先生成包含部署模块的 deploy_plan。')
    for item in selected:
        repo = next((r for r in cfg.repos if r.name == item['repo']), None)
        require(repo is not None, 'GitLab CI', 'repo', item['repo'], [r.name for r in cfg.repos])
        assert repo is not None
        check_branch(cfg, repo, repo.test_branch)
        merge = run.get('merges', {}).get(repo.name, {})
        if not merge.get('merge_sha'):
            raise DceError(ErrorCode.PRECONDITION_FAILED,
                           f'GitLab {repo.name}: run 中缺少 merge_sha，尚未合并。',
                           '取得 G2 确认后调用 merge_to_test。')
        check_branch(cfg, repo, merge.get('test_branch'))
    return selected


def _fallback(run: Run, repo: Repo) -> tuple[bool, int | None]:
    events = [e for e in run['events'] if e['action'] == 'create_pipeline'
              and e['target'] == repo.name]
    for event in reversed(events):
        found = re.fullmatch(r'pipeline_id=([0-9]+)', event['detail'])
        if event['result'] == 'ok' and found:
            return True, int(found[1])
    return bool(events), None


def _locate(client: GitLab, repo: Repo, run: Run, deadline: float, clock: Clock,
            pipeline_id: int | None = None) -> tuple[int, int | None]:
    sha = run['merges'][repo.name]['merge_sha']
    project = str(repo.gitlab.id)
    while True:
        if pipeline_id is None:
            pipelines = list(client.pipelines(project, str(repo.test_branch), sha))
            candidates = [p for p in pipelines if p.get('ref', repo.test_branch) == repo.test_branch
                          and p.get('sha', sha) == sha]
            if candidates:
                pipeline_id = max(int(p['id']) for p in candidates)
        child = None
        if pipeline_id is not None:
            if not repo.ci or repo.ci.mode == 'direct':
                return pipeline_id, None
            bridges = client.bridges(project, str(pipeline_id))
            child = next((b.get('downstream_pipeline') for b in bridges
                          if b.get('name') == repo.ci.trigger_job), None)
            if child:
                return pipeline_id, int(child['id'])
        if clock.monotonic() >= deadline:
            raise DceError(ErrorCode.TIMEOUT,
                           f'GitLab project {project} HTTP 200: {repo.test_branch} sha={sha} '
                           f'流水线或子流水线 {repo.ci.trigger_job if repo.ci else ""} 尚未出现。',
                           '在 GitLab 核对该合并提交的流水线和 trigger job，稍后再调用 ci_build。')
        clock.sleep(min(5, deadline - clock.monotonic()))


def _missing(client: GitLab, repo: Repo, pipeline: int, names: list[str]) -> DceError:
    url = f'{client.reader.config.base_url}/{repo.gitlab.project}/-/pipelines/{pipeline}'
    return DceError(ErrorCode.CI_JOB_MISSING,
                    f'GitLab project {repo.gitlab.id} 流水线 {pipeline} HTTP 200: '
                    f'缺少 job {", ".join(names)}，changes 规则可能未命中。',
                    f'打开 {url} 核对 job 规则和 dce.yaml 中的名字，再调用 ci_build。')


def _pipeline_jobs(ws: Path, cfg: DceConfig, run: Run, repo: Repo,
                   selected: list[dict[str, Any]], client: GitLab, deadline: float,
                   clock: Clock, mutate: bool) -> tuple[int, int | None, dict[str, dict[str, Any]]]:
    attempted, fallback = _fallback(run, repo)
    pipeline, child = _locate(client, repo, run, deadline, clock, fallback)
    names = {i[k] for i in selected for k in ('compile_job', 'build_job') if i.get(k)}
    while True:
        jobs = {j['name']: j for j in sorted(
            client.jobs_all(str(repo.gitlab.id), str(child or pipeline)),
            key=lambda j: int(j['id']))}

        missing = sorted(names - jobs.keys())
        if not missing:
            return pipeline, child, jobs
        if not mutate or attempted:
            raise _missing(client, repo, child or pipeline, missing)
        check_pipeline_ref(cfg, repo, repo.test_branch)
        append_event(run, 'ci_build', 'create_pipeline', repo.name, 'requested',
                     '补建流水线请求已发起；本 run 只尝试一次。')
        save_run(ws, run)
        try:
            created = client.create_pipeline(str(repo.gitlab.id), str(repo.test_branch))
        except DceError as exc:
            append_event(run, 'ci_build', 'create_pipeline', repo.name, 'error', exc.message,
                         error_code=exc.code.value)
            save_run(ws, run)
            raise
        pipeline = int(created['id'])
        append_event(run, 'ci_build', 'create_pipeline', repo.name, 'ok', f'pipeline_id={pipeline}')
        save_run(ws, run)
        attempted = True
        pipeline, child = _locate(client, repo, run, deadline, clock, pipeline)


def _old(compile: dict[str, Any], build: dict[str, Any]) -> bool:
    start, finish = compile.get('started_at'), build.get('finished_at')
    if build.get('status') != 'success' or not start or not finish:
        return False
    try:
        return datetime.fromisoformat(str(finish).replace('Z', '+00:00')) < datetime.fromisoformat(
            str(start).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        raise DceError(ErrorCode.PLATFORM_ERROR,
                       f"GitLab build job {build.get('id')} HTTP 200: "
                       "started_at/finished_at 无效。",
                       '在 GitLab 核对 job 的开始和结束时间后重试。') from None


def _brief(job: dict[str, Any]) -> dict[str, Any]:
    return {k: job[k] for k in ('id', 'status', 'web_url', 'started_at', 'finished_at') if k in job}


def _act(ws: Path, cfg: DceConfig, run: Run, repo: Repo, item: dict[str, Any],
         job: dict[str, Any], client: GitLab, retry_failed: bool, old: bool) -> dict[str, Any]:
    status = job['status']
    action = ('play' if status == 'manual' else
              'retry' if old or (status in FAILED and retry_failed) else None)
    if action is None:
        brief = _brief(job)
        if status not in FAILED:
            brief['action'] = 'already_succeeded' if status == 'success' else 'already_running'
        return brief
    check_branch(cfg, repo, repo.test_branch)
    check_job(cfg, item, job.get('project_id', repo.gitlab.id), job['name'])
    try:
        result = getattr(client, action)(str(repo.gitlab.id), str(job['id']))
    except DceError as exc:
        append_event(run, 'ci_build', action, f"{repo.name}:{job['name']}", 'error', exc.message,
                     error_code=exc.code.value)
        save_run(ws, run)
        raise
    append_event(run, 'ci_build', action, f"{repo.name}:{job['name']}", 'ok',
                 f"job_id={result['id']}")
    save_run(ws, run)
    return {**_brief(result), 'action': 'played' if action == 'play' else 'retried'}


def start_builds(ws: Path, cfg: DceConfig, run: Run, items: list[str] | None = None,
                 retry_failed: bool = False, *, client: GitLab, clock: Clock = time
                 ) -> dict[str, Any]:
    selected = _selection(cfg, run, items)
    deadline = clock.monotonic() + 45
    rows = []
    for repo in cfg.repos:
        group = [i for i in selected if i['repo'] == repo.name]
        if not group:
            continue
        pipeline, child, jobs = _pipeline_jobs(
            ws, cfg, run, repo, group, client, deadline, clock, True)
        for item in group:
            row: dict[str, Any] = {'item': item['id'], 'pipeline_id': pipeline}
            if child is not None:
                row['child_pipeline_id'] = child
            compile = jobs.get(item.get('compile_job') or '', {})
            for kind in ('compile', 'build'):
                name = item.get(f'{kind}_job')
                if not name:
                    continue
                job = jobs[name]
                check_job(cfg, item, job.get('project_id', repo.gitlab.id), name)
                ready = kind == 'compile' or not compile or compile['status'] == 'success'
                row[kind] = (_act(ws, cfg, run, repo, item, job, client, retry_failed,
                                   kind == 'build' and _old(compile, job))
                             if ready else _brief(job))
                jobs[name] = {**job, **row[kind]}
            run['builds'][item['id']] = {k: v for k, v in row.items() if k != 'item'}
            rows.append(row)
    run['stage'] = 'building'
    save_run(ws, run)
    return success(f'已检查 {len(rows)} 个计划条目的 CI 动作。', {'items': rows},
                   '调用 ci_status 跟踪 compile/build；手动 build 就绪后再次调用 ci_build。')


def _snapshot(ws: Path, cfg: DceConfig, run: Run, client: GitLab, clock: Clock
              ) -> dict[str, Any]:
    selected = _selection(cfg, run, None)
    rows, warnings = [], []
    needs_action = failed = code_failed = False
    all_success = True
    for repo in cfg.repos:
        group = [i for i in selected if i['repo'] == repo.name]
        if not group:
            continue
        pipeline, child, jobs = _pipeline_jobs(
            ws, cfg, run, repo, group, client, clock.monotonic(), clock, False)
        for item in group:
            row: dict[str, Any] = {'item': item['id'], 'pipeline_id': pipeline}
            if child is not None:
                row['child_pipeline_id'] = child
            compile = jobs.get(item.get('compile_job') or '', {})
            for kind in ('compile', 'build'):
                name = item.get(f'{kind}_job')
                if not name:
                    continue
                job = jobs[name]
                check_job(cfg, item, job.get('project_id', repo.gitlab.id), name)
                brief = row[kind] = _brief(job)
                old = kind == 'build' and _old(compile, job)
                all_success &= job['status'] == 'success' and not old
                needs_action |= job['status'] == 'manual' or old
                if job['status'] in FAILED:
                    failed = True
                    trace = client.trace_tail(str(repo.gitlab.id), str(job['id']))
                    category = 'infrastructure' if INFRA.search(trace) else (
                        'code' if CODE.search(trace) else 'unknown')
                    brief.update(failure=category, trace_tail='\n'.join(trace.splitlines()[-80:]))
                    code_failed |= category == 'code'
                elif kind == 'build' and job['status'] == 'success' and not old:
                    matches = DIGEST.findall(client.trace_tail(str(repo.gitlab.id), str(job['id'])))
                    brief['digest'] = matches[-1] if matches else None
                    if not matches:
                        warnings.append({'code': 'DIGEST_UNKNOWN', 'message':
                                         f'GitLab project {repo.gitlab.id} job {job["id"]} '
                                         'Trace HTTP 200: 未找到镜像 digest，请核对镜像推送日志。'})
            run['builds'][item['id']] = {k: v for k, v in row.items() if k != 'item'}
            rows.append(row)
    overall = 'failed' if failed else 'succeeded' if all_success else 'building'
    run['stage'] = 'built' if all_success else 'fixing' if code_failed else 'building'
    save_run(ws, run)
    next_step = ('调用 ci_build 处理手动 job 或旧构建。' if needs_action else
                 '构建成功，调用 service_deploy。' if overall == 'succeeded' else
                 '代码失败时回到修复；基础设施或 unknown 失败时先询问用户，'
                 '再 ci_build(retry_failed=true)。'
                 if failed else '继续调用 ci_status 跟踪构建。')
    result = success(f'CI {overall}：{len(rows)} 个计划条目。',
                     {'overall': overall, 'items': rows}, next_step)
    if warnings:
        result['warnings'] = warnings
    return result


def poll_builds(ws: Path, cfg: DceConfig, run: Run, wait_seconds: int = 0,
                clock: Clock = time, *, client: GitLab) -> dict[str, Any]:
    if not 0 <= wait_seconds <= 45:
        raise DceError(ErrorCode.CONFIG_INVALID, 'ci_status.wait_seconds 必须在 0–45 秒之间。',
                       'MCP 单次最多等待 45 秒；CLI 可分段等待。')
    deadline = clock.monotonic() + wait_seconds
    initial = _snapshot(ws, cfg, run, client, clock)
    result = initial
    while result['data']['overall'] == 'building' and clock.monotonic() < deadline:
        clock.sleep(min(5, deadline - clock.monotonic()))
        result = _snapshot(ws, cfg, run, client, clock)
        if result['data'] != initial['data']:
            break
    return result
