import asyncio

from aiohttp import web
from aiohttp_remotes.exceptions import RemoteError, TooManyHeaders
from aiohttp_remotes.x_forwarded import XForwardedBase
from connexion import AioHttpApp
from yarl import URL

X_FORWARDED_PATH = "X-Forwarded-Path"


class XPathForwarded(XForwardedBase):

    def __init__(self, num=1):
        self._num = num

    def get_forwarded_path(self, headers):
        forwarded_host = headers.getall(X_FORWARDED_PATH, [])
        if len(forwarded_host) > 1:
            raise TooManyHeaders(X_FORWARDED_PATH)
        return forwarded_host[0] if forwarded_host else None

    @web.middleware
    async def middleware(self, request, handler):
        try:
            overrides = {}
            headers = request.headers

            forwarded_for = self.get_forwarded_for(headers)
            if forwarded_for:
                overrides['remote'] = str(forwarded_for[-self._num])

            proto = self.get_forwarded_proto(headers)
            if proto:
                overrides['scheme'] = proto[-self._num]

            host = self.get_forwarded_host(headers)
            if host is not None:
                overrides['host'] = host

            prefix = self.get_forwarded_path(headers)
            if prefix is not None:
                prefix = '/' + prefix.strip('/') + '/'
                request_path = URL(request.path.lstrip('/'))
                overrides['rel_url'] = URL(prefix).join(request_path)

            request = request.clone(**overrides)

            return await handler(request)
        except RemoteError as exc:
            exc.log(request)
        await self.raise_error(request)


    @asyncio.coroutine
    def test_swagger_json_behind_proxy(simple_api_spec_dir, aiohttp_client):
        """ Verify the swagger.json file is returned with base_path updated
            according to X-Forwarded-Path header. """
        app = AioHttpApp(__name__, port=5001,
                         specification_dir=simple_api_spec_dir,
                         debug=True)
        api = app.add_api('swagger.yaml')

        aio = app.app
        reverse_proxied = XPathForwarded()
        aio.middlewares.append(reverse_proxied.middleware)

        app_client = yield from aiohttp_client(app.app)
        headers = {'X-Forwarded-Path': '/behind/proxy'}

        swagger_ui = yield from app_client.get('/v1.0/ui/', headers=headers)
        assert swagger_ui.status == 200
        assert b'url = "/behind/proxy/v1.0/swagger.json"' in (
            yield from swagger_ui.read()
        )

        swagger_json = yield from app_client.get('/v1.0/swagger.json',
                                                 headers=headers)
        assert swagger_json.status == 200
        assert swagger_json.headers.get('Content-Type') == 'application/json'
        json_ = yield from swagger_json.json()

        assert api.specification.raw['basePath'] == '/v1.0', \
            "Original specifications should not have been changed"

        assert json_.get('basePath') == '/behind/proxy/v1.0', \
            "basePath should contains original URI"

        json_['basePath'] = api.specification.raw['basePath']
        assert api.specification.raw == json_, \
            "Only basePath should have been updated"


    @asyncio.coroutine
    def test_openapi_json_behind_proxy(simple_api_spec_dir, aiohttp_client):
        """ Verify the swagger.json file is returned with base_path updated
            according to X-Forwarded-Path header. """
        app = AioHttpApp(__name__, port=5001,
                         specification_dir=simple_api_spec_dir,
                         debug=True)

        api = app.add_api('openapi.yaml')

        aio = app.app
        reverse_proxied = XPathForwarded()
        aio.middlewares.append(reverse_proxied.middleware)

        app_client = yield from aiohttp_client(app.app)
        headers = {'X-Forwarded-Path': '/behind/proxy'}

        swagger_ui = yield from app_client.get('/v1.0/ui/', headers=headers)
        assert swagger_ui.status == 200
        assert b'url: "/behind/proxy/v1.0/openapi.json"' in (
            yield from swagger_ui.read()
        )

        swagger_json = yield from app_client.get('/v1.0/openapi.json',
                                                 headers=headers)
        assert swagger_json.status == 200
        assert swagger_json.headers.get('Content-Type') == 'application/json'
        json_ = yield from swagger_json.json()

        assert json_.get('servers', [{}])[0].get('url') == '/behind/proxy/v1.0', \
            "basePath should contains original URI"

        url = api.specification.raw.get('servers', [{}])[0].get('url')
        assert url != '/behind/proxy/v1.0', \
            "Original specifications should not have been changed"

        json_['servers'] = api.specification.raw.get('servers')
        assert api.specification.raw == json_, \
            "Only there servers block should have been updated"
