from mock import MagicMock
from connexion.decorators.security import get_tokeninfo_url

def test_get_tokeninfo_url(monkeypatch):
    env = {}
    monkeypatch.setattr('os.environ', env)
    security_def = {}
    assert get_tokeninfo_url(security_def) is None
    env['TOKENINFO_URL'] = 'issue-146'
    assert get_tokeninfo_url(security_def) == 'issue-146'
    env['HTTP_TOKENINFO_URL'] = 'foo'
    assert get_tokeninfo_url(security_def) == 'foo'
    security_def = {'x-tokenInfoUrl': 'bar'}
    assert get_tokeninfo_url(security_def) == 'bar'
