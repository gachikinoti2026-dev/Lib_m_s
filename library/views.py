from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Count, F, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import BookForm, RegistrationForm
from .models import Announcement, Book, Loan, Member, unpaid_fines


librarian_required = user_passes_test(lambda u: u.is_staff)


def student_required(view):
    """Logged-in members only; librarians are sent to their dashboard."""
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            return redirect("dashboard")
        if not request.user.is_approved:
            logout(request)
            messages.warning(request, "Your account is waiting for approval by the library admin.")
            return redirect("login")
        return view(request, *args, **kwargs)
    return wrapper


def with_availability(qs):
    return (qs.annotate(n_out=Count("loans", filter=Q(loans__status=Loan.BORROWED)))
              .annotate(n_available=F("copies") - F("n_out")))


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegistrationForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Account created. You can log in once the library admin approves it.")
        return redirect("login")
    return render(request, "library/register.html", {"form": form})


@student_required
def home(request):
    loans = request.user.loans.select_related("book")
    context = {
        "announcements": Announcement.objects.filter(is_active=True)[:5],
        "active_loans": loans.filter(status=Loan.BORROWED),
        "pending_count": loans.filter(status=Loan.PENDING).count(),
        "book_count": Book.objects.count(),
        "new_arrivals": Book.objects.order_by("-added_at")[:5],
        "fines_due": sum(l.fine for l in unpaid_fines(request.user.loans)),
    }
    return render(request, "library/home.html", context)


@student_required
def books(request):
    q = request.GET.get("q", "").strip()
    qs = with_availability(Book.objects.all())
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(author__icontains=q) | Q(isbn__icontains=q))
    requested = set(request.user.loans.filter(status__in=[Loan.PENDING, Loan.BORROWED])
                    .values_list("book_id", flat=True))
    return render(request, "library/books.html", {"books": qs, "q": q, "requested": requested})


@student_required
@require_POST
def borrow(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    if request.user.loans.filter(book=book, status__in=[Loan.PENDING, Loan.BORROWED]).exists():
        messages.warning(request, f"You already have “{book}” requested or borrowed.")
    elif unpaid_fines(request.user.loans):
        messages.error(request, "Please clear your outstanding fines at the desk before borrowing.")
    elif book.available < 1:
        messages.error(request, f"“{book}” has no copies available right now.")
    else:
        Loan.objects.create(book=book, member=request.user)
        messages.success(request, f"Request for “{book}” sent. A librarian will approve it shortly.")
    return redirect("books")


@student_required
def my_loans(request):
    loans = request.user.loans.select_related("book")
    return render(request, "library/loans.html", {"loans": loans})


# ---- Librarian side ----

@librarian_required
def dashboard(request):
    stock = with_availability(Book.objects.all())
    unpaid = unpaid_fines(Loan.objects)
    return render(request, "library/dashboard.html", {
        "title_count": stock.count(),
        "out_of_stock": stock.filter(n_available__lte=0).count(),
        "fines_total": sum(l.fine for l in unpaid),
        "requests": Loan.objects.filter(status=Loan.PENDING).select_related("book", "member"),
        "out": Loan.objects.filter(status=Loan.BORROWED).select_related("book", "member")
                           .order_by("due_date"),
        "unpaid": unpaid,
        "signups": Member.objects.filter(is_staff=False, is_approved=False).order_by("date_joined"),
    })


@librarian_required
@require_POST
def review_member(request, member_id, action):
    member = get_object_or_404(Member, pk=member_id, is_staff=False, is_approved=False)
    if action == "approve":
        member.is_approved = True
        member.save()
        messages.success(request, f"{member} can now log in.")
    elif action == "reject":
        member.delete()
        messages.info(request, f"Sign-up from {member} rejected.")
    return redirect("dashboard")


@librarian_required
def stock(request):
    q = request.GET.get("q", "").strip()
    show = request.GET.get("show", "")
    qs = with_availability(Book.objects.all())
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(author__icontains=q) | Q(isbn__icontains=q))
    if show == "in":
        qs = qs.filter(n_available__gt=0)
    elif show == "out":
        qs = qs.filter(n_available__lte=0)
    return render(request, "library/stock.html", {"books": qs, "q": q, "show": show})


@librarian_required
def book_form(request, book_id=None):
    book = get_object_or_404(Book, pk=book_id) if book_id else None
    form = BookForm(request.POST or None, instance=book)
    if form.is_valid():
        form.save()
        messages.success(request, f"“{form.instance}” saved.")
        return redirect("stock")
    return render(request, "library/book_form.html", {"form": form, "book": book})


@librarian_required
@require_POST
def book_delete(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    try:
        book.delete()
        messages.success(request, f"“{book}” removed from the catalogue.")
    except ProtectedError:
        messages.error(request, f"“{book}” has loan history and can't be deleted. Set its copies to 0 instead.")
    return redirect("stock")


@librarian_required
@require_POST
def update_loan(request, loan_id, action):
    with transaction.atomic():
        loan = get_object_or_404(Loan.objects.select_for_update(), pk=loan_id)
        if action == "approve" and loan.status == Loan.PENDING:
            if loan.book.available < 1:
                messages.error(request, f"No copies of “{loan.book}” left to lend.")
            else:
                loan.approve()
                messages.success(request, f"Approved “{loan.book}” for {loan.member.username}.")
        elif action == "reject" and loan.status == Loan.PENDING:
            loan.status = Loan.REJECTED
            loan.save()
            messages.info(request, "Request rejected.")
        elif action == "return" and loan.status == Loan.BORROWED:
            loan.mark_returned()
            note = f" Fine due: KES {loan.fine:,}." if loan.fine else ""
            messages.success(request, f"“{loan.book}” returned.{note}")
        elif action == "pay" and loan.fine_unpaid:
            loan.pay_fine()
            messages.success(request, f"Fine of KES {loan.fine:,} paid by {loan.member.username}.")
        else:
            messages.error(request, "That action isn't valid for this loan.")
    return redirect("dashboard")
