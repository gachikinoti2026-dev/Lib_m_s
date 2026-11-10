from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Announcement, Book, Loan, Member


@admin.register(Member)
class MemberAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Library", {"fields": ("is_approved", "phone", "program", "department", "address")}),)
    list_display = ("username", "first_name", "last_name", "email", "program", "is_approved", "is_staff")
    list_filter = ("is_approved", "is_staff")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "isbn", "copies", "added_at")
    search_fields = ("title", "author", "isbn")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("book", "member", "status", "requested_at", "due_date", "returned_at", "fine_paid_at")
    list_filter = ("status",)
    search_fields = ("book__title", "member__username")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "is_active")
    list_filter = ("is_active",)
