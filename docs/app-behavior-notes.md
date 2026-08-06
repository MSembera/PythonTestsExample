# Verified API/UI behavior (reference)

The application's actual behavior was verified directly against the live site rather than assumed, and the test suite is built to match it exactly — including a few real quirks that are easy to get wrong by guessing. This is reference material for anyone maintaining or extending the suite; see [design.md](design.md) for the overall architecture and rationale.

## Auth (`/api/auth`)

- `POST /api/auth/login` `{"username", "password"}` → `200 {"token": "<str>"}` on success; `401 {"error": "Invalid credentials"}` on failure.
- `POST /api/auth/validate` `{"token"}` → `200 {"valid": true}` if valid; `403 {"error": "Invalid token"}` if invalid.
- `POST /api/auth/logout` `{"token"}` → `200 {"success": true}`. Note: this does **not** actually invalidate the token — a subsequent `validate` call with the same token still succeeds.
- Auth is a cookie named `token` (not httpOnly), not an `Authorization` header. A real UI form login sets this cookie automatically; a login request made through Playwright's `page.request` does not (the token is only returned in the JSON body, with no `Set-Cookie` header) — code that authenticates that way must extract the token and add it explicitly via `page.context.add_cookies(...)`.

## Room (`/api/room`)

- `GET /api/room` → `200 {"rooms": [{roomid, roomName, type, accessible, description, features: [...], roomPrice, image?}]}`.
- `GET /api/room/{id}` → `200 <room>`; an unknown id returns `500` (not 404) — a real quirk of this demo.
- `POST /api/room` (auth required) → `200 {"success": true}` — does not return the created room; re-fetch the room list and match by `roomName` to find the new id. No auth → `401`.
- `PUT /api/room/{id}` (auth required) → `202 <updated room>`. No auth → `403`.
- `DELETE /api/room/{id}` (auth required) → `202`. No auth → `403`.

## Booking (`/api/booking`)

- `GET /api/booking?roomid={id}` requires auth — `401` without it, regardless of `roomid`. Once authenticated, `roomid` is required — omitting it returns `400`.
- `GET /api/booking/{id}` → `200 <booking>`; unknown id → `404` (this endpoint 404s correctly, unlike Room).
- `POST /api/booking` (no auth required — public) → `201 <created booking>`. Missing a required field (e.g. `lastname`) → `400`. `checkout` before `checkin` → `409`.
- `PUT /api/booking/{id}` (auth required) → `200`. No auth → `403`. Overlapping dates with an existing booking on that room (including its own current dates) → `409` — always use genuinely free dates when updating.
- `DELETE /api/booking/{id}` (auth required) → `202`. No auth → `403`.

## UI — public site

Reservation flow: a `Reserve Now` button reveals a guest-details form (Firstname/Lastname/Email/Phone, identified by placeholder text, no labels); clicking it again submits. On success: a `Booking Confirmed` heading and the check-in/check-out date range are shown. On validation failure: inline messages such as "Firstname should not be blank".

## UI — admin panel

- The app has no persisted client-side session: a full page reload always shows the login form again, even though the `token` cookie may still be valid for API calls. Every UI test performs a real login through the form rather than assuming a previous login carries over.
- The room create form and the room edit form use different element ids for the same "Refreshments" feature checkbox (`#refreshCheckbox` vs `#refreshmentsCheckbox`) — an easy trap when writing selectors.
- **There is no delete control anywhere in the admin UI**, for either a room or a booking — deleting is only possible via the API, which is why UI-test cleanup goes through Playwright's `page.request` rather than a UI action.
