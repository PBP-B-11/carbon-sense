from unittest.mock import patch

from django.test import SimpleTestCase


class BrowserApiCorsTests(SimpleTestCase):
    origin = "http://localhost:7357"

    @patch("profil.api_views.city_options", return_value=[])
    def test_city_search_allows_the_flutter_origin(self, _city_options):
        response = self.client.get(
            "/api/v1/profile/cities/?q=Depok", HTTP_ORIGIN=self.origin
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"), self.origin
        )

    def test_registration_allows_a_json_post_from_flutter(self):
        response = self.client.options(
            "/api/v1/auth/register/",
            HTTP_ORIGIN=self.origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )

        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"), self.origin
        )
        self.assertIn("POST", response.headers["Access-Control-Allow-Methods"])
        self.assertIn("content-type", response.headers["Access-Control-Allow-Headers"])

    def test_other_origins_and_web_pages_are_unaffected(self):
        for path, origin in (
            ("/api/v1/auth/register/", "https://example.org"),
            ("/profil/login/", self.origin),
        ):
            with self.subTest(path=path, origin=origin):
                response = self.client.options(
                    path,
                    HTTP_ORIGIN=origin,
                    HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
                )
                self.assertNotIn("Access-Control-Allow-Origin", response.headers)
