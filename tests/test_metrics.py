from unittest.mock import MagicMock

import flask
import pytest

from especifico.decorators.metrics import UWSGIMetricsCollector
from especifico.exceptions import ProblemException


def test_timer(monkeypatch):
    wrapper = UWSGIMetricsCollector("/foo/bar/<param>", "get")

    def operation(req):
        raise ProblemException(418, "", "")

    op = wrapper(operation)
    metrics = MagicMock()
    monkeypatch.setattr("flask.request", MagicMock())
    monkeypatch.setattr("flask.current_app", MagicMock(response_class=flask.Response))
    monkeypatch.setattr("especifico.decorators.metrics.uwsgi_metrics", metrics)
    with pytest.raises(ProblemException):
        op(MagicMock())
    assert metrics.timer.call_args[0][:2] == (
        "especifico.response",
        "418.GET.foo.bar.{param}",
    )
