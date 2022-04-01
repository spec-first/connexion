from especifico.lifecycle import EspecificoResponse


async def aiohttp_validate_responses():
    return EspecificoResponse(body=b'{"validate": true}')
