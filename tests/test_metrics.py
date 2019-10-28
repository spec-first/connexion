import json

import flask
import pytest
from mock import MagicMock

import connexion
from connexion.exceptions import ProblemException
from connexion.decorators.metrics import UWSGIMetricsCollector


def test_timer(monkeypatch):
    wrapper = UWSGIMetricsCollector('/foo/bar/<param>', 'get')

    def operation(req):
        raise ProblemException(418, '', '')

    op = wrapper(operation)
    metrics = MagicMock()
    monkeypatch.setattr('flask.request', MagicMock())
    monkeypatch.setattr('flask.current_app', MagicMock(response_class=flask.Response))
    monkeypatch.setattr('connexion.decorators.metrics.uwsgi_metrics', metrics)
    with pytest.raises(ProblemException) as exc:
        op(MagicMock())
    assert metrics.timer.call_args[0][:2] == ('connexion.response',
                                              '418.GET.foo.bar.{param}')
