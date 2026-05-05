#!/usr/bin/env python3
"""Lofty companion tool for daily lead follow-up.

Reads a Lofty-exported CSV and produces:
- terminal summary
- prioritized CSV for today's follow-up
- text-message drafts CSV
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"]


@dataclass
class Lead:
    name: str
    phone: str
    stage: str
    motivation: int
    last_contact_date: dt.date | None
    touches_7d: int
    property_views_7d: int
    replied_30d: bool
    preferred_area: str
    notes: str


@dataclass
class ScoreConfig:
    motivation_weight: int = 6
    property_view_weight: int = 2
    touch_weight: int = 2
    reply_bonus: int = 10
    inactivity_2d_bonus: int = 4
    inactivity_5d_bonus: int = 10
    inactivity_10d_bonus: int = 18
    hot_stage_bonus: int = 12
    warm_stage_bonus: int = 5


@dataclass
class ScoredLead:
    lead: Lead
    score: int
    urgency: str
    days_since_contact: int
    suggested_action: str
    suggested_text: str


def clamp_int(value: str, default: int, min_value: int, max_value: int) -> int:
    try:
        num = int(str(value).strip())
    except ValueError:
        num = default
    return max(min_value, min(max_value, num))


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def parse_date(value: str) -> dt.date | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def days_since_contact(last_contact_date: dt.date | None, today: dt.date) -> int:
    if not last_contact_date:
        return 30
    return max(0, (today - last_contact_date).days)


def load_leads(path: Path) -> list[Lead]:
    leads: list[Lead] = []
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        required = {
            "name",
            "phone",
            "stage",
            "motivation",
            "last_contact_date",
            "touches_7d",
            "property_views_7d",
            "replied_30d",
            "preferred_area",
            "notes",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            joined = ", ".join(sorted(missing))
            raise ValueError(f"Missing required CSV columns: {joined}")

        for row in reader:
            leads.append(
                Lead(
                    name=(row.get("name") or "Unknown").strip() or "Unknown",
                    phone=(row.get("phone") or "").strip(),
                    stage=(row.get("stage") or "new").strip().lower(),
                    motivation=clamp_int(row.get("motivation", "5"), 5, 0, 10),
                    last_contact_date=parse_date(row.get("last_contact_date", "")),
                    touches_7d=clamp_int(row.get("touches_7d", "0"), 0, 0, 100),
                    property_views_7d=clamp_int(row.get("property_views_7d", "0"), 0, 0, 100),
                    replied_30d=parse_bool(row.get("replied_30d", "no")),
                    preferred_area=(row.get("preferred_area") or "your target area").strip() or "your target area",
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return leads


def score_lead(lead: Lead, config: ScoreConfig, today: dt.date) -> tuple[int, int]:
    days = days_since_contact(lead.last_contact_date, today)

    score = lead.motivation * config.motivation_weight
    score += min(lead.property_views_7d * config.property_view_weight, 20)
    score += min(lead.touches_7d * config.touch_weight, 16)
    score += config.reply_bonus if lead.replied_30d else 0

    if days >= 10:
        score += config.inactivity_10d_bonus
    elif days >= 5:
        score += config.inactivity_5d_bonus
    elif days >= 2:
        score += config.inactivity_2d_bonus

    if lead.stage in {"hot", "appointment", "touring"}:
        score += config.hot_stage_bonus
    elif lead.stage in {"warm", "nurture"}:
        score += config.warm_stage_bonus

    return max(0, min(100, score)), days


def urgency_band(score: int) -> str:
    if score >= 75:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


def suggest_action(score: int, days: int) -> str:
    if score >= 75:
        return f"Text now + call today if no reply (last touch {days}d ago)."
    if score >= 50:
        return f"Send check-in text today (last touch {days}d ago)."
    return "Nurture touch this week."


def suggest_text(lead: Lead, score: int) -> str:
    first_name = lead.name.split()[0] if lead.name.split() else "there"
    if score >= 75:
        return (
            f"Hey {first_name}, quick one — I found a couple homes in {lead.preferred_area} that seem like a fit. "
            "Want me to send them over?"
        )
    if score >= 50:
        return (
            f"Hi {first_name}! Just checking in — are you still thinking about moving in {lead.preferred_area}? "
            "Happy to send a short list if helpful."
        )
    return (
        f"Hey {first_name}, just staying in touch. If your timing changes for {lead.preferred_area}, "
        "I’m happy to help anytime."
    )


def score_leads(leads: Iterable[Lead], config: ScoreConfig, today: dt.date) -> list[ScoredLead]:
    result: list[ScoredLead] = []
    for lead in leads:
        score, days = score_lead(lead, config, today)
        result.append(
            ScoredLead(
                lead=lead,
                score=score,
                urgency=urgency_band(score),
                days_since_contact=days,
                suggested_action=suggest_action(score, days),
                suggested_text=suggest_text(lead, score),
            )
        )
    return sorted(result, key=lambda x: x.score, reverse=True)


def write_priority_csv(scored: list[ScoredLead], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "name",
            "phone",
            "stage",
            "score",
            "urgency",
            "days_since_contact",
            "suggested_action",
            "notes",
        ])
        for item in scored:
            writer.writerow([
                item.lead.name,
                item.lead.phone,
                item.lead.stage,
                item.score,
                item.urgency,
                item.days_since_contact,
                item.suggested_action,
                item.lead.notes,
            ])


def write_message_csv(scored: list[ScoredLead], output_path: Path, max_rows: int) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["name", "phone", "urgency", "score", "message"])
        for item in scored[:max_rows]:
            writer.writerow([item.lead.name, item.lead.phone, item.urgency, item.score, item.suggested_text])


def print_terminal_summary(scored: list[ScoredLead], top: int) -> None:
    print("\n=== Daily Follow-Up Priority ===")
    for lead in scored[:top]:
        print(f"- {lead.lead.name:20} | {lead.urgency:6} | Score {lead.score:3} | {lead.suggested_action}")

    high_count = sum(1 for x in scored if x.urgency == "HIGH")
    med_count = sum(1 for x in scored if x.urgency == "MEDIUM")
    print("\n=== Suggested Daily Actions ===")
    if high_count:
        print(f"- Send texts to top {min(8, high_count)} HIGH leads.")
        print(f"- Call top {min(5, high_count)} HIGH leads with no reply after 3 hours.")
    if med_count:
        print(f"- Send check-ins to top {min(10, med_count)} MEDIUM leads.")
    print("- Log outcomes in Lofty (replied, no response, call booked, not now).")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple Lofty lead follow-up companion")
    parser.add_argument("--input", required=True, help="Lofty export CSV path")
    parser.add_argument("--top", type=int, default=10, help="How many leads to show in terminal")
    parser.add_argument("--output-dir", default=".", help="Directory for generated CSV outputs")
    parser.add_argument("--date", default="", help="Optional run date YYYY-MM-DD (defaults to today)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_date = parse_date(args.date) if args.date else dt.date.today()
    if run_date is None:
        raise ValueError("Invalid --date. Use YYYY-MM-DD.")

    leads = load_leads(Path(args.input))
    scored = score_leads(leads, ScoreConfig(), run_date)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    priority_path = output_dir / "daily_followup_priority.csv"
    message_path = output_dir / "daily_text_drafts.csv"

    write_priority_csv(scored, priority_path)
    write_message_csv(scored, message_path, max_rows=max(1, args.top))
    print_terminal_summary(scored, top=max(1, args.top))

    print("\nFiles generated:")
    print(f"- {priority_path}")
    print(f"- {message_path}")


if __name__ == "__main__":
    main()
