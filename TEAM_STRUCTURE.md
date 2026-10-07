# SkillSwap team structure

This repository is **one Django + MongoDB application**, deployed from the root containing `manage.py`. Team folders are Python packages, not independent projects.

## Move inventory

| Original location | New location | Contents preserved |
| --- | --- | --- |
| `config/` | `farhan/config/` | Settings, root URLs, WSGI/ASGI, homepage, MongoDB AppConfigs/router, ObjectId converter |
| `accounts/` | `farhan/accounts/` | Models, forms, views, URLs, admin, signals, authentication backend, presentation helpers, checks, tests, seed command, existing migrations |
| `mongo_migrations/` | `farhan/mongo_migrations/` | Existing auth, admin and contenttypes migrations |
| `templates/accounts/` | `farhan/accounts/templates/accounts/` | All five account/profile templates |
| `skills/` | `ankon/skills/` | Models, forms, views, URLs, admin, AppConfig and existing migrations |
| `templates/skills/` | `ankon/skills/templates/skills/` | All five skill templates |
| `exchanges/` | `pranay/exchanges/` | Models, forms, views, URLs, services, admin, AppConfig and existing migrations |
| `templates/exchanges/` | `pranay/exchanges/templates/exchanges/` | All seven exchange/dashboard/review templates, including the selection form |

Shared root files remain: `manage.py`, requirements, `.env` (ignored), `.env.example`, `.gitignore`, README documents, `templates/base.html`, `templates/home.html`, `templates/includes/`, `static/`, `tests/`, and `tools/`. Existing local database/media/environment files are not relocated or committed.

## Imports, settings and database identity

- Python paths become `farhan.accounts`, `ankon.skills`, `pranay.exchanges`, and `farhan.config`. Cross-app imports, test mocks, authentication backend paths, URL includes and the profile migration's upload callable import are updated accordingly.
- AppConfig **labels remain** `accounts`, `skills`, and `exchanges`. Relationship strings such as `skills.Skill`, migration dependencies, model labels, collection names and permissions retain their original names. `ObjectIdAutoField` is preserved.
- `DJANGO_SETTINGS_MODULE` is `farhan.config.settings`; `ROOT_URLCONF` is `farhan.config.urls`.
- WSGI entry point: `farhan.config.wsgi.application`. ASGI entry point: `farhan.config.asgi.application`.
- `BASE_DIR` still resolves to the repository root. `.env`, static files, shared templates and media paths therefore retain their original locations.
- `MIGRATION_MODULES` points to `farhan.mongo_migrations.admin`, `.auth`, and `.contenttypes`. Existing migration files are moved, not regenerated. The Profile migration only changes the import path for its existing upload callable.
- App templates are discovered through `APP_DIRS=True`; their lookup names and every public URL remain unchanged. The standalone preview exporter searches the new app template directories too.
- A small middleware translates the old authentication backend string in existing signed sessions to its new Python path, preserving logins across the move.
- MongoDB engine, URI, database name, environment file and credentials are unchanged. No SQLite fallback is introduced.

## Migration reconciliation encountered during validation

The connected Atlas database contained an existing user and profile but lacked the corresponding initial migration history. A normal migration attempt therefore found an existing `auth_user` collection. This was not resolved by resetting the database.

The existing user/profile records were validated against the preserved models. Missing indexes and implicit authentication relationship collections were added through the installed Django MongoDB schema editor. Initial migrations for already-existing compatible collections were recorded with `migrate --fake-initial`; genuinely missing collections were created by the existing migrations. Before/after fingerprints confirmed the existing user and profile records were unchanged.

This was a one-time repair of the connected database's incomplete migration state. Normal future runs use `python manage.py migrate`. **Do not routinely use `--fake` or `--fake-initial`, regenerate initial migrations, or delete collections.**

## Local and deployment entry points

Final validation after the move:

- `python manage.py check`: passes with no issues.
- `python manage.py migrate`: passes; no pending migrations after the one-time reconciliation described above.
- `python manage.py makemigrations --check --dry-run`: no changes detected.
- 26 unit/integration tests passed against Atlas using a newly created, isolated test database, which the test runner removed afterward. This covered registration/login/logout, profile edits, skill CRUD and ownership, search, matching, accept/reject/cancel/complete, review rules, dashboard and page rendering.
- 85 standalone template render checks passed.
- `python manage.py runserver`: starts successfully. Live HTTP checks passed for homepage, registration, login, browse/search, protected dashboard redirect and the unchanged stylesheet.
- Fingerprint checks confirmed identical `.env` and database configuration, every original template/CSS file, URL patterns, model labels, collection names, primary-key types and migration identities.

Run the unit checks with `python manage.py test farhan.accounts`; the integration module remains `tests.integration`. App labels used in ORM relationships and migration commands remain `accounts`, `skills`, and `exchanges`—the longer paths are Python import/test paths only.

Run all commands from the repository root:

```powershell
.\venv\Scripts\Activate.ps1
python manage.py check
python manage.py migrate
python manage.py runserver
```

For a process manager already configured to serve WSGI/ASGI, update its application module to `farhan.config.wsgi:application` or `farhan.config.asgi:application`. If it sets `DJANGO_SETTINGS_MODULE` externally, update it to `farhan.config.settings`. Keep its working directory at the repository root. Deploy the entire merged repository. No deployment provider was changed and no three-service deployment was introduced.

Use the current requirements and existing production environment configuration. For deployment, retain the README's DEBUG/SECRET_KEY/host/static/media setup. Do not upload `.env` to GitHub.

## Git workflow

The inspected workspace did not contain a `.git` directory. No repository, remote, branch, commit or push was created automatically. The following commands assume you are in your team's existing Git clone with `origin` configured and a `main` branch. If this folder is a downloaded ZIP, first use the team's actual Git clone or initialize/configure its remote yourself.

**One-time restructuring integration:** commit the entire move together on one integration branch before dividing later work. Staging only a destination folder in that initial commit would omit root import changes and source deletions.

```powershell
git switch main
git pull --ff-only origin main
git switch -c team-folder-restructure
git add -A
git diff --cached --stat
git status --short
git commit -m "Organize SkillSwap into team-owned packages"
git push -u origin team-folder-restructure
```

Open a pull request from `team-folder-restructure` to `main`, review, and merge. `.gitignore` excludes local environments, `.env` variants, bytecode, local databases, media and private-key files; `.env.example` remains trackable. Inspect the staged list before committing.

After the restructure is merged, use these independent workflows. If a branch already exists, use `git switch <branch>` instead of `git switch -c <branch>`.

### Farhan

```powershell
git switch main
git pull --ff-only origin main
git switch -c farhan-part
git add farhan/
git add manage.py requirements.txt .gitignore .env.example README.md README_FRONTEND.md TEAM_STRUCTURE.md
git add templates/ static/ tests/ tools/
git diff --cached --stat
git commit -m "Add accounts and project integration by Farhan"
git push -u origin farhan-part
```

Open PR: `farhan-part` → `main`. Farhan coordinates shared changes and deployment configuration.

### Ankon

```powershell
git switch main
git pull --ff-only origin main
git switch -c ankon-part
git add ankon/
git diff --cached --stat
git commit -m "Add skills module by Ankon"
git push -u origin ankon-part
```

Open PR: `ankon-part` → `main`.

### Pranay

```powershell
git switch main
git pull --ff-only origin main
git switch -c pranay-part
git add pranay/
git diff --cached --stat
git commit -m "Add matching and exchange module by Pranay"
git push -u origin pranay-part
```

Open PR: `pranay-part` → `main`.

These commit commands are for actual future changes; Git correctly reports nothing to commit if your branch has no changes.
