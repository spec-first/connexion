import pytest
from connexion.decorators.security import get_tokeninfo_url, verify_oauth
from connexion.exceptions import OAuthProblem
from mock import MagicMock


def test_get_tokeninfo_url(monkeypatch):
    env = {}
    monkeypatch.setattr('os.environ', env)
    logger = MagicMock()
    monkeypatch.setattr('connexion.decorators.security.logger', logger)
    security_def = {}
    assert get_tokeninfo_url(security_def) is None
    logger.warn.assert_not_called()
    env['TOKENINFO_URL'] = 'issue-146'
    assert get_tokeninfo_url(security_def) == 'issue-146'
    logger.warn.assert_not_called()
    logger.warn.reset_mock()
    security_def = {'x-tokenInfoUrl': 'bar'}
    assert get_tokeninfo_url(security_def) == 'bar'
    logger.warn.assert_not_called()


def test_verify_oauth_invalid_auth_header(monkeypatch):
    def func():
        pass

    wrapped_func = verify_oauth('https://example.org/tokeninfo', set(['admin']), func)

    request = MagicMock()
    app = MagicMock()
    monkeypatch.setattr('flask.current_app', app)

    with pytest.raises(OAuthProblem) as exc_info:
        wrapped_func(MagicMock())
