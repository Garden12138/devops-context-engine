"""Atomic run snapshots with locked, append-only audit events."""

import fcntl
import json
import os
import re
import sys
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import ValidationError

from dce.errors import DceError, ErrorCode
from dce.redact import redact
from dce.workspace.config import DceConfig, Model, load_config


class Run(dict[str, Any]):
    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.baseline = deepcopy(data)


def now() -> str:
    return datetime.now().astimezone().isoformat()


def run_path(ws: Path, run_id: str) -> Path:
    directory = ws / '.dce/runs'
    path = directory / f'{run_id}.json'
    if (not re.fullmatch(r'[\w-]+', run_id) or path.is_symlink()
            or path.with_suffix('.lock').is_symlink() or directory.is_symlink()
            or (ws / '.dce').is_symlink()
            or not path.resolve().is_relative_to(ws.resolve())):
        raise DceError(ErrorCode.OUT_OF_SCOPE, f'run {run_id}: 路径越出工作区或包含符号链接。',
                       '使用 dce_status 返回的本地 run_id，检查 .dce/runs 路径。')
    return path


def new_run(ws: Path, bug_ids: list[int]) -> Run:
    stamp = datetime.now().astimezone().strftime('%Y%m%d-%H%M')
    run_id = '-'.join([stamp, *(str(b) for b in dict.fromkeys(bug_ids)), uuid4().hex[:8]])
    run_path(ws, run_id)
    run = Run({'run_id': run_id, 'created_at': now(), 'updated_at': now(), 'stage': 'planned',
                'bugs': [{'id': b} for b in dict.fromkeys(bug_ids)], 'feature_branches': {},
                'plan': {}, 'merges': {}, 'builds': {}, 'deploys': {}, 'verifications': {},
                'record': {}, 'zentao': {}, 'events': []})
    run.baseline = {}
    return run


def load_run(ws: Path, run_id: str) -> Run:
    path = run_path(ws, run_id)
    if not path.is_file():
        raise DceError(ErrorCode.NOT_FOUND, f'run {run_id}: 本地运行记录不存在。',
                       '先调用 dce_status 查看已有运行记录。')
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or data.get('run_id') != run_id:
            raise ValueError('run_id')
        return Run(data)
    except (OSError, UnicodeError, ValueError) as exc:
        raise DceError(ErrorCode.CONFIG_INVALID,
                       f'{path.name}: {type(exc).__name__}，运行记录无法读取或 run_id 不一致。',
                       '检查该运行记录的 JSON 语法、run_id 和读取权限。') from None


def merge_changes(current: dict[str, Any], baseline: dict[str, Any],
                  changed: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(current)
    for key in baseline.keys() - changed.keys():
        result.pop(key, None)
    for key, value in changed.items():
        if key in baseline and value == baseline[key]:
            continue
        if isinstance(value, dict) and isinstance(baseline.get(key), dict):
            result[key] = merge_changes(result.get(key, {}), baseline[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def save_run(ws: Path, run: Run, *, update_stage: bool = False) -> None:
    path = run_path(ws, run['run_id'])
    temporary: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path.with_suffix('.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            current = load_run(ws, run['run_id']) if path.exists() else {}
            previous = run.baseline.get('events', [])
            events = run.get('events', [])
            if events[:len(previous)] != previous:
                raise DceError(ErrorCode.PRECONDITION_FAILED,
                               f"run {run['run_id']}: events 历史被修改或删除。",
                               '重新读取 run 并只通过 append_event 追加事件。')
            data = merge_changes(current, run.baseline, run)
            if update_stage:
                data['stage'] = verification_stage(data)
            data['events'] = deepcopy(current.get('events', [])) + events[len(previous):]
            data['updated_at'] = now()
            data = redact(data)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                             prefix=f'.{run["run_id"]}-', delete=False) as stream:
                temporary = stream.name
                json.dump(data, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            run.clear()
            run.update(data)
            run.baseline = deepcopy(data)
    except OSError as exc:
        raise DceError(ErrorCode.PLATFORM_ERROR,
                       f"本地 run {run['run_id']} 保存失败：{type(exc).__name__}: {exc}",
                       '检查 .dce/runs 写权限与可用磁盘空间，然后重试。') from None
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def append_event(run: Run, tool: str, action: str, target: str, result: str, detail: str,
                 *, error_code: str | None = None) -> None:
    event = redact({'at': now(), 'tool': tool, 'action': action, 'target': target,
                    'result': result, 'detail': detail})
    run.setdefault('events', []).append(event)
    print(json.dumps(redact({'ts': event['at'], 'request_id': uuid4().hex, 'tool': tool,
                            'action': action, 'target': target, 'result': result,
                            'error_code': error_code})),
          file=sys.stderr)


def list_runs(ws: Path) -> list[Run]:
    return sorted((load_run(ws, p.stem) for p in (ws / '.dce/runs').glob('*.json')),
                  key=lambda r: str(r.get('updated_at', '')), reverse=True)


class Verification(Model):
    bug_id: int
    result: Literal['passed', 'failed']
    notes: str
    evidence: list[str]


class Record(Model):
    file: str
    commit: str


def verification_stage(run: dict[str, Any]) -> str:
    outcomes = [run.get('verifications', {}).get(str(b['id']), {}).get('result')
                for b in run.get('bugs', [])]
    if 'failed' in outcomes:
        return 'fixing'
    if outcomes and all(result == 'passed' for result in outcomes):
        if run.get('stage') == 'resolved':
            return 'resolved'
        return 'recorded' if run.get('record', {}).get('commit') else 'verified'
    return 'verifying' if 'passed' in outcomes else str(run['stage'])


def check_evidence(ws: Path, value: str) -> None:
    try:
        path = (ws / value).resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise DceError(ErrorCode.CONFIG_INVALID, f'验证截图 {value!r}: {type(exc).__name__}。',
                       '检查路径格式、符号链接和读取权限。') from None
    if not path.is_relative_to(ws.resolve()):
        raise DceError(ErrorCode.OUT_OF_SCOPE, f'验证截图 {value!r} 位于工作区外。',
                       '把截图保存到工作区内再提交 evidence 路径。')
    if not path.is_file():
        raise DceError(ErrorCode.PRECONDITION_FAILED, f'验证截图 {value!r} 不存在或不是文件。',
                       '保存截图后核对 evidence 路径。')


def check_record_commit(ws: Path, cfg: DceConfig, record: Record) -> None:
    from dce.loop.gitops import reference, run_git

    repo = next((repo for repo in cfg.repos if repo.name == cfg.records.repo), None)
    if repo is None or not (ws / repo.path / '.git').exists():
        raise DceError(ErrorCode.CONFIG_INVALID,
                       f'修复记录仓库 {cfg.records.repo!r}: 找不到已配置的 Git 工作副本。',
                       '检查 .dce/dce.yaml 中 records.repo 和对应的 repos[].path。')
    result = run_git(ws / repo.path, 'cat-file', '-e', '--',
                     f'{reference(record.commit)}^{{commit}}', allowed=(0, 1, 128))
    if result.returncode:
        raise DceError(ErrorCode.PRECONDITION_FAILED,
                       f'Git {repo.name}: 找不到修复记录提交 {record.commit}，'
                       f'git cat-file 退出码 {result.returncode}。{result.stderr.strip()}',
                       '在 records 仓库提交修复记录，核对提交 SHA 后重试。')


def update_run(ws: Path, cfg: DceConfig, run_id: str,
               verification: dict[str, Any] | None = None,
               record: dict[str, str] | None = None, note: str | None = None) -> Run:
    if verification is None and record is None and note is None:
        raise DceError(ErrorCode.CONFIG_INVALID,
                       'run_update 至少需要 verification、record 或 note。',
                       '提供验证结论、记录提交或说明。')
    try:
        change = None if verification is None else Verification.model_validate(verification)
        document = None if record is None else Record.model_validate(record)
    except ValidationError as exc:
        error = exc.errors()[0]
        raise DceError(ErrorCode.CONFIG_INVALID,
                       f"run_update {exc.title}.{'.'.join(map(str, error['loc']))}: "
                       f"{error['msg']}", '参照 run_update 工具契约修正该参数。') from None
    run = load_run(ws, run_id)
    if change is not None:
        if not any(bug['id'] == change.bug_id for bug in run['bugs']):
            raise DceError(ErrorCode.OUT_OF_SCOPE, f'缺陷 {change.bug_id} 不属于 run {run_id}。',
                           '通过 dce_status 查看包含该缺陷的 run。')
        for value in change.evidence:
            check_evidence(ws, value)
    if document is not None:
        check_record_commit(ws, cfg, document)
    if change is not None:
        run.setdefault('verifications', {})[str(change.bug_id)] = {
            **change.model_dump(exclude={'bug_id'}), 'at': now(),
        }
        append_event(run, 'run_update', 'verification', str(change.bug_id), 'ok', change.result)
    if document is not None:
        run['record'] = {**document.model_dump(), 'at': now()}
        append_event(run, 'run_update', 'record', document.file, 'ok', document.commit)
    if note is not None:
        append_event(run, 'run_update', 'note', run_id, 'ok', note)
    save_run(ws, run, update_stage=change is not None or document is not None)
    return run


def status(ws: Path, run_id: str | None = None) -> dict[str, Any]:
    config = load_config(ws)
    snapshots = list_runs(ws)
    run = load_run(ws, run_id) if run_id is not None else None
    facts = None
    if run is not None:
        facts = []
        for bug in run.get('bugs', []):
            bug_id = bug['id']
            commits = {repo: [c for c in entries if bug_id in c.get('bugs', [])]
                       for repo, entries in run.get('plan', {}).get('commits', {}).items()}
            repos = [name for name, entries in commits.items() if entries]
            times = [run.get('merges', {}).get(repo, {}).get('merged_at') for repo in repos]
            verification = run.get('verifications', {}).get(str(bug_id), {})
            facts.append({
                'bug': bug_id, 'title': bug.get('title'), 'severity': bug.get('severity'),
                'pri': bug.get('pri'), 'opened_at': bug.get('opened_at'),
                'fixed_at': max((t for t in times if t), default=None),
                'verified_at': verification.get('at'), 'repos': repos,
                'commits': [f"{c['sha']} {c['subject']}" for entries in commits.values()
                            for c in entries], 'evidence': verification.get('evidence', []),
            })
    return {
        'config': {'name': config.name, 'repos': len(config.repos),
                   'environment': config.environment.name, 'stack': config.environment.stack,
                   'gates': config.gates.model_dump()},
        'runs': [{'run_id': r['run_id'], 'bugs': [b['id'] for b in r.get('bugs', [])],
                  'stage': r.get('stage'), 'updated_at': r.get('updated_at')} for r in snapshots],
        'run': run, 'record_facts': facts,
    }
