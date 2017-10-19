import asyncio
import functools


def get_wrapper(function, _wrapper):
    @functools.wraps(function)
    def wrapper(request):
        response = yield from function(request)
        return _wrapper(request, response)

    return asyncio.coroutine(wrapper)
