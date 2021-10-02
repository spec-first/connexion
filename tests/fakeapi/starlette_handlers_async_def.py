from connexion.lifecycle import ConnexionResponse


async def starlette_validate_responses():
    return ConnexionResponse(body=b'{"validate": true}')
