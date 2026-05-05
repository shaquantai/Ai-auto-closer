# AI Auto Closer (Lofty Companion)

This is a **daily follow-up helper** for your existing Lofty CRM workflow.
It does not replace Lofty.

## What this gives you every day

1. A ranked follow-up list (`daily_followup_priority.csv`)
2. Lead scoring (0–100) based on motivation + activity + recency
3. Natural text message drafts (`daily_text_drafts.csv`)
4. A short daily action plan in your terminal

## Input format (from Lofty export)

Required columns:
- `name`
- `phone`
- `stage`
- `motivation` (0–10)
- `last_contact_date` (prefer `YYYY-MM-DD`; `MM/DD/YYYY` accepted)
- `touches_7d`
- `property_views_7d`
- `replied_30d` (`yes/no`)
- `preferred_area`
- `notes`

## Run it

```bash
python3 lead_assistant.py --input leads_example.csv --top 5 --output-dir ./out
```

Optional run date (helpful for backtesting):

```bash
python3 lead_assistant.py --input leads_example.csv --date 2026-05-01
```

## Daily Lofty workflow

1. Export leads from Lofty to CSV.
2. Run this script.
3. Open `daily_followup_priority.csv` to see who to contact first.
4. Copy/paste from `daily_text_drafts.csv` into Lofty SMS.
5. Log replies and outcomes back in Lofty.

## Notes

- If required columns are missing, the script clearly tells you what is missing.
- Scoring logic is in `score_lead()` inside `lead_assistant.py`.
