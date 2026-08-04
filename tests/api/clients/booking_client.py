import httpx

from config.settings import settings


class BookingClient:
    def __init__(self, token: str | None = None) -> None:
        cookies = {"token": token} if token else {}
        self._http = httpx.Client(base_url=settings.base_url, cookies=cookies)

    def list_bookings(self, room_id: int) -> httpx.Response:
        return self._http.get("/api/booking", params={"roomid": room_id})

    def get_booking(self, booking_id: int) -> httpx.Response:
        return self._http.get(f"/api/booking/{booking_id}")

    def create_booking(self, payload: dict) -> httpx.Response:
        return self._http.post("/api/booking", json=payload)

    def update_booking(self, booking_id: int, payload: dict) -> httpx.Response:
        return self._http.put(f"/api/booking/{booking_id}", json=payload)

    def delete_booking(self, booking_id: int) -> httpx.Response:
        return self._http.delete(f"/api/booking/{booking_id}")
