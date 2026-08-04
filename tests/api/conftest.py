import pytest

from config.settings import settings
from tests.api.clients.auth_client import AuthClient


@pytest.fixture(scope="session")
def admin_token() -> str:
    response = AuthClient().login(settings.admin_username, settings.admin_password)
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    assert isinstance(token, str) and token
    return token
