# SkillSwap

Learn what you need. Teach what you know.

SkillSwap connects people through reciprocal skill exchanges. The source is organized into three team-owned packages within one Django project. See [TEAM_STRUCTURE.md](TEAM_STRUCTURE.md) for the move inventory, deployment entry points and exact Git workflows. The existing HTML/CSS frontend is now connected to a Django ORM backend: accounts, profiles, teaching/learning skills, search, calculated matches, exchange requests, completion and participant reviews.

## Technologies and ownership

Python 3.14, Django 6.1.1, Django ORM, MongoDB Atlas, `django-mongodb-backend` 6.1.0, `python-dotenv`, Pillow, HTML5 and CSS3. No frontend framework or JavaScript was added.

| Member | Responsibilities | Main files |
| --- | --- | --- |
| Farhan | Authentication, profiles, homepage, configuration, database setup, integration | `farhan/accounts/`, `farhan/config/`, requirements, environment setup |
| Ankon | Skill catalog, teaching/learning skills, browsing, search and filters | `ankon/skills/` |
| Pranay | Matching, requests, workflow, reviews and dashboard | `pranay/exchanges/` |

## Setup

1. Clone your repository and open its project directory (currently `D:\skillshwap`).
2. Create a virtual environment if one does not already exist.
3. Activate it and install the requirements.
4. Copy `.env.example` to `.env` if `.env` does not already exist.
5. Edit `.env` and replace only the MongoDB URI placeholder with your real Atlas connection string. Use an Atlas database user with access to the chosen database and allow your development IP in Atlas Network Access. URL-encode special characters in the URI password.
6. Apply migrations, create an administrator, optionally seed demo data, and start Django.

PowerShell commands for a fresh checkout:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env now; insert your Atlas URI.
python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo  # optional; prints passwords for newly created demo users
python manage.py runserver
```

If activation is blocked, use `.\venv\Scripts\python.exe` in place of `python`; no execution-policy change is necessary. In Command Prompt, activate with `venv\Scripts\activate.bat`.

Open [SkillSwap](http://127.0.0.1:8000/) or [Django admin](http://127.0.0.1:8000/admin/).

The existing workspace `.env` and Atlas configuration are preserved. For a fresh checkout, after adding your own URI, the exact remaining commands are:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

`seed_demo` is optional. Migrations are committed, so `makemigrations` is not required on setup. After changing models, use `python manage.py makemigrations` followed by `python manage.py migrate`.

## Environment and MongoDB configuration

```dotenv
MONGODB_URI=your_mongodb_atlas_connection_string_here
MONGODB_NAME=skillswap
DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
```

Settings load `.env` with `load_dotenv(BASE_DIR / '.env')`. Process environment variables take precedence. `.env` and uploaded media are ignored by Git. Local development uses `DEBUG=True` in `.env`; without it, DEBUG defaults to False and a private secret key is required. `SECRET_KEY` is the preferred key variable; `DJANGO_SECRET_KEY` remains a compatibility fallback.

For Vercel, set `MONGODB_URI` (your existing Atlas connection string), `MONGODB_NAME`, `SECRET_KEY` (a private, random value), and `DEBUG=False` in the project environment variables for Production and any Preview deployments, then redeploy. Reuse your existing secret key value when moving to `SECRET_KEY` to preserve sessions. Local hosts and `.vercel.app` hosts are allowed, and HTTPS Vercel origins are trusted for CSRF validation; forms still require CSRF tokens. `DJANGO_ALLOWED_HOSTS` can add custom domains. Configure static/media serving and HTTPS for your deployment; MongoDB settings are unchanged.

MongoDB is the only configured application database. The old `db.sqlite3` is left untouched as a local artifact; the new backend does not read it. Old SQLite users are not automatically migrated to MongoDB.

Without a URI, `runserver`, `migrate`, and other database-dependent commands fail with a clear setup message. Offline `check`, `makemigrations`, and unit tests still work; `check` reports the expected `skillswap.W001` warning. An offline migration router skips only the database-history probe when no URI is configured; it does not change the backend or apply migrations elsewhere.

MongoDB-specific preparation includes:

- `ObjectIdAutoField` on all application models and compatible AppConfigs for Django's built-in User, permission/content type and admin models.
- Generated MongoDB migrations under `farhan/mongo_migrations/` for `auth`, `admin`, and `contenttypes`; normal app migrations under each app's `migrations/`.
- ObjectId URL converters, so malformed IDs give a 404 instead of an invalid field lookup.
- MongoDB backend `transaction.atomic()` for multi-document profile/account/skill writes. Atlas replica sets support these transactions; a local test MongoDB must also run as a replica set.
- ORM-only application reads and writes. No Djongo, MongoEngine, raw MongoDB queries or direct PyMongo CRUD.

Reference: [MongoDB backend configuration](https://django-mongodb-backend.readthedocs.io/en/latest/intro/configure/) and [MongoDB backend transactions](https://django-mongodb-backend.readthedocs.io/en/latest/topics/transactions/). The dependency versions are pinned together intentionally; update Django and the MongoDB backend to compatible major/minor versions together.

## Models and forms

| App | Models | Forms |
| --- | --- | --- |
| Accounts | `Profile` related one-to-one to Django's built-in `User` | `RegistrationForm`, `LoginForm`, `ProfileForm` |
| Skills | `SkillCategory`, `Skill`, `SkillOffer`, `SkillWanted` | `SkillForm` |
| Exchanges | `ExchangeRequest`, `Review` | `ExchangeRequestForm`, `ReviewForm` |

Catalog skill names are whitespace-normalized and case-folded for identity; “Django” and “ django ” match the same skill. A shared skill has one category. Each member can have at most one offer and one wanted record for a given catalog skill. Editing a skill changes the member's association/description, not another user's shared catalog record. Changing teaching to learning requires adding a separate record. Removing a member's skill preserves the catalog and historical exchanges.

Registration validates username/email, confirmation and Django's password rules; stores a hashed password; automatically creates a profile; and logs the member in. Login accepts username or email, handles inactive users, and redirects to the dashboard. Remember-me sets a two-week session; otherwise the session expires when the browser closes. Profiles accept validated JPG/PNG/WebP images up to 5 MB. Media is served locally only with DEBUG; production needs separate media serving.

## Matching and workflow

`pranay/exchanges/services.py` keeps matching and workflow rules outside views.

Matching uses canonical skill IDs. For each distinct other active user:

- 40 points if you teach something they want.
- 40 points if they teach something you want.
- 10 points when both directions match.
- 5 points for the same nonempty location (case-insensitive).
- 5 points when at least one compatible teacher's level meets the learner's selected level.

No shared skill means no match, even with the same location. Results are unique by user and ordered by score descending, then name/ID for stable ties. Scores range from 0 to 100 and are calculated from current records. One-way matches are shown, but creating an exchange requires a valid pair in both directions.

Request buttons open a skill-selection form that uses the existing form styling. Both selections are restricted on the server to skills one participant offers and the other wants. A unique active-pair key prevents duplicate pending/accepted exchanges between the same two people in either direction, including concurrent submissions. Terminal exchanges release that key.

| Action | Actor | Allowed state | Result |
| --- | --- | --- | --- |
| Send | Authenticated sender, different active recipient | Valid reciprocal skills, no active pair | Pending |
| Accept | Recipient only | Pending | Accepted |
| Reject | Recipient only | Pending | Rejected |
| Cancel | Sender for pending; either participant for accepted | Pending/accepted | Cancelled |
| Complete | Either participant | Accepted | Completed with timestamp |
| Review | A participant reviewing the other participant | Completed | One review per reviewer/exchange, rating 1–5 |

Transitions use conditional ORM updates against the expected old status, so a stale browser cannot overwrite a newer decision. Completed exchanges cannot be cancelled. Reviews have database uniqueness protection and server-side rating/participant validation. Average ratings and counts are queried with Django ORM aggregation.

All state-changing actions use POST and CSRF. Authenticated views and object-owner/participant filters enforce access independently of button visibility. Admin can inspect exchange/review records but cannot bypass workflow by adding or editing them directly. Live chat is intentionally not included.

## Views and URLs

Existing URL names are retained. ID routes now use MongoDB ObjectIds rather than integers.

| App | View/URL names |
| --- | --- |
| Project | `home` |
| Accounts | `login`, `register`, `logout`, `profile`, `edit_profile`, `user_profile` |
| Skills | `skills`, `my_skills`, `add_skill`, `edit_skill`, `remove_skill`, `delete_skill` (alias), `search_skills`, `skill_detail` |
| Exchanges | `dashboard`, `matches`, `exchange_requests`, `send_exchange_request`, `respond_exchange`, `exchange_detail`, `exchange_history`, `review`, `accept_exchange`, `reject_exchange`, `cancel_exchange`, `complete_exchange` |

Browse/search accepts `q`, `category`, `level`, `skill_type` (`teach`/`learn`), `location`, and `page` as applicable. Search uses ORM `Q` expressions for skill, category and user names. Pagination preserves filters. Profile, dashboard and homepage statistics use real data, including zero counts. Empty databases show the existing empty-state designs.

## Demo data

`python manage.py seed_demo` explicitly creates `farhan_demo`, `ankon_demo`, and `pranay_demo`, seven categories and six skills, complementary offers/wants, and a completed exchange with a review when practical. Passwords are random and printed only for newly created accounts. Keep them if you want to log in as those accounts. Rerunning preserves existing passwords and avoids duplicate demo records. Matches are calculated, not seeded as fixed percentages. Seeding never runs automatically. With DEBUG=False, the command requires the explicit `--allow-production` flag.

## Verification

Offline (no database URI):

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test farhan.accounts
python tools/check_templates.py
```

Database integration (a configured MongoDB replica set or Atlas connection is required):

```powershell
python manage.py test tests.integration
```

Django creates and destroys `test_<MONGODB_NAME>` for this suite. Use a development/test database account with the necessary permissions. Tests cover registration/login, profile updates and invalid uploads, skill ownership and duplicates, filtered searches, matching, reciprocal request validation, duplicate-pair indexes, transitions, review rules, rendering of real objects and seed idempotency. Do not point integration tests at a database named `test_<MONGODB_NAME>` that contains data you want to retain.



## Frontend preservation and file changes

The existing stylesheet, navigation, footer, card classes, page layouts and responsive rules are preserved. Template edits are limited to real values, valid ID links, POST actions, and workflow controls. `pranay/exchanges/templates/exchanges/send_request.html` adds the necessary skill-selection step using existing form classes. The landing-page Farhan/Ankon illustration remains a clearly labeled example; lists, ratings and statistics use database values.

Created: models/forms/admin modules in all three apps; account signals/backend/presentation helpers; exchange services; seed command; application and built-in migrations; MongoDB configuration helpers; `.env.example`; integration tests; this README.

Modified: settings, URL modules, app configurations, existing views, requirements, `.gitignore`, regression tests, selected template data bindings and actions, and the standalone frontend preview exporter. The existing `.env` is preserved and ignored by Git; `.env.example` contains only setup placeholders. See `README_FRONTEND.md` for the original design/component inventory.
