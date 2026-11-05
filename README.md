# Kerala IT Job Search

A free, fresher-focused Python job-alert project for Kerala, covering QA/software testing and cybersecurity.

## Features
- Scrapes configured public Infopark, Technopark and employer career pages.
- Filters QA, manual testing, automation testing, SOC, cybersecurity, VAPT, security analyst, trainee and internship roles.
- Targets fresher / 0–1 year opportunities; excludes senior roles and experience requirements above the target.
- Stores listings in SQLite and avoids repeat notifications.
- Sends Telegram alerts using the official Telegram Bot API.
- Provides LinkedIn search shortcuts and a manual CSV import workflow. It does **not** scrape LinkedIn or automate a logged-in LinkedIn account.
- Adds conservative listing checks: VERIFIED, CROSS-CHECKED, UNVERIFIED and SUSPICIOUS. These labels are indicators only, not guarantees of recruiter identity or job legitimacy.
- Runs twice daily using GitHub Actions (08:00 and 18:00 IST).

## Local setup
1. Install Python 3.12 or later.
2. Create and activate a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env`.
5. Create a Telegram bot with @BotFather, send it /start, and run `python scripts/get_chat_id.py`.
6. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to `.env`.
7. Run `python -m src.main`.

## LinkedIn
Run `python -m src.linkedin` to print searches. Create LinkedIn's built-in job alerts, then export/enter selected vacancies into `data/linkedin_jobs.csv` using the example CSV format. The import runs as part of the next job scan.

## GitHub Actions
Add repository secrets named `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` under Settings → Secrets and variables → Actions. Enable Actions and run the workflow manually once to test.

The workflow's cron runs at 02:30 and 12:30 UTC, corresponding to 08:00 and 18:00 IST. GitHub may delay scheduled runs; they are not guaranteed to start at the exact minute. The database is committed back to the repository to retain duplicate history.

## Safety and accuracy
- Check the original employer page before applying. A park-board listing is not independent proof of an offer.
- Never pay application, interview, training, placement or security-deposit fees based solely on a job message. Never disclose OTPs, passwords, UPI PINs or card credentials.
- A SUSPICIOUS flag reflects risky wording; a personal email or WhatsApp contact is a warning for manual review, not conclusive proof of fraud.
- Scrapers depend on public page layouts. A layout change or JavaScript-rendered page can produce a warning; an empty parse is not proof that no jobs exist.
- Respect each site's terms and robots rules; use reasonable request intervals.

## Tests
Run `pip install pytest` then `python -m pytest -q`.

## License
MIT.
