import allure
import pytest
from playwright.sync_api import Page, expect

from config.settings import settings
from tests.ui.pages.admin_login_page import AdminLoginPage

pytestmark = [pytest.mark.ui, allure.feature("Admin Login")]


def test_login_with_valid_credentials_shows_the_rooms_page(page: Page) -> None:
    login_page = AdminLoginPage(page).open()

    login_page.login(settings.admin_username, settings.admin_password)

    expect(page.get_by_role("button", name="Create")).to_be_visible()


def test_login_with_invalid_credentials_shows_an_error(page: Page) -> None:
    login_page = AdminLoginPage(page).open()

    login_page.login(settings.admin_username, "not-the-password")

    expect(login_page.error_message()).to_be_visible()


def test_logout_returns_to_a_logged_out_state(admin_page: Page) -> None:
    login_page = AdminLoginPage(admin_page)

    login_page.logout()

    expect(admin_page.get_by_role("heading", name="Welcome to Shady Meadows B&B")).to_be_visible()

    AdminLoginPage(admin_page).open()

    expect(login_page.username_field()).to_be_visible()
