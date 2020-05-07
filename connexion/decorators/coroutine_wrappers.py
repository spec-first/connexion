import asyncio
import functools


def get_request_life_cycle_wrapper(function, api, mimetype):
    """
    It is a wrapper used on `RequestResponseDecorator` class.
    This function is located in an extra module because python2.7 don't
    support the 'yield from' syntax. This function is used to await
    the coroutines to connexion does the proper validation of parameters
    and responses.

    :rtype asyncio.coroutine
    """
    @functools.wraps(function)
    async def wrapper(*args, **kwargs):
        connexion_request = api.get_request(*args, **kwargs)
        while asyncio.iscoroutine(connexion_request):
            connexion_request = await connexion_request

        connexion_response = function(connexion_request)
        while asyncio.iscoroutine(connexion_response):
            connexion_response = await connexion_response

        framework_response = api.get_response(connexion_response, mimetype,
                                              connexion_request)
        while asyncio.iscoroutine(framework_response):
            framework_response = await framework_response

        return framework_response

    return wrapper


def get_response_validator_wrapper(function, _wrapper):
    """
    It is a wrapper used on `ResponseValidator` class.
    This function is located in an extra module because python2.7 don't
    support the 'yield from' syntax. This function is used to await
    the coroutines to connexion does the proper validation of parameters
    and responses.

    :rtype asyncio.coroutine
    """
    @functools.wraps(function)
    async def wrapper(request):
        response = function(request)
        while asyncio.iscoroutine(response):
            response = await response

        return _wrapper(request, response)

    return wrapper
