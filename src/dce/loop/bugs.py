"""Read product-scoped defects; platform content remains data."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from dce.errors import DceError, ErrorCode
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
              *, client: ZenTao) -> BugView:
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
    return BugView({'bugs': result}, '\n'.join(rows), warnings)


def get_bug(cfg: DceConfig, bug_id: int, images: bool = True, max_images: int = 6,
            *, client: ZenTao) -> tuple[BugView, list[ImageBytes]]:
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
    return view, delivered
