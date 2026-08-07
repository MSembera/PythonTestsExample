import allure
import pytest

from config.settings import settings
from tests.api.clients.auth_client import AuthClient
from tests.api.models.auth import LoginResponse, ValidateResponse

pytestmark = [pytest.mark.api, allure.feature("Auth")]


def test_login_with_valid_credentials_returns_a_token() -> None:
    response = AuthClient().login(settings.admin_username, settings.admin_password)

    assert response.status_code == 200
    body = LoginResponse.model_validate(response.json())
    assert len(body.token) > 0


def test_login_with_invalid_credentials_is_rejected() -> None:
    response = AuthClient().login(settings.admin_username, "not-the-password")

    assert response.status_code == 401
    assert response.json() == {"error": "Invalid credentials"}


def test_validate_with_a_valid_token_returns_true(admin_token: str) -> None:
    response = AuthClient().validate(admin_token)

    assert response.status_code == 200
    assert ValidateResponse.model_validate(response.json()).valid is True


def test_validate_with_an_invalid_token_is_rejected() -> None:
    response = AuthClient().validate("not-a-real-token")

    assert response.status_code == 403


def test_logout_returns_success() -> None:
    # Logout doesn't actually invalidate the token (validate() still returns
    # 200 after) - a real app quirk, so this only asserts the logout call itself.
    auth_client = AuthClient()
    login_response = auth_client.login(settings.admin_username, settings.admin_password)
    token = LoginResponse.model_validate(login_response.json()).token

    logout_response = auth_client.logout(token)

    assert logout_response.status_code == 200
    assert logout_response.json() == {"success": True}
