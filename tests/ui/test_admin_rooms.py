import allure
import pytest
from faker import Faker
from playwright.sync_api import Page, expect

from config.settings import settings
from tests.ui.conftest import RoomCleanup
from tests.ui.pages.admin_rooms_page import AdminRoomsPage

pytestmark = [pytest.mark.ui, allure.feature("Admin Rooms")]

fake = Faker()


def _find_room_id_by_name(page: Page, room_name: str) -> int:
    rooms = page.request.get(f"{settings.base_url}/api/room").json()["rooms"]
    return int(next(r["roomid"] for r in rooms if r["roomName"] == room_name))


def test_creating_a_room_makes_it_appear_in_the_room_list(
    admin_page: Page, room_cleanup: RoomCleanup
) -> None:
    rooms_page = AdminRoomsPage(admin_page).open()
    room_name = str(fake.unique.random_int(min=500, max=99999))

    rooms_page.create_room(
        room_name=room_name,
        room_type="Suite",
        accessible=True,
        price=321,
        features=["WiFi", "Safe"],
    )

    try:
        expect(admin_page.locator(f"#roomName{room_name}")).to_be_visible()
    finally:
        room_cleanup.room_ids.append(_find_room_id_by_name(admin_page, room_name))


def test_editing_a_room_updates_its_details(admin_page: Page, room_cleanup: RoomCleanup) -> None:
    room_name = str(fake.unique.random_int(min=500, max=99999))
    # admin_page is already authenticated via a real UI form login
    admin_page.request.post(
        f"{settings.base_url}/api/room",
        data={
            "roomName": room_name,
            "type": "Single",
            "accessible": True,
            "roomPrice": 100,
            "description": "original description",
            "features": ["WiFi"],
        },
    )
    room_id = _find_room_id_by_name(admin_page, room_name)
    room_cleanup.room_ids.append(room_id)
    rooms_page = AdminRoomsPage(admin_page).open()

    rooms_page.open_room(room_name)
    rooms_page.click_edit()
    rooms_page.set_price(250)
    rooms_page.set_description("updated by an automated test")
    rooms_page.click_update()

    # /admin/room/{id} itself can keep showing pre-edit data for 30s+ after a
    # successful update - a confirmed app bug (see app-behavior-notes.md), not
    # something a longer wait fixes - so verify the edit through the API instead.
    updated_room = admin_page.request.get(f"{settings.base_url}/api/room/{room_id}").json()
    assert updated_room["roomPrice"] == 250
    assert updated_room["description"] == "updated by an automated test"


def test_room_detail_page_shows_its_bookings(admin_page: Page, room_cleanup: RoomCleanup) -> None:
    room_name = str(fake.unique.random_int(min=500, max=99999))
    # admin_page is already authenticated via a real UI form login
    admin_page.request.post(
        f"{settings.base_url}/api/room",
        data={
            "roomName": room_name,
            "type": "Single",
            "accessible": True,
            "roomPrice": 100,
            "description": "room for booking visibility test",
            "features": ["WiFi"],
        },
    )
    room_id = _find_room_id_by_name(admin_page, room_name)
    room_cleanup.room_ids.append(room_id)
    booking_response = admin_page.request.post(
        f"{settings.base_url}/api/booking",
        data={
            "roomid": room_id,
            "firstname": "Ada",
            "lastname": "Lovelace",
            "depositpaid": True,
            "bookingdates": {"checkin": "2028-05-01", "checkout": "2028-05-03"},
        },
    )

    room_cleanup.booking_ids.append(booking_response.json()["bookingid"])
    rooms_page = AdminRoomsPage(admin_page).open()

    rooms_page.open_room(room_name)

    expect(admin_page.get_by_text("Ada")).to_be_visible()
    expect(admin_page.get_by_text("Lovelace")).to_be_visible()
