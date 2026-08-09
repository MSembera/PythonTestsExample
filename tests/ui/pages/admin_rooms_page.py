import allure
from playwright.sync_api import Page

from config.settings import settings

CREATE_FORM_FEATURE_CHECKBOX_IDS = {
    "WiFi": "wifiCheckbox",
    "TV": "tvCheckbox",
    "Radio": "radioCheckbox",
    "Refreshments": "refreshCheckbox",
    "Safe": "safeCheckbox",
    "Views": "viewsCheckbox",
}


class AdminRoomsPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self) -> "AdminRoomsPage":
        self.page.goto(f"{settings.base_url}/admin/rooms")
        return self

    def create_room(
        self, room_name: str, room_type: str, accessible: bool, price: int, features: list[str]
    ) -> None:
        with allure.step(f"Create room '{room_name}' via the admin rooms form"):
            self.page.locator("#roomName").fill(room_name)
            self.page.locator("#type").select_option(room_type)
            self.page.locator("#accessible").select_option("true" if accessible else "false")
            self.page.locator("#roomPrice").fill(str(price))
            for feature in features:
                self.page.locator(f"#{CREATE_FORM_FEATURE_CHECKBOX_IDS[feature]}").check()
            self.page.get_by_role("button", name="Create").click()

    def open_room(self, room_name: str) -> None:
        self.page.locator(f"#roomName{room_name}").click()

    def click_edit(self) -> None:
        self.page.get_by_role("button", name="Edit").click()

    def set_price(self, price: int) -> None:
        self.page.locator("#roomPrice").fill(str(price))

    def set_description(self, description: str) -> None:
        self.page.locator("#description").fill(description)

    def click_update(self) -> None:
        # A plain click doesn't wait for the PUT it triggers to actually land -
        # a caller checking the result (even via the API) right after this
        # returns can race ahead of the request. Wait for the real response.
        with allure.step("Submit the room edit form"):
            with self.page.expect_response(
                lambda r: "/api/room/" in r.url and r.request.method == "PUT"
            ):
                self.page.locator("#update").click()

