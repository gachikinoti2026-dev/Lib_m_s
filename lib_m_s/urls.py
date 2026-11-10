from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path

from library.forms import RoleLoginForm

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", LoginView.as_view(authentication_form=RoleLoginForm), name="login"),
    # logout, password reset — Django's built-in auth views
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("library.urls")),
]
