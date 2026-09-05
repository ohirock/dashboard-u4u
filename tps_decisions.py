"""Static Federal Register TPS termination notices for the public dashboard."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class TpsDecision:
    country_key: str
    designation_start: date
    expiration_reviewed: date
    notice_date: date
    timing_days: int
    notice_url: str
    superseded: bool = False


TPS_TERMINATION_DECISIONS: tuple[TpsDecision, ...] = (
    TpsDecision("venezuela_2023", date(2023, 10, 3), date(2025, 4, 2), date(2025, 2, 5), -56, "https://www.federalregister.gov/d/2025-02294"),
    TpsDecision("afghanistan", date(2022, 5, 20), date(2025, 5, 20), date(2025, 5, 13), -7, "https://www.federalregister.gov/d/2025-08201"),
    TpsDecision("cameroon", date(2022, 6, 7), date(2025, 6, 7), date(2025, 6, 4), -3, "https://www.federalregister.gov/d/2025-10236"),
    TpsDecision("nepal", date(2015, 6, 24), date(2025, 6, 24), date(2025, 6, 6), -18, "https://www.federalregister.gov/d/2025-10363"),
    TpsDecision("haiti", date(2010, 1, 21), date(2025, 8, 3), date(2025, 7, 1), -33, "https://www.federalregister.gov/d/2025-12224", superseded=True),
    TpsDecision("honduras", date(1999, 1, 5), date(2025, 7, 5), date(2025, 7, 8), 3, "https://www.federalregister.gov/d/2025-12621"),
    TpsDecision("nicaragua", date(1999, 1, 5), date(2025, 7, 5), date(2025, 7, 8), 3, "https://www.federalregister.gov/d/2025-12688"),
    TpsDecision("venezuela_2021", date(2021, 3, 9), date(2025, 9, 10), date(2025, 9, 8), -2, "https://www.federalregister.gov/d/2025-17087"),
    TpsDecision("syria", date(2012, 3, 29), date(2025, 9, 30), date(2025, 9, 22), -8, "https://www.federalregister.gov/d/2025-18322"),
    TpsDecision("south_sudan", date(2011, 11, 3), date(2025, 11, 3), date(2025, 11, 6), 3, "https://www.federalregister.gov/d/2025-19800"),
    TpsDecision("burma", date(2021, 5, 25), date(2025, 11, 25), date(2025, 11, 25), 0, "https://www.federalregister.gov/d/2025-21069"),
    TpsDecision("haiti", date(2010, 1, 21), date(2026, 2, 3), date(2025, 11, 28), -67, "https://www.federalregister.gov/d/2025-21379"),
    TpsDecision("ethiopia", date(2022, 12, 12), date(2025, 12, 12), date(2025, 12, 15), 3, "https://www.federalregister.gov/d/2025-22746"),
    TpsDecision("somalia", date(1991, 9, 16), date(2026, 3, 17), date(2026, 1, 14), -62, "https://www.federalregister.gov/d/2026-00596"),
    TpsDecision("yemen", date(2015, 9, 3), date(2026, 3, 3), date(2026, 3, 3), 0, "https://www.federalregister.gov/d/2026-04179"),
)
