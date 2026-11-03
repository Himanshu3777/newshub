"""Public reader accounts: register, login, logout (NOT the admin login).

A normal user must be able to create an account, log in with it, see their
name on the site, and log out - and a wrong password must be rejected.
Reader accounts are never staff/superuser.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User

PW = "Reader@Test2026"  # passes the site validators (10+ chars, not common)


class ReaderAuthTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_page_renders(self):
        self.assertEqual(self.client.get("/accounts/register/").status_code, 200)

    def test_login_page_renders(self):
        r = self.client.get("/accounts/login/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"/accounts/register/", r.content)

    def test_register_creates_normal_user_and_logs_in(self):
        r = self.client.post("/accounts/register/", {
            "username": "ravi_reader", "email": "ravi@example.com",
            "password1": PW, "password2": PW})
        self.assertEqual(r.status_code, 302)
        u = User.objects.get(username="ravi_reader")
        self.assertFalse(u.is_staff)
        self.assertFalse(u.is_superuser)
        self.assertIn("_auth_user_id", self.client.session)
        home = self.client.get("/").content
        self.assertIn("ravi_reader".encode(), home)
        self.assertIn(b"Logout", home)

    def test_register_rejects_weak_password(self):
        r = self.client.post("/accounts/register/", {
            "username": "weakling", "password1": "12345678", "password2": "12345678"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="weakling").exists())

    def test_register_rejects_duplicate_username(self):
        User.objects.create_user(username="taken", password=PW)
        r = self.client.post("/accounts/register/", {
            "username": "taken", "password1": PW, "password2": PW})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(User.objects.filter(username="taken").count(), 1)

    def test_login_correct_and_wrong_password(self):
        User.objects.create_user(username="meera", password=PW)
        bad = self.client.post("/accounts/login/", {"username": "meera", "password": "WrongPass999"})
        self.assertEqual(bad.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        ok = self.client.post("/accounts/login/", {"username": "meera", "password": PW})
        self.assertEqual(ok.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_clears_session(self):
        User.objects.create_user(username="kabir", password=PW)
        self.client.post("/accounts/login/", {"username": "kabir", "password": PW})
        self.assertIn("_auth_user_id", self.client.session)
        self.client.post("/accounts/logout/")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_topbar_anonymous_shows_login_register_not_admin_login(self):
        home = self.client.get("/").content
        self.assertIn(b"/accounts/login/", home)
        self.assertIn(b"/accounts/register/", home)
