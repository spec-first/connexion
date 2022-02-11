#!/usr/bin/env python3
'''
example of aiohttp connexion running behind a path-altering reverse-proxy
'''

import json
import logging

import connexion
from aiohttp import web
from aiohttp_remotes.exceptions import RemoteError, TooManyHeaders
from aiohttp_remotes.x_forwarded import XForwardedBase
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
        logging.warning(
            "this demo is not secure by default!! "
            "You'll want to make sure these headers are coming from your proxy, "
            "and not directly from users on the web!"
            )
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


def hello(request):
    ret = {
        "host": request.host,
        "scheme": request.scheme,
        "path": request.path,
        "_href": str(request.url)
    }
    return web.Response(text=json.dumps(ret), status=200)


if __name__ == '__main__':
    app = connexion.AioHttpApp(__name__)
    app.add_api('openapi.yaml', pass_context_arg_name='request')
    aio = app.app
    reverse_proxied = XPathForwarded()
    aio.middlewares.append(reverse_proxied.middleware)
    app.run(port=8080)
