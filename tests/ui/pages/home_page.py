from playwright.sync_api import Locator, Page

from config.settings import settings


class HomePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self) -> "HomePage":
        self.page.goto(settings.base_url)
        return self

    def room_heading(self, room_type: str) -> Locator:
        return self.page.get_by_role("heading", name=room_type, exact=True)

    def book_now_link(self, room_type: str) -> Locator:
        heading = self.room_heading(room_type)
        return heading.locator("xpath=following::a[normalize-space(text())='Book now'][1]")
