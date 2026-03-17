from pathlib import Path
from urllib.parse import urlparse

import httpx


async def download_to_tmp(url: str, session_name: str) -> str:
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix or ".bin"
    target = Path("/tmp") / f"{session_name}_{abs(hash(url))}{ext}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url)
        response.raise_for_status()
        target.write_bytes(response.content)
    return str(target)
