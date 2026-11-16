from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from dce.errors import DceError
from dce.workspace.config import dump_config, load_config, locate_workspace


@pytest.fixture
def config_data():
    return yaml.safe_load(Path('examples/dce.example.yaml').read_text())


def write_config(tmp_path, data):
    directory = tmp_path / '.dce'
    directory.mkdir(exist_ok=True)
    (directory / 'dce.yaml').write_text(yaml.safe_dump(data))
    return load_config(tmp_path)


def test_config_roundtrip(tmp_path, config_data):
    config = write_config(tmp_path, config_data)
    assert config.repos[1].modules[0].services == ['demo_test_demo-modules-order']
    assert yaml.safe_load(dump_config(config)) == config.model_dump(exclude_none=True)


@pytest.mark.parametrize('case,path', [
    ('version', 'version'), ('duplicate_repo', 'repos[1].name'),
    ('outside', 'repos[0].path'), ('symlink', 'repos[0].path'),
    ('protected', 'repos[0].test_branch'), ('defaults', 'protected_branches'),
    ('library_artifact', 'repos[0].modules[0].artifact'),
    ('library_compile', 'repos[0].modules[0].compile_job'),
    ('library_build', 'repos[0].modules[0].build_job'),
    ('library_services', 'repos[0].modules[0].services'),
    ('service_jobs', 'repos[1].modules[0].compile_job'),
    ('service_image', 'repos[1].modules[0].image'),
    ('service_services', 'repos[1].modules[0].services'),
    ('namespace', 'repos[1].modules[0].services[0]'),
    ('duplicate_module', 'repos[1].modules[1].path'),
    ('dot_module', 'repos[1].modules[0].path'),
])
def test_config_invalid_paths(tmp_path, config_data, case, path):
    data = deepcopy(config_data)
    library = data['repos'][0]['modules'][0]
    service = data['repos'][1]['modules'][0]
    if case == 'version':
        data['version'] = 1
    elif case == 'duplicate_repo':
        data['repos'][1]['name'] = data['repos'][0]['name']
    elif case == 'outside':
        data['repos'][0]['path'] = '../demo-outside'
    elif case == 'symlink':
        (tmp_path / data['repos'][0]['path']).symlink_to(tmp_path.parent)
    elif case == 'protected':
        data['repos'][0]['test_branch'] = 'release'
    elif case == 'defaults':
        data['protected_branches'].remove('main')
    elif case in {'library_artifact', 'library_compile'}:
        library.pop('artifact' if case.endswith('artifact') else 'compile_job')
    elif case == 'library_build':
        library['build_job'] = 'build_demo'
    elif case == 'library_services':
        library['services'] = ['demo_test_demo-lib']
    elif case == 'service_jobs':
        service.pop('compile_job')
        service.pop('build_job')
    elif case in {'service_image', 'service_services'}:
        service.pop('image' if case.endswith('image') else 'services')
    elif case == 'namespace':
        service['services'] = ['demo_other_service']
    else:
        data['repos'][1]['modules'].append(deepcopy(service))
        if case == 'dot_module':
            service['path'] = '.'
    with pytest.raises(DceError) as error:
        write_config(tmp_path, data)
    assert error.value.code == 'CONFIG_INVALID'
    assert path in error.value.message


def test_workspace_resolution(tmp_path, config_data):
    assert locate_workspace(str(tmp_path), None, Path('/')) == tmp_path
    assert locate_workspace(None, tmp_path, Path('/')) == tmp_path
    with pytest.raises(DceError, match='workspaceFolder') as error:
        locate_workspace(None, None, tmp_path)
    assert error.value.code == 'WORKSPACE_REQUIRED'
    with pytest.raises(DceError) as error:
        locate_workspace(str(tmp_path.parent), tmp_path, Path('/'))
    assert error.value.code == 'WORKSPACE_MISMATCH'
    write_config(tmp_path, config_data)
    assert locate_workspace(None, None, tmp_path) == tmp_path
    with pytest.raises(DceError):
        locate_workspace('relative', None, tmp_path)


def test_missing_and_invalid_yaml(tmp_path):
    with pytest.raises(DceError) as error:
        load_config(tmp_path)
    assert error.value.code == 'CONFIG_MISSING'
    (tmp_path / '.dce').mkdir()
    (tmp_path / '.dce/dce.yaml').write_text('version: [')
    with pytest.raises(DceError) as error:
        load_config(tmp_path)
    assert error.value.code == 'CONFIG_INVALID'
