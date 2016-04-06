from connexion.decorators.metrics import UWSGIMetricsCollector

from mock import MagicMock


def test_timer(monkeypatch):
    wrapper = UWSGIMetricsCollector('/foo/bar/<param>', 'get')

    def operation():
        return None, 418, None

    op = wrapper(operation)
    metrics = MagicMock()
    monkeypatch.setattr('flask.request', MagicMock())
    monkeypatch.setattr('connexion.decorators.metrics.uwsgi_metrics', metrics)
    op()
    assert metrics.timer.call_args[0][:2] == ('connexion.response',
                                              '418.GET.foo.bar.{param}')
