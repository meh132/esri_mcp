import time
import httpx
from .config import config


class TokenManager:
    """Manages ArcGIS token lifecycle: generation, caching, and refresh."""

    _token: str | None = None
    _expires_at: float = 0.0  # epoch seconds

    async def get_token(self, client: httpx.AsyncClient) -> str | None:
        if not config.has_credentials:
            return None
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        await self._refresh(client)
        return self._token

    async def _refresh(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            config.token_url,
            data={
                "username": config.username,
                "password": config.password,
                "client": "requestip",
                "expiration": 60,  # minutes
                "f": "json",
            },
        )
        resp.raise_for_status()
        body = resp.json()
        if "error" in body:
            raise RuntimeError(f"Token generation failed: {body['error']['message']}")
        self._token = body["token"]
        # ESRI returns expiration in milliseconds since epoch
        self._expires_at = body["expires"] / 1000.0


token_manager = TokenManager()
