import allure
import pytest

from tests.api.clients.booking_client import BookingClient
from tests.api.factories.booking_factory import random_booking_payload
from tests.api.models.booking import Booking, BookingList

pytestmark = [pytest.mark.api, allure.feature("Booking")]


def test_create_booking_is_persisted(
    created_room: dict, anon_booking_client: BookingClient, booking_client: BookingClient
) -> None:
    payload = random_booking_payload(created_room["roomid"])

    response = anon_booking_client.create_booking(payload)
    response_body = response.json()
    created_bookingid = response_body.get("bookingid")

    try:
        assert response.status_code == 201
        body = Booking.model_validate(response_body)
        assert body.roomid == created_room["roomid"]
        assert body.firstname == payload["firstname"]
        assert body.lastname == payload["lastname"]
        assert body.bookingdates.model_dump() == payload["bookingdates"]
    finally:
        # Delete requires auth even though create is anonymous; guard against a
        # totally failed create (no bookingid) so cleanup never crashes.
        if created_bookingid is not None:
            booking_client.delete_booking(created_bookingid)


def test_create_booking_with_missing_lastname_is_rejected(
    created_room: dict, anon_booking_client: BookingClient
) -> None:
    payload = random_booking_payload(created_room["roomid"])
    del payload["lastname"]

    response = anon_booking_client.create_booking(payload)

    assert response.status_code == 400
    assert "Lastname" in response.json()["errors"][0]


def test_create_booking_with_checkout_before_checkin_is_rejected(
    created_room: dict, anon_booking_client: BookingClient
) -> None:
    payload = random_booking_payload(created_room["roomid"])
    payload["bookingdates"] = {"checkin": "2027-09-10", "checkout": "2027-09-05"}

    response = anon_booking_client.create_booking(payload)

    assert response.status_code == 409


def test_get_booking_by_id_returns_its_details(
    created_booking: dict, booking_client: BookingClient
) -> None:
    response = booking_client.get_booking(created_booking["bookingid"])

    assert response.status_code == 200
    assert Booking.model_validate(response.json()).bookingid == created_booking["bookingid"]


def test_get_booking_with_an_unknown_id_returns_not_found(booking_client: BookingClient) -> None:
    response = booking_client.get_booking(999999)

    assert response.status_code == 404


def test_list_bookings_for_a_room_includes_the_created_booking(
    created_booking: dict, created_room: dict, booking_client: BookingClient
) -> None:
    response = booking_client.list_bookings(created_room["roomid"])

    assert response.status_code == 200
    booking_list = BookingList.model_validate(response.json())
    assert any(b.bookingid == created_booking["bookingid"] for b in booking_list.bookings)


def test_list_bookings_without_a_room_id_is_rejected(booking_client: BookingClient) -> None:
    # list_bookings() always supplies roomid, so this negative case (missing
    # roomid, once authenticated) needs a dedicated client method.
    response = booking_client.list_bookings_without_room_id()

    assert response.status_code == 400
    assert response.json() == {"error": "Room ID is required"}


def test_update_booking_changes_its_fields(
    created_booking: dict, created_room: dict, booking_client: BookingClient
) -> None:
    new_dates = {"checkin": "2028-01-10", "checkout": "2028-01-12"}
    updated_payload = {
        "roomid": created_room["roomid"],
        "firstname": "Updated",
        "lastname": created_booking["lastname"],
        "depositpaid": created_booking["depositpaid"],
        "bookingdates": new_dates,
    }

    response = booking_client.update_booking(created_booking["bookingid"], updated_payload)

    assert response.status_code == 200
    assert response.json()["booking"]["firstname"] == "Updated"
    assert response.json()["booking"]["bookingdates"] == new_dates


def test_update_booking_without_authentication_is_rejected(
    created_booking: dict, created_room: dict, anon_booking_client: BookingClient
) -> None:
    updated_payload = {
        "roomid": created_room["roomid"],
        "firstname": "Hacked",
        "lastname": created_booking["lastname"],
        "depositpaid": created_booking["depositpaid"],
        "bookingdates": {"checkin": "2028-02-10", "checkout": "2028-02-12"},
    }

    response = anon_booking_client.update_booking(created_booking["bookingid"], updated_payload)

    assert response.status_code == 403


def test_delete_booking_removes_it(
    created_room: dict, anon_booking_client: BookingClient, booking_client: BookingClient
) -> None:
    payload = random_booking_payload(created_room["roomid"])
    booking = anon_booking_client.create_booking(payload).json()

    delete_response = booking_client.delete_booking(booking["bookingid"])
    get_after_delete = booking_client.get_booking(booking["bookingid"])

    assert delete_response.status_code == 202
    assert get_after_delete.status_code == 404


def test_delete_booking_without_authentication_is_rejected(
    created_booking: dict, anon_booking_client: BookingClient
) -> None:
    response = anon_booking_client.delete_booking(created_booking["bookingid"])

    assert response.status_code == 403
