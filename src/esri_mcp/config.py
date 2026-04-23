import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    server_url: str
    username: str | None
    password: str | None

    def __init__(self) -> None:
        self._server_url = os.getenv("ESRI_SERVER_URL", "https://boston.maps.arcgis.com").rstrip("/")
        self.username = os.getenv("ESRI_USERNAME") or None
        self.password = os.getenv("ESRI_PASSWORD") or None
        self.host = os.getenv("MCP_HOST", "0.0.0.0")
        self.port = int(os.getenv("MCP_PORT", "8000"))
        self.ssl_certfile = os.getenv("MCP_SSL_CERTFILE") or None
        self.ssl_keyfile = os.getenv("MCP_SSL_KEYFILE") or None

    @property
    def ssl_enabled(self) -> bool:
        return bool(self.ssl_certfile and self.ssl_keyfile)

    @property
    def server_url(self) -> str:
        if not self._server_url:
            raise ValueError("ESRI_SERVER_URL environment variable is required")
        return self._server_url

    @property
    def has_credentials(self) -> bool:
        return bool(self.username and self.password)

    @property
    def token_url(self) -> str:
        return f"{self.server_url}/sharing/rest/generateToken"

    @property
    def portal_search_url(self) -> str:
        return f"{self.server_url}/sharing/rest/search"


config = Config()
