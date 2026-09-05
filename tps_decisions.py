"""Static official TPS actions for the public dashboard."""

from dataclasses import dataclass
from datetime import date


USCIS_TPS_ROOT = (
    "https://www.uscis.gov/humanitarian/temporary-protected-status/"
    "temporary-protected-status-designated-country-"
)


@dataclass(frozen=True, slots=True)
class TpsDecision:
    country_key: str
    decision_type: str
    designation_start: date
    expiration_reviewed: date
    notice_date: date | None
    notice_url: str | None
    uscis_url: str
    superseded: bool = False

    @property
    def timing_days(self) -> int | None:
        if self.notice_date is None:
            return None
        return (self.notice_date - self.expiration_reviewed).days


def _uscis(country_slug: str) -> str:
    return f"{USCIS_TPS_ROOT}{country_slug}"


# Designations without a termination are listed first. Remaining action rows
# follow Federal Register publication order, including superseded notices.
TPS_DECISIONS: tuple[TpsDecision, ...] = (
    TpsDecision("el_salvador", "no_decision", date(2001, 3, 9), date(2026, 9, 9), None, None, _uscis("el-salvador")),
    TpsDecision("sudan", "no_decision", date(1997, 11, 4), date(2026, 10, 19), None, None, _uscis("sudan")),
    TpsDecision("ukraine", "no_decision", date(2022, 4, 19), date(2026, 10, 19), None, None, _uscis("ukraine")),
    TpsDecision("lebanon", "auto_extension", date(2024, 11, 27), date(2026, 5, 27), date(2026, 5, 29), "https://www.federalregister.gov/d/2026-10704", _uscis("lebanon")),
    TpsDecision("venezuela_2023", "termination", date(2023, 10, 3), date(2025, 4, 2), date(2025, 2, 5), "https://www.federalregister.gov/d/2025-02294", _uscis("venezuela")),
    TpsDecision("south_sudan", "auto_extension", date(2011, 11, 3), date(2025, 5, 3), date(2025, 5, 6), "https://www.federalregister.gov/d/2025-07976", _uscis("south-sudan")),
    TpsDecision("afghanistan", "termination", date(2022, 5, 20), date(2025, 5, 20), date(2025, 5, 13), "https://www.federalregister.gov/d/2025-08201", _uscis("afghanistan")),
    TpsDecision("cameroon", "termination", date(2022, 6, 7), date(2025, 6, 7), date(2025, 6, 4), "https://www.federalregister.gov/d/2025-10236", _uscis("cameroon")),
    TpsDecision("nepal", "termination", date(2015, 6, 24), date(2025, 6, 24), date(2025, 6, 6), "https://www.federalregister.gov/d/2025-10363", _uscis("nepal")),
    TpsDecision("haiti", "termination", date(2010, 1, 21), date(2025, 8, 3), date(2025, 7, 1), "https://www.federalregister.gov/d/2025-12224", _uscis("haiti"), superseded=True),
    TpsDecision("honduras", "termination", date(1999, 1, 5), date(2025, 7, 5), date(2025, 7, 8), "https://www.federalregister.gov/d/2025-12621", _uscis("honduras")),
    TpsDecision("nicaragua", "termination", date(1999, 1, 5), date(2025, 7, 5), date(2025, 7, 8), "https://www.federalregister.gov/d/2025-12688", _uscis("nicaragua")),
    TpsDecision("venezuela_2021", "termination", date(2021, 3, 9), date(2025, 9, 10), date(2025, 9, 8), "https://www.federalregister.gov/d/2025-17087", _uscis("venezuela")),
    TpsDecision("syria", "termination", date(2012, 3, 29), date(2025, 9, 30), date(2025, 9, 22), "https://www.federalregister.gov/d/2025-18322", _uscis("syria")),
    TpsDecision("south_sudan", "termination", date(2011, 11, 3), date(2025, 11, 3), date(2025, 11, 6), "https://www.federalregister.gov/d/2025-19800", _uscis("south-sudan")),
    TpsDecision("burma", "termination", date(2021, 5, 25), date(2025, 11, 25), date(2025, 11, 25), "https://www.federalregister.gov/d/2025-21069", _uscis("burma")),
    TpsDecision("haiti", "termination", date(2010, 1, 21), date(2026, 2, 3), date(2025, 11, 28), "https://www.federalregister.gov/d/2025-21379", _uscis("haiti")),
    TpsDecision("ethiopia", "termination", date(2022, 12, 12), date(2025, 12, 12), date(2025, 12, 15), "https://www.federalregister.gov/d/2025-22746", _uscis("ethiopia")),
    TpsDecision("somalia", "termination", date(1991, 9, 16), date(2026, 3, 17), date(2026, 1, 14), "https://www.federalregister.gov/d/2026-00596", _uscis("somalia")),
    TpsDecision("yemen", "termination", date(2015, 9, 3), date(2026, 3, 3), date(2026, 3, 3), "https://www.federalregister.gov/d/2026-04179", _uscis("yemen")),
)
