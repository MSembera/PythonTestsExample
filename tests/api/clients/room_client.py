import httpx

from config.settings import settings


class RoomClient:
    def __init__(self, token: str | None = None) -> None:
        cookies = {"token": token} if token else {}
        self._http = httpx.Client(base_url=settings.base_url, cookies=cookies)

    def list_rooms(self) -> httpx.Response:
        return self._http.get("/api/room")

    def get_room(self, room_id: int) -> httpx.Response:
        return self._http.get(f"/api/room/{room_id}")

    def create_room(self, payload: dict) -> httpx.Response:
        return self._http.post("/api/room", json=payload)

    def update_room(self, room_id: int, payload: dict) -> httpx.Response:
        return self._http.put(f"/api/room/{room_id}", json=payload)

    def delete_room(self, room_id: int) -> httpx.Response:
        return self._http.delete(f"/api/room/{room_id}")
