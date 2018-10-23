from connexion.lifecycle import ConnexionResponse


async def aiohttp_validate_responses():
    return ConnexionResponse(body=b'{"validate": true}')
