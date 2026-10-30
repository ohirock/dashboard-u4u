import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard_data import (
    DashboardSnapshot,
    PersonalDashboardSnapshot,
    fetch_personal_dashboard_snapshot,
)
from test_dashboard_data import FakeResponse, personal_snapshot_document, snapshot_document


def questionnaire_document():
    document = personal_snapshot_document()
    document["questionnaire"] = {
        "answered_submission_count": 1,
        "complete_submission_count": 1,
        "questions": [{
            "field": "arrival_route", "answered_count": 1,
            "by_answer": [{"key": "u4u", "count": 1}, {"key": "mexico", "count": 0}],
        }],
        "outcomes_by_form": [{
            "key": "i_131", "by_status": [{"key": "conditional_approval", "count": 1}],
        }],
        "reparole_evidence_outcomes": [{"key": "yes", "by_status": []}],
    }
    return document


class QuestionnaireTests(unittest.TestCase):
    def test_client_requests_new_shape_and_accepts_legacy_shape(self):
        requests = []

        def opener(request, **kwargs):
            requests.append(request)
            return FakeResponse(personal_snapshot_document())

        legacy = fetch_personal_dashboard_snapshot("https://example.com", opener=opener)
        self.assertIsNotNone(legacy)
        self.assertIsNone(legacy.questionnaire)
        self.assertIn("include_questionnaire=true", requests[0].full_url)
        current = PersonalDashboardSnapshot.model_validate(questionnaire_document())
        self.assertEqual(current.questionnaire.questions[0].by_answer[1].count, 0)

    def test_questionnaire_tab_renders_both_languages_and_legacy_fallback(self):
        from streamlit.testing.v1 import AppTest

        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        for language in ("uk", "en"):
            for extended in (True, False):
                with self.subTest(language=language, extended=extended):
                    personal = PersonalDashboardSnapshot.model_validate(
                        questionnaire_document() if extended else personal_snapshot_document()
                    )
                    with (
                        patch("dashboard_data.fetch_dashboard_snapshot", return_value=
                              DashboardSnapshot.model_validate(snapshot_document())),
                        patch("dashboard_data.fetch_personal_dashboard_snapshot", return_value=personal),
                    ):
                        app = AppTest.from_file("dashboard.py", default_timeout=30)
                        app.query_params["lang"] = language
                        app.query_params["section"] = "questionnaire"
                        app.run()
                    self.assertEqual(list(app.exception), [])
                    expected = "Анкета" if language == "uk" else "Questionnaire"
                    self.assertIn(expected, [tab.label for tab in app.tabs])
                    if extended:
                        self.assertIn("50.0%", [metric.value for metric in app.metric])


if __name__ == "__main__":
    unittest.main()
