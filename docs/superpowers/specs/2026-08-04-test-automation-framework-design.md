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
| Kvalita kódu | `ruff` (lint+format) + `mypy` | konzistentní styl, typová kontrola |
| CI/CD | GitHub Actions | **později**, jako samostatný krok mimo tento návrh |

**Auth handling (API):** fixture `admin_token` se zaloguje přes `AuthClient` a token/cookie poskytne ostatním testům, které to potřebují (např. mazání pokoje vyžaduje auth).

**Auth handling (UI):** samostatná fixture provede login flow přes admin UI (ne přes API – sady jsou oddělené) a vrátí přihlášenou `page`, aby to nemusel opakovat každý admin test.

## 3. Životní cyklus testovacích dat a izolace

Každý test, který potřebuje entitu (booking/room), si ji **sám vytvoří a sám uklidí**:

- **API testy:** fixture s `yield` – v setupu vytvoří entitu přes API s Faker daty, testu předá její ID/data, po testu (i při selhání testu) ji smaže v teardownu.
- **UI testy:** obdobně, ale přes UI akce – např. admin test vytvoří pokoj přes formulář v adminu, otestuje ho, na konci ho smaže přes UI. Read-only public testy (browse rooms) pracují s existujícími daty; testy vytvářející booking si ho po sobě uklidí přes admin rozhraní.
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
- Správa pokojů: vytvoření, editace, smazání pokoje
- Správa rezervací: zobrazení seznamu, smazání rezervace
- Odhlášení

Cílem je z každé oblasti mít pár dobře napsaných testů (happy path + 1-2 negativní/edge case), které demonstrují návrh, ne kvantitu.

## Mimo rozsah (zatím)

- CI/CD pipeline (GitHub Actions) – přidá se jako samostatný krok po dokončení testovací sady
- Message/Report API endpoint – jen okrajově, není priorita
- Hybridní API+UI testy (API setup pro UI testy) – zvažováno, ale zamítnuto ve prospěch čistě oddělených sad

## Repozitář

- GitHub remote: https://github.com/MSembera/PythonTestsExample.git
