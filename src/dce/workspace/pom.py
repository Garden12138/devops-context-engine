import warnings
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree


@dataclass
class MavenModule:
    artifact: str
    depends_on: set[str]


def scan_maven(repo_root: Path) -> dict[str, MavenModule]:
    modules: dict[str, MavenModule] = {}
    for path in sorted(repo_root.rglob('pom.xml')):
        if not path.resolve().is_relative_to(repo_root.resolve()):
            continue
        try:
            text = path.read_text()
            if '<!DOCTYPE' in text or '<!ENTITY' in text:
                raise ValueError('含 DOCTYPE/ENTITY 声明')
            root = ElementTree.fromstring(text)
            # Strip namespaces once; all supported Maven fields are direct children.
            for node in root.iter():
                node.tag = node.tag.rsplit('}', 1)[-1]
            group = root.findtext('groupId') or root.findtext('parent/groupId')
            artifact = root.findtext('artifactId')
            if not group or not artifact:
                raise ValueError('缺少 groupId 或 artifactId')
            dependencies = {
                f'{g}:{a}' for dependency in root.findall('dependencies/dependency')
                if (g := dependency.findtext('groupId'))
                and (a := dependency.findtext('artifactId'))
            }
            modules[path.parent.relative_to(repo_root).as_posix()] = MavenModule(
                f'{group}:{artifact}', dependencies,
            )
        except (OSError, UnicodeError, ElementTree.ParseError, ValueError) as exc:
            warnings.warn(
                f'{path.relative_to(repo_root)}: {type(exc).__name__}，已跳过；检查 pom.xml。',
                stacklevel=2,
            )
    return modules


def closure(modules: dict[str, MavenModule]) -> dict[str, set[str]]:
    artifacts = {module.artifact: module.depends_on for module in modules.values()}
    result: dict[str, set[str]] = {}
    for path, module in modules.items():
        seen: set[str] = set()
        pending = list(module.depends_on)
        while pending:
            dependency = pending.pop()
            if dependency in seen or dependency == module.artifact:
                continue
            seen.add(dependency)
            pending.extend(artifacts.get(dependency, set()) - seen)
        result[path] = seen
    return result
