from connexion.decorators.metrics import UWSGIMetricsCollector
import connexion
from mock import MagicMock


def test_timer(monkeypatch):
    wrapper = UWSGIMetricsCollector('/foo/bar/<param>', 'get')

    def operation():
        return connexion.problem(418, '', '')

    op = wrapper(operation)
    metrics = MagicMock()
    monkeypatch.setattr('flask.request', MagicMock())
    monkeypatch.setattr('connexion.decorators.metrics.uwsgi_metrics', metrics)
    op()
    assert metrics.timer.call_args[0][:2] == ('connexion.response',
                                              '418.GET.foo.bar.{param}')
