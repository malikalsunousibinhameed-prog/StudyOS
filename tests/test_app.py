import os
import tempfile
import unittest
from datetime import date, timedelta

from app import app as flask_app
from database import init_db, get_assignments, get_statistics


class StudyOSTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        init_db(self.db_path)
        flask_app.config.update(
            TESTING=True,
            DATABASE=self.db_path,
            WTF_CSRF_ENABLED=False,
            SECRET_KEY="test-key",
        )
        self.client = flask_app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def valid_assignment(self, **overrides):
        values = {
            "title": "Read chapter 2",
            "subject": "Biology",
            "description": "Take notes",
            "due_date": (date.today() + timedelta(days=2)).isoformat(),
            "priority": "Medium",
        }
        values.update(overrides)
        return values

    def test_dashboard_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Today's Mission", response.data)

    def test_create_assignment(self):
        response = self.client.post("/assignments/new", data=self.valid_assignment(), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Read chapter 2", response.data)
        self.assertEqual(len(get_assignments(self.db_path)), 1)

    def test_reject_missing_title(self):
        response = self.client.post("/assignments/new", data=self.valid_assignment(title=""))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Enter an assignment title", response.data)
        self.assertEqual(len(get_assignments(self.db_path)), 0)

    def test_edit_assignment(self):
        self.client.post("/assignments/new", data=self.valid_assignment())
        item = get_assignments(self.db_path)[0]
        response = self.client.post(
            f"/assignments/{item['id']}/edit",
            data=self.valid_assignment(title="Updated chapter"),
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Updated chapter", response.data)

    def test_toggle_and_delete_assignment(self):
        self.client.post("/assignments/new", data=self.valid_assignment())
        item = get_assignments(self.db_path)[0]
        self.client.post(f"/assignments/{item['id']}/toggle")
        self.assertEqual(get_assignments(self.db_path, status="completed")[0]["id"], item["id"])
        self.client.post(f"/assignments/{item['id']}/delete")
        self.assertEqual(len(get_assignments(self.db_path)), 0)

    def test_search_and_filter(self):
        self.client.post("/assignments/new", data=self.valid_assignment(title="Biology report"))
        self.client.post("/assignments/new", data=self.valid_assignment(title="History essay", subject="History"))
        results = get_assignments(self.db_path, search="Biology")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Biology report")

    def test_statistics_empty_database(self):
        stats = get_statistics(self.db_path)
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["total_seconds"], 0)
        self.assertEqual(len(stats["chart"]), 7)


if __name__ == "__main__":
    unittest.main()
