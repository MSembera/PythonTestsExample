from collections.abc import Iterator

import pytest
from faker import Faker
from playwright.sync_api import Page, expect

from config.settings import settings
from tests.ui.pages.admin_rooms_page import AdminRoomsPage

pytestmark = pytest.mark.ui

fake = Faker()


@pytest.fixture
def room_cleanup(page: Page) -> Iterator[list[int]]:
    room_ids: list[int] = []

    yield room_ids

    if not room_ids:
        return

    login_response = page.request.post(
        f"{settings.base_url}/api/auth/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    token = login_response.json()["token"]
    page.context.add_cookies([{"name": "token", "value": token, "url": settings.base_url}])
    for room_id in room_ids:
        page.request.delete(f"{settings.base_url}/api/room/{room_id}")


def _find_room_id_by_name(page: Page, room_name: str) -> int:
    rooms = page.request.get(f"{settings.base_url}/api/room").json()["rooms"]
    return int(next(r["roomid"] for r in rooms if r["roomName"] == room_name))


def test_creating_a_room_makes_it_appear_in_the_room_list(
    admin_page: Page, room_cleanup: list[int]
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

    expect(admin_page.locator(f"#roomName{room_name}")).to_be_visible()
    room_cleanup.append(_find_room_id_by_name(admin_page, room_name))


def test_editing_a_room_updates_its_details(admin_page: Page, room_cleanup: list[int]) -> None:
    room_name = str(fake.unique.random_int(min=500, max=99999))
    login_response = admin_page.request.post(
        f"{settings.base_url}/api/auth/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    token = login_response.json()["token"]
    admin_page.context.add_cookies([{"name": "token", "value": token, "url": settings.base_url}])
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
    room_cleanup.append(room_id)
    rooms_page = AdminRoomsPage(admin_page).open()

    rooms_page.open_room(room_name)
    rooms_page.click_edit()
    rooms_page.set_price(250)
    rooms_page.set_description("updated by an automated test")
    rooms_page.click_update()

    expect(admin_page.get_by_text("250")).to_be_visible()
    expect(admin_page.get_by_text("updated by an automated test")).to_be_visible()


def test_room_detail_page_shows_its_bookings(admin_page: Page, room_cleanup: list[int]) -> None:
    room_name = str(fake.unique.random_int(min=500, max=99999))
    login_response = admin_page.request.post(
        f"{settings.base_url}/api/auth/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    token = login_response.json()["token"]
    admin_page.context.add_cookies([{"name": "token", "value": token, "url": settings.base_url}])
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
    room_cleanup.append(room_id)
    admin_page.request.post(
        f"{settings.base_url}/api/booking",
        data={
            "roomid": room_id,
            "firstname": "Ada",
            "lastname": "Lovelace",
            "depositpaid": True,
            "bookingdates": {"checkin": "2028-05-01", "checkout": "2028-05-03"},
        },
    )
    rooms_page = AdminRoomsPage(admin_page).open()

    rooms_page.open_room(room_name)

    expect(admin_page.get_by_text("Ada")).to_be_visible()
    expect(admin_page.get_by_text("Lovelace")).to_be_visible()
