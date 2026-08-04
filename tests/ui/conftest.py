from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from playwright.sync_api import Page, expect

from config.settings import settings
from tests.ui.pages.admin_login_page import AdminLoginPage


def authenticate_via_api(page: Page) -> None:
    """Log in through the API and add the resulting token as a cookie.

    The login endpoint returns the token only in the JSON body, not as a
    Set-Cookie header, when called via page.request (not the login form) -
    add it to the browser context's cookie jar ourselves so later
    page.request calls in the same test/fixture are authenticated. Verified
    live on 2026-08-04 during Task 5.
    """
    login_response = page.request.post(
        f"{settings.base_url}/api/auth/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    token = login_response.json()["token"]
    page.context.add_cookies([{"name": "token", "value": token, "url": settings.base_url}])


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

    authenticate_via_api(page)
    bookings = page.request.get(
        f"{settings.base_url}/api/booking", params={"roomid": registered["room_id"]}
    ).json()["bookings"]
    match = next(
        b
        for b in bookings
        if b["firstname"] == registered["firstname"] and b["lastname"] == registered["lastname"]
    )
    page.request.delete(f"{settings.base_url}/api/booking/{match['bookingid']}")


@dataclass
class RoomCleanup:
    """UI-suite-wide cleanup collector for rooms and their bookings.

    There is no admin UI path to delete a room or a booking (see the plan's
    "Known facts" section), so teardown reaches the API directly through
    page.request, which shares the browser context's cookies. Bookings are
    deleted before their room since a room's DELETE cascading to its bookings
    is undocumented/unverified - deleting explicitly here doesn't rely on it.
    """

    room_ids: list[int] = field(default_factory=list)
    booking_ids: list[int] = field(default_factory=list)


@pytest.fixture
def room_cleanup(page: Page) -> Iterator[RoomCleanup]:
    cleanup = RoomCleanup()

    yield cleanup

    if not cleanup.room_ids and not cleanup.booking_ids:
        return

    authenticate_via_api(page)
    for booking_id in cleanup.booking_ids:
        page.request.delete(f"{settings.base_url}/api/booking/{booking_id}")
    for room_id in cleanup.room_ids:
        page.request.delete(f"{settings.base_url}/api/room/{room_id}")
