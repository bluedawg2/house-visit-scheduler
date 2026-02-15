# House Visit Scheduler

Streamlit app for scheduling house visits. Guests book dates; admin accepts/rejects.

## Commands

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Architecture

- `app.py` — Entry point. Multi-page Streamlit app with hidden navigation.
- `guest_view.py` — 3-step booking wizard (dates → details → confirmation). Default page at `/`.
- `admin_view.py` — Admin dashboard at `/admin` (requests, availability, history, settings).
- `database.py` — SQLite layer. DB file: `calendar.db` (auto-created, WAL mode).
- `email_service.py` — SMTP email sending with .ics calendar attachments.
- `styles.py` — CSS injection for guest/admin views (step indicator, badges, background).
- `docs/` — User-facing guides (admin + visitor).

## Key Patterns

- All dates stored as ISO strings (`YYYY-MM-DD`) in SQLite.
- Removing availability auto-rejects pending requests that no longer fit.
- Accepted bookings are carved out of availability ranges (guests don't see booked dates as green).
- Guest and admin views both define `_get_gmail_config()` independently (reads `st.secrets["gmail"]`).

## Configuration

Gmail credentials in `.streamlit/secrets.toml`:
```toml
[gmail]
address = "you@gmail.com"
app_password = "xxxx xxxx xxxx xxxx"
```

Admin emails and booking rules (min/max stay) are stored in the `config` table in SQLite.

## Gotchas

- Admin page has no auth — anyone with the `/admin` URL can manage bookings.
- Custom background: place `assets/background.{jpg,jpeg,png,webp}` in project root. Falls back to CSS gradient.
- `streamlit-calendar` wraps FullCalendar. Background events use `display: "background"` with CSS hacks to hide text.
- No tests in the project.
