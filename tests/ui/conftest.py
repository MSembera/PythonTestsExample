from collections.abc import Iterator

import pytest
from playwright.sync_api import Page, expect

from config.settings import settings
from tests.ui.pages.admin_login_page import AdminLoginPage


@pytest.fixture
def admin_page(page: Page) -> Page:
    AdminLoginPage(page).open().login(settings.admin_username, settings.admin_password)
    # The login POST is async; without waiting for it to settle, an immediate
    # page.goto() in a test (e.g. AdminRoomsPage.open()) cancels the in-flight
    # request and the browser never becomes authenticated. Waiting for the
    # post-login dashboard to render guarantees "already logged in" is true
    # before handing the page back.
    expect(page.get_by_role("button", name="Create")).to_be_visible()
    return page


@pytest.fixture
def booking_cleanup(page: Page) -> Iterator[dict]:
    # No UI can delete a booking, so teardown deletes it via page.request instead.
    registered: dict = {}

    yield registered

    if not registered:
        return

    login_response = page.request.post(
        f"{settings.base_url}/api/auth/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    token = login_response.json()["token"]
    page.context.add_cookies([{"name": "token", "value": token, "url": settings.base_url}])
    bookings = page.request.get(
        f"{settings.base_url}/api/booking", params={"roomid": registered["room_id"]}
    ).json()["bookings"]
    match = next(
        b
        for b in bookings
        if b["firstname"] == registered["firstname"] and b["lastname"] == registered["lastname"]
    )
    page.request.delete(f"{settings.base_url}/api/booking/{match['bookingid']}")
