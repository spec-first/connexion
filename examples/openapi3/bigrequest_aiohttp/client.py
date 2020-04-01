import asyncio
import aiohttp

async def run():
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.post(
                "http://localhost:8080/api/",
                json="1" * 20 * 1024 * 1024,
        ) as resp:
            print(await resp.text())

asyncio.run(run())
