# SkillSwap frontend

**Learn what you need. Teach what you know.**

A complete, responsive frontend using HTML5, CSS3 and Django templates. No JavaScript, frameworks, external fonts or UI libraries. Django now connects the pages to real accounts, skills, matching, exchanges and reviews through MongoDB-compatible ORM models.

## Backend status

The complete Django ORM backend is now implemented. Follow [README.md](README.md) for MongoDB Atlas setup, migrations, authentication, workflows and testing. The original frontend component inventory below is retained. The static exporter remains an optional design preview, not the running application.

## Files and ownership

```text
templates/
  base.html                         Farhan: document, messages, shared layout
  home.html                         Farhan: landing page
  includes/
    navbar.html, nav_links.html, account_links.html, footer.html
    empty_state.html, form_errors.html, pagination.html, workspace_nav.html
    profile_content.html            Farhan
    skill_card.html, person_card.html, managed_skill.html  Ankon
    match_card.html, request_card.html, request_table.html,
    history_card.html               Pranay
farhan/accounts/templates/accounts/  Farhan
  login.html, register.html, profile.html, edit_profile.html, user_profile.html
ankon/skills/templates/skills/        Ankon
  skills.html, add_skill.html, skill_detail.html, search_skills.html, my_skills.html
pranay/exchanges/templates/exchanges/ Pranay
  dashboard.html, matches.html, exchange_requests.html,
  exchange_detail.html, exchange_history.html, review.html, send_request.html
static/css/style.css                Shared stylesheet, coordinated by Farhan
tools/check_templates.py            Optional development-only validation/export
```

App templates moved without content changes. Template lookup names such as `accounts/login.html` remain unchanged because Django uses app template discovery. Python ownership markers use one short comment per major file. Historical ownership comments remain in the preserved HTML. Django requires `extends` as the first template tag, so ownership comments follow it on child pages. Ankon owns the SKILLS CSS section; Pranay owns DASHBOARD and EXCHANGES; Farhan maintains global styles and shared components.

## Preview without implementing the backend

Python and Django 5.1+ are needed to render these templates (`querystring` requires 5.1+). The templates cannot be opened directly as working HTML because browsers do not interpret Django tags.

```powershell
python tools/check_templates.py --preview-dir "$env:TEMP\skillswap-preview"
python -m http.server 8080 --bind 127.0.0.1 --directory "$env:TEMP\skillswap-preview"
```

Open `http://127.0.0.1:8080`. This exports disposable HTML and serves files only. It does not create a Django application. The validator uses temporary URL definitions solely to verify template URL reversal. Run `python tools/check_templates.py` to validate without exporting files. Stop the static server with Ctrl+C.

Preview navigation links between all 17 pages. Search forms, uploads, authentication and mutation buttons require the future backend. Demo submission buttons are disabled. The mobile menu, received/sent request switch and rating selection work with native HTML and CSS only. Search/filter forms use GET; their results require server rendering.

## Template integration contract

The project already configures `TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates']`, `APP_DIRS=True`, and the `request`, `auth` and `messages` context processors, plus sessions, authentication, CSRF and messages middleware. Views use `render(request, template_name, context)`.

Set `STATIC_URL = '/static/'` and `STATICFILES_DIRS = [BASE_DIR / 'static']`; enable `django.contrib.staticfiles`. During development, `manage.py runserver` serves these assets when DEBUG is enabled. For deployment, set a separate `STATIC_ROOT`, run `manage.py collectstatic`, and configure static serving in your deployment. Profile uploads use media storage, not the static directory; connect `MEDIA_ROOT` and `MEDIA_URL` separately.

Every template extends `base.html`. It includes the navbar and footer, has a messages area, and exposes `title` and `content` blocks. Reuse card includes rather than duplicating markup. No template tags are marked `safe`; user text remains escaped.

The real application omits `demo_mode`; data comes from ORM views. Set it explicitly to `True` only for demonstrations. Never derive it from an untrusted query parameter. Real lists use loops and empty states; sample cards appear only in demo mode. Supply complete objects according to the contract below, since individual detail fields also have presentation fallback text.

On GET, provide an initialized Django `form`. On invalid POST, pass the **bound** form back to the same template. The hand-written inputs bind to `form.<field>.value`; forms display per-field and non-field errors through a shared summary. Passwords and files are not repopulated. For edit views initialize the form from the current object. For add-skill GET, use the validated `skill_type` query parameter (`teach` or `learn`) as the form's initial value. Pass `editing=True` when reusing `skills/add_skill.html` for edits.

Server validation, permissions and ownership checks are implemented in the app forms, views and exchange services. Skill removal, logout, exchange requests and request responses are POST forms with CSRF tokens. A send-request view must determine a valid offered/wanted skill pairing, or render a selection step when ambiguous; a user ID alone is not a complete exchange. Exchange controls now use POST workflow routes with server-side state checks.

## URL contract

These names are intentionally unnamespaced and are now registered in the app URL modules. Preserve them when extending views, or update all template references consistently. Missing routes raise `NoReverseMatch`; they are not silently replaced with dead links. ID routes receive one MongoDB ObjectId `pk`. The methods below describe the backend contract.

| URL name | ID | Expected method / template |
| --- | --- | --- |
| `home` | — | GET `home.html` |
| `login` | — | GET/POST `accounts/login.html` |
| `register` | — | GET/POST `accounts/register.html` |
| `logout` | — | POST, then redirect |
| `profile` | — | GET `accounts/profile.html`, current user |
| `edit_profile` | — | GET/POST `accounts/edit_profile.html` |
| `user_profile` | user | GET `accounts/user_profile.html` |
| `skills` | — | GET `skills/skills.html` |
| `add_skill` | — | GET/POST `skills/add_skill.html` |
| `edit_skill` | skill | GET/POST same form, `editing=True` |
| `remove_skill` | skill | POST, then redirect to `my_skills` |
| `skill_detail` | skill | GET `skills/skill_detail.html` |
| `search_skills` | — | GET `skills/search_skills.html` |
| `my_skills` | — | GET `skills/my_skills.html` |
| `dashboard` | — | GET `exchanges/dashboard.html` |
| `matches` | — | GET `exchanges/matches.html` |
| `exchange_requests` | — | GET `exchanges/exchange_requests.html` |
| `send_exchange_request` | recipient user | POST, create/validate request then redirect |
| `respond_exchange` | exchange | POST `decision=accept` or `reject`, then redirect |
| `exchange_detail` | exchange | GET `exchanges/exchange_detail.html` |
| `exchange_history` | — | GET `exchanges/exchange_history.html` |
| `review` | exchange | GET/POST `exchanges/review.html`; GET shows existing review if present |

## Context contract

The objects below can be models, presentation objects or dictionaries; methods such as `get_full_name` and `get_category_display` can be callable methods (Django calls no-argument methods) or supplied strings. Missing collections should be empty lists. Supply numeric zero explicitly where applicable.

| Page | Context |
| --- | --- |
| All | `request`, `user`, `messages`, optional `demo_mode`; forms receive `form` |
| Home | `popular_skills`; optional `community` with `members`, `skills`, `exchanges`, `rating` |
| Own/other profile | `profile`, `teaching_skills`, `learning_skills` |
| Browse | `skills`, optional `page_obj`; GET `q`, `category` |
| Search | `people`, optional `page_obj`; GET `q`, `category`, `level`, `skill_type`, `location` |
| Skill detail | `skill`, `teachers` (person objects) |
| My skills | `teaching_skills`, `learning_skills` |
| Add/edit skill | `form`, optional `editing` |
| Dashboard | `stats`, `recommended_matches`, `recent_requests` |
| Matches | `matches`, optional `page_obj` |
| Requests | `received_requests`, `sent_requests` |
| Exchange detail | `exchange` |
| History | `completed_exchanges`, optional `page_obj` |
| Review | `exchange`, optional existing `review`, or `form` |

- **User:** `pk`, `first_name`, `username`, `get_full_name`, `date_joined`, `is_authenticated`.
- **Profile:** `user`, `location`, `bio`, optional `image.url`, `completed_exchanges`, `rating`, `review_count`. Pass the viewed member here; the navbar still uses the authenticated `user`.
- **Skill:** `pk`, `name`, `description`, `get_category_display`, `get_level_display`, `get_skill_type_display`, `owner` (user), `successful_exchanges` for profile cards.
- **Person search result:** `pk` (user ID), `first_name`, `get_full_name`, `location`, `rating`, `offered_skill`, `wanted_skill`. Flatten profile values into the result object or adapt the include.
- **Match:** `pk`, `person` (person object), `percentage` (0–100, backend calculated), `you_teach`, `you_learn`. Percentages are shown using native `<meter>` elements; no frontend calculation.
- **Exchange:** `pk`, `partner` (user), `you_teach`, `you_learn`, `offered_skill`, `wanted_skill`, `status`, `get_status_display`, `completed_at`, optional `review`. `offered_skill`/`wanted_skill` describe the request sender's offer; `you_teach`/`you_learn` are relative to the viewer. Status codes: `pending`, `accepted`, `learning`, `completed`, `rejected`, `cancelled`.
- **Review:** `rating` (integer 1–5), `comment`, `created_at`.
- **Dashboard stats:** `active_skills`, `pending_requests`, `matches`, `completed_exchanges`.
- **Pagination:** supply the current page's items in the relevant list and `page_obj`. The `querystring` tag preserves current filters in next/previous links.

### Form field names

- Login: `username` (username or email), `password`, `remember_me`. Email login and remember-me session policy need custom backend handling.
- Register: `first_name`, `last_name`, `username`, `email`, `password1`, `password2`. Enforce password matching and validators on the server.
- Edit profile: `first_name`, `last_name`, `email`, `location`, `bio`, `image`. Bind both `request.POST` and `request.FILES`.
- Skill: `name`, `skill_type` (`teach`, `learn`), `category`, `level`, `description`.
- Categories: `programming`, `design`, `language`, `business`, `photography`, `music`, `other`.
- Levels: `beginner`, `intermediate`, `advanced`, `expert`.
- Review: `rating` (1–5), `comment`.

## Placeholder inventory

The homepage hero is an explicitly labeled Farhan/Ankon example. Homepage community counts default to the requested illustrative 1,250+, 350+, 2,100+ and 4.8/5 and show a sample-data caption when `community` is absent. Demo mode adds a visible notice on every page and enables sample skills, profiles, matches (95%, 87%, 80%), requests and exchange history dated 12 September 2026. Profile images are initials unless a real image is provided. Fallback detail strings are presentation examples; populate full context for production. No statistics or matching scores are calculated here.

Responsive breakpoints are 1100, 900 and 650 pixels. All styling is in `static/css/style.css`; mobile navigation uses native `<details>`, request switching uses keyboard-accessible radios, and rating choices use labeled native radio inputs. There are skip links, visible focus indicators, semantic landmarks, form labels, readable status text and reduced-motion support.
