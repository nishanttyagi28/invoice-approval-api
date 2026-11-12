from django.urls import path

from apps.accounts.views import ThrottledTokenObtainPairView, ThrottledTokenRefreshView

urlpatterns = [
    path("auth/token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain"),
    path("auth/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
]
