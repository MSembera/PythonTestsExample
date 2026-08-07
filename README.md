# Restful Booker Platform — Test Automation Suite

[![Tests](https://github.com/MSembera/PythonTestsExample/actions/workflows/tests.yml/badge.svg)](https://github.com/MSembera/PythonTestsExample/actions/workflows/tests.yml)

An automated API + UI test suite for the [Restful Booker Platform](https://github.com/mwinteringham/restful-booker-platform) demo hosted at https://automationintesting.online/.

## Stack

- **pytest** — test runner for both suites
- **httpx** + **pydantic** — API test client and validation
- **pytest-playwright** — UI automation with a Page Object Model
- **Faker** — disposable, randomized test data
- **allure-pytest** — test reporting
- **ruff** + **mypy** — linting (import order, pyupgrade, bugbear rules) and static type checking; there is no `ruff format` / `[tool.ruff.format]` setup in this project, so code formatting is manual/editor-driven, not enforced by a tool
- **uv** — dependency and environment management

## Project layout

```
.
├── config/
│   └── settings.py       # single source of configuration (base URL, admin credentials), read from .env
├── docs/
│   ├── design.md          # architecture and design rationale
│   └── app-behavior-notes.md  # verified API/UI behavior of the app under test
├── tests/
│   ├── api/
│   │   ├── conftest.py
│   │   ├── clients/       # AuthClient, RoomClient, BookingClient — thin wrappers over httpx
│   │   ├── models/        # pydantic models validating API response shapes
│   │   ├── factories/     # Faker-based random test data
│   │   └── test_*.py
│   └── ui/
│       ├── conftest.py
│       ├── pages/         # Page Object Model (HomePage, AdminLoginPage, AdminRoomsPage, ...)
│       └── test_*.py
└── .github/workflows/
    └── tests.yml          # CI: lint, api-tests, ui-tests
```

- `tests/api/` — API tests (Auth, Room, Booking) against the REST API, using `httpx` clients under `clients/` and Faker-based data under `factories/`.
- `tests/ui/` — UI tests (public booking flow, admin login, admin room management) using Playwright, with Page Objects under `pages/`.
- `config/settings.py` — single source of configuration (base URL, admin credentials), read from `.env`.

The two suites are intentionally independent: `tests/ui` never imports from `tests/api`. Where a UI test needs to set up or tear down data the UI itself cannot reach (the app has no UI to delete a room or a booking — see [app-behavior-notes.md](docs/app-behavior-notes.md)), it uses Playwright's `page.request`, which shares the browser's session, instead of reaching into the API test suite's clients.

> **Note:** the target site is a shared public demo used by other testers too. Every test creates and tears down its own disposable data, but a failed test run (or a concurrent user's own testing) may occasionally leave stray rooms/bookings behind despite that cleanup design. That's expected and acceptable for a project against a live shared demo, not a bug to chase. If you want to spot-check for leftovers, `GET /api/room` should only ever show the 3 seeded rooms (101/102/103); anything else can be removed via `DELETE /api/room/{id}` with an admin token.

## Setup

```bash
uv sync
uv run playwright install chromium
cp .env.example .env
```

Then fill in `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`. This target is a public training demo with a documented, non-secret admin account (`admin` / `password` — see the app's own README at https://github.com/mwinteringham/restful-booker-platform); against a real application these would be per-environment test credentials injected via `.env` or CI secrets, never committed. `.env` is gitignored either way — only `.env.example` (with empty placeholders) is tracked.

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

Design rationale is documented in [`docs/design.md`](docs/design.md); the exact, verified API/UI behavior this suite is built against is in [`docs/app-behavior-notes.md`](docs/app-behavior-notes.md).
