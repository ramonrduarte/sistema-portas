from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", login_required(lambda _: redirect("pedidos_lista")), name="home"),
    path("", include("portas.urls")),
    path("api/v1/", include("portas.api.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
