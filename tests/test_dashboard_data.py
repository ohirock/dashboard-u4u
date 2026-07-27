import io
import json
import unittest
from datetime import UTC, datetime, timedelta
from email.message import Message
from urllib.error import URLError

from dashboard_data import (
    DEFAULT_PUBLIC_API_BASE_URL,
    PublicDashboardUnavailable,
    fetch_dashboard_snapshot,
    public_api_base_url,
    snapshot_age_hours,
)


def snapshot_document() -> dict:
    return {
        "generated_at": "2026-07-25T02:48:26Z",
        "data_version": 3,
        "filters": {
            "supported_form_types": ["i_131"],
            "supported_statuses": ["approved"],
            "min_reported_date": "2026-07-25",
            "max_reported_date": "2026-07-25",
        },
        "metrics": {
            "report_count": 1,
            "case_observation_count": 1,
            "reports_by_month": [{"key": "2026-07", "count": 1}],
            "decisions_by_month": [],
            "reports_by_form": [{"key": "i_131", "count": 1}],
            "reports_by_subtype": [],
            "current_status_distribution": [{"key": "approved", "count": 1}],
            "filing_to_decision": {
                "sample_size": 0,
                "average_days": None,
                "median_days": None,
                "first_quartile_days": None,
                "third_quartile_days": None,
            },
            "final_decisions": {
                "last_7_days": 0,
                "previous_calendar_week": 0,
                "current_calendar_week": 0,
                "current_calendar_month": 0,
            },
            "milestone_durations": [],
            "weekly_milestone_durations": [],
            "expedite_duration_comparisons": [],
            "monthly_decision_durations": [],
            "expedite_request_count": 0,
            "expedite_by_channel": [],
            "reports_with_expedite": 0,
            "outcomes_with_expedite": [],
            "outcomes_without_expedite": [{"key": "approved", "count": 1}],
            "historic_pending_count": 0,
            "historic_reviewed_count": 0,
        },
        "quality": {
            "included_report_count": 1,
            "excluded_report_count": 0,
            "unknown_form_count": 0,
            "unknown_status_count": 0,
            "reports_missing_filed_date": 1,
            "reports_missing_decision_date": 1,
            "conflicting_evidence_count": 0,
        },
    }


class FakeResponse:
    def __init__(self, document: dict) -> None:
        self._body = io.BytesIO(json.dumps(document).encode())
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"
        self.headers["Content-Length"] = str(len(self._body.getvalue()))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, size: int) -> bytes:
        return self._body.read(size)


class DashboardDataTests(unittest.TestCase):
    def test_default_and_override_api_origins_are_safe(self) -> None:
        self.assertEqual(public_api_base_url({}), DEFAULT_PUBLIC_API_BASE_URL)
        self.assertEqual(
            public_api_base_url({"U4U_PUBLIC_API_BASE_URL": "http://localhost:8000/"}),
            "http://localhost:8000",
        )
        with self.assertRaises(PublicDashboardUnavailable):
            public_api_base_url({"U4U_PUBLIC_API_BASE_URL": "http://example.com"})
        with self.assertRaises(PublicDashboardUnavailable):
            public_api_base_url(
                {"U4U_PUBLIC_API_BASE_URL": "https://user:pass@example.com"}
            )

    def test_fetches_and_strictly_validates_aggregate_snapshot(self) -> None:
        requests = []

        def opener(request, **_kwargs):
            requests.append(request)
            return FakeResponse(snapshot_document())

        snapshot = fetch_dashboard_snapshot(
            DEFAULT_PUBLIC_API_BASE_URL,
            opener=opener,
        )
        self.assertEqual(
            requests[0].get_header("X-u4u-dashboard-schema"),
            "2",
        )
        self.assertEqual(snapshot.metrics.report_count, 1)
        invalid = snapshot_document()
        invalid["raw_messages"] = []
        with self.assertRaises(PublicDashboardUnavailable):
            fetch_dashboard_snapshot(
                DEFAULT_PUBLIC_API_BASE_URL,
                opener=lambda *_args, **_kwargs: FakeResponse(invalid),
            )

    def test_network_error_is_sanitized(self) -> None:
        def fail(*_args, **_kwargs):
            raise URLError("private diagnostic")

        with self.assertRaisesRegex(
            PublicDashboardUnavailable,
            "could not be reached",
        ):
            fetch_dashboard_snapshot(
                DEFAULT_PUBLIC_API_BASE_URL,
                opener=fail,
            )

    def test_snapshot_age_is_non_negative(self) -> None:
        snapshot = fetch_dashboard_snapshot(
            DEFAULT_PUBLIC_API_BASE_URL,
            opener=lambda *_args, **_kwargs: FakeResponse(snapshot_document()),
        )
        self.assertEqual(
            snapshot_age_hours(
                snapshot,
                now=datetime(2026, 7, 25, 5, 48, 26, tzinfo=UTC),
            ),
            3.0,
        )
        self.assertEqual(
            snapshot_age_hours(
                snapshot,
                now=snapshot.generated_at - timedelta(hours=1),
            ),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
