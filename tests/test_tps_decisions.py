import unittest

from tps_decisions import TPS_TERMINATION_DECISIONS


class TpsDecisionsTest(unittest.TestCase):
    def test_notices_are_chronological_and_use_official_links(self) -> None:
        dates = [item.notice_date for item in TPS_TERMINATION_DECISIONS]
        self.assertEqual(dates, sorted(dates))
        self.assertTrue(all(item.notice_url.startswith("https://www.federalregister.gov/d/") for item in TPS_TERMINATION_DECISIONS))

    def test_haiti_superseding_notice_is_explicit(self) -> None:
        haiti = [item for item in TPS_TERMINATION_DECISIONS if item.country_key == "haiti"]
        self.assertEqual(len(haiti), 2)
        self.assertTrue(haiti[0].superseded)
        self.assertFalse(haiti[1].superseded)


if __name__ == "__main__":
    unittest.main()
