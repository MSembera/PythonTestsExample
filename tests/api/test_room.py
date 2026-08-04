import pytest

from tests.api.clients.room_client import RoomClient
from tests.api.factories.room_factory import random_room_payload
from tests.api.models.room import Room, RoomList

pytestmark = pytest.mark.api


def test_create_room_is_visible_in_the_room_list(room_client: RoomClient) -> None:
    payload = random_room_payload()

    create_response = room_client.create_room(payload)
    room_list = RoomList.model_validate(room_client.list_rooms().json())
    created = next(r for r in room_list.rooms if r.roomName == payload["roomName"])

    assert create_response.status_code == 200
    assert create_response.json() == {"success": True}
    assert created.type == payload["type"]
    assert created.accessible == payload["accessible"]
    assert created.roomPrice == payload["roomPrice"]
    assert created.description == payload["description"]
    assert sorted(created.features) == sorted(payload["features"])

    room_client.delete_room(created.roomid)


def test_create_room_without_authentication_is_rejected(anon_room_client: RoomClient) -> None:
    response = anon_room_client.create_room(random_room_payload())

    assert response.status_code == 401
    assert response.json() == {"errors": ["Authentication required"]}


def test_get_room_by_id_returns_its_details(created_room: dict, room_client: RoomClient) -> None:
    response = room_client.get_room(created_room["roomid"])

    assert response.status_code == 200
    room = Room.model_validate(response.json())
    assert room.roomid == created_room["roomid"]
    assert room.roomName == created_room["roomName"]


def test_get_room_with_an_unknown_id_returns_server_error(room_client: RoomClient) -> None:
    # Known quirk of this demo API: an unknown room id returns 500, not 404.
    response = room_client.get_room(999999)

    assert response.status_code == 500


def test_update_room_changes_its_fields(created_room: dict, room_client: RoomClient) -> None:
    updated_payload = {
        "roomName": created_room["roomName"],
        "type": "Suite",
        "accessible": not created_room["accessible"],
        "roomPrice": created_room["roomPrice"] + 50,
        "description": "Updated by an automated test",
        "features": ["Views"],
    }

    response = room_client.update_room(created_room["roomid"], updated_payload)

    assert response.status_code == 202
    body = response.json()
    assert body["type"] == "Suite"
    assert body["roomPrice"] == created_room["roomPrice"] + 50
    assert body["description"] == "Updated by an automated test"
    assert body["features"] == ["Views"]


def test_update_room_without_authentication_is_rejected(
    created_room: dict, anon_room_client: RoomClient
) -> None:
    response = anon_room_client.update_room(created_room["roomid"], random_room_payload())

    assert response.status_code == 403


def test_delete_room_removes_it_from_the_room_list(room_client: RoomClient) -> None:
    payload = random_room_payload()
    room_client.create_room(payload)
    rooms = room_client.list_rooms().json()["rooms"]
    created = next(r for r in rooms if r["roomName"] == payload["roomName"])

    delete_response = room_client.delete_room(created["roomid"])
    rooms_after_delete = room_client.list_rooms().json()["rooms"]

    assert delete_response.status_code == 202
    assert all(r["roomid"] != created["roomid"] for r in rooms_after_delete)


def test_delete_room_without_authentication_is_rejected(
    created_room: dict, anon_room_client: RoomClient
) -> None:
    response = anon_room_client.delete_room(created_room["roomid"])

    assert response.status_code == 403
