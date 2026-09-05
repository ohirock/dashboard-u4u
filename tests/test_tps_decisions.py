import unittest

from tps_decisions import TPS_DECISIONS


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


if __name__ == "__main__":
    unittest.main()
