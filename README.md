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
