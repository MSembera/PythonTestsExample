import pytest
from playwright.sync_api import Page, expect

from config.settings import settings
from tests.ui.pages.admin_login_page import AdminLoginPage

pytestmark = pytest.mark.ui


def test_login_with_valid_credentials_shows_the_rooms_page(page: Page) -> None:
    login_page = AdminLoginPage(page).open()

    login_page.login(settings.admin_username, settings.admin_password)

    expect(page.get_by_role("button", name="Create")).to_be_visible()


def test_login_with_invalid_credentials_shows_an_error(page: Page) -> None:
    login_page = AdminLoginPage(page).open()

    login_page.login(settings.admin_username, "not-the-password")

    expect(login_page.error_message()).to_be_visible()
