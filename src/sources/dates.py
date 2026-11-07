"""Shared inclusive publication window; unknown/ambiguous dates fail closed."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
import re


def parse_publication_date(value: str | datetime | date | None) -> tuple[datetime | None, str | None]:
    if value is None or value == "":
        return None, "missing"
    try:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, date):
            parsed = datetime.combine(value, time(), timezone.utc)
        elif isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
            parsed = datetime.combine(date.fromisoformat(value.strip()), time(), timezone.utc)
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError:
                parsed = parsedate_to_datetime(value.strip())
        else:
            return None, "malformed"
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None, "ambiguous_timezone"
        return parsed.astimezone(timezone.utc), None
    except (ValueError, TypeError, OverflowError):
        return None, "malformed"


@dataclass(frozen=True)
class PublicationWindow:
    start: datetime
    end: datetime

    @classmethod
    def recent(cls, days_back=7, reference_time=None):
        end, error = parse_publication_date(reference_time or datetime.now(timezone.utc))
        if error or days_back < 0:
            raise ValueError("A nonnegative lookback and timezone-aware reference time are required")
        return cls(end - timedelta(days=days_back), end)

    def filter(self, papers: list[dict]) -> tuple[list[dict], dict[str, int]]:
        accepted, rejected = [], {}
        for paper in papers:
            published, reason = parse_publication_date(paper.get("published"))
            if not reason and not self.start <= published <= self.end:
                reason = "before_window" if published < self.start else "after_window"
            if reason:
                rejected[reason] = rejected.get(reason, 0) + 1
                continue
            record = dict(paper)
            record.setdefault("published_original", paper["published"])
            record["published"] = published.isoformat()
            accepted.append(record)
        return accepted, rejected
