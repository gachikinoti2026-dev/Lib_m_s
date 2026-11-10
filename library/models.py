from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

LOAN_DAYS = 14
FINE_PER_DAY = 20  # KES per overdue day


class Member(AbstractUser):
    # username = student/member ID; AbstractUser already has first/last name, email, password.
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    program = models.CharField("University program", max_length=150, blank=True)
    department = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False, help_text="Students can log in once a librarian approves them.")

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.username})"


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=150)
    isbn = models.CharField("ISBN", max_length=20, unique=True)
    description = models.TextField(blank=True)
    published_date = models.DateField(null=True, blank=True)
    copies = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    @property
    def available(self):
        return self.copies - self.loans.filter(status=Loan.BORROWED).count()


class Loan(models.Model):
    PENDING, BORROWED, RETURNED, REJECTED = "pending", "borrowed", "returned", "rejected"
    STATUS_CHOICES = [(PENDING, "Pending"), (BORROWED, "Borrowed"),
                      (RETURNED, "Returned"), (REJECTED, "Rejected")]

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="loans")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="loans")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    borrowed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    fine_paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.book} → {self.member.username} ({self.status})"

    def approve(self):
        self.status = Loan.BORROWED
        self.borrowed_at = timezone.now()
        self.due_date = timezone.localdate() + timedelta(days=LOAN_DAYS)
        self.save()

    def mark_returned(self):
        self.status = Loan.RETURNED
        self.returned_at = timezone.now()
        self.save()

    @property
    def overdue_days(self):
        if not self.due_date or self.status not in (Loan.BORROWED, Loan.RETURNED):
            return 0
        end = timezone.localdate(self.returned_at) if self.returned_at else timezone.localdate()
        return max((end - self.due_date).days, 0)

    @property
    def fine(self):
        return self.overdue_days * FINE_PER_DAY

    @property
    def fine_unpaid(self):
        return self.status == Loan.RETURNED and self.fine > 0 and not self.fine_paid_at

    def pay_fine(self):
        self.fine_paid_at = timezone.now()
        self.save()


def unpaid_fines(loans):
    # ponytail: fines are computed in Python; fine for a class-sized library, store the amount on return if it grows.
    return [l for l in loans.filter(status=Loan.RETURNED, fine_paid_at__isnull=True)
            .select_related("book", "member") if l.fine_unpaid]


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
