import pytest
from test_local_credentials import CREDENTIALS, files

from dce.errors import DceError
from dce.settings import load_settings


@pytest.mark.parametrize(
    ('change', 'code', 'message'),
    [
        ('permissions', 'CREDENTIALS_INVALID', '权限必须为 0600'),
        ('missing', 'CREDENTIALS_INVALID', '缺少 GitLab 令牌（GITLAB_TOKEN 或 DCE_GITLAB_TOKEN）'),
        ('url', 'CONFIG_INVALID', 'ZEN_URL'),
        ('http', 'CONFIG_INVALID', 'allow_http = true'),
        ('token', 'CONFIG_INVALID', '凭证只能放在凭证文件'),
    ],
)
def test_specific_configuration_errors(tmp_path, change, code, message):
    config, credentials = files(tmp_path, CREDENTIALS)
    if change == 'permissions':
        credentials.chmod(0o644)
    elif change == 'missing':
        credentials.write_text(CREDENTIALS.replace('GITLAB_TOKEN=fake-git\n', ''))
    elif change == 'url':
        credentials.write_text(CREDENTIALS + 'ZEN_URL=https://demo-user@zentao.example.invalid\n')
    elif change == 'http':
        config.write_text(config.read_text().replace('https://gitlab', 'http://gitlab'))
    else:
        config.write_text(config.read_text() + 'token="fake-inline"\n')
    with pytest.raises(DceError) as error:
        load_settings(config, credentials, environ={})
    assert error.value.code == code
    assert message in error.value.message
    assert 'fake-git' not in str(error.value)
    assert 'demo-user@' not in str(error.value)


def test_alias_and_lazy_zentao_login(tmp_path):
    config, credentials = files(tmp_path, CREDENTIALS)
    settings = load_settings(config, credentials, environ={})
    assert settings.portainer.token.get_secret_value() == 'fake-port'
    assert settings._zentao_tokens is not None
