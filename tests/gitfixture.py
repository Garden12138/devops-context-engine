"""Local bare origin and disposable clones; no network or user git configuration."""

import os
import subprocess
from pathlib import Path


class GitFixture:
    def __init__(self, root: Path, initial: str = 'master') -> None:
        root.mkdir(parents=True)
        self.origin = root / 'demo-origin.git'
        self.work = root / 'demo-work'
        self.git(root, 'init', '--bare', f'--initial-branch={initial}', str(self.origin))
        self.git(root, 'clone', str(self.origin), str(self.work))
        self.commit('README.md', 'demo base\n', 'chore: demo base')
        self.push(initial)
        self.branch('develop')
        self.push('develop')
        self.branch('feature/1.2.0')
        self.push('feature/1.2.0')

    @staticmethod
    def git(path, *args):
        return subprocess.run(
            ['git', '-c', 'user.name=demo-dev', '-c', 'user.email=demo@example.invalid',
             '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', *args],
            cwd=path, shell=False, timeout=60, check=True, capture_output=True, text=True,
            env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1',
                 'GIT_CONFIG_GLOBAL': os.devnull},
        ).stdout.strip()

    def commit(self, path, content, msg):
        target = self.work / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        self.git(self.work, 'add', '--', path)
        self.git(self.work, 'commit', '-m', msg)
        return self.git(self.work, 'rev-parse', 'HEAD')

    def branch(self, name, start=None):
        self.git(self.work, 'checkout', '-b', name, *([start] if start else []))

    def checkout(self, name):
        self.git(self.work, 'checkout', name)

    def push(self, name='feature/1.2.0'):
        self.git(self.work, 'push', 'origin', f'{name}:refs/heads/{name}')
