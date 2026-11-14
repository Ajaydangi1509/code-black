# Code Black — Full-stack website starter

A custom multi-page cybersecurity company website built with:
- **Frontend:** HTML, CSS, vanilla JavaScript
- **Backend:** Python + FastAPI
- **Templates:** Jinja2
- **Database:** SQLite
- **Motion:** CSS keyframes + IntersectionObserver scroll reveals

This is designed as a learning project: readable code, no frontend build pipeline, and a real backend for enquiry storage.

## Pages
- `/` — custom homepage with animated radar graphic and scroll sections
- `/services` — all five service descriptions
- `/about` — founder/company principles (avoid inventing credentials)
- `/careers` — internship expression-of-interest form
- `/contact` — lead generation form
- `/privacy` — development-stage privacy notice placeholder
- `/health` — simple backend health endpoint

## Run locally

### 1. Create and activate a virtual environment

Windows PowerShell:
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install packages
```bash
python -m pip install -r requirements.txt
```

### 3. Start FastAPI
From the project root:
```bash
uvicorn app.main:app --reload
```

Open:
- Website: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

The first run creates `codeblack.db` in the project root.

## How lead generation works
1. Visitor fills the contact form.
2. Browser JavaScript sends JSON to `POST /api/enquiries`.
3. FastAPI validates the fields using Pydantic.
4. The backend inserts the enquiry into SQLite using parameterized SQL.
5. The browser displays a success or error message.

The careers form uses `POST /api/applications` and stores expressions of interest separately.

**Important:** submissions are stored in SQLite only. This starter does not send email notifications, does not include a CRM, and does not provide an admin dashboard. Do not tell visitors that an email has been sent. For the real launch, add an email provider and a protected admin workflow, or connect a CRM.

## Learn the animation code
Open `app/static/js/site.js`:
- `IntersectionObserver` adds `.is-visible` when an element enters the viewport.
- `prefers-reduced-motion` disables motion for users who request it.
- scroll listener updates the reading-progress bar.
- CSS transitions animate opacity and vertical position.

Open `app/static/css/site.css`:
- `@keyframes spin` rotates the radar sweep.
- `@keyframes pulse` animates the small status dot.
- `@keyframes point` animates radar points.
- `@media` rules make the site responsive.

## Before public launch — required work
This is a starter, not a production-hardened business platform.

1. Replace the privacy placeholder with a reviewed policy containing the real operator/contact details, purpose, legal basis where applicable, retention, deletion, processors, and international-transfer disclosures.
2. Add a monitored business email and configure email notifications.
3. Add persistent production database hosting/backups; SQLite on ephemeral hosting may lose data on redeploy or instance replacement.
4. Replace the in-memory rate limiter with a shared production rate limiter (Redis or host-level controls); configure trusted proxy handling.
5. Add CSRF/origin controls if cookie-authenticated features are introduced. Do not add an unauthenticated admin endpoint.
6. Add structured logging, monitoring, error handling, database migration management, backups, and a retention/deletion process.
7. Use HTTPS, secure deployment settings, secrets via environment variables, and a proper domain.
8. Test accessibility, form spam protection, privacy requirements, and mobile performance.
9. Only advertise services you can actually deliver. Every security test must have explicit written authorization, defined scope, permitted methods, timing, exclusions, and escalation contacts.
10. For international enquiries, get suitable legal/privacy advice for the jurisdictions where you operate.

## Suggested learning path while building
1. HTML structure and semantic sections.
2. CSS layout, responsive design, variables, transitions and keyframes.
3. JavaScript DOM, events, FormData, fetch and IntersectionObserver.
4. HTTP methods, JSON, status codes and browser network panel.
5. FastAPI routes, request models, validation and API docs.
6. SQLite tables, parameterized queries and data lifecycle.
7. Production deployment, email delivery, CRM integration and security hardening.
