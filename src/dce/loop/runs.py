"""Read local run snapshots for dce_status; run mutation is implemented in M2."""

import json
import re
from pathlib import Path
from typing import Any

from dce.errors import DceError, ErrorCode
from dce.workspace.config import load_config


def load_run(ws: Path, run_id: str) -> dict[str, Any]:
    directory = ws / '.dce/runs'
    path = directory / f'{run_id}.json'
    if (not re.fullmatch(r'[\w-]+', run_id) or path.is_symlink()
            or not path.resolve().is_relative_to(ws.resolve())):
        raise DceError(ErrorCode.OUT_OF_SCOPE, f'run {run_id}: 路径越出工作区或包含符号链接。',
                       '使用 dce_status 返回的本地 run_id。')
    if not path.is_file():
        raise DceError(ErrorCode.NOT_FOUND, f'run {run_id}: 本地运行记录不存在。',
                       '先调用 dce_status 查看已有运行记录。')
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or data.get('run_id') != run_id:
            raise ValueError('run_id')
        return data
    except (OSError, UnicodeError, ValueError) as exc:
        raise DceError(ErrorCode.CONFIG_INVALID,
                       f'{path.name}: {type(exc).__name__}，运行记录无法读取或 run_id 不一致。',
                       '检查该运行记录的 JSON 语法、run_id 和读取权限。') from None


def list_runs(ws: Path) -> list[dict[str, Any]]:
    return sorted((load_run(ws, p.stem) for p in (ws / '.dce/runs').glob('*.json')),
                  key=lambda r: str(r.get('updated_at', '')), reverse=True)


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
