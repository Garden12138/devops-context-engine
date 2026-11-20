import pytest

from dce.workspace.pom import closure, scan_maven


def pom(tmp_path, path, artifact, dependencies=()):
    directory = tmp_path / path
    directory.mkdir(parents=True, exist_ok=True)
    deps = ''.join(f'<dependency><groupId>com.demo</groupId><artifactId>{a}</artifactId>'
                   '</dependency>' for a in dependencies)
    (directory / 'pom.xml').write_text(
        '<project xmlns="http://maven.apache.org/POM/4.0.0">'
        '<parent><groupId>com.demo</groupId><artifactId>demo-parent</artifactId></parent>'
        f'<artifactId>{artifact}</artifactId><dependencies>{deps}</dependencies></project>'
    )


def test_maven_inheritance_dependencies_and_closure(tmp_path):
    pom(tmp_path, 'demo-a', 'demo-a', ['demo-b'])
    pom(tmp_path, 'demo-b', 'demo-b', ['demo-common'])
    pom(tmp_path, 'demo-common', 'demo-common')
    modules = scan_maven(tmp_path)
    assert modules['demo-a'].artifact == 'com.demo:demo-a'
    assert modules['demo-a'].depends_on == {'com.demo:demo-b'}
    assert closure(modules)['demo-a'] == {'com.demo:demo-b', 'com.demo:demo-common'}


@pytest.mark.parametrize('bad', [
    '<!DOCTYPE project><project/>', '<!ENTITY x "demo"><project/>', '<project>',
])
def test_unsafe_or_invalid_xml_warns_and_skips(tmp_path, bad):
    (tmp_path / 'pom.xml').write_text(bad)
    with pytest.warns(UserWarning, match='pom.xml'):
        assert scan_maven(tmp_path) == {}


def test_non_maven_and_cyclic_dependencies(tmp_path):
    assert scan_maven(tmp_path) == {}
    pom(tmp_path, 'demo-a', 'demo-a', ['demo-b'])
    pom(tmp_path, 'demo-b', 'demo-b', ['demo-a'])
    assert closure(scan_maven(tmp_path))['demo-a'] == {'com.demo:demo-b'}
