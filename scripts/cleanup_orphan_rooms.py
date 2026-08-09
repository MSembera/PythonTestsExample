"""Delete stray rooms (and their bookings) left behind by a hard-killed test run.

Manual/scheduled maintenance, not part of the test suite: a room is only
ever deleted if its roomName matches the pattern every room-creation call
site in this repo uses (see is_orphan_room_name) - anything else, including
the seeded 101/102/103, is left alone.
"""

from config.settings import settings
from tests.api.clients.auth_client import AuthClient
from tests.api.clients.booking_client import BookingClient
from tests.api.clients.room_client import RoomClient


def is_orphan_room_name(room_name: str) -> bool:
    return room_name.isdigit() and 500 <= int(room_name) <= 99999


def main() -> int:
    with AuthClient() as auth_client:
        login_response = auth_client.login(settings.admin_username, settings.admin_password)
        token = login_response.json()["token"]

    with RoomClient(token=token) as room_client, BookingClient(token=token) as booking_client:
        rooms = room_client.list_rooms().json()["rooms"]
        orphans = [r for r in rooms if is_orphan_room_name(r["roomName"])]

        if not orphans:
            print("No orphan rooms found.")
            return 0

        for room in orphans:
            bookings = booking_client.list_bookings(room["roomid"]).json()["bookings"]
            for booking in bookings:
                booking_client.delete_booking(booking["bookingid"])
            room_client.delete_room(room["roomid"])
            print(
                f"Deleted room {room['roomid']} ({room['roomName']!r}) "
                f"and {len(bookings)} booking(s)."
            )

    print(f"Cleaned up {len(orphans)} orphan room(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
