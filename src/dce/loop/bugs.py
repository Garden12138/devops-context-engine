"""Read product-scoped defects; platform content remains data."""

from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from dce.errors import DceError, ErrorCode
from dce.loop.guard import check_bug
from dce.loop.runs import Run, append_event, list_runs, now, save_run
from dce.platforms.zentao import ZenTao
from dce.workspace.config import DceConfig


@dataclass
class BugView:
    data: dict[str, Any]
    summary: str
    warnings: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ImageBytes:
    content: bytes
    mime: str
    name: str


def identity(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, dict) else value


def brief(bug: dict[str, Any]) -> dict[str, Any]:
    return {
        **{k: bug.get(k) for k in ('id', 'title', 'status', 'severity', 'pri', 'type')},
        'module': identity(bug.get('module'), 'name'),
        'opened_by': identity(bug.get('openedBy'), 'account'),
        'opened_at': bug.get('openedDate'),
        'assigned_to': identity(bug.get('assignedTo'), 'account'), 'run_id': None,
    }


def list_bugs(cfg: DceConfig, scope: str = 'mine', status: str = 'active', limit: int = 20,
              *, client: ZenTao, ws: Path | None = None) -> BugView:
    account = cfg.zentao.account or client.reader.settings._zentao_account
    if (scope not in {'mine', 'all'} or status not in {'active', 'resolved', 'all'}
            or limit < 1 or cfg.zentao.product is None or (scope == 'mine' and not account)):
        raise DceError(ErrorCode.CONFIG_INVALID,
                       'bug_list: 需要配置产品、有效 scope/status、正数 limit 和 mine 的账号。',
                       '检查 .dce/dce.yaml 的 zentao.product/account 和调用参数。')
    result: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    for page in range(1, 11):
        bugs = client.bugs_page(cfg.zentao.product, page, 100)
        for bug in bugs:
            view = brief(bug)
            if status != 'all' and view['status'] != status:
                continue
            if scope == 'mine' and view['assigned_to'] != account:
                continue
            result.append(view)
            if len(result) == limit:
                break
        if len(result) == limit or len(bugs) < 100:
            break
        if page == 10:
            warnings.append({'code': 'TRUNCATED', 'message': '禅道缺陷列表已读 10 页，每页 100 条；'
                             '后续页未读取，可缩小产品内的筛选范围后核对禅道页面。'})
    rows = ['| 缺陷 | 标题 | 严重程度 | 优先级 | 状态 | 指派 |', '|---|---|---|---|---|---|']
    rows.extend(f"| {b['id']} | {b['title']} | {b['severity']} | {b['pri']} | "
                f"{b['status']} | {b['assigned_to']} |" for b in result)
    result_view = BugView({'bugs': result}, '\n'.join(rows), warnings)
    link_runs(result_view, ws)
    return result_view


def get_bug(cfg: DceConfig, bug_id: int, images: bool = True, max_images: int = 6,
            *, client: ZenTao, ws: Path | None = None) -> tuple[BugView, list[ImageBytes]]:
    if bug_id <= 0 or max_images < 0 or cfg.zentao.product is None:
        raise DceError(ErrorCode.CONFIG_INVALID,
                       'bug_get: bug_id 必须为正数、max_images 至少为 0，且需要 zentao.product。',
                       '检查调用参数和 .dce/dce.yaml。')
    bug = client.bug(str(bug_id))
    product = identity(bug.get('product'), 'id')
    if str(product) != str(cfg.zentao.product):
        raise DceError(ErrorCode.OUT_OF_SCOPE,
                       f'禅道缺陷 {bug_id} HTTP 200: 产品 {product} 与配置产品 '
                       f'{cfg.zentao.product} 不一致。', '使用配置产品中的缺陷 ID。')
    text, sources = client.parse_steps(bug)
    data = {**brief(bug), 'steps_text': text, 'images': [], 'history': []}
    view = BugView(data, f"禅道缺陷 #{bug_id}：{data['title']}")
    actions = bug.get('actions')
    if isinstance(actions, list):
        data['history'] = [{k: a.get(k) for k in ('date', 'actor', 'action', 'comment')}
                           for a in actions if isinstance(a, dict)]
    else:
        view.warnings.append({'code': 'HISTORY_UNAVAILABLE', 'message':
                              f'禅道缺陷 {bug_id} HTTP 200: actions 列表未提供；'
                              '请在禅道查看历史。'})
    delivered: list[ImageBytes] = []
    for index, source in enumerate(sources):
        name = Path(unquote(urlsplit(source).path)).name or f'image-{index}'
        entry = {'index': index, 'name': name, 'delivered': False}
        data['images'].append(entry)
        if not images or index >= max_images:
            continue
        try:
            content, mime = client.image_content(source)
            delivered.append(ImageBytes(content, mime, name))
            entry['delivered'] = True
        except DceError as exc:
            view.summary += f'\n图片 {name} 未交付：{exc.message} {exc.hint or ""}'
    remaining = [i['name'] for i in data['images'] if not i['delivered']]
    if remaining:
        view.summary += '\n未交付图片：' + '、'.join(remaining)
    link_runs(view, ws)
    return view, delivered


def link_runs(view: BugView, ws: Path | None) -> None:
    links: dict[int, str] = {}
    for run in list_runs(ws) if ws else []:
        for bug in run.get('bugs', []):
            links.setdefault(bug['id'], run['run_id'])
    for data in view.data.get('bugs', [view.data]):
        data['run_id'] = links.get(data['id'])


def save_image_files(directory: Path, images: list[ImageBytes]) -> None:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for index, image in enumerate(images):
            (directory / f'{index}-{image.name}').write_bytes(image.content)
    except OSError as exc:
        raise DceError(ErrorCode.PLATFORM_ERROR,
                       f'本地图片目录 {directory}: {type(exc).__name__}: {exc}',
                       '选择可写目录后重试 dce bug show --save-images。') from None


def resolve_comment(run: Run, bug_id: int, extra: str | None) -> str:
    lines = ['已修复，测试环境验证通过。']
    for repo, commits in run.get('plan', {}).get('commits', {}).items():
        matching = [commit for commit in commits if bug_id in commit.get('bugs', [])]
        if not matching:
            continue
        branch = run.get('feature_branches', {}).get(repo, '')
        for commit in matching:
            lines.append(f"修复提交：{repo} {branch} {commit['sha'][:7]}（{commit['subject']}）")
        merge = run.get('merges', {}).get(repo)
        if merge:
            merged_at = merge['merged_at'].replace('T', ' ')[:16]
            lines.append(f"合入测试分支：{merge['test_branch']} {merge['merge_sha'][:7]}，"
                         f"{merged_at}")
    deployments = run.get('deploys', {})
    builds = run.get('builds', {})
    related_services = {service: item['id'] for item in run.get('plan', {}).get('items', [])
                        if bug_id in item.get('bugs', []) for service in item.get('services', [])}
    for service, item_id in related_services.items():
        deployment = deployments.get(service)
        if deployment is None:
            continue
        running = deployment.get('running_digest')
        digest = running or builds.get(item_id, {}).get('build', {}).get('digest')
        display = '运行 digest 待核对'
        if digest:
            display = digest[:19] + ('…' if len(digest) > 19 else '')
            if not running:
                display += '（构建 digest，运行待核对）'
        lines.append(f'部署：{service} {display}')
    lines.append(f"验证：{run['verifications'][str(bug_id)].get('notes', '')}")
    record = run['record']
    lines.append(f"记录：{record.get('file', '')}（commit {record['commit'][:7]}）")
    if extra:
        lines.append(extra)
    text = '\n'.join(lines).replace('\r\n', '\n').replace('\r', '\n')
    return escape(text, quote=False).replace('\n', '<br>')


def _save_resolution(ws: Path, run: Run, bug_id: int, status: str) -> None:
    resolved = run.setdefault('zentao', {})
    resolved[str(bug_id)] = {'action': status, 'at': now()}
    if all(str(bug['id']) in resolved for bug in run['bugs']):
        run['stage'] = 'resolved'
    save_run(ws, run)


def resolve_bugs(ws: Path, cfg: DceConfig, run: Run, bug_ids: list[int] | None = None,
                 comment: str | None = None, *, client: ZenTao) -> list[dict[str, Any]]:
    members = {bug['id']: bug for bug in run['bugs']}
    selected = list(dict.fromkeys(bug_ids if bug_ids is not None else members))
    outside = [bug_id for bug_id in selected if bug_id not in members]
    if outside:
        raise DceError(ErrorCode.OUT_OF_SCOPE,
                       f"禅道缺陷 {outside} 不属于 run {run['run_id']}。",
                       '使用 dce_status 核对这个 run 包含的缺陷。')
    results: list[dict[str, Any]] = []
    for bug_id in selected:
        row: dict[str, Any] = {'bug': bug_id, 'status': 'blocked'}
        results.append(row)
        verification = run.get('verifications', {}).get(str(bug_id), {})
        if verification.get('result') != 'passed':
            row['reason'] = 'verification 未通过，请通过 run_update 记录通过的验证。'
            continue
        if not run.get('record', {}).get('commit'):
            row['reason'] = '缺少修复记录提交，请通过 run_update 保存记录。'
            continue
        live = client.bug(str(bug_id))
        check_bug(cfg, live)
        status = live.get('status')
        if status in ('resolved', 'closed'):
            row.update(status='skipped', reason=f'已是 {status}')
            if str(bug_id) not in run.get('zentao', {}):
                _save_resolution(ws, run, bug_id, 'skipped')
            continue
        if status != 'active':
            row['reason'] = f'禅道缺陷 {bug_id} HTTP 200: 当前状态 {status!r}，请核对为 active。'
            continue
        config = cfg.zentao.resolve
        assigned = (identity(live.get('openedBy'), 'account') if config.assign_to == 'opener'
                    else config.assign_to)
        if not isinstance(assigned, str) or not assigned.strip():
            raise DceError(ErrorCode.PLATFORM_ERROR,
                           f'禅道缺陷 {bug_id} HTTP 200: openedBy 缺少提测人账号。',
                           '核对禅道响应或配置 zentao.resolve.assign_to 的具体账号。')
        body = {'resolution': config.resolution, 'resolvedBuild': config.resolved_build,
                'assignedTo': assigned, 'comment': resolve_comment(run, bug_id, comment)}
        try:
            client.resolve(bug_id, body)
            confirmed = client.bug(str(bug_id))
            if confirmed.get('status') != 'resolved':
                raise DceError(ErrorCode.PLATFORM_ERROR,
                               f"禅道缺陷 {bug_id} 复读 HTTP 200: 状态为 "
                               f"{confirmed.get('status')!r}，预期为 resolved。",
                               '核对禅道解决返回和缺陷历史后再重试。')
        except DceError as exc:
            append_event(run, 'bug_resolve', 'resolve', str(bug_id), 'error',
                         '禅道解决请求或复读失败', error_code=exc.code.value)
            save_run(ws, run)
            raise
        row.update(status='resolved', assigned_to=assigned)
        append_event(run, 'bug_resolve', 'resolve', str(bug_id), 'ok', '复读已确认 resolved')
        _save_resolution(ws, run, bug_id, 'resolved')
    return results
