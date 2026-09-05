import unittest
from datetime import date

from tps_decisions import (
    TPS_DECISIONS,
    actual_end_date,
    litigation_end_date,
    litigation_status,
)


class TpsDecisionsTest(unittest.TestCase):
    def test_notices_use_official_links(self) -> None:
        self.assertTrue(
            all(
                item.notice_url.startswith("https://www.federalregister.gov/d/")
                for item in TPS_DECISIONS
                if item.notice_url
            )
        )

    def test_haiti_superseding_notice_is_explicit(self) -> None:
        haiti = [item for item in TPS_DECISIONS if item.country_key == "haiti"]
        self.assertEqual(len(haiti), 2)
        self.assertTrue(haiti[0].superseded)
        self.assertFalse(haiti[1].superseded)

    def test_full_scope_and_links(self) -> None:
        self.assertEqual(len(TPS_DECISIONS), 20)
        self.assertEqual(
            {item.country_key for item in TPS_DECISIONS if item.decision_type == "no_decision"},
            {"el_salvador", "sudan", "ukraine"},
        )
        self.assertTrue(all(item.uscis_url.startswith("https://www.uscis.gov/") for item in TPS_DECISIONS))
        self.assertEqual(
            {(item.country_key, item.decision_type) for item in TPS_DECISIONS if item.decision_type == "auto_extension"},
            {("lebanon", "auto_extension"), ("south_sudan", "auto_extension")},
        )

    def test_timing_is_derived_from_dates(self) -> None:
        dated = [item for item in TPS_DECISIONS if item.notice_date]
        self.assertTrue(
            all(item.timing_days == (item.notice_date - item.expiration_reviewed).days for item in dated)
        )


    def test_actual_end_dates_cover_every_action(self) -> None:
        self.assertTrue(all(actual_end_date(item) >= item.designation_start for item in TPS_DECISIONS))
        self.assertEqual(
            actual_end_date(next(item for item in TPS_DECISIONS if item.country_key == "yemen")),
            date(2026, 7, 20),
        )

    def test_venezuela_limited_cohort_is_explicit(self) -> None:
        item = next(item for item in TPS_DECISIONS if item.country_key == "venezuela_2023")
        self.assertEqual(actual_end_date(item), date(2025, 4, 2))
        self.assertEqual(litigation_end_date(item), date(2026, 10, 2))
        self.assertEqual(litigation_status(item), "pending_limited")

    def test_pending_litigation_does_not_imply_tps_is_active(self) -> None:
        item = next(item for item in TPS_DECISIONS if item.country_key == "burma")
        self.assertEqual(litigation_status(item), "pending_ended")
        self.assertIsNone(litigation_end_date(item))


if __name__ == "__main__":
    unittest.main()
