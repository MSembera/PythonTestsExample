import httpx

from config.settings import settings


class AuthClient:
    def __init__(self) -> None:
        self._http = httpx.Client(base_url=settings.base_url)

    def login(self, username: str, password: str) -> httpx.Response:
        return self._http.post("/api/auth/login", json={"username": username, "password": password})

    def validate(self, token: str) -> httpx.Response:
        return self._http.post("/api/auth/validate", json={"token": token})

    def logout(self, token: str) -> httpx.Response:
        return self._http.post("/api/auth/logout", json={"token": token})
