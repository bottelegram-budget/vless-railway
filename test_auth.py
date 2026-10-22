import unittest
import app

class AccessTests(unittest.TestCase):
    def setUp(self):
        self.old_token = app.ADMIN_TOKEN
        self.old_uuid = app.UUID_ENV
        app.ADMIN_TOKEN = "new-test-admin-token"
        app.UUID_ENV = "00000000-0000-4000-8000-000000000001"
        self.client = app.app.test_client()
    def tearDown(self):
        app.ADMIN_TOKEN = self.old_token
        app.UUID_ENV = self.old_uuid
    def test_info_requires_auth(self):
        r = self.client.get("/api/info")
        self.assertEqual(r.status_code, 401)
        self.assertNotIn("share_example", r.get_json())
        self.assertNotIn("ws_path", r.get_json())
    def test_old_token_rejected(self):
        self.assertEqual(self.client.get("/api/info", headers={"X-Auth-Token": "old-test-token"}).status_code, 401)
    def test_new_token_gets_info(self):
        r = self.client.get("/api/info", headers={"X-Auth-Token": app.ADMIN_TOKEN})
        self.assertEqual(r.status_code, 200)
        self.assertIn(app.UUID_ENV, r.get_json()["share_example"])
    def test_no_configured_admin_fails_closed(self):
        app.ADMIN_TOKEN = ""
        self.assertEqual(self.client.get("/api/info").status_code, 401)
    def test_health_is_public(self):
        self.assertEqual(self.client.get("/api/healthz").status_code, 200)

if __name__ == "__main__":
    unittest.main()
