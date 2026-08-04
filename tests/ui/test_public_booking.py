import re

import pytest
from faker import Faker
from playwright.sync_api import Page, expect

from tests.ui.pages.home_page import HomePage
from tests.ui.pages.reservation_page import ReservationPage

pytestmark = pytest.mark.ui

fake = Faker()


def test_home_page_lists_the_available_rooms(page: Page) -> None:
    home = HomePage(page).open()

    expect(home.room_heading("Single")).to_be_visible()
    expect(home.room_heading("Double")).to_be_visible()
    expect(home.room_heading("Suite")).to_be_visible()
    expect(page.get_by_text("£100")).to_be_visible()


def test_booking_a_room_shows_a_confirmation(page: Page, booking_cleanup: dict) -> None:
    home = HomePage(page).open()
    book_now_link = home.book_now_link("Suite")
    href = book_now_link.get_attribute("href")
    assert href is not None
    room_id = int(re.search(r"/reservation/(\d+)", href).group(1))  # type: ignore[union-attr]

    book_now_link.click()
    reservation = ReservationPage(page)
    reservation.click_reserve_now()
    firstname, lastname = fake.first_name(), fake.last_name()
    reservation.fill_guest_details(firstname, lastname, fake.email(), "01234567890")
    reservation.click_reserve_now()

    expect(reservation.confirmation_heading()).to_be_visible()
    booking_cleanup.update(room_id=room_id, firstname=firstname, lastname=lastname)


def test_reserving_a_room_without_guest_details_shows_validation_errors(page: Page) -> None:
    reservation = ReservationPage(page).open(room_id=1, checkin="2028-06-01", checkout="2028-06-03")

    reservation.click_reserve_now()
    reservation.click_reserve_now()

    expect(reservation.firstname_required_error()).to_be_visible()
    expect(reservation.lastname_required_error()).to_be_visible()
