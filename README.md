# AI Auto Closer (Lofty Companion)

This is **not a replacement CRM**.
It is a lightweight helper you can run daily with a CSV export from **Lofty CRM** to decide who to follow up with, what to do, and what to text.

## What it does

1. **Daily follow-up priority list**: ranks leads by urgency.
2. **Lead scoring**: combines motivation, engagement, and recency into a 0–100 score.
3. **Natural text drafts**: gives conversational SMS drafts for each lead.
4. **Daily action suggestions**: outputs a short action plan for the day.

## Files

- `lead_assistant.py` — main script.
- `leads_example.csv` — sample data in the expected format.

## Quick start

```bash
python3 lead_assistant.py --input leads_example.csv --top 5
```

## Lofty workflow (simple)

1. In Lofty, export your leads to CSV (daily or every morning).
2. Ensure columns match this format:
   - `name`
   - `phone`
   - `stage`
   - `motivation` (0-10)
   - `last_contact_date` (`YYYY-MM-DD` preferred)
   - `touches_7d`
   - `property_views_7d`
   - `replied_30d` (`yes/no`)
   - `preferred_area`
   - `notes`
3. Run the script against that export.
4. Copy top message drafts into Lofty SMS, send, and log outcomes in Lofty.

## Customize scoring quickly

In `lead_assistant.py`, edit `score_lead()`:
- Increase motivation weight for higher-intent pipelines.
- Increase inactivity points if you want tighter follow-up cadence.
- Add or tune stage bonuses (`hot`, `touring`, etc.).

## Why this is useful

You keep **Lofty as source of truth** while adding a simple daily assistant that:
- tells you who to contact first,
- gives you message starting points,
- and keeps your daily follow-up execution focused.
