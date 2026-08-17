# Test Automation Framework – Design

**Date:** 2026-08-04
**Goal:** Design and build a well-architected automated test suite (API + UI) for a real web application, with a focus on solid test automation practices developed in collaboration with AI.

## Application under test

- **Web:** https://automationintesting.online/ (Restful Booker Platform – public shared demo)
- **API documentation:** Postman collection – https://www.postman.com/automation-in-testing/restful-booker-collections/request/vy3jhj1
- **Application source code:** https://github.com/mwinteringham/restful-booker-platform

## Priorities and philosophy

The goal is **depth and quality of architecture**, not test quantity. A smaller number of well-designed tests (POM, fixtures, clean structure, type safety, reporting) is preferred over exhaustive coverage of every possible scenario. CI/CD (GitHub Actions) was deliberately deferred until the test suite itself was solid, then added once that was true – see section 6.

## 1. Architecture and project structure

A single repository managed with **uv**, containing two independent test suites (API and UI) that share only a minimal amount of common infrastructure (configuration, test data generation). The API and UI suites are deliberately independent of each other (no API-driven setup for UI tests) – they are two separate, independently runnable capabilities.

> **Note:** one exception to the rule above exists – `test_booking_a_room_shows_a_confirmation` (`tests/ui/test_public_booking.py`) creates a disposable room via `page.request` before making the actual booking through the UI. Reason: on a shared public demo there is no other safe way to obtain a room that cannot collide with a real visitor's data. This is a targeted, deliberate exception, not a relaxation of the principle itself – the suites remain independent at the code level (`tests/ui` never imports from `tests/api`), and cleanup here also goes through `page.request`, not the `tests.api` package.

```
PythonTestsExample/
├── pyproject.toml          # uv, pytest, ruff, mypy config
├── uv.lock
├── .env.example             # BASE_URL, ADMIN_USER, ADMIN_PASS (no real values)
├── .gitignore
├── .pre-commit-config.yaml   # optional local ruff/mypy hooks – see section 7
├── README.md                 # project description, how to run it, Allure report screenshots
├── config/
│   └── settings.py           # pydantic-settings – reads .env, single source of truth for URL/credentials
├── tests/
│   ├── api/
│   │   ├── conftest.py
│   │   ├── clients/           # AuthClient, BookingClient, RoomClient – thin wrappers around HTTP calls
│   │   ├── models/            # pydantic models for request/response (schema validation)
│   │   ├── factories/         # Faker – random test data generation
│   │   └── test_*.py
│   ├── ui/
│   │   ├── conftest.py
│   │   ├── pages/              # Page Object Model (HomePage, AdminLoginPage, AdminRoomsPage...)
│   │   ├── components/         # shared UI components across pages (nav, modals)
│   │   └── test_*.py
│   └── canary/                 # deliberately-failing test exercising the CI failure-analysis pipeline
├── scripts/
│   ├── analyze_failures.py     # summarizes CI failures via Claude – see section 6
│   └── cleanup_orphan_rooms.py # deletes stray test-created rooms – see section 6
```

Tests can be run separately (`pytest -m api`, `pytest -m ui`) or together, thanks to the pytest markers `api` and `ui`.

## 2. Key components and technologies

| Area            | Choice                                 | Notes                                                                                                                                                     |
|-----------------|----------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| Test runner     | pytest                                 | shared by API and UI                                                                                                                                      |
| API HTTP client | `httpx`                                | modern, typed                                                                                                                                             |
| API validation  | `pydantic` models                      | request/response schemas, catches API inconsistencies                                                                                                     |
| UI              | `pytest-playwright` + custom POM layer | official plugin + a Page Object Model built on top                                                                                                        |
| Test data       | `Faker`                                | random data for Booking/Room, so tests don't collide with the shared demo                                                                                 |
| Configuration   | `pydantic-settings` + `.env`           | base URL, admin credentials, no hardcoded values                                                                                                          |
| Reporting       | `allure-pytest`                        | graphical report, steps, screenshots on failure                                                                                                           |
| Code quality    | `ruff` (lint only) + `mypy`            | consistent style, type checking; `ruff format` / `[tool.ruff.format]` is not configured in this project, so this tooling does not enforce code formatting |
| CI/CD           | GitHub Actions                         | five jobs on push/PR to `main`, on manual trigger, and on a weekly cron – see section 6                                                                   |
| CI failure triage | Claude API (`claude-sonnet-5`)       | advisory-only root-cause summary of failed tests, uploaded as a CI artifact – see section 6                                              |

**Auth handling (API):** the `admin_token` fixture logs in via `AuthClient` and provides the token/cookie to the other tests that need it (e.g. deleting a room requires auth).

**Auth handling (UI):** a dedicated fixture performs the login flow through the admin UI (not the API – the suites are independent) and returns a logged-in `page`, so each admin test doesn't have to repeat it.

## 3. Test data lifecycle and isolation

Every test that needs an entity (booking/room) **creates it itself and cleans it up itself**:

- **API tests:** a `yield` fixture creates the entity via the API with Faker data during setup, hands its ID/data to the test, and deletes it in teardown (even if the test fails).
- **UI tests:** entity creation goes through the UI wherever possible (e.g. an admin test creates a room through the form). Read-only public tests (browsing rooms) work with existing data. Deletion (of both rooms and bookings), however, **has no UI path in the application at all** (see the finding in section 5) – cleanup after UI tests therefore goes through Playwright's `page.request` (it shares cookies with the browser, so it reuses the already-authenticated admin session) calling the API directly, not the `tests.api` package – so the suites stay independent at the code level, even though teardown effectively calls the same REST API.
- No test depends on execution order or on data created by another test – tests must be runnable independently and repeatedly, since this is a public shared demo environment.

## 4. Error handling and test resilience

- **API:** the wrapper clients (`BookingClient`, etc.) don't mask errors – a failed status code is checked explicitly in the test/assertion. Pydantic models catch cases where the API returns an unexpected data shape.
- **UI:** relies on Playwright auto-waiting + explicit `expect()` assertions (no custom sleeps). `pytest-playwright` automatically saves a screenshot/trace/video on test failure (`--screenshot=only-on-failure --video=retain-on-failure --tracing=retain-on-failure`), which also feeds into the Allure report.
- **Cleanup even on failure:** teardown fixtures always run (via `yield` in a pytest fixture), so even a failed test cleans up the data it created.

## 5. Scope of test scenarios

**API (full CRUD + edge cases for Auth, Booking, Room):**
- **Auth:** successful login, login with wrong credentials, logout, token validation (valid/invalid/missing)
- **Room:** create/read/update/delete happy path; negative – missing required fields, unauthorized access (no token), non-existent ID (404)
- **Booking:** create/read/update/delete happy path; negative – invalid dates (checkout before checkin), missing fields, unauthorized update/delete, non-existent ID

**UI – public site:**
- Browsing available rooms on the home page
- Creating a reservation through the booking widget (happy path)
- Reservation form validation (e.g. missing name/email, invalid email)
- Contact form (basic happy path, possibly one negative validation) – only if time allows, not a priority

**UI – admin panel:**
- Login (successful / unsuccessful)
- Room management: creating, editing a room
- Viewing a room's bookings (read-only)
- Logout

The goal is to have a handful of well-written tests per area (happy path + 1-2 negative/edge cases) that demonstrate the design, not the quantity.

> **Note:** the admin UI has no way to delete a room or a booking – deletion only exists at the API level (`DELETE /api/room/{id}`, `DELETE /api/booking/{id}`). In UI tests, deletion is therefore only used to clean up data created by the test (via the API in teardown), never as a tested UI step. See [app-behavior-notes.md](app-behavior-notes.md) for the full, verified API/UI behavior reference.

## 6. CI/CD pipeline

Runs in GitHub Actions from `.github/workflows/tests.yml`, on every push and pull request targeting `main`, plus a manual `workflow_dispatch` trigger (a "Run workflow" button in the Actions tab, with a checkbox to also run `canary` below).

Five jobs, each independent (no job waits on another):

- **`lint`** – `ruff check .` and `mypy .`. Catches style/type issues.
- **`api-tests`** – `pytest -m api` against the live application.
- **`ui-tests`** – installs Chromium (`playwright install --with-deps chromium`) then `pytest -m ui` against the live application.
- **`canary`** – manual trigger only; runs one deliberately-failing test (`tests/canary/`) to exercise the AI failure-analysis pipeline below without waiting for a real failure. Scoped to `pytest tests/canary` rather than a bare `-m canary` filter, since pytest still *collects* (imports) `tests/api`/`tests/ui` before marker filtering applies, which would fail on their missing credentials in this job.
- **`cleanup-orphans`** – weekly cron (`0 6 * * 1`) plus manual trigger; runs [`scripts/cleanup_orphan_rooms.py`](../scripts/cleanup_orphan_rooms.py), which deletes any room (and its bookings) whose `roomName` is a digit-only string in `[500, 99999]` – the range every room-creation call site in this repo uses (`fake.unique.random_int(min=500, max=99999)`), which never overlaps the seeded `101`/`102`/`103`. Automates the manual `GET`/`DELETE` cleanup step the README used to document. Not run after every test job: fixture teardown already cleans up normal failures (it runs on a failed test too, just not on a run killed hard enough to skip teardown entirely, which is the only way an orphan happens), so per-run cleanup would mostly be extra load on the shared demo for no reason – weekly is a deliberately generous upper bound on how long a genuine orphan could survive.

**Credentials:** `ADMIN_USERNAME`/`ADMIN_PASSWORD` are stored as GitHub Actions **repository secrets** and injected as environment variables (`${{ secrets.ADMIN_USERNAME }}` etc.), the same variables `config/settings.py` already reads via `.env` locally – no code changes needed between local and CI runs.

**Artifacts:** after each test job (including on failure, `if: always()`), `allure-results/` is uploaded as a downloadable GitHub Actions artifact – the same directory `allure serve allure-results` reads locally, so a CI run's results can be pulled down and inspected the same way as a local run. Retained for 90 days (GitHub's default, and – since this is a public repo – its maximum too).

**AI failure analysis:** on a failed `api-tests`, `ui-tests`, or `canary` job, [`scripts/analyze_failures.py`](../scripts/analyze_failures.py) sends each pytest failure (traceback plus the closest own-project source file – frames inside installed packages are skipped) to Claude (`claude-sonnet-5`) and uploads the resulting root-cause writeup as its own artifact (`ai-analysis-api`/`ai-analysis-ui`/`ai-analysis-canary`). Deliberately advisory: a missing `ANTHROPIC_API_KEY` secret or a failed API call is logged and skipped rather than failing the job, since it runs as a separate `if: always()` step after the tests, not part of them. In practice this has already surfaced real findings beyond the raw traceback – e.g. a stale-price failure in the room-edit UI traced back to `PUT /api/room/{id}` returning `202` (accepted, not necessarily persisted) rather than a bug in the test itself; see [app-behavior-notes.md](app-behavior-notes.md).

## 7. Developer tooling

**Pre-commit:** `.pre-commit-config.yaml` runs `uv run ruff check .` / `uv run mypy .` as local hooks (`repo: local`), reusing the versions already pinned via `uv` instead of duplicating separate version pins in the hook config. No formatting hook, matching this project's deliberate choice not to enforce `ruff format`. Optional locally (`pre-commit install`) – CI's `lint` job is still the actual gate.

**Dependabot (tried, removed):** ran `uv` + `github-actions` updates weekly, but in practice produced a high volume of low-value PRs for this project's actual dependency churn, and Dependabot-triggered runs don't get repository secrets by default (GitHub treats them like fork PRs) – it caused a confusing API-test failure (`401 Invalid credentials`) before that was diagnosed. Removed in favor of updating dependencies manually as needed.

## Out of scope (for now)

- Message/Report API endpoint – only marginally, not a priority
- Hybrid API+UI tests (API setup for UI tests) as a general principle – considered but rejected in favor of fully independent suites; one targeted exception (the disposable room in `test_booking_a_room_shows_a_confirmation`) ended up being introduced out of necessity – see the addendum in section 1

## Repository

- GitHub remote: https://github.com/MSembera/PythonTestsExample.git
