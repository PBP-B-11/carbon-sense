from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings


class StaticFilesTests(SimpleTestCase):
    def test_css_is_served_without_collectstatic(self):
        with TemporaryDirectory() as static_root:
            with override_settings(DEBUG=False, STATIC_ROOT=static_root):
                response = self.client.get(
                    "/static/css/styles.css",
                    HTTP_HOST="faishal-falih-carbon-sense.pws.cs.ui.ac.id",
                )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/css"))
