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
            "wait_times": [
                {"answer": "u4u", "case_family": "re_parole", "stage": "awaiting_final",
                 "sample_size": 2, "excluded_count": 1, "min_days": 10,
                 "average_days": 20.0, "max_days": 30},
                {"answer": "u4u", "case_family": "ead", "stage": "approved",
                 "sample_size": 0, "excluded_count": 1, "min_days": None,
                 "average_days": None, "max_days": None},
            ],
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
        self.assertIn("include_wait_times=true", requests[0].full_url)
        current = PersonalDashboardSnapshot.model_validate(questionnaire_document())
        self.assertEqual(current.questionnaire.questions[0].by_answer[1].count, 0)

    def test_questionnaire_tab_renders_both_languages_and_legacy_fallback(self):
        import streamlit as st
        from streamlit.testing.v1 import AppTest

        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        for language in ("uk", "en"):
            for extended in (True, False):
                with self.subTest(language=language, extended=extended):
                    st.cache_data.clear()
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
                        min_column = "Мін. днів" if language == "uk" else "Min days"
                        tables = [item.value for item in app.dataframe if min_column in item.value]
                        self.assertEqual(len(tables), 2)
                    else:
                        expected_info = (
                            "Статистика анкети поки недоступна"
                            if language == "uk" else "Questionnaire statistics are not available yet"
                        )
                        self.assertTrue(any(expected_info in item.value for item in app.info))


if __name__ == "__main__":
    unittest.main()
