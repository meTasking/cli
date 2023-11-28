import aiohttp

from .base import handle_response, API_VERSION


async def delete(
    server: str,
    record_id: int,
    **kwargs,
) -> dict:
    url = f"{server}/api/{API_VERSION}/record/{record_id}"
    async with aiohttp.ClientSession() as session:
        async with session.delete(url, json=kwargs) as response:
            return await handle_response(response)
