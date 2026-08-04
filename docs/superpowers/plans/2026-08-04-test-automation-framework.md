# Test Automation Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a portfolio-quality automated test suite (pytest + httpx for API, pytest-playwright for UI) covering the Auth/Room/Booking API and the public + admin UI of https://automationintesting.online/, with Allure reporting, Ruff/mypy quality tooling, and a uv-managed project.

**Architecture:** Two independent test suites (`tests/api`, `tests/ui`) sharing only a `config/settings.py` module. API tests use `httpx` clients wrapping the REST API, validated against real response shapes captured from the live app. UI tests use `pytest-playwright` with a Page Object Model. Every test creates its own disposable data (Faker) and tears it down; since the app has no UI to delete a room or a booking, teardown for UI tests uses Playwright's `page.request` (which shares the browser's cookies) to call the API directly, keeping `tests/ui` free of any import from `tests/api`.

**Tech Stack:** Python 3.12+, uv, pytest, httpx, pydantic / pydantic-settings, Faker, pytest-playwright, allure-pytest, ruff, mypy.

## Global Constraints

- Package/env management: `uv` (not pip/poetry) — every command below is `uv run ...`.
- Test runner: `pytest`, with two custom markers, `api` and `ui`, registered in `pyproject.toml` so each suite can run independently (`uv run pytest -m api`, `uv run pytest -m ui`).
- No CI/CD in this plan — explicitly deferred per the spec.
- Base URL: `https://automationintesting.online` (public shared demo — see "Known facts about the real app" below for real, verified behavior; do not assume undocumented REST conventions).
- Admin credentials for this demo: username `admin`, password `password` (публично known/intended demo credentials for this training site — safe to ship as defaults in `.env.example`).
- All code must pass `uv run ruff check .` and `uv run mypy .` before a task is considered done.
- Every test file must carry `pytestmark = pytest.mark.api` or `pytestmark = pytest.mark.ui`.

## Known facts about the real app (verified live on 2026-08-04 — do not deviate from these)

**Auth (`/api/auth`):**
- `POST /api/auth/login` `{"username", "password"}` → `200 {"token": "<str>"}` on success; `401 {"error": "Invalid credentials"}` on failure.
- `POST /api/auth/validate` `{"token"}` → `200 {"valid": true}` if valid; `403 {"error": "Invalid token"}` if invalid.
- `POST /api/auth/logout` `{"token"}` → `200 {"success": true}`.
- Auth is a cookie named `token` (not httpOnly). For `httpx`, set it directly via `cookies={"token": <value>}` on the client — no `Authorization` header is used.

**Room (`/api/room`):**
- `GET /api/room` → `200 {"rooms": [{roomid, roomName, type, accessible, description, features: [...], roomPrice, image?}]}`.
- `GET /api/room/{id}` → `200 <room>`; **unknown id returns `500` (not 404) — a known quirk of this demo, assert it as-is.**
- `POST /api/room` (auth required) → `200 {"success": true}` — does **not** return the created room; re-`GET /api/room` and match by `roomName` to find the new `roomid`. No auth → `401 {"errors": ["Authentication required"]}`.
- `PUT /api/room/{id}` (auth required) → `202 <updated room>`. No auth → `403` (empty body).
- `DELETE /api/room/{id}` (auth required) → `202` (empty body). No auth → `403` (empty body).
- Room fields: `roomName: str`, `type: str` (`Single`/`Twin`/`Double`/`Family`/`Suite`), `accessible: bool`, `roomPrice: int`, `description: str`, `features: list[str]` (subset of `WiFi`/`TV`/`Radio`/`Refreshments`/`Safe`/`Views`).

**Booking (`/api/booking`):**
- `GET /api/booking?roomid={id}` → `200 {"bookings": [{bookingid, roomid, firstname, lastname, depositpaid, bookingdates: {checkin, checkout}}]}`. **`roomid` query param is required** — omitting it returns `400 {"error": "Room ID is required"}`.
- `GET /api/booking/{id}` → `200 <booking>`; unknown id → `404` (empty body, this one *does* 404 correctly).
- `POST /api/booking` (**no auth required — public**) `{"roomid", "firstname", "lastname", "depositpaid", "bookingdates": {"checkin", "checkout"}}` → `201 <created booking incl. bookingid>`. Missing required field (e.g. `lastname`) → `400 {"errors": ["Lastname should not be blank"]}`. `checkout` before `checkin` → `409 {"error": "Failed to create booking"}`.
- `PUT /api/booking/{id}` (auth required) → `200 {"booking": {...}, "bookingid": id}`. No auth → `403` (empty body). Overlapping dates with an existing booking on that room (including the booking's own current dates) → `409` (empty body) — always pick genuinely free dates when updating.
- `DELETE /api/booking/{id}` (auth required) → `202`. No auth → `403` (empty body).

**UI — public site:**
- Home page room cards: heading text `Single` / `Double` / `Suite`, price text `£100` / `£150` / `£225`, each followed (in document order) by a `Book now` link (`role=link`, no unique id/class) that navigates to `/reservation/{roomid}?checkin=...&checkout=...`.
- Reservation page (`/reservation/{roomid}?checkin=YYYY-MM-DD&checkout=YYYY-MM-DD`): a `Reserve Now` button (`role=button`) reveals a guest-details form (`Firstname`/`Lastname`/`Email`/`Phone`, all identified by **placeholder text**, no labels). Clicking `Reserve Now` again submits.
- On success: heading `Booking Confirmed`, text `Your booking has been confirmed for the following dates:`, and the `checkin - checkout` date range is shown.
- On validation failure (empty required fields): inline text `Firstname should not be blank` and `Lastname should not be blank` appear (there are more messages for phone/email but these two are the stable, reliable ones to assert on).

**UI — admin panel (`/admin`):**
- **The app has no persisted client-side session.** A full page navigation (not in-SPA routing) always shows the login form again, even though the `token` cookie may still be valid for API calls. Every UI test must perform a real login through the form — never assume a previous login carries over.
- Login form: username input via placeholder `Enter username`, password input via placeholder `Password`, submit button `role=button name="Login"`. Wrong credentials → visible text `Invalid credentials`.
- Rooms list (`/admin/rooms`): each room row's number is `<p id="roomName{roomNumber}">` (e.g. `#roomName101`) inside a clickable `.row.detail` — clicking `#roomName{roomNumber}` navigates to that room's detail page.
- Create-room form (bottom of `/admin/rooms`, **no `<form>` wrapper, no accessible names — use CSS ids**): `#roomName` (text), `#type` (select: `Single`/`Twin`/`Double`/`Family`/`Suite`), `#accessible` (select: `false`/`true`), `#roomPrice` (text), feature checkboxes `#wifiCheckbox` / `#tvCheckbox` / `#radioCheckbox` / `#refreshCheckbox` / `#safeCheckbox` / `#viewsCheckbox`, submit button `role=button name="Create"`.
- Room detail page: `<h2>Room: {roomNumber}</h2>`, an `Edit` button (`role=button`), and below it a **read-only** list of that room's bookings (first name / last name / price / deposit paid / check in / check out as plain text — no table markup, no delete control).
- Edit form (after clicking `Edit`, **different ids than the create form** — note `refreshmentsCheckbox` here vs `refreshCheckbox` on create): `#roomName`, `#type`, `#accessible`, `#roomPrice`, `#description` (textarea), `#wifiCheckbox` / `#tvCheckbox` / `#radioCheckbox` / `#refreshmentsCheckbox` / `#safeCheckbox` / `#viewsCheckbox`, `#image`, buttons `#cancelEdit` (text `Cancel`) and `#update` (text `Update`).
- **There is no delete control anywhere in the admin UI**, for either a room or a booking. Deleting is only possible via the API. UI-test cleanup therefore uses Playwright's `page.request` (shares the browser context's cookies, so it reuses whatever admin session the test already logged into).

---

## File Structure

```
PythonTestsExample/
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── config/
│   ├── __init__.py
│   └── settings.py
└── tests/
    ├── __init__.py
    ├── api/
    │   ├── __init__.py
    │   ├── conftest.py
    │   ├── clients/
    │   │   ├── __init__.py
    │   │   ├── auth_client.py
    │   │   ├── room_client.py
    │   │   └── booking_client.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── auth.py
    │   │   ├── room.py
    │   │   └── booking.py
    │   ├── factories/
    │   │   ├── __init__.py
    │   │   ├── room_factory.py
    │   │   └── booking_factory.py
    │   ├── test_auth.py
    │   ├── test_room.py
    │   └── test_booking.py
    └── ui/
        ├── __init__.py
        ├── conftest.py
        ├── pages/
        │   ├── __init__.py
        │   ├── home_page.py
        │   ├── reservation_page.py
        │   ├── admin_login_page.py
        │   └── admin_rooms_page.py
        ├── test_public_booking.py
        ├── test_admin_login.py
        └── test_admin_rooms.py
```

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `config/__init__.py`
- Create: `config/settings.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: `config.settings.settings` — a `Settings` instance with attributes `base_url: str`, `admin_username: str`, `admin_password: str`. Every later task imports this.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "python-tests-example"
version = "0.1.0"
description = "Automated API + UI test suite for the Restful Booker Platform demo (portfolio project)."
requires-python = ">=3.12"
dependencies = [
    "pytest>=8.3",
    "pytest-playwright>=0.5",
    "httpx>=0.27",
    "pydantic>=2.9",
    "pydantic-settings>=2.5",
    "faker>=30.0",
    "allure-pytest>=2.13",
]

[dependency-groups]
dev = [
    "ruff>=0.7",
    "mypy>=1.13",
]

[tool.pytest.ini_options]
minversion = "8.0"
addopts = "--alluredir=allure-results"
markers = [
    "api: API tests against the Restful Booker Platform REST API",
    "ui: UI tests against the Restful Booker Platform website (Playwright)",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.12"
strict = true
disallow_any_generics = false
ignore_missing_imports = true
```

`disallow_any_generics` is turned off because API payloads and raw JSON bodies are intentionally handled as bare `dict` (only response *shapes* we care about asserting on are validated through the pydantic models in `tests/api/models/`) — requiring `dict[str, object]` everywhere would add noise without catching real bugs here.

- [ ] **Step 2: Create `.env.example`**

```
BASE_URL=https://automationintesting.online
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password
```

- [ ] **Step 3: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
allure-results/
allure-report/
.mypy_cache/
.ruff_cache/
.pytest_cache/
test-results/
playwright-report/
```

- [ ] **Step 4: Create `config/__init__.py`** (empty file)

- [ ] **Step 5: Create `config/settings.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    base_url: str = "https://automationintesting.online"
    admin_username: str = "admin"
    admin_password: str = "password"


settings = Settings()
```

- [ ] **Step 6: Create `tests/__init__.py`** (empty file)

- [ ] **Step 7: Install dependencies and Playwright browser**

Run:
```bash
uv sync
uv run playwright install chromium
```
Expected: `uv sync` creates `.venv` and `uv.lock` with no errors; `playwright install` downloads the Chromium browser.

- [ ] **Step 8: Verify settings load and quality tools run clean**

Run:
```bash
uv run python -c "from config.settings import settings; print(settings.base_url)"
uv run ruff check .
uv run mypy .
```
Expected: prints `https://automationintesting.online`; both tools report no errors (an empty `tests/` tree is fine at this point).

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml .env.example .gitignore config/ tests/__init__.py uv.lock
git commit -m "Scaffold uv project with pytest, ruff, mypy and settings module"
```

---

## Task 2: Auth API client, models, and tests

**Files:**
- Create: `tests/api/__init__.py`
- Create: `tests/api/clients/__init__.py`
- Create: `tests/api/clients/auth_client.py`
- Create: `tests/api/models/__init__.py`
- Create: `tests/api/models/auth.py`
- Create: `tests/api/conftest.py`
- Create: `tests/api/test_auth.py`

**Interfaces:**
- Consumes: `config.settings.settings` (Task 1).
- Produces: `AuthClient` with methods `login(username: str, password: str) -> httpx.Response`, `validate(token: str) -> httpx.Response`, `logout(token: str) -> httpx.Response`. Produces pydantic models `LoginResponse`, `ValidateResponse`. Produces fixture `admin_token: str` (session-scoped) — consumed by Tasks 3 and 4.

- [ ] **Step 1: Create empty `__init__.py` files**

Create `tests/api/__init__.py`, `tests/api/clients/__init__.py`, and `tests/api/models/__init__.py`, all empty.

- [ ] **Step 2: Write `tests/api/clients/auth_client.py`**

```python
import httpx

from config.settings import settings


class AuthClient:
    def __init__(self) -> None:
        self._http = httpx.Client(base_url=settings.base_url)

    def login(self, username: str, password: str) -> httpx.Response:
        return self._http.post("/api/auth/login", json={"username": username, "password": password})

    def validate(self, token: str) -> httpx.Response:
        return self._http.post("/api/auth/validate", json={"token": token})

    def logout(self, token: str) -> httpx.Response:
        return self._http.post("/api/auth/logout", json={"token": token})
```

- [ ] **Step 3: Write `tests/api/models/auth.py`**

```python
from pydantic import BaseModel


class LoginResponse(BaseModel):
    token: str


class ValidateResponse(BaseModel):
    valid: bool
```

- [ ] **Step 4: Write `tests/api/conftest.py`**

```python
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
```

- [ ] **Step 5: Write the failing tests in `tests/api/test_auth.py`**

```python
import pytest

from config.settings import settings
from tests.api.clients.auth_client import AuthClient
from tests.api.models.auth import LoginResponse, ValidateResponse

pytestmark = pytest.mark.api


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
    # NOTE: verified live on 2026-08-04 that this demo API does not actually
    # invalidate the token on logout (validate() still returns 200 afterwards) -
    # a real quirk of the app, not a test bug. This test only asserts the
    # logout call itself succeeds; it does not assert token invalidation.
    auth_client = AuthClient()
    login_response = auth_client.login(settings.admin_username, settings.admin_password)
    token = LoginResponse.model_validate(login_response.json()).token

    logout_response = auth_client.logout(token)

    assert logout_response.status_code == 200
    assert logout_response.json() == {"success": True}
```

Note: `test_logout_returns_success` logs in with its own fresh `AuthClient`/token rather than the shared `admin_token` fixture, so it never touches the session-scoped token other tests rely on.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/api/test_auth.py -v -m api`
Expected: all 5 tests PASS.

- [ ] **Step 7: Lint and type-check**

Run:
```bash
uv run ruff check .
uv run mypy .
```
Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add tests/api/__init__.py tests/api/clients/ tests/api/models/ tests/api/conftest.py tests/api/test_auth.py
git commit -m "Add Auth API client, models and tests (login, validate, logout)"
```

---

## Task 3: Room API client, factory, and tests

**Files:**
- Create: `tests/api/clients/room_client.py`
- Create: `tests/api/models/room.py`
- Create: `tests/api/factories/__init__.py`
- Create: `tests/api/factories/room_factory.py`
- Modify: `tests/api/conftest.py` (add `room_client`, `anon_room_client`, `created_room` fixtures)
- Create: `tests/api/test_room.py`

**Interfaces:**
- Consumes: `admin_token` fixture (Task 2), `config.settings.settings`.
- Produces: `RoomClient` with `list_rooms()`, `get_room(room_id)`, `create_room(payload)`, `update_room(room_id, payload)`, `delete_room(room_id)` (all return `httpx.Response`). Produces pydantic models `Room`, `RoomList`. Produces `random_room_payload() -> dict`. Produces fixture `created_room: dict` (a real, persisted room with a fresh random `roomName`) — consumed by Task 4.

- [ ] **Step 1: Write `tests/api/clients/room_client.py`**

```python
import httpx

from config.settings import settings


class RoomClient:
    def __init__(self, token: str | None = None) -> None:
        cookies = {"token": token} if token else {}
        self._http = httpx.Client(base_url=settings.base_url, cookies=cookies)

    def list_rooms(self) -> httpx.Response:
        return self._http.get("/api/room")

    def get_room(self, room_id: int) -> httpx.Response:
        return self._http.get(f"/api/room/{room_id}")

    def create_room(self, payload: dict) -> httpx.Response:
        return self._http.post("/api/room", json=payload)

    def update_room(self, room_id: int, payload: dict) -> httpx.Response:
        return self._http.put(f"/api/room/{room_id}", json=payload)

    def delete_room(self, room_id: int) -> httpx.Response:
        return self._http.delete(f"/api/room/{room_id}")
```

- [ ] **Step 2: Write `tests/api/models/room.py`**

```python
from pydantic import BaseModel


class Room(BaseModel):
    roomid: int
    roomName: str
    type: str
    accessible: bool
    description: str
    features: list[str]
    roomPrice: int
    image: str | None = None


class RoomList(BaseModel):
    rooms: list[Room]
```

- [ ] **Step 3: Create `tests/api/factories/__init__.py`** (empty file)

- [ ] **Step 4: Write `tests/api/factories/room_factory.py`**

```python
from faker import Faker

fake = Faker()

ROOM_TYPES = ["Single", "Twin", "Double", "Family", "Suite"]
ROOM_FEATURES = ["WiFi", "TV", "Radio", "Refreshments", "Safe", "Views"]


def random_room_payload() -> dict:
    return {
        "roomName": str(fake.unique.random_int(min=500, max=99999)),
        "type": fake.random_element(ROOM_TYPES),
        "accessible": fake.boolean(),
        "roomPrice": fake.random_int(min=50, max=500),
        "description": fake.sentence(),
        "features": fake.random_elements(ROOM_FEATURES, length=2, unique=True),
    }
```

- [ ] **Step 5: Add fixtures to `tests/api/conftest.py`**

Append to the existing file (add the `Iterator` import alongside the existing `pytest` import at the top):

```python
from collections.abc import Iterator

from tests.api.clients.room_client import RoomClient
from tests.api.factories.room_factory import random_room_payload


@pytest.fixture
def room_client(admin_token: str) -> RoomClient:
    return RoomClient(token=admin_token)


@pytest.fixture
def anon_room_client() -> RoomClient:
    return RoomClient()


@pytest.fixture
def created_room(room_client: RoomClient) -> Iterator[dict]:
    payload = random_room_payload()
    room_client.create_room(payload)
    rooms = room_client.list_rooms().json()["rooms"]
    room = next(r for r in rooms if r["roomName"] == payload["roomName"])

    yield room

    room_client.delete_room(room["roomid"])
```

- [ ] **Step 6: Write `tests/api/test_room.py`**

```python
import pytest

from tests.api.clients.room_client import RoomClient
from tests.api.factories.room_factory import random_room_payload
from tests.api.models.room import Room, RoomList

pytestmark = pytest.mark.api


def test_create_room_is_visible_in_the_room_list(room_client: RoomClient) -> None:
    payload = random_room_payload()

    create_response = room_client.create_room(payload)
    room_list = RoomList.model_validate(room_client.list_rooms().json())
    created = next(r for r in room_list.rooms if r.roomName == payload["roomName"])

    assert create_response.status_code == 200
    assert create_response.json() == {"success": True}
    assert created.type == payload["type"]
    assert created.accessible == payload["accessible"]
    assert created.roomPrice == payload["roomPrice"]
    assert created.description == payload["description"]
    assert sorted(created.features) == sorted(payload["features"])

    room_client.delete_room(created.roomid)


def test_create_room_without_authentication_is_rejected(anon_room_client: RoomClient) -> None:
    response = anon_room_client.create_room(random_room_payload())

    assert response.status_code == 401
    assert response.json() == {"errors": ["Authentication required"]}


def test_get_room_by_id_returns_its_details(created_room: dict, room_client: RoomClient) -> None:
    response = room_client.get_room(created_room["roomid"])

    assert response.status_code == 200
    room = Room.model_validate(response.json())
    assert room.roomid == created_room["roomid"]
    assert room.roomName == created_room["roomName"]


def test_get_room_with_an_unknown_id_returns_server_error(room_client: RoomClient) -> None:
    # Known quirk of this demo API: an unknown room id returns 500, not 404.
    response = room_client.get_room(999999)

    assert response.status_code == 500


def test_update_room_changes_its_fields(created_room: dict, room_client: RoomClient) -> None:
    updated_payload = {
        "roomName": created_room["roomName"],
        "type": "Suite",
        "accessible": not created_room["accessible"],
        "roomPrice": created_room["roomPrice"] + 50,
        "description": "Updated by an automated test",
        "features": ["Views"],
    }

    response = room_client.update_room(created_room["roomid"], updated_payload)

    assert response.status_code == 202
    body = response.json()
    assert body["type"] == "Suite"
    assert body["roomPrice"] == created_room["roomPrice"] + 50
    assert body["description"] == "Updated by an automated test"
    assert body["features"] == ["Views"]


def test_update_room_without_authentication_is_rejected(
    created_room: dict, anon_room_client: RoomClient
) -> None:
    response = anon_room_client.update_room(created_room["roomid"], random_room_payload())

    assert response.status_code == 403


def test_delete_room_removes_it_from_the_room_list(room_client: RoomClient) -> None:
    payload = random_room_payload()
    room_client.create_room(payload)
    rooms = room_client.list_rooms().json()["rooms"]
    created = next(r for r in rooms if r["roomName"] == payload["roomName"])

    delete_response = room_client.delete_room(created["roomid"])
    rooms_after_delete = room_client.list_rooms().json()["rooms"]

    assert delete_response.status_code == 202
    assert all(r["roomid"] != created["roomid"] for r in rooms_after_delete)


def test_delete_room_without_authentication_is_rejected(
    created_room: dict, anon_room_client: RoomClient
) -> None:
    response = anon_room_client.delete_room(created_room["roomid"])

    assert response.status_code == 403
```

- [ ] **Step 7: Run the tests**

Run: `uv run pytest tests/api/test_room.py -v -m api`
Expected: all 8 tests PASS.

- [ ] **Step 8: Lint and type-check**

Run:
```bash
uv run ruff check .
uv run mypy .
```
Expected: no errors.

- [ ] **Step 9: Commit**

```bash
git add tests/api/clients/room_client.py tests/api/models/room.py tests/api/factories/ tests/api/conftest.py tests/api/test_room.py
git commit -m "Add Room API client, models, factory, fixtures and CRUD tests"
```

---

## Task 4: Booking API client, factory, and tests

**Files:**
- Create: `tests/api/clients/booking_client.py`
- Create: `tests/api/models/booking.py`
- Create: `tests/api/factories/booking_factory.py`
- Modify: `tests/api/conftest.py` (add `booking_client`, `anon_booking_client`, `created_booking` fixtures)
- Create: `tests/api/test_booking.py`

**Interfaces:**
- Consumes: `admin_token`, `created_room` (Task 3), `config.settings.settings`.
- Produces: `BookingClient` with `list_bookings(room_id)`, `get_booking(booking_id)`, `create_booking(payload)`, `update_booking(booking_id, payload)`, `delete_booking(booking_id)`. Produces pydantic models `Booking`, `BookingDates`, `BookingList`. Produces `random_booking_payload(room_id: int) -> dict`. Produces fixture `created_booking: dict`.

- [ ] **Step 1: Write `tests/api/clients/booking_client.py`**

```python
import httpx

from config.settings import settings


class BookingClient:
    def __init__(self, token: str | None = None) -> None:
        cookies = {"token": token} if token else {}
        self._http = httpx.Client(base_url=settings.base_url, cookies=cookies)

    def list_bookings(self, room_id: int) -> httpx.Response:
        return self._http.get("/api/booking", params={"roomid": room_id})

    def get_booking(self, booking_id: int) -> httpx.Response:
        return self._http.get(f"/api/booking/{booking_id}")

    def create_booking(self, payload: dict) -> httpx.Response:
        return self._http.post("/api/booking", json=payload)

    def update_booking(self, booking_id: int, payload: dict) -> httpx.Response:
        return self._http.put(f"/api/booking/{booking_id}", json=payload)

    def delete_booking(self, booking_id: int) -> httpx.Response:
        return self._http.delete(f"/api/booking/{booking_id}")
```

- [ ] **Step 2: Write `tests/api/models/booking.py`**

```python
from pydantic import BaseModel


class BookingDates(BaseModel):
    checkin: str
    checkout: str


class Booking(BaseModel):
    bookingid: int
    roomid: int
    firstname: str
    lastname: str
    depositpaid: bool
    bookingdates: BookingDates


class BookingList(BaseModel):
    bookings: list[Booking]
```

- [ ] **Step 3: Write `tests/api/factories/booking_factory.py`**

```python
from datetime import timedelta

from faker import Faker

fake = Faker()


def random_booking_payload(room_id: int) -> dict:
    checkin = fake.date_between(start_date="+30d", end_date="+90d")
    checkout = checkin + timedelta(days=fake.random_int(min=1, max=5))
    return {
        "roomid": room_id,
        "firstname": fake.first_name(),
        "lastname": fake.last_name(),
        "depositpaid": fake.boolean(),
        "bookingdates": {
            "checkin": checkin.isoformat(),
            "checkout": checkout.isoformat(),
        },
    }
```

- [ ] **Step 4: Add fixtures to `tests/api/conftest.py`**

Append to the existing file:

```python
from tests.api.clients.booking_client import BookingClient
from tests.api.factories.booking_factory import random_booking_payload


@pytest.fixture
def booking_client(admin_token: str) -> BookingClient:
    return BookingClient(token=admin_token)


@pytest.fixture
def anon_booking_client() -> BookingClient:
    return BookingClient()


@pytest.fixture
def created_booking(booking_client: BookingClient, created_room: dict) -> Iterator[dict]:
    payload = random_booking_payload(created_room["roomid"])
    booking = booking_client.create_booking(payload).json()

    yield booking

    booking_client.delete_booking(booking["bookingid"])
```

`created_booking` depends on `created_room`, so every test using it automatically gets an isolated room (never one of the seeded rooms 1/2/3), avoiding any date collision with real visitors' bookings on the shared demo.

- [ ] **Step 5: Write `tests/api/test_booking.py`**

```python
import pytest

from tests.api.clients.booking_client import BookingClient
from tests.api.factories.booking_factory import random_booking_payload
from tests.api.models.booking import Booking

pytestmark = pytest.mark.api


def test_create_booking_is_persisted(created_room: dict, anon_booking_client: BookingClient) -> None:
    payload = random_booking_payload(created_room["roomid"])

    response = anon_booking_client.create_booking(payload)

    assert response.status_code == 201
    body = Booking.model_validate(response.json())
    assert body.roomid == created_room["roomid"]
    assert body.firstname == payload["firstname"]
    assert body.lastname == payload["lastname"]
    assert body.bookingdates.model_dump() == payload["bookingdates"]

    anon_booking_client.delete_booking(body.bookingid)


def test_create_booking_with_missing_lastname_is_rejected(
    created_room: dict, anon_booking_client: BookingClient
) -> None:
    payload = random_booking_payload(created_room["roomid"])
    del payload["lastname"]

    response = anon_booking_client.create_booking(payload)

    assert response.status_code == 400
    assert "Lastname" in response.json()["errors"][0]


def test_create_booking_with_checkout_before_checkin_is_rejected(
    created_room: dict, anon_booking_client: BookingClient
) -> None:
    payload = random_booking_payload(created_room["roomid"])
    payload["bookingdates"] = {"checkin": "2027-09-10", "checkout": "2027-09-05"}

    response = anon_booking_client.create_booking(payload)

    assert response.status_code == 409


def test_get_booking_by_id_returns_its_details(
    created_booking: dict, booking_client: BookingClient
) -> None:
    response = booking_client.get_booking(created_booking["bookingid"])

    assert response.status_code == 200
    assert Booking.model_validate(response.json()).bookingid == created_booking["bookingid"]


def test_get_booking_with_an_unknown_id_returns_not_found(booking_client: BookingClient) -> None:
    response = booking_client.get_booking(999999)

    assert response.status_code == 404


def test_update_booking_changes_its_fields(
    created_booking: dict, created_room: dict, booking_client: BookingClient
) -> None:
    new_dates = {"checkin": "2028-01-10", "checkout": "2028-01-12"}
    updated_payload = {
        "roomid": created_room["roomid"],
        "firstname": "Updated",
        "lastname": created_booking["lastname"],
        "depositpaid": created_booking["depositpaid"],
        "bookingdates": new_dates,
    }

    response = booking_client.update_booking(created_booking["bookingid"], updated_payload)

    assert response.status_code == 200
    assert response.json()["booking"]["firstname"] == "Updated"
    assert response.json()["booking"]["bookingdates"] == new_dates


def test_update_booking_without_authentication_is_rejected(
    created_booking: dict, created_room: dict, anon_booking_client: BookingClient
) -> None:
    updated_payload = {
        "roomid": created_room["roomid"],
        "firstname": "Hacked",
        "lastname": created_booking["lastname"],
        "depositpaid": created_booking["depositpaid"],
        "bookingdates": {"checkin": "2028-02-10", "checkout": "2028-02-12"},
    }

    response = anon_booking_client.update_booking(created_booking["bookingid"], updated_payload)

    assert response.status_code == 403


def test_delete_booking_removes_it(
    created_room: dict, anon_booking_client: BookingClient, booking_client: BookingClient
) -> None:
    payload = random_booking_payload(created_room["roomid"])
    booking = anon_booking_client.create_booking(payload).json()

    delete_response = booking_client.delete_booking(booking["bookingid"])
    get_after_delete = booking_client.get_booking(booking["bookingid"])

    assert delete_response.status_code == 202
    assert get_after_delete.status_code == 404


def test_delete_booking_without_authentication_is_rejected(
    created_booking: dict, anon_booking_client: BookingClient
) -> None:
    response = anon_booking_client.delete_booking(created_booking["bookingid"])

    assert response.status_code == 403
```

- [ ] **Step 6: Run the full API suite**

Run: `uv run pytest tests/api -v -m api`
Expected: all 22 tests (5 auth + 8 room + 9 booking) PASS.

- [ ] **Step 7: Lint and type-check**

Run:
```bash
uv run ruff check .
uv run mypy .
```
Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add tests/api/clients/booking_client.py tests/api/models/booking.py tests/api/factories/booking_factory.py tests/api/conftest.py tests/api/test_booking.py
git commit -m "Add Booking API client, models, factory, fixtures and CRUD tests"
```

---

## Task 5: UI infrastructure — public Page Objects and booking tests

**Files:**
- Create: `tests/ui/__init__.py`
- Create: `tests/ui/pages/__init__.py`
- Create: `tests/ui/pages/home_page.py`
- Create: `tests/ui/pages/reservation_page.py`
- Create: `tests/ui/conftest.py`
- Create: `tests/ui/test_public_booking.py`

**Interfaces:**
- Consumes: `config.settings.settings`, Playwright's built-in `page` fixture (from `pytest-playwright`).
- Produces: `HomePage`, `ReservationPage` classes. Produces fixture `booking_cleanup` (registers a booking for API-based teardown) — reused conceptually by Task 6 (each UI test file defines what it needs from `tests/ui/conftest.py`).

- [ ] **Step 1: Create empty `__init__.py` files**

Create `tests/ui/__init__.py` and `tests/ui/pages/__init__.py`, both empty.

- [ ] **Step 2: Write `tests/ui/pages/home_page.py`**

```python
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
```

- [ ] **Step 3: Write `tests/ui/pages/reservation_page.py`**

```python
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
```

`click_reserve_now` is used twice by tests: once to reveal the guest-details form, once to submit it — it is the same button both times, Playwright re-resolves the locator on each call.

- [ ] **Step 4: Write `tests/ui/conftest.py`**

```python
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

    page.request.post(
        f"{settings.base_url}/api/auth/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    bookings = page.request.get(
        f"{settings.base_url}/api/booking", params={"roomid": registered["room_id"]}
    ).json()["bookings"]
    match = next(
        b
        for b in bookings
        if b["firstname"] == registered["firstname"] and b["lastname"] == registered["lastname"]
    )
    page.request.delete(f"{settings.base_url}/api/booking/{match['bookingid']}")
```

- [ ] **Step 5: Write `tests/ui/test_public_booking.py`**

```python
import re

import pytest
from faker import Faker
from playwright.sync_api import Page, expect

from tests.ui.pages.home_page import HomePage
from tests.ui.pages.reservation_page import ReservationPage

pytestmark = pytest.mark.ui

fake = Faker()


def test_home_page_lists_the_available_rooms(page: Page) -> None:
    home = HomePage(page).open()

    expect(home.room_heading("Single")).to_be_visible()
    expect(home.room_heading("Double")).to_be_visible()
    expect(home.room_heading("Suite")).to_be_visible()
    expect(page.get_by_text("£100")).to_be_visible()


def test_booking_a_room_shows_a_confirmation(page: Page, booking_cleanup: dict) -> None:
    home = HomePage(page).open()
    book_now_link = home.book_now_link("Suite")
    href = book_now_link.get_attribute("href")
    assert href is not None
    room_id = int(re.search(r"/reservation/(\d+)", href).group(1))  # type: ignore[union-attr]

    book_now_link.click()
    reservation = ReservationPage(page)
    reservation.click_reserve_now()
    firstname, lastname = fake.first_name(), fake.last_name()
    reservation.fill_guest_details(firstname, lastname, fake.email(), "01234567890")
    reservation.click_reserve_now()

    expect(reservation.confirmation_heading()).to_be_visible()
    booking_cleanup.update(room_id=room_id, firstname=firstname, lastname=lastname)


def test_reserving_a_room_without_guest_details_shows_validation_errors(page: Page) -> None:
    reservation = ReservationPage(page).open(room_id=1, checkin="2028-06-01", checkout="2028-06-03")

    reservation.click_reserve_now()
    reservation.click_reserve_now()

    expect(reservation.firstname_required_error()).to_be_visible()
    expect(reservation.lastname_required_error()).to_be_visible()
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/ui/test_public_booking.py -v -m ui --browser chromium`
Expected: all 3 tests PASS. (First run may take longer while Chromium warms up.)

- [ ] **Step 7: Lint and type-check**

Run:
```bash
uv run ruff check .
uv run mypy .
```
Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add tests/ui/__init__.py tests/ui/pages/__init__.py tests/ui/pages/home_page.py tests/ui/pages/reservation_page.py tests/ui/conftest.py tests/ui/test_public_booking.py
git commit -m "Add public-site UI Page Objects and booking tests"
```

---

## Task 6: Admin UI Page Objects and tests

**Files:**
- Create: `tests/ui/pages/admin_login_page.py`
- Create: `tests/ui/pages/admin_rooms_page.py`
- Modify: `tests/ui/conftest.py` (add `admin_page` fixture)
- Create: `tests/ui/test_admin_login.py`
- Create: `tests/ui/test_admin_rooms.py`

**Interfaces:**
- Consumes: `config.settings.settings`, Playwright `page` fixture.
- Produces: `AdminLoginPage`, `AdminRoomsPage` classes, fixture `admin_page: Page` (already logged in).

- [ ] **Step 1: Write `tests/ui/pages/admin_login_page.py`**

```python
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
```

- [ ] **Step 2: Write `tests/ui/pages/admin_rooms_page.py`**

```python
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
        self.page.locator("#update").click()
```

- [ ] **Step 3: Add the `admin_page` fixture to `tests/ui/conftest.py`**

Append to the existing file (add the import at the top alongside the existing ones):

```python
from tests.ui.pages.admin_login_page import AdminLoginPage


@pytest.fixture
def admin_page(page: Page) -> Page:
    AdminLoginPage(page).open().login(settings.admin_username, settings.admin_password)
    return page
```

- [ ] **Step 4: Write `tests/ui/test_admin_login.py`**

```python
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
```

- [ ] **Step 5: Write `tests/ui/test_admin_rooms.py`**

```python
from collections.abc import Iterator

import pytest
from faker import Faker
from playwright.sync_api import Page, expect

from config.settings import settings
from tests.ui.pages.admin_rooms_page import AdminRoomsPage

pytestmark = pytest.mark.ui

fake = Faker()


@pytest.fixture
def room_cleanup(page: Page) -> Iterator[list[int]]:
    room_ids: list[int] = []

    yield room_ids

    if not room_ids:
        return

    page.request.post(
        f"{settings.base_url}/api/auth/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    for room_id in room_ids:
        page.request.delete(f"{settings.base_url}/api/room/{room_id}")


def _find_room_id_by_name(page: Page, room_name: str) -> int:
    rooms = page.request.get(f"{settings.base_url}/api/room").json()["rooms"]
    return next(r["roomid"] for r in rooms if r["roomName"] == room_name)


def test_creating_a_room_makes_it_appear_in_the_room_list(
    admin_page: Page, room_cleanup: list[int]
) -> None:
    rooms_page = AdminRoomsPage(admin_page).open()
    room_name = str(fake.unique.random_int(min=500, max=99999))

    rooms_page.create_room(
        room_name=room_name, room_type="Suite", accessible=True, price=321, features=["WiFi", "Safe"]
    )

    expect(admin_page.locator(f"#roomName{room_name}")).to_be_visible()
    room_cleanup.append(_find_room_id_by_name(admin_page, room_name))


def test_editing_a_room_updates_its_details(admin_page: Page, room_cleanup: list[int]) -> None:
    room_name = str(fake.unique.random_int(min=500, max=99999))
    admin_page.request.post(
        f"{settings.base_url}/api/auth/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    admin_page.request.post(
        f"{settings.base_url}/api/room",
        data={
            "roomName": room_name,
            "type": "Single",
            "accessible": True,
            "roomPrice": 100,
            "description": "original description",
            "features": ["WiFi"],
        },
    )
    room_id = _find_room_id_by_name(admin_page, room_name)
    room_cleanup.append(room_id)
    rooms_page = AdminRoomsPage(admin_page).open()

    rooms_page.open_room(room_name)
    rooms_page.click_edit()
    rooms_page.set_price(250)
    rooms_page.set_description("updated by an automated test")
    rooms_page.click_update()

    expect(admin_page.get_by_text("250")).to_be_visible()
    expect(admin_page.get_by_text("updated by an automated test")).to_be_visible()


def test_room_detail_page_shows_its_bookings(admin_page: Page, room_cleanup: list[int]) -> None:
    room_name = str(fake.unique.random_int(min=500, max=99999))
    admin_page.request.post(
        f"{settings.base_url}/api/auth/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    admin_page.request.post(
        f"{settings.base_url}/api/room",
        data={
            "roomName": room_name,
            "type": "Single",
            "accessible": True,
            "roomPrice": 100,
            "description": "room for booking visibility test",
            "features": ["WiFi"],
        },
    )
    room_id = _find_room_id_by_name(admin_page, room_name)
    room_cleanup.append(room_id)
    admin_page.request.post(
        f"{settings.base_url}/api/booking",
        data={
            "roomid": room_id,
            "firstname": "Ada",
            "lastname": "Lovelace",
            "depositpaid": True,
            "bookingdates": {"checkin": "2028-05-01", "checkout": "2028-05-03"},
        },
    )
    rooms_page = AdminRoomsPage(admin_page).open()

    rooms_page.open_room(room_name)

    expect(admin_page.get_by_text("Ada")).to_be_visible()
    expect(admin_page.get_by_text("Lovelace")).to_be_visible()
```

Room and booking setup in the last two tests uses `admin_page.request` (Playwright's API request context) instead of the UI, because there is no admin UI path to pre-seed a room with a chosen description or to create a booking at all — this is documented as a deliberate, verified constraint of the app at the top of this plan, not a workaround invented for convenience.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/ui/test_admin_login.py tests/ui/test_admin_rooms.py -v -m ui --browser chromium`
Expected: all 5 tests PASS.

- [ ] **Step 7: Run the full UI suite together, then the full project**

Run:
```bash
uv run pytest -m ui --browser chromium -v
uv run pytest -v
```
Expected: all UI tests pass; the combined run (22 API + 8 UI = 30 tests) passes.

- [ ] **Step 8: Lint and type-check**

Run:
```bash
uv run ruff check .
uv run mypy .
```
Expected: no errors.

- [ ] **Step 9: Commit**

```bash
git add tests/ui/pages/admin_login_page.py tests/ui/pages/admin_rooms_page.py tests/ui/conftest.py tests/ui/test_admin_login.py tests/ui/test_admin_rooms.py
git commit -m "Add admin UI Page Objects and login/room management tests"
```

---

## Task 7: Allure report and README

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: nothing new — this task documents and verifies what Tasks 1–6 built.

- [ ] **Step 1: Generate an Allure result set and confirm it's populated**

Run:
```bash
uv run pytest -v
```
Expected: exits 0; an `allure-results/` directory now exists with `.json` files in it (one set per test, per the `--alluredir=allure-results` addopts from Task 1).

- [ ] **Step 2: Render the HTML report locally (requires the Allure commandline, not a Python package)**

Run (Windows, via Scoop — adjust for another package manager if the user has one installed):
```bash
scoop install allure
allure serve allure-results
```
Expected: opens a browser tab with the Allure report showing 30 passed tests split by suite/marker. If `allure` is not on PATH, note this step as manual/optional in the README rather than failing the task — the report generation is a nice-to-have on top of the `--alluredir` results, which are already produced by plain `pytest`.

- [ ] **Step 3: Write `README.md`**

```markdown
# Restful Booker Platform — Test Automation Suite

Portfolio project: an automated API + UI test suite for the [Restful Booker Platform](https://github.com/mwinteringham/restful-booker-platform) demo hosted at https://automationintesting.online/.

## Stack

- **pytest** — test runner for both suites
- **httpx** + **pydantic** — API test client and validation
- **pytest-playwright** — UI automation with a Page Object Model
- **Faker** — disposable, randomized test data
- **allure-pytest** — test reporting
- **ruff** + **mypy** — linting, formatting, type checking
- **uv** — dependency and environment management

## Project layout

- `tests/api/` — API tests (Auth, Room, Booking) against the REST API, using `httpx` clients under `clients/` and Faker-based data under `factories/`.
- `tests/ui/` — UI tests (public booking flow, admin login, admin room management) using Playwright, with Page Objects under `pages/`.
- `config/settings.py` — single source of configuration (base URL, admin credentials), read from `.env`.

The two suites are intentionally independent: `tests/ui` never imports from `tests/api`. Where a UI test needs to set up or tear down data the UI itself cannot reach (the app has no UI to delete a room or a booking — see the plan doc below), it uses Playwright's `page.request`, which shares the browser's session, instead of reaching into the API test suite's clients.

## Setup

```bash
uv sync
uv run playwright install chromium
cp .env.example .env  # defaults already point at the public demo
```

## Running the tests

```bash
uv run pytest -m api          # API tests only
uv run pytest -m ui            # UI tests only
uv run pytest                  # everything
```

## Reporting

Every run writes raw results to `allure-results/`. To view the HTML report, install the [Allure commandline](https://allurereport.org/docs/install/) and run:

```bash
allure serve allure-results
```

## Code quality

```bash
uv run ruff check .
uv run mypy .
```

## Design notes

Full design rationale and the exact, verified API/UI behavior this suite is built against are documented in [`docs/superpowers/specs/2026-08-04-test-automation-framework-design.md`](docs/superpowers/specs/2026-08-04-test-automation-framework-design.md) and [`docs/superpowers/plans/2026-08-04-test-automation-framework.md`](docs/superpowers/plans/2026-08-04-test-automation-framework.md).
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "Add project README"
```

---

## Final verification

- [ ] Run `uv run pytest -v` — 30 tests pass (22 API + 8 UI).
- [ ] Run `uv run ruff check .` and `uv run mypy .` — both clean.
- [ ] Confirm the shared demo app's data is back to its baseline: 3 rooms (`101`/`102`/`103`) and exactly one booking per seeded room. If a leftover test room/booking exists (e.g. from a failed run whose teardown didn't execute), delete it manually via `DELETE /api/room/{id}` or `DELETE /api/booking/{id}` using an admin token.
