from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import FINE_PER_DAY, Book, Loan, Member


class CirculationTest(TestCase):
    def test_full_flow(self):
        r = self.client.post(reverse("register"), {
            "first_name": "Ada", "last_name": "L", "username": "S001", "email": "ADA@x.com",
            "phone": "0700", "program": "BSc Computer Science", "password1": "Shelf-Reader-42", "password2": "Shelf-Reader-42"})
        self.assertRedirects(r, reverse("login"))
        member = Member.objects.get(username="S001")
        self.assertEqual(member.email, "ada@x.com")
        self.assertFalse(member.is_approved)

        # can't log in until a librarian approves the account
        creds = {"username": "S001", "password": "Shelf-Reader-42", "role": "student"}
        self.assertContains(self.client.post(reverse("login"), creds), "waiting for approval")
        staff = Member.objects.create_user("lib", email="lib@x.com", password="x", is_staff=True)
        self.client.force_login(staff)
        self.assertContains(self.client.get(reverse("dashboard")), "S001")
        self.client.post(reverse("review_member", args=[member.id, "approve"]))
        member.refresh_from_db()
        self.assertTrue(member.is_approved)
        self.assertRedirects(self.client.post(reverse("login"), creds), reverse("home"))

        book = Book.objects.create(title="Dune", author="Herbert", isbn="1", copies=1)
        self.client.post(reverse("borrow", args=[book.id]))
        self.client.post(reverse("borrow", args=[book.id]))  # duplicate ignored
        loan = Loan.objects.get()
        self.assertEqual(loan.status, Loan.PENDING)

        # members can't reach the desk
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)

        self.client.force_login(staff)
        self.client.post(reverse("update_loan", args=[loan.id, "approve"]))
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.BORROWED)
        self.assertEqual(book.available, 0)

        # a second request can't be approved while the only copy is out
        other = Loan.objects.create(book=book, member=staff)
        self.client.post(reverse("update_loan", args=[other.id, "approve"]))
        other.refresh_from_db()
        self.assertEqual(other.status, Loan.PENDING)

        # 3 days late → fine
        Loan.objects.filter(pk=loan.pk).update(due_date=timezone.localdate() - timedelta(days=3))
        self.client.post(reverse("update_loan", args=[loan.id, "return"]))
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.RETURNED)
        self.assertEqual(loan.fine, 3 * FINE_PER_DAY)
        self.assertEqual(book.available, 1)

        # unpaid fine blocks borrowing until the desk marks it paid
        self.client.force_login(member)
        self.client.post(reverse("borrow", args=[book.id]))
        self.assertFalse(Loan.objects.filter(member=member, status=Loan.PENDING).exists())
        self.client.force_login(staff)
        self.client.post(reverse("update_loan", args=[loan.id, "pay"]))
        loan.refresh_from_db()
        self.assertIsNotNone(loan.fine_paid_at)
        self.client.force_login(member)
        self.client.post(reverse("borrow", args=[book.id]))
        self.assertTrue(Loan.objects.filter(member=member, status=Loan.PENDING).exists())
        self.client.force_login(staff)

        # librarian path: own pages work, student pages bounce to the dashboard
        for name in ("dashboard", "stock", "book_add"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertRedirects(self.client.get(reverse("home")), reverse("dashboard"))
        self.assertContains(self.client.get(reverse("stock") + "?show=in"), "Dune")

        # stock management: add, edit (can't drop below copies on loan), delete-protection
        self.client.post(reverse("book_add"), {"title": "Emma", "author": "Austen", "isbn": "2", "copies": 3})
        emma = Book.objects.get(isbn="2")
        self.client.post(reverse("book_delete", args=[emma.id]))
        self.assertFalse(Book.objects.filter(isbn="2").exists())
        self.client.post(reverse("book_delete", args=[book.id]))  # has loan history
        self.assertTrue(Book.objects.filter(pk=book.pk).exists())

        # student path: own pages work, librarian pages are off-limits
        self.client.force_login(member)
        for name in ("home", "books", "my_loans"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertEqual(self.client.get(reverse("stock")).status_code, 302)

    def test_login_role_must_match_account(self):
        Member.objects.create_user("S9", email="s@x.com", password="pw", is_approved=True)
        Member.objects.create_user("boss", email="b@x.com", password="pw", is_staff=True)
        login = reverse("login")
        self.assertContains(self.client.post(login, {"username": "S9", "password": "pw", "role": "admin"}),
                            "isn&#x27;t a library admin")
        self.assertContains(self.client.post(login, {"username": "boss", "password": "pw", "role": "student"}),
                            "library admin account")
        self.assertRedirects(self.client.post(login, {"username": "boss", "password": "pw", "role": "admin"}),
                             reverse("home"), target_status_code=302)

    def test_reject_signup_deletes_it(self):
        pending = Member.objects.create_user("S2", email="p@x.com", password="pw")
        self.client.force_login(Member.objects.create_user("lib", email="l@x.com", password="x", is_staff=True))
        self.client.post(reverse("review_member", args=[pending.id, "reject"]))
        self.assertFalse(Member.objects.filter(username="S2").exists())

    def test_password_reset_uses_library_templates(self):
        r = self.client.get(reverse("password_reset"))
        self.assertTemplateUsed(r, "base.html")
        self.assertNotContains(r, "Django administration")
