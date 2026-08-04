# Test Automation Framework – Design

**Datum:** 2026-08-04
**Cíl projektu:** Portfoliový projekt demonstrující schopnost navrhnout a implementovat kvalitní automatizované testy (API + UI) včetně spolupráce s AI, prezentovaný recruiterům.

## Testovaná aplikace

- **Web:** https://automationintesting.online/ (Restful Booker Platform – veřejné sdílené demo)
- **API dokumentace:** Postman kolekce – https://www.postman.com/automation-in-testing/restful-booker-collections/request/vy3jhj1
- **Zdrojový kód aplikace:** https://github.com/mwinteringham/restful-booker-platform

## Priority a filozofie

Cílem je **hloubka a kvalita architektury**, ne kvantita testů. Preferujeme menší počet dobře navržených testů (POM, fixtures, čistá struktura, typová bezpečnost, reporting) před vyčerpávajícím pokrytím všech možných scénářů. CI/CD (GitHub Actions) je vědomě odloženo na pozdější fázi, aby se nejdřív dotáhla kvalita samotných testů.

## 1. Architektura a struktura projektu

Jeden repozitář spravovaný přes **uv**, se dvěma nezávislými sadami testů (API a UI), které sdílí jen minimum společné infrastruktury (konfigurace, generování testovacích dat). API a UI testy na sebe úmyslně nezávisí (žádné API-driven setup pro UI testy) – jde o dvě oddělené, samostatně spustitelné kompetence.

> **Dodatek (final review fix pass, 2026-08-04):** jedna výjimka z výše uvedeného pravidla existuje - `test_booking_a_room_shows_a_confirmation` (`tests/ui/test_public_booking.py`) si přes `page.request` vytváří jednorázový pokoj ještě před samotným bookováním přes UI. Důvod: na sdíleném veřejném demu neexistuje jiný bezpečný způsob, jak získat pokoj, který se nemůže srazit s daty skutečného návštěvníka. Jde o cílenou, zdokumentovanou výjimku (viz "Post-implementation addendum" v [implementačním plánu](../plans/2026-08-04-test-automation-framework.md)), ne o rozšíření principu jako takového - suity zůstávají na úrovni kódu nezávislé (`tests/ui` neimportuje z `tests/api`), teardown i tady jde přes `page.request`, ne přes `tests.api` balíček.

```
PythonTestsExample/
├── pyproject.toml          # uv, pytest, ruff, mypy config
├── uv.lock
├── .env.example             # BASE_URL, ADMIN_USER, ADMIN_PASS (bez skutečných hodnot)
├── .gitignore
├── README.md                 # popis projektu, jak spustit, screenshoty Allure reportu
├── config/
│   └── settings.py           # pydantic-settings – čte .env, jeden zdroj pravdy pro URL/credentials
├── tests/
│   ├── api/
│   │   ├── conftest.py
│   │   ├── clients/           # AuthClient, BookingClient, RoomClient – tenké wrappery nad HTTP voláními
│   │   ├── models/            # pydantic modely pro request/response (validace schémat)
│   │   ├── factories/         # Faker – generování náhodných testovacích dat
│   │   └── test_*.py
│   └── ui/
│       ├── conftest.py
│       ├── pages/              # Page Object Model (HomePage, AdminLoginPage, AdminRoomsPage...)
│       ├── components/         # sdílené UI komponenty napříč stránkami (nav, modaly)
│       └── test_*.py
```

Testy jde spouštět zvlášť (`pytest -m api`, `pytest -m ui`) i dohromady, díky pytest markerům `api` a `ui`.

## 2. Klíčové komponenty a technologie

| Oblast | Volba | Poznámka |
|---|---|---|
| Test runner | pytest | společný pro API i UI |
| API HTTP klient | `httpx` | moderní, typované |
| API validace | `pydantic` modely | request/response schémata, odhalí nekonzistence API |
| UI | `pytest-playwright` + vlastní POM vrstva | official plugin + Page Object Model nad ním |
| Testovací data | `Faker` | náhodná data pro Booking/Room, aby se testy nebily se sdíleným demem |
| Konfigurace | `pydantic-settings` + `.env` | base URL, admin credentials, žádné hardcoded hodnoty |
| Reporting | `allure-pytest` | grafický report, kroky, screenshoty při selhání |
| Kvalita kódu | `ruff` (jen lint) + `mypy` | konzistentní styl, typová kontrola; `ruff format` / `[tool.ruff.format]` v projektu není nastaven, formátování kódu tedy tento nástroj nevynucuje |
| CI/CD | GitHub Actions | **později**, jako samostatný krok mimo tento návrh |

**Auth handling (API):** fixture `admin_token` se zaloguje přes `AuthClient` a token/cookie poskytne ostatním testům, které to potřebují (např. mazání pokoje vyžaduje auth).

**Auth handling (UI):** samostatná fixture provede login flow přes admin UI (ne přes API – sady jsou oddělené) a vrátí přihlášenou `page`, aby to nemusel opakovat každý admin test.

## 3. Životní cyklus testovacích dat a izolace

Každý test, který potřebuje entitu (booking/room), si ji **sám vytvoří a sám uklidí**:

- **API testy:** fixture s `yield` – v setupu vytvoří entitu přes API s Faker daty, testu předá její ID/data, po testu (i při selhání testu) ji smaže v teardownu.
- **UI testy:** vytvoření entity jde přes UI, kde to jde (např. admin vytvoří pokoj přes formulář). Read-only public testy (browse rooms) pracují s existujícími daty. Mazání (pokoj i booking) ale **nemá v aplikaci žádnou UI cestu** (viz zjištění v sekci 5) – úklid po UI testech proto probíhá přes Playwrightův `page.request` (sdílí cookies s prohlížečem, takže využívá už přihlášenou admin session) volající přímo API, ne přes `tests.api` balíček – suity tak zůstávají nezávislé na úrovni kódu, i když teardown fakticky volá stejné REST API.
- Žádný test nezávisí na pořadí spuštění ani na datech vytvořených jiným testem – testy musí být spustitelné nezávisle a opakovaně, protože jde o veřejné sdílené demo prostředí.

## 4. Error handling a odolnost testů

- **API:** wrapper klienti (`BookingClient` atd.) chyby nekamuflují – neúspěšný status code se ověřuje explicitně v testu/assertu. Pydantic modely odhalí, když API vrátí neočekávaný tvar dat.
- **UI:** spoléháme na Playwright auto-waiting + explicitní `expect()` assertions (žádné vlastní sleepy). `pytest-playwright` při selhání testu automaticky uloží screenshot/trace/video (`--screenshot=only-on-failure --video=retain-on-failure --tracing=retain-on-failure`), což se propojí i do Allure reportu.
- **Cleanup i při selhání:** teardown fixtures běží vždy (přes `yield` v pytest fixture), takže i padlý test po sobě uklidí vytvořená data.

## 5. Rozsah testovacích scénářů

**API (plné CRUD + edge cases pro Auth, Booking, Room):**
- **Auth:** úspěšný login, login se špatnými credentials, logout, validace tokenu (platný/neplatný/chybějící)
- **Room:** create/read/update/delete happy path; negativní – chybějící povinná pole, neautorizovaný přístup (bez tokenu), neexistující ID (404)
- **Booking:** create/read/update/delete happy path; negativní – neplatné datumy (checkout před checkin), chybějící pole, neautorizovaná úprava/smazání, neexistující ID

**UI – veřejná část:**
- Prohlížení dostupných pokojů na hlavní stránce
- Vytvoření rezervace přes booking widget (happy path)
- Validace formuláře rezervace (např. chybějící jméno/email, neplatný email)
- Kontaktní formulář (základní happy path, případně jedna negativní validace) – jen pokud zbude prostor, není priorita

**UI – admin panel:**
- Přihlášení (úspěšné / neúspěšné)
- Správa pokojů: vytvoření, editace pokoje
- Zobrazení rezervací u pokoje (read-only)
- Odhlášení

Cílem je z každé oblasti mít pár dobře napsaných testů (happy path + 1-2 negativní/edge case), které demonstrují návrh, ne kvantitu.

> **Zjištěno při průzkumu aplikace (2026-08-04):** admin UI neumožňuje smazat pokoj ani rezervaci – mazání existuje jen na úrovni API (`DELETE /api/room/{id}`, `DELETE /api/booking/{id}`). V UI testech se tedy mazání použije pouze jako úklid dat vytvořených v testu (přes API v teardownu), ne jako testovaný UI krok. Detailní zjištěné API/UI chování je v [implementačním plánu](../plans/2026-08-04-test-automation-framework.md).

## Mimo rozsah (zatím)

- CI/CD pipeline (GitHub Actions) – přidá se jako samostatný krok po dokončení testovací sady
- Message/Report API endpoint – jen okrajově, není priorita
- Hybridní API+UI testy (API setup pro UI testy) jako obecný princip – zvažováno, ale zamítnuto ve prospěch čistě oddělených sad; jedna cílená výjimka (jednorázový pokoj v `test_booking_a_room_shows_a_confirmation`) byla nakonec zavedena z nutnosti - viz dodatek u sekce 1

## Repozitář

- GitHub remote: https://github.com/MSembera/PythonTestsExample.git
