import io
import unittest

import python1


class FakeSentimentModel:
    def __call__(self, feedback):
        label = "5 stars" if "great" in feedback.lower() else "1 star"
        return [{"label": label}]


class EventFeedbackTests(unittest.TestCase):
    def setUp(self):
        python1.events.clear()
        python1.sentiment_model = FakeSentimentModel()
        python1.app.config["TESTING"] = True
        self.client = python1.app.test_client()

    def test_import_feedback_accepts_xquik_csv_columns(self):
        self.client.post("/add_event", json={"event": "launch"})
        csv_file = io.BytesIO(
            b"Tweet Text,Tweet Created At\n"
            b"Great event,2026-07-05\n"
            b",2026-07-05\n"
            b"Great event,2026-07-05\n"
            b"Need more demos,2026-07-05\n"
        )

        response = self.client.post(
            "/import_feedback",
            data={"event": "launch", "file": (csv_file, "xquik.csv")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["count"], 2)
        self.assertEqual(python1.events["launch"], ["Great event", "Need more demos"])

    def test_submit_feedback_rejects_blank_feedback(self):
        self.client.post("/add_event", json={"event": "launch"})

        response = self.client.post(
            "/submit_feedback",
            json={"event": "launch", "feedback": "   "},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("required", response.get_json()["error"])

    def test_analyze_feedback_deduplicates_before_counting(self):
        result = python1.analyze_feedback(["Great event", "Great event", "Need more demos"])

        self.assertEqual(result["likes"], 1)
        self.assertEqual(result["dislikes"], 1)
        self.assertEqual(result["percent_positive"], 50)


if __name__ == "__main__":
    unittest.main()
