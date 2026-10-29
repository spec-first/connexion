import asyncio
from pathlib import Path
from typing import AsyncIterator

from connexion import AsyncApp
from starlette.responses import StreamingResponse


async def stream_handler() -> StreamingResponse:
    async def event_source() -> AsyncIterator[str]:
        for idx in range(3):
            await asyncio.sleep(1)
            yield f"event: tick\ndata: {idx}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


app = AsyncApp(__name__, specification_dir="spec")
app.add_api("openapi.yaml", arguments={"title": "Connexion Streaming Demo"})


if __name__ == "__main__":
    app.run(f"{Path(__file__).stem}:app", port=8080)
