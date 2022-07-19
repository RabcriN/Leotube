from django.test import Client, TestCase


class StaticPagesURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_about_url_exists_at_desired_location(self):
        """Проверка доступности адреса /about/author/"""
        response = self.guest_client.get('/about/author/')
        self.assertEqual(response.status_code, 200)

    def test_tech_url_exists_at_desired_location(self):
        """Проверка доступности адреса /about/tech/"""
        response = self.guest_client.get('/about/tech/')
        self.assertEqual(response.status_code, 200)
