import json
import sys
import traceback
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from dce.errors import DceError, ErrorCode
from dce.loop.bugs import BugView
from dce.loop.runs import Run
from dce.redact import redact
from dce.workspace.config import DceConfig
from dce.workspace.doctor import Check
from dce.workspace.scan import ScanResult


def compact(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(',', ':'))


def success(summary: str, data: Any, next_step: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {'ok': True, 'summary': summary, 'data': data}
    if next_step:
        result['next'] = next_step
    return result


def bug_output(view: BugView) -> dict[str, Any]:
    payload = success(view.summary, view.data)
    if view.warnings:
        payload['warnings'] = view.warnings
    return payload


def plan_output(run: Run, cfg: DceConfig) -> dict[str, Any]:
    plan = run['plan']
    repos = {r.name: r for r in cfg.repos}
    rows = ['| 顺序 | 仓库 | 合并 | 编译 job | 构建 job | 镜像 | 服务 | 原因 | 缺陷 |',
            '|---|---|---|---|---|---|---|---|---|']
    for index, item in enumerate(plan['items'], 1):
        name = item['repo']
        reason = ('改动' if item['reason'] == 'changed' else item['reason'])
        if not item['required']:
            reason = f"依赖 {item['reason'].removeprefix('depends_on:')}（建议重编）"
        cells = [index, name, f"{run['feature_branches'][name]} → {repos[name].test_branch}",
                 item['compile_job'], item['build_job'], item['image'],
                 ', '.join(item['services']), reason, ', '.join(map(str, item['bugs']))]
        rows.append('| ' + ' | '.join(str(c or '—') for c in cells) + ' |')
    payload = success('\n'.join(rows), {'run_id': run['run_id'], **{
        key: plan[key] for key in ('items', 'order', 'commits', 'unmapped', 'bugs_without_commits')
    }}, f"确认后调用 merge_to_test(run_id={run['run_id']}, approved_by_user=true)。")
    payload['warnings'] = plan['warnings']
    return payload


def scan_output(result: ScanResult) -> dict[str, Any]:
    rows = ['| 仓库 | GitLab ID | 测试分支 | 模块 | 匹配服务 | TODO |',
            '|---|---|---|---|---|---|']
    rows.extend(f"| {r['name']} | {r['gitlab_id']} | {r['test_branch']} | {r['modules']} | "
                f"{r['services_matched']} | {r['todos']} |" for r in result.repos)
    rows.append(f'请在编辑器中处理 {len(result.todos)} 个 TODO(确认)，'
                '然后调用 project_setup(check)。')
    return success('\n'.join(rows), asdict(result))


def check_output(checks: list[Check]) -> dict[str, Any]:
    failed = sum(c.status == 'fail' for c in checks)
    warned = sum(c.status == 'warn' for c in checks)
    priority = {'fail': 0, 'warn': 1, 'pass': 2}
    ordered = sorted(checks, key=lambda item: priority[item.status])
    return success(f'自检：{len(checks) - failed - warned} pass，{warned} warn，{failed} fail。',
                   {'passed': failed == 0, 'checks': [
                       {k: v for k, v in asdict(c).items() if v is not None} for c in ordered
                   ]})


def bounded(payload: dict[str, Any], secrets: tuple[str, ...] = (), budget: int = 24000
            ) -> dict[str, Any]:
    payload = redact(payload, secrets)
    run = payload.get('data', {}).get('run') if isinstance(payload.get('data'), dict) else None
    removed = 0
    if isinstance(run, dict) and len(compact(run).encode()) > budget:
        events = run.get('events', [])
        if len(events) > 20:
            removed = len(events) - 20
            run['events'] = events[-20:]
    removed_chars = 0
    if not removed and len(compact(payload).encode()) <= budget:
        return payload
    lists: list[list[Any]] = []
    strings: list[tuple[dict[str, Any], str]] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == 'warnings':
                    continue
                if isinstance(child, str):
                    strings.append((value, key))
                collect(child)
        elif isinstance(value, list):
            if value:
                lists.append(value)
            for child in value:
                collect(child)

    while True:
        warning = {'code': 'TRUNCATED', 'message': f'输出超过 {budget} 字节，'
                   f'截去 {removed} 个列表项、{removed_chars} 个字符。'}
        warnings = payload.setdefault('warnings', [])
        if warnings and warnings[-1].get('code') == 'TRUNCATED':
            warnings[-1] = warning
        else:
            warnings.append(warning)
        if len(compact(payload).encode()) <= budget:
            break
        lists.clear()
        strings.clear()
        collect(payload)
        if lists:
            longest = max(lists, key=lambda v: len(compact(v)))
            count = max(1, len(longest) // 2)
            del longest[-count:]
            removed += count
        elif strings:
            parent, key = max(strings, key=lambda item: len(item[0][item[1]]))
            removed_chars += len(parent[key]) - len(parent[key]) // 2
            parent[key] = parent[key][:len(parent[key]) // 2]
        else:
            break
    return payload


def invoke(operation: Callable[[], dict[str, Any]], secrets: Callable[[], tuple[str, ...]]
           ) -> dict[str, Any]:
    try:
        payload = operation()
    except DceError as exc:
        payload = {'ok': False, 'error': exc.as_dict()}
    except Exception as exc:
        print(redact(traceback.format_exc(), secrets()), file=sys.stderr)
        error = DceError(
            ErrorCode['INTERNAL'], f'{type(exc).__name__}: {redact(str(exc), secrets())}',
            '根据 stderr 的脱敏 traceback 修复异常，然后重试。',
        )
        payload = {'ok': False, 'error': error.as_dict()}
    return bounded(payload, secrets())
