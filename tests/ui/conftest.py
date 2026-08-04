from collections.abc import Iterator

import pytest
from playwright.sync_api import Page

from config.settings import settings


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
