from playwright.sync_api import Locator, Page

from config.settings import settings


class AdminLoginPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self) -> "AdminLoginPage":
        self.page.goto(f"{settings.base_url}/admin")
        return self

    def login(self, username: str, password: str) -> None:
        self.page.get_by_placeholder("Enter username").fill(username)
        self.page.get_by_placeholder("Password").fill(password)
        self.page.get_by_role("button", name="Login").click()

    def error_message(self) -> Locator:
        return self.page.get_by_text("Invalid credentials")
