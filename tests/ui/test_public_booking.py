import re

import allure
import pytest
from faker import Faker
from playwright.sync_api import Page, expect

from config.settings import settings
from tests.ui.conftest import RoomCleanup, authenticate_via_api
from tests.ui.pages.home_page import HomePage
from tests.ui.pages.reservation_page import ReservationPage

pytestmark = [pytest.mark.ui, allure.feature("Public Booking")]

fake = Faker()


def test_home_page_lists_the_available_rooms(page: Page) -> None:
    home = HomePage(page).open()

    expect(home.room_heading("Single")).to_be_visible()
    expect(home.room_heading("Double")).to_be_visible()
    expect(home.room_heading("Suite")).to_be_visible()
    expect(page.get_by_text("£100")).to_be_visible()


def test_booking_a_room_shows_a_confirmation(
    # Fixture teardown runs in reverse declaration order, so listing
    # room_cleanup before booking_cleanup here makes booking_cleanup's
    # teardown (deleting the booking) run before room_cleanup's (deleting
    # the room it belongs to) - the room should still exist when the
    # booking delete happens. Keep this order if either fixture list grows.
    page: Page,
    room_cleanup: RoomCleanup,
    booking_cleanup: dict,
) -> None:
    # Prove the home page's "Book now" link navigates to a reservation page
    # (test_home_page_lists_the_available_rooms already covers the room
    # listing itself) - without actually booking the shared seeded "Suite"
    # room, which risks colliding with a real visitor's booking on this
    # public demo. The actual booking below uses a disposable room instead.
    home = HomePage(page).open()
    book_now_link = home.book_now_link("Suite")
    expect(book_now_link).to_be_visible()
    book_now_link.click()
    expect(page).to_have_url(re.compile(r"/reservation/\d+"))

    # Create a disposable room via the API (same auth pattern as
    # tests/ui/test_admin_rooms.py) so the booking below can't collide with a
    # real visitor's data.
    authenticate_via_api(page)
    room_name = str(fake.unique.random_int(min=500, max=99999))
    page.request.post(
        f"{settings.base_url}/api/room",
        data={
            "roomName": room_name,
            # "Twin" is not one of the room types asserted on elsewhere in
            # this file (test_home_page_lists_the_available_rooms checks
            # "Single"/"Double"/"Suite" with exact=True, a strict-mode
            # locator that fails on more than one match) - using a
            # different type here avoids any chance of this disposable
            # room colliding with that assertion if both happen to exist
            # at the same moment.
            "type": "Twin",
            "accessible": True,
            "roomPrice": 225,
            "description": "disposable room for booking confirmation test",
            "features": ["WiFi"],
        },
    )
    rooms = page.request.get(f"{settings.base_url}/api/room").json()["rooms"]
    room_id = int(next(r["roomid"] for r in rooms if r["roomName"] == room_name))
    room_cleanup.room_ids.append(room_id)

    # Far-future dates on a disposable room - the sibling validation test
    # below already proves this /reservation/{id}?checkin=...&checkout=...
    # URL shape works.
    reservation = ReservationPage(page).open(
        room_id=room_id, checkin="2028-06-01", checkout="2028-06-03"
    )
    reservation.click_reserve_now()
    firstname, lastname = fake.first_name(), fake.last_name()
    # Registered for cleanup as soon as the identifying details are known -
    # before submitting the form - so a failed assertion below still leaves
    # this booking queued for teardown.
    booking_cleanup.update(room_id=room_id, firstname=firstname, lastname=lastname)
    reservation.fill_guest_details(firstname, lastname, fake.email(), "01234567890")
    reservation.click_reserve_now()

    expect(reservation.confirmation_heading()).to_be_visible()


def test_reserving_a_room_without_guest_details_shows_validation_errors(page: Page) -> None:
    reservation = ReservationPage(page).open(room_id=1, checkin="2028-06-01", checkout="2028-06-03")

    reservation.click_reserve_now()
    reservation.click_reserve_now()

    expect(reservation.firstname_required_error()).to_be_visible()
    expect(reservation.lastname_required_error()).to_be_visible()
