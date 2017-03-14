import pytest
from connexion.decorators.security import get_tokeninfo_url, verify_oauth
from connexion.exceptions import (OAuthProblem, OAuthResponseProblem,
                                  OAuthScopeProblem)
from mock import MagicMock, PropertyMock
from testfixtures import LogCapture


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

    wrapped_func = verify_oauth('https://example.org/tokeninfo', set(['admin']), [], func)

    request = MagicMock()
    app = MagicMock()
    monkeypatch.setattr('connexion.decorators.security.request', request)
    monkeypatch.setattr('flask.current_app', app)

    with pytest.raises(OAuthProblem):
        wrapped_func()


def _setup_request_mock(remote_addr, x_forwarded_for=None):
    def get_header(header):
        if header == "Authorization":
            return "Bearer 12345678"
        elif header == "X-Forwarded-For":
            return x_forwarded_for
    headers = MagicMock(side_effect=get_header)
    request = MagicMock()
    type(request).url = PropertyMock(return_value="http://localhost:9090/v1/resource/123")
    type(request).remote_addr = PropertyMock(return_value=remote_addr)
    return request, headers


def _setup_token_request_mock(valid=True, status_code=200, text="OK"):
    token_request = MagicMock()
    type(token_request.return_value).ok = PropertyMock(return_value=valid)
    type(token_request.return_value).status_code = PropertyMock(return_value=status_code)
    type(token_request.return_value).text = PropertyMock(return_value=text)
    return token_request


def test_correct_client_ip_logged(monkeypatch):
    def func():
        pass

    app = MagicMock()
    monkeypatch.setattr('flask.current_app', app)

    # 1) remote_addr, no x-forwarded-for, invalid token (401)
    with LogCapture() as l:
        wrapped_func = verify_oauth('https://example.org/tokeninfo', set(['admin']), [], func)
        request, headers = _setup_request_mock(remote_addr="123.123.123.123")
        monkeypatch.setattr('connexion.decorators.security.request', request)
        monkeypatch.setattr('connexion.decorators.security.request.headers.get', headers)
        token_request = _setup_token_request_mock(valid=False, status_code=401, text="Invalid token")
        monkeypatch.setattr('connexion.decorators.security.session.get', token_request)
        with pytest.raises(OAuthResponseProblem):
            wrapped_func()
        l.check(
            ('connexion.api.security', 'DEBUG', 'http://localhost:9090/v1/resource/123 Oauth verification...'),
            ('connexion.api.security', 'DEBUG', '... Getting token from https://example.org/tokeninfo'),
            ('connexion.api.security', 'DEBUG', "... Token info (401): Invalid token for client IP '123.123.123.123'"))

    # 2) remote_addr, x-forwarded-for, trusted ip, invalid token (401)
    with LogCapture() as l:
        wrapped_func = verify_oauth('https://example.org/tokeninfo', set(['admin']), ["192.168.1.10"], func)
        request, headers = _setup_request_mock(remote_addr="192.168.1.10", x_forwarded_for="123.123.123.123")
        monkeypatch.setattr('connexion.decorators.security.request', request)
        monkeypatch.setattr('connexion.decorators.security.request.headers.get', headers)
        token_request = _setup_token_request_mock(valid=False, status_code=401, text="Invalid token")
        monkeypatch.setattr('connexion.decorators.security.session.get', token_request)
        with pytest.raises(OAuthResponseProblem):
            wrapped_func()
        l.check(
            ('connexion.api.security', 'DEBUG', 'http://localhost:9090/v1/resource/123 Oauth verification...'),
            ('connexion.api.security', 'DEBUG', '... Getting token from https://example.org/tokeninfo'),
            ('connexion.api.security', 'DEBUG', "... Token info (401): Invalid token for client IP '123.123.123.123'"))

    # 3) remote_addr, x-forwarded-for, untrusted ip, invalid token (401)
    with LogCapture() as l:
        wrapped_func = verify_oauth('https://example.org/tokeninfo', set(['admin']), ["192.168.1.10"], func)
        request, headers = _setup_request_mock(remote_addr="1.2.3.4", x_forwarded_for="123.123.123.123")
        monkeypatch.setattr('connexion.decorators.security.request', request)
        monkeypatch.setattr('connexion.decorators.security.request.headers.get', headers)
        token_request = _setup_token_request_mock(valid=False, status_code=401, text="Invalid token")
        monkeypatch.setattr('connexion.decorators.security.session.get', token_request)
        with pytest.raises(OAuthResponseProblem):
            wrapped_func()
        l.check(
            ('connexion.api.security', 'DEBUG', 'http://localhost:9090/v1/resource/123 Oauth verification...'),
            ('connexion.api.security', 'DEBUG', '... Getting token from https://example.org/tokeninfo'),
            ('connexion.api.security', 'DEBUG', "... Token info (401): Invalid token for client IP '1.2.3.4'"))

    # 4) remote_addr, no x-forwarded-for, insufficient scope (403)
    with LogCapture() as l:
        wrapped_func = verify_oauth('https://example.org/tokeninfo', set(['admin']), [], func)
        request, headers = _setup_request_mock(remote_addr="123.123.123.123")
        monkeypatch.setattr('connexion.decorators.security.request', request)
        monkeypatch.setattr('connexion.decorators.security.request.headers.get', headers)
        token_request = _setup_token_request_mock(valid=True, status_code=200, text="OK")
        monkeypatch.setattr('connexion.decorators.security.session.get', token_request)
        with pytest.raises(OAuthScopeProblem):
            wrapped_func()
        l.check(
            ('connexion.api.security', 'DEBUG', 'http://localhost:9090/v1/resource/123 Oauth verification...'),
            ('connexion.api.security', 'DEBUG', '... Getting token from https://example.org/tokeninfo'),
            ('connexion.api.security', 'DEBUG', "... Token info (200): OK for client IP '123.123.123.123'"),
            ('connexion.api.security', 'DEBUG', "... Scopes required: admin"),
            ('connexion.api.security', 'DEBUG', "... User scopes: None"),
            ('connexion.api.security', 'INFO', ("... User scopes (None) do not match the scopes necessary "
                                                "to call endpoint (admin). "
                                                "Aborting with 403 for client IP '123.123.123.123'")))

    # 5) remote_addr, x-forwarded-for, trusted ip, insufficient scope (403)
    with LogCapture() as l:
        wrapped_func = verify_oauth('https://example.org/tokeninfo', set(['admin']), ["192.168.1.10"], func)
        request, headers = _setup_request_mock(remote_addr="192.168.1.10", x_forwarded_for="123.123.123.123")
        monkeypatch.setattr('connexion.decorators.security.request', request)
        monkeypatch.setattr('connexion.decorators.security.request.headers.get', headers)
        token_request = _setup_token_request_mock(valid=True, status_code=200, text="OK")
        monkeypatch.setattr('connexion.decorators.security.session.get', token_request)
        with pytest.raises(OAuthScopeProblem):
            wrapped_func()
        l.check(
            ('connexion.api.security', 'DEBUG', 'http://localhost:9090/v1/resource/123 Oauth verification...'),
            ('connexion.api.security', 'DEBUG', '... Getting token from https://example.org/tokeninfo'),
            ('connexion.api.security', 'DEBUG', "... Token info (200): OK for client IP '123.123.123.123'"),
            ('connexion.api.security', 'DEBUG', "... Scopes required: admin"),
            ('connexion.api.security', 'DEBUG', "... User scopes: None"),
            ('connexion.api.security', 'INFO', ("... User scopes (None) do not match the scopes necessary "
                                                "to call endpoint (admin). "
                                                "Aborting with 403 for client IP '123.123.123.123'")))

    # 6) remote_addr, x-forwarded-for, untrusted ip, insufficient scope (403)
    with LogCapture() as l:
        wrapped_func = verify_oauth('https://example.org/tokeninfo', set(['admin']), ["192.168.1.10"], func)
        request, headers = _setup_request_mock(remote_addr="1.2.3.4", x_forwarded_for="123.123.123.123")
        monkeypatch.setattr('connexion.decorators.security.request', request)
        monkeypatch.setattr('connexion.decorators.security.request.headers.get', headers)
        token_request = _setup_token_request_mock(valid=True, status_code=200, text="OK")
        monkeypatch.setattr('connexion.decorators.security.session.get', token_request)
        with pytest.raises(OAuthScopeProblem):
            wrapped_func()
        l.check(
            ('connexion.api.security', 'DEBUG', 'http://localhost:9090/v1/resource/123 Oauth verification...'),
            ('connexion.api.security', 'DEBUG', '... Getting token from https://example.org/tokeninfo'),
            ('connexion.api.security', 'DEBUG', "... Token info (200): OK for client IP '1.2.3.4'"),
            ('connexion.api.security', 'DEBUG', "... Scopes required: admin"),
            ('connexion.api.security', 'DEBUG', "... User scopes: None"),
            ('connexion.api.security', 'INFO', ("... User scopes (None) do not match the scopes necessary "
                                                "to call endpoint (admin). "
                                                "Aborting with 403 for client IP '1.2.3.4'")))
