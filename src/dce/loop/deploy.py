"""Build-gated test service updates and task digest verification."""

import re
import time
from pathlib import Path
from typing import Any

from dce.errors import DceError, ErrorCode
from dce.loop.build import Clock, _old
from dce.loop.guard import check_service, require
from dce.loop.runs import Run, append_event, now, save_run
from dce.output import success
from dce.platforms.docker_logs import timestamp_ns
from dce.platforms.portainer import Portainer
from dce.redact import redact
from dce.workspace.config import DceConfig


def _digest(image: str) -> str | None:
    match = re.search(r'@(sha256:[0-9a-f]{64})$', image)
    return match[1] if match else None


def _timestamp(value: object) -> int | None:
    if isinstance(value, str):
        try:
            return timestamp_ns(value)
        except ValueError:
            pass
    return None


def _endpoint(cfg: DceConfig) -> int:
    endpoint = cfg.portainer.endpoint
    require(endpoint is not None, 'Portainer', 'endpoint', endpoint, '配置中的测试 endpoint')
    assert endpoint is not None
    return endpoint


def _selection(cfg: DceConfig, run: Run, items: list[str] | None) -> list[dict[str, Any]]:
    plan = run.get('plan', {})
    planned: list[dict[str, Any]] = plan.get('items', [])
    requested = set(items) if items is not None else {i['id'] for i in planned}
    require(not requested - {i['id'] for i in planned}, 'Portainer deploy', 'items',
            sorted(requested), [i['id'] for i in planned])
    selected = [i for i in planned if i['id'] in requested and i['kind'] in {'service', 'web'}]
    for item in selected:
        module = next((m for r in cfg.repos if r.name == item['repo'] for m in r.modules
                       if m.path == item['module']), None)
        require(module is not None, 'Portainer deploy', 'module', item['id'],
                [f'{r.name}:{m.path}' for r in cfg.repos for m in r.modules])
        assert module is not None
        for field in ('kind', 'image', 'services'):
            require(item.get(field) == getattr(module, field), f"Portainer item {item['id']}",
                    field, item.get(field), getattr(module, field))
    order = {name: index for index, name in enumerate(plan.get('order', []))}
    return sorted(selected, key=lambda i: order.get(i['id'], len(order)))


def _service(cfg: DceConfig, client: Portainer, name: str, swarm: str,
             endpoint: int) -> dict[str, Any]:
    require(name in [s for r in cfg.repos for m in r.modules for s in m.services],
            'Portainer', 'service', name, '配置中的测试服务')
    service = client.service(str(endpoint), name)
    check_service(cfg, service, swarm, endpoint)
    require(service['Spec'].get('Name') == name, f'Portainer service {name}',
            'service', service['Spec'].get('Name'), name)
    if not isinstance(service.get('ID'), str) or not service['ID']:
        raise DceError(ErrorCode.PLATFORM_ERROR,
                       f'Portainer service {name} HTTP 200: 缺少服务 ID。',
                       '检查 Docker 服务详情响应，然后重新生成计划。')
    return service


def _write(ws: Path, cfg: DceConfig, run: Run, client: Portainer,
           service: dict[str, Any], swarm: str, endpoint: int, method: str) -> int:
    check_service(cfg, service, swarm, endpoint)
    name, sid = service['Spec']['Name'], service['ID']
    try:
        if method == 'forceupdateservice':
            code = client.force_update(endpoint, sid, cfg.portainer.registry_id)
        else:
            client.docker_update(endpoint, sid, service['Version']['Index'], service['Spec'],
                                 cfg.portainer.registry_id)
            code = 200
    except DceError as exc:
        detail = redact(f'Portainer service {name} ({sid}): {exc.message}',
                        client.reader.secrets())
        append_event(run, 'service_deploy', method, name, 'error', detail,
                     error_code=exc.code.value)
        save_run(ws, run)
        raise DceError(exc.code, detail, exc.hint, exc.retryable) from None
    append_event(run, 'service_deploy', method, name,
                 'fallback' if code in {404, 405} else 'ok', f'service_id={sid}, HTTP {code}')
    save_run(ws, run)
    return code


def deploy(ws: Path, cfg: DceConfig, run: Run, items: list[str] | None = None,
           *, client: Portainer) -> dict[str, Any]:
    selected = _selection(cfg, run, items)
    rows: list[dict[str, Any]] = []
    swarm: str | None = None
    for item in selected:
        build = run.get('builds', {}).get(item['id'], {})
        job = build.get('build', {})
        reason = ('构建未完成' if job.get('status') != 'success' else
                  '旧构建' if _old(build.get('compile', {}), job) else None)
        for name in item['services']:
            if reason:
                row = {'service': name, 'status': 'skipped', 'reason': reason}
                rows.append(row)
                run['deploys'][name] = {'status': 'skipped', 'reason': reason}
                save_run(ws, run)
                continue
            endpoint = _endpoint(cfg)
            if swarm is None:
                swarm = client.swarm_id(endpoint)
            service = _service(cfg, client, name, swarm, endpoint)
            version = service.get('Version', {}).get('Index')
            if type(version) is not int or version < 0:
                raise DceError(ErrorCode.PLATFORM_ERROR,
                               f'Portainer service {name} HTTP 200: Version.Index 无效。',
                               '检查 Docker 服务版本详情，然后重试部署。')
            image = service['Spec']['TaskTemplate']['ContainerSpec']['Image']
            before = {'digest': _digest(image), 'version': version,
                      'updated_at': service.get('UpdatedAt')}
            run['deploys'][name] = {'service_id': service['ID'], 'before': before,
                                     'requested_at': now()}
            run['stage'] = 'deploying'
            save_run(ws, run)
            method = 'forceupdateservice'
            if _write(ws, cfg, run, client, service, swarm, endpoint, method) in {404, 405}:
                method = 'docker_update'
                _write(ws, cfg, run, client, service, swarm, endpoint, method)
            rows.append({'service': name, 'service_id': service['ID'],
                         'status': 'update_requested', 'before_digest': before['digest'],
                         'expected_digest': job.get('digest'), 'method': method})
    if not any(r['status'] == 'update_requested' for r in rows):
        detail = '；'.join(f"{r['service']}: {r['reason']}（skipped）" for r in rows)
        raise DceError(ErrorCode.PRECONDITION_FAILED,
                       f"Portainer run {run['run_id']}: {detail or '没有 service/web 部署条目'}。",
                       '调用 ci_status 核对构建；旧构建需 ci_build 后再部署。')
    count = sum(r['status'] == 'update_requested' for r in rows)
    return success(f'已请求更新 {count} 个测试服务。',
                   {'services': rows}, '调用 service_status 核验运行任务和镜像 digest。')


def _verdict(service: dict[str, Any], tasks: list[dict[str, Any]],
             record: dict[str, Any], expected: str | None) -> dict[str, Any]:
    requested_at = _timestamp(record.get('requested_at'))
    errors = []
    active = []
    for task in tasks:
        task_status = task.get('Status', {})
        task_state = task_status.get('State')
        if task_state in {'failed', 'rejected'}:
            failed_at = _timestamp(task_status.get('Timestamp'))
            if failed_at is None:
                failed_at = _timestamp(task.get('UpdatedAt'))
            if requested_at is not None and failed_at is not None and failed_at < requested_at:
                continue
            errors.append(f"{task.get('ID')}: {task_status.get('Err') or task_state}")
        if task.get('DesiredState', 'running') == 'running':
            active.append(task)
    running = [t for t in active if t.get('Status', {}).get('State') == 'running']
    spec = service['Spec']
    desired = spec.get('Mode', {}).get('Replicated', {}).get(
        'Replicas', service.get('ServiceStatus', {}).get('DesiredTasks', len(active)))
    update = service.get('UpdateStatus', {})
    state = update.get('State')
    if state == 'paused' or str(state).startswith('rollback_'):
        errors.append(f"UpdateStatus {state}: {update.get('Message', '')}")
    digests = [_digest(t.get('Spec', {}).get('ContainerSpec', {}).get('Image', ''))
               for t in running]
    digest = digests[0] if digests and len(set(digests)) == 1 else None
    ready = (requested_at is not None and len(active) == len(running) == desired
             and state in {None, 'completed'})
    verdict = 'failed' if errors else 'updating'
    if not errors and ready:
        if expected and digest == expected:
            verdict = 'converged'
        elif not expected and digest and record.get('before', {}).get('digest') and (
                digest != record['before']['digest']):
            verdict = 'digest_unverified'
        elif (state == 'completed' and expected and None in digests
              and all(value in (None, expected) for value in digests)):
            verdict = 'digest_unverified'
    return {'service': spec['Name'], 'verdict': verdict, 'running': len(running),
            'desired': desired, 'running_digest': digest, 'expected_digest': expected,
            'update_state': state, 'task_errors': errors, 'logs': None}


def _snapshot(ws: Path, cfg: DceConfig, run: Run | str, logs_tail: int,
              client: Portainer) -> dict[str, Any]:
    names = ([run] if isinstance(run, str) else list(dict.fromkeys(
        s for i in _selection(cfg, run, None) for s in i['services'])))
    require(bool(names), 'Portainer service_status', 'service', names, '计划或配置中的测试服务')
    endpoint = _endpoint(cfg)
    swarm = client.swarm_id(endpoint)
    rows = []
    for name in names:
        record = {} if isinstance(run, str) else run.get('deploys', {}).get(name, {})
        expected = None
        if not isinstance(run, str):
            item = next(i for i in run['plan']['items'] if name in i.get('services', []))
            expected = run.get('builds', {}).get(item['id'], {}).get('build', {}).get('digest')
        service = _service(cfg, client, name, swarm, endpoint)
        row = _verdict(service, client.tasks(endpoint, service['ID']), record, expected)
        tail = logs_tail or (50 if row['verdict'] == 'failed' else 0)
        if tail:
            row['logs'] = client.service_logs_since(endpoint, service['ID'],
                                                     record.get('requested_at'), tail)
        row = redact(row, client.reader.secrets())
        rows.append(row)
        if not isinstance(run, str) and record:
            record.update(verdict=row['verdict'], running_digest=row['running_digest'])
    if not isinstance(run, str):
        if all(r['verdict'] == 'converged' for r in rows):
            run['stage'] = 'deployed'
        save_run(ws, run)
    failed = any(r['verdict'] == 'failed' for r in rows)
    unverified = any(r['verdict'] == 'digest_unverified' for r in rows)
    missing_running_digest = any(r['verdict'] == 'digest_unverified' and r['running_digest'] is None
                                 for r in rows)
    next_step = ('部署任务失败，先向用户报告任务错误和日志，处理后再部署。' if failed else
                 '运行任务缺少镜像 digest，请在 Portainer 核对运行容器镜像的 RepoDigests。'
                 if missing_running_digest else
                 '构建 digest 未知，请核对镜像推送日志和运行 digest。' if unverified else
                 '服务已收敛，开始浏览器验证。' if all(r['verdict'] == 'converged' for r in rows)
                 else '继续调用 service_status 跟踪滚动更新；跳过的服务先完成构建再部署。')
    return success(f"测试服务：{', '.join(r['service'] + ' ' + r['verdict'] for r in rows)}。",
                   {'services': rows}, next_step)


def status(ws: Path, cfg: DceConfig, run: Run | str, wait_seconds: int = 0,
           logs_tail: int = 0, clock: Clock = time, *, client: Portainer) -> dict[str, Any]:
    if not 0 <= wait_seconds <= 45 or not 0 <= logs_tail <= 300:
        raise DceError(ErrorCode.CONFIG_INVALID,
                       'service_status: wait_seconds 必须在 0–45，logs_tail 必须在 0–300 之间。',
                       '调整等待秒数和日志行数后重试。')
    deadline = clock.monotonic() + wait_seconds
    initial = _snapshot(ws, cfg, run, logs_tail, client)
    result = initial
    while (any(r['verdict'] == 'updating' for r in result['data']['services'])
           and not any(r['verdict'] == 'failed' for r in result['data']['services'])
           and clock.monotonic() < deadline):
        clock.sleep(min(5, deadline - clock.monotonic()))
        result = _snapshot(ws, cfg, run, logs_tail, client)
        if result['data'] != initial['data']:
            break
    return result
