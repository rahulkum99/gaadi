from django.urls import path

from accounts.views import (
    EmailTokenObtainPairView,
    EmailTokenRefreshView,
    MeView,
    RoleDetailView,
    RoleListView,
    UserAssignmentDestroyView,
    UserAssignmentListCreateView,
    UserDetailView,
    UserListCreateView,
)

urlpatterns = [
    path("auth/login/", EmailTokenObtainPairView.as_view(), name="auth-login"),
    path("auth/refresh/", EmailTokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("users/", UserListCreateView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path(
        "users/<int:user_id>/assignments/",
        UserAssignmentListCreateView.as_view(),
        name="user-assignment-list",
    ),
    path(
        "users/<int:user_id>/assignments/<int:pk>/",
        UserAssignmentDestroyView.as_view(),
        name="user-assignment-detail",
    ),
    path("roles/", RoleListView.as_view(), name="role-list"),
    path("roles/<int:pk>/", RoleDetailView.as_view(), name="role-detail"),
]
