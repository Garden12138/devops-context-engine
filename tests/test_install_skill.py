import re
from pathlib import Path

from typer.testing import CliRunner

from dce.cli import app

ROOT = Path(__file__).resolve().parents[1]
SKILL = 'dce-bugfix-loop'


def test_skill_files_exactly_match_playbook():
    playbook = (ROOT / 'docs/v2/07-Playbook.md').read_bytes()
    skill, record = re.findall(rb'````markdown\n(.*?)````', playbook, re.S)
    source = ROOT / 'skills' / SKILL
    assert (source / 'SKILL.md').read_bytes() == skill
    assert (source / 'record-template.md').read_bytes() == record


def test_install_skill_from_another_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / 'demo-skills'
    result = CliRunner().invoke(app, ['install-skill', '--dest', str(dest)])
    assert result.exit_code == 0, result.output
    for name in ('SKILL.md', 'record-template.md'):
        assert (dest / SKILL / name).read_bytes() == (ROOT / 'skills' / SKILL / name).read_bytes()


def test_existing_skill_shows_diff_and_only_force_overwrites(tmp_path):
    target = tmp_path / SKILL
    target.mkdir()
    skill = target / 'SKILL.md'
    skill.write_text('demo local text\n')
    extra = target / 'demo-local.md'
    extra.write_text('demo')
    args = ['install-skill', '--dest', str(tmp_path)]
    preview = CliRunner().invoke(app, args)
    assert preview.exit_code != 0 and '--force' in preview.output
    assert '-demo local text' in preview.stdout
    assert skill.read_text() == 'demo local text\n'
    assert not (target / 'record-template.md').exists()
    applied = CliRunner().invoke(app, [*args, '--force'])
    assert applied.exit_code == 0, applied.output
    assert '-demo local text' in applied.stdout
    assert skill.read_bytes() == (ROOT / 'skills' / SKILL / skill.name).read_bytes()
    assert (target / 'record-template.md').is_file() and extra.read_text() == 'demo'
    assert CliRunner().invoke(app, args).exit_code == 0
