from collections.abc import Iterator

import pytest

from config.settings import settings
from tests.api.clients.auth_client import AuthClient
from tests.api.clients.booking_client import BookingClient
from tests.api.clients.room_client import RoomClient
from tests.api.factories.booking_factory import random_booking_payload
from tests.api.factories.room_factory import random_room_payload


@pytest.fixture(scope="session")
def admin_token() -> str:
    response = AuthClient().login(settings.admin_username, settings.admin_password)
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    assert isinstance(token, str) and token
    return token


@pytest.fixture
def room_client(admin_token: str) -> RoomClient:
    return RoomClient(token=admin_token)


@pytest.fixture
def anon_room_client() -> RoomClient:
    return RoomClient()


@pytest.fixture
def created_room(room_client: RoomClient) -> Iterator[dict]:
    payload = random_room_payload()
    room_client.create_room(payload)
    rooms = room_client.list_rooms().json()["rooms"]
    room = next(r for r in rooms if r["roomName"] == payload["roomName"])

    yield room

    room_client.delete_room(room["roomid"])


@pytest.fixture
def booking_client(admin_token: str) -> BookingClient:
    return BookingClient(token=admin_token)


@pytest.fixture
def anon_booking_client() -> BookingClient:
    return BookingClient()


@pytest.fixture
def created_booking(booking_client: BookingClient, created_room: dict) -> Iterator[dict]:
    payload = random_booking_payload(created_room["roomid"])
    booking = booking_client.create_booking(payload).json()

    yield booking

    booking_client.delete_booking(booking["bookingid"])
