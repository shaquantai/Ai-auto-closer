#!/usr/bin/env python3
"""Simple daily lead follow-up assistant for Lofty CRM exports.

Usage:
  python lead_assistant.py --input leads.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import List


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
class ScoredLead:
    lead: Lead
    score: int
    urgency: str
    suggested_action: str
    suggested_text: str


def parse_date(value: str) -> dt.date | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "yes", "1", "y"}


def clamp_int(value: str, default: int = 0, min_value: int = 0, max_value: int = 10) -> int:
    try:
        result = int(str(value).strip())
    except ValueError:
        result = default
    return max(min_value, min(max_value, result))


def load_leads(path: Path) -> List[Lead]:
    leads: List[Lead] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(
                Lead(
                    name=row.get("name", "Unknown").strip() or "Unknown",
                    phone=row.get("phone", "").strip(),
                    stage=row.get("stage", "new").strip().lower(),
                    motivation=clamp_int(row.get("motivation", "5"), default=5),
                    last_contact_date=parse_date(row.get("last_contact_date", "")),
                    touches_7d=clamp_int(row.get("touches_7d", "0"), default=0, max_value=100),
                    property_views_7d=clamp_int(row.get("property_views_7d", "0"), default=0, max_value=100),
                    replied_30d=parse_bool(row.get("replied_30d", "")),
                    preferred_area=row.get("preferred_area", "your target area").strip() or "your target area",
                    notes=row.get("notes", "").strip(),
                )
            )
    return leads


def days_since_contact(lead: Lead) -> int:
    if not lead.last_contact_date:
        return 30
    return (dt.date.today() - lead.last_contact_date).days


def score_lead(lead: Lead) -> int:
    days = days_since_contact(lead)

    score = 0
    score += lead.motivation * 6
    score += min(lead.property_views_7d * 2, 20)
    score += min(lead.touches_7d * 2, 16)
    score += 10 if lead.replied_30d else 0

    if days >= 10:
        score += 18
    elif days >= 5:
        score += 10
    elif days >= 2:
        score += 4

    if lead.stage in {"hot", "appointment", "touring"}:
        score += 12
    elif lead.stage in {"warm", "nurture"}:
        score += 5

    return max(0, min(100, score))


def urgency_band(score: int) -> str:
    if score >= 75:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


def suggest_action(lead: Lead, score: int) -> str:
    days = days_since_contact(lead)
    if score >= 75:
        return f"Text now and call today (last touch {days}d ago)."
    if score >= 50:
        return f"Send a check-in text today (last touch {days}d ago)."
    return "Queue for nurture touch this week."


def suggest_text(lead: Lead, score: int) -> str:
    first = lead.name.split()[0]
    if score >= 75:
        return (
            f"Hey {first}, it's been a little bit since we last connected. "
            f"I found a couple options in {lead.preferred_area} that might fit what you're looking for. "
            "Want me to text them over?"
        )
    if score >= 50:
        return (
            f"Hi {first}! Quick check-in: are you still thinking about a move in {lead.preferred_area}? "
            "Happy to send a short list if that helps."
        )
    return (
        f"Hey {first}, just staying in touch. If your plans change, I'm here to help with anything in {lead.preferred_area}."
    )


def build_daily_plan(scored: List[ScoredLead]) -> List[str]:
    high = [s for s in scored if s.urgency == "HIGH"]
    med = [s for s in scored if s.urgency == "MEDIUM"]

    tasks: List[str] = []
    if high:
        tasks.append(f"Send texts to top {min(8, len(high))} HIGH-priority leads.")
        tasks.append(f"Call top {min(5, len(high))} HIGH-priority leads who do not respond in 3 hours.")
    if med:
        tasks.append(f"Send check-ins to {min(10, len(med))} MEDIUM-priority leads.")
    tasks.append("Update outcomes in Lofty (replied / not now / booked call).")
    return tasks


def score_and_sort(leads: List[Lead]) -> List[ScoredLead]:
    scored: List[ScoredLead] = []
    for lead in leads:
        score = score_lead(lead)
        scored.append(
            ScoredLead(
                lead=lead,
                score=score,
                urgency=urgency_band(score),
                suggested_action=suggest_action(lead, score),
                suggested_text=suggest_text(lead, score),
            )
        )
    return sorted(scored, key=lambda s: s.score, reverse=True)


def print_report(scored: List[ScoredLead], top_n: int) -> None:
    print("\n=== Daily Follow-Up Priority ===")
    for item in scored[:top_n]:
        print(f"- {item.lead.name:20} | Score: {item.score:3} | {item.urgency:6} | {item.suggested_action}")

    print("\n=== Suggested Daily Actions ===")
    for task in build_daily_plan(scored):
        print(f"- {task}")

    print("\n=== Suggested Text Messages ===")
    for item in scored[:top_n]:
        print(f"\n{item.lead.name} ({item.lead.phone or 'no phone'})")
        print(item.suggested_text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily lead follow-up helper for Lofty CRM exports")
    parser.add_argument("--input", required=True, help="Path to CSV file")
    parser.add_argument("--top", type=int, default=10, help="How many leads to show")
    args = parser.parse_args()

    leads = load_leads(Path(args.input))
    scored = score_and_sort(leads)
    print_report(scored, max(1, args.top))


if __name__ == "__main__":
    main()
