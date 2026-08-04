from playwright.sync_api import Locator, Page

from config.settings import settings


class ReservationPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self, room_id: int, checkin: str, checkout: str) -> "ReservationPage":
        self.page.goto(f"{settings.base_url}/reservation/{room_id}?checkin={checkin}&checkout={checkout}")
        return self

    def click_reserve_now(self) -> None:
        self.page.get_by_role("button", name="Reserve Now").click()

    def fill_guest_details(self, firstname: str, lastname: str, email: str, phone: str) -> None:
        self.page.get_by_placeholder("Firstname").fill(firstname)
        self.page.get_by_placeholder("Lastname").fill(lastname)
        self.page.get_by_placeholder("Email").fill(email)
        self.page.get_by_placeholder("Phone").fill(phone)

    def confirmation_heading(self) -> Locator:
        return self.page.get_by_role("heading", name="Booking Confirmed")

    def firstname_required_error(self) -> Locator:
        return self.page.get_by_text("Firstname should not be blank")

    def lastname_required_error(self) -> Locator:
        return self.page.get_by_text("Lastname should not be blank")
