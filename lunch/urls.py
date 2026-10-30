
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("menu/", views.menu, name="menu"),
    path("kitchen/", views.kitchen, name="kitchen"),
    path("economics/", views.economics, name="economics"),
    path("accounting/", views.accounting, name="accounting"),
    path("assistant/", views.assistant, name="assistant"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="lunch/login.html"
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
]
