from django.urls import path

from . import views

urlpatterns = [
    # students / library users
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("books/", views.books, name="books"),
    path("books/<int:book_id>/borrow/", views.borrow, name="borrow"),
    path("loans/", views.my_loans, name="my_loans"),
    # librarian
    path("librarian/", views.dashboard, name="dashboard"),
    path("librarian/stock/", views.stock, name="stock"),
    path("librarian/stock/add/", views.book_form, name="book_add"),
    path("librarian/stock/<int:book_id>/edit/", views.book_form, name="book_edit"),
    path("librarian/stock/<int:book_id>/delete/", views.book_delete, name="book_delete"),
    path("librarian/members/<int:member_id>/<str:action>/", views.review_member, name="review_member"),
    path("librarian/loans/<int:loan_id>/<str:action>/", views.update_loan, name="update_loan"),
]
