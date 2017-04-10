import json

import connexion
import flask
from connexion.decorators.metrics import UWSGIMetricsCollector
from mock import MagicMock


def test_timer(monkeypatch):
    wrapper = UWSGIMetricsCollector('/foo/bar/<param>', 'get')

    def operation(req):
        return connexion.problem(418, '', '')

    op = wrapper(operation)
    metrics = MagicMock()
    monkeypatch.setattr('flask.request', MagicMock())
    monkeypatch.setattr('flask.current_app', MagicMock(response_class=flask.Response))
    monkeypatch.setattr('connexion.decorators.metrics.uwsgi_metrics', metrics)
    op(MagicMock())
    assert metrics.timer.call_args[0][:2] == ('connexion.response',
                                              '418.GET.foo.bar.{param}')
