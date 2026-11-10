from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.forms import ValidationError

from .models import Book, Loan, Member


class NoColon:
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


class RegistrationForm(NoColon, UserCreationForm):
    # UserCreationForm already handles password confirmation, validation and hashing.
    class Meta:
        model = Member
        fields = ["first_name", "last_name", "username", "email", "phone", "program", "department", "address"]
        labels = {"username": "Student ID"}
        widgets = {"program": forms.TextInput(attrs={"placeholder": "e.g. BSc Computer Science"})}
        help_texts = {"username": ""}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("first_name", "last_name", "email", "phone", "program"):
            self.fields[name].required = True
        self.fields["address"].widget.attrs["rows"] = 3

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if Member.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email


class RoleLoginForm(NoColon, AuthenticationForm):
    role = forms.ChoiceField(choices=[("student", "Student"), ("admin", "Library admin")],
                             initial="student", widget=forms.RadioSelect)

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if self.cleaned_data.get("role") == "admin" and not user.is_staff:
            raise ValidationError("This account isn't a library admin. Choose “Student” to log in.")
        if self.cleaned_data.get("role") == "student" and user.is_staff:
            raise ValidationError("This is a library admin account. Choose “Library admin” to log in.")
        if not user.is_staff and not user.is_approved:
            raise ValidationError("Your account is waiting for approval by the library admin. Please check back later.")


class BookForm(NoColon, forms.ModelForm):
    class Meta:
        model = Book
        fields = ["title", "author", "isbn", "copies", "published_date", "description"]
        widgets = {
            "published_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_copies(self):
        copies = self.cleaned_data["copies"]
        if self.instance.pk:
            out = self.instance.loans.filter(status=Loan.BORROWED).count()
            if copies < out:
                raise ValidationError(f"{out} copies are currently on loan; copies can't go below that.")
        return copies
