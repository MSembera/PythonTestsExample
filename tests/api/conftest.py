import time
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
    with AuthClient() as auth_client:
        response = auth_client.login(settings.admin_username, settings.admin_password)
        assert response.status_code == 200, response.text
        token = response.json()["token"]
        assert isinstance(token, str) and token
        return token


@pytest.fixture
def room_client(admin_token: str) -> Iterator[RoomClient]:
    with RoomClient(token=admin_token) as client:
        yield client


@pytest.fixture
def anon_room_client() -> Iterator[RoomClient]:
    with RoomClient() as client:
        yield client


@pytest.fixture
def created_room(room_client: RoomClient) -> Iterator[dict]:
    payload = random_room_payload()
    create_response = room_client.create_room(payload)
    assert create_response.status_code == 200, create_response.text

    # POST /api/room doesn't return the created room (see app-behavior-notes.md),
    # so it has to be found by re-listing - on this shared public demo that can
    # lag behind the create, so retry a few times before giving up for real.
    room = None
    for attempt in range(5):
        rooms = room_client.list_rooms().json()["rooms"]
        room = next((r for r in rooms if r["roomName"] == payload["roomName"]), None)
        if room is not None:
            break
        if attempt < 4:
            time.sleep(5)
    assert room is not None, f"Room {payload['roomName']!r} not found after 5 attempts"

    yield room

    room_client.delete_room(room["roomid"])


@pytest.fixture
def booking_client(admin_token: str) -> Iterator[BookingClient]:
    with BookingClient(token=admin_token) as client:
        yield client


@pytest.fixture
def anon_booking_client() -> Iterator[BookingClient]:
    with BookingClient() as client:
        yield client


@pytest.fixture
def created_booking(booking_client: BookingClient, created_room: dict) -> Iterator[dict]:
    payload = random_booking_payload(created_room["roomid"])
    create_response = booking_client.create_booking(payload)
    assert create_response.status_code == 201, create_response.text
    booking = create_response.json()

    yield booking

    booking_client.delete_booking(booking["bookingid"])
