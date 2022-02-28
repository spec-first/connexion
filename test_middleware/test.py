import contextlib
import time
import threading

import requests
import uvicorn


class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()


apps = [
    'flask_app',
    'quart_app',
    'sanic_app',
    'starlette_app'
]


def test_app(app):
    print(f'Testing {app}')
    config = uvicorn.Config(f'{app}:app', host="127.0.0.1", port=8000, log_level="info")
    server = Server(config=config)

    with server.run_in_thread():
        response = requests.get('http://localhost:8000/test', params={'int': 1})

    assert response.headers.get('operation_id') == 'success'
    print(response.headers.get('operation_id'))
    print()


for app in apps:
    test_app(app)
