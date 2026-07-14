# AI Resume Optimizer Pro

A Django-based AI resume optimizer that analyzes a resume against a job description,
scores it for ATS (Applicant Tracking System) compatibility, rewrites the content to
better match the role **without changing layout/formatting**, and generates tailored
interview questions with an AI mock-interview coach.

Built with Django, the Groq API (`llama-3.3-70b-versatile`), Bootstrap 5, Chart.js, and SQLite.

---

## ⚠️ Honest notes before you start

- **AI-detector claims**: no tool can *guarantee* rewritten text passes GPTZero,
  Originality.ai, Copyleaks, or similar detectors — those tools are themselves
  imperfect and change often. The rewrite prompt (`analysis/services/prompts.py`)
  is engineered to avoid common AI-sounding phrasing and produce natural, varied,
  recruiter-style writing, which is the real, defensible way to reduce AI-detection
  risk. Treat any "95–100% guaranteed to pass" marketing claim, including from other
  tools, with skepticism.
- **Layout preservation**: for **DOCX** resumes, the app edits your original file's
  paragraphs in place — same fonts, spacing, bullet styles, and section order. For
  **PDF** resumes, in-place text replacement is not reliably possible (PDFs are not a
  paragraph-based format), so the app generates a clean, ATS-friendly single-column
  document using the same section headings/order instead of visually editing the PDF.

---

## Features

- Drag-and-drop resume upload (PDF/DOCX) with text + section extraction
- Paste or upload a job description
- AI-powered ATS analysis: keyword match, skills match, recruiter match, formatting,
  grammar, and readability scores, plus section-by-section strengths/weaknesses
- Deterministic formatting checks (tables, columns, images) computed from the DOCX
  file itself, not guessed by the LLM
- AI resume rewrite that preserves structure and naturally works in missing keywords
- Layout-preserving DOCX/PDF/TXT export of the optimized resume
- Side-by-side comparison view with an AI-generated change log and rationale
- AI-generated interview question bank (technical, HR, behavioral, role-specific)
  with sample answers, tips, and difficulty ratings
- AI mock interview: answer questions, get instant scoring (confidence, grammar,
  technical accuracy, communication, STAR method) and a model answer
- Dashboard with history, stats, and an ATS-improvement chart
- Dark/light theme, glassmorphism UI, responsive sidebar layout

---

## Project structure

```
resume_optimizer/
├── core/                  # Django project settings, urls, middleware
├── authentication/        # Register/login/logout, user profile & Groq key override
├── dashboard/              # Landing page, home dashboard, history, settings
├── resumes/                # Resume/JD upload, parsing (pdfplumber/PyMuPDF/python-docx)
├── analysis/                # ATS analysis, prompts, Groq client, rewriter, exports
│   └── services/
│       ├── groq_client.py   # Resilient Groq API wrapper (retries, JSON repair)
│       ├── prompts.py        # All prompt engineering lives here
│       ├── scoring.py         # Deterministic keyword/formatting helpers
│       └── rewriter.py         # Layout-preserving DOCX/PDF/TXT generation
├── interview/               # Interview question generation + mock interview
├── templates/                # All HTML templates (Bootstrap 5 + Chart.js)
├── static/                    # theme.css (design tokens) + app.js (UI behavior)
├── requirements.txt
├── .env.example
└── manage.py
```

---

## 1. Installation

```bash
# clone / unzip the project, then:
cd resume_optimizer
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# edit .env and add your GROQ_API_KEY (see step 2 below)

python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

Visit `http://127.0.0.1:8000`.

## 2. Groq API setup

1. Create a free account at [console.groq.com](https://console.groq.com)
2. Go to **API Keys** → **Create API Key**
3. Copy the key (starts with `gsk_...`)
4. Paste it into `.env` as `GROQ_API_KEY=gsk_...`, **or** log into the app and paste
   it under **Settings → Groq API Key** to use your own key instead of the server default
5. The default model is `llama-3.3-70b-versatile`; change `GROQ_MODEL` in `.env` to
   switch to any other current Groq-hosted model

## 3. Switching from SQLite to PostgreSQL

`core/settings.py` contains a commented-out `DATABASES` block for PostgreSQL — just
uncomment it, set `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT` in `.env`,
install `psycopg2-binary`, and re-run `python manage.py migrate`.

## 4. Security & performance notes

- CSRF protection is on by default (Django middleware); all POST forms include `{% csrf_token %}`
- File uploads are validated for extension and size (`resumes/forms.py`)
- A simple per-user, per-minute rate limit guards the AI endpoints (`AI_RATE_LIMIT_PER_MINUTE` in `.env`)
- All requests to `/analysis/` and `/interview/` are logged with timing to `app.log`
  (`core/middleware.py`) so slow or failing AI calls are easy to spot
- The Groq client retries transient failures and repairs near-JSON responses before parsing

## 5. Deployment

### Render / Railway
1. Push this project to a GitHub repo
2. Create a new **Web Service**, connect the repo
3. Build command: `pip install -r requirements.txt && python manage.py migrate`
4. Start command: `gunicorn core.wsgi:application`
5. Add environment variables from `.env.example` (including `GROQ_API_KEY`) in the
   platform's dashboard
6. Set `DJANGO_ALLOWED_HOSTS` to your Render/Railway domain

### PythonAnywhere
1. Upload the project (or `git clone` it in a Bash console)
2. Create a virtualenv and `pip install -r requirements.txt`
3. Set environment variables in the **Web** tab's WSGI config file
4. Point the WSGI file at `core.wsgi.application`
5. Run `python manage.py migrate` from a console, then reload the web app

### Docker
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
```
```bash
docker build -t resume-optimizer .
docker run -p 8000:8000 --env-file .env resume-optimizer
```

---

## Known limitations / good next steps

- PDF-origin resumes are re-typeset (see the honesty note above) rather than edited pixel-for-pixel
- The section-splitting heuristic (`resumes/utils/parsers.py`) covers common resume
  formats but may need tuning for very unusual layouts
- Background/async processing (e.g. Celery) is not wired up; AI calls run synchronously
  inside the request — fine for a single user, but add a task queue before scaling
- No automated test suite is included yet; the pipeline was verified manually end-to-end
  (upload → parse → analyze → rewrite → export → interview → mock interview)
# Resume-Optimizer-ATS
