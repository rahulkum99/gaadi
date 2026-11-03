from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    DestroyAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.audit import actor_label, client_ip, logger
from accounts.models import Role, UserAssignment
from accounts.permissions import IsSuperAdmin
from accounts.throttles import LoginRateThrottle
from accounts.serializers import (
    EmailTokenObtainPairSerializer,
    RoleSerializer,
    RoleUpdateSerializer,
    UserAssignmentReplaceSerializer,
    UserAssignmentSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


def _user_queryset():
    return User.objects.select_related("role").prefetch_related(
        "role__permissions",
        "assignments",
    )


class EmailTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
    serializer_class = EmailTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        email = (request.data.get("email") or "").lower()
        ip = client_ip(request)
        try:
            response = super().post(request, *args, **kwargs)
        except Exception:
            logger.warning("login_failed email=%s ip=%s", email, ip)
            raise
        logger.info("login_success email=%s ip=%s", email, ip)
        return response


class EmailTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        ip = client_ip(request)
        try:
            response = super().post(request, *args, **kwargs)
        except Exception:
            logger.warning("token_refresh_failed ip=%s", ip)
            raise
        logger.info("token_refresh_success ip=%s", ip)
        return response


class MeView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return _user_queryset().get(pk=self.request.user.pk)


class UserListCreateView(ListCreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = _user_queryset()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info(
            "user_created actor=%s user_id=%s email=%s role=%s ip=%s",
            actor_label(request.user),
            user.pk,
            user.email,
            user.role.code if user.role else None,
            client_ip(request),
        )
        output = UserSerializer(_user_queryset().get(pk=user.pk))
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)


class UserDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = _user_queryset()

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return UserUpdateSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info(
            "user_updated actor=%s user_id=%s email=%s role=%s active=%s ip=%s",
            actor_label(request.user),
            user.pk,
            user.email,
            user.role.code if user.role else None,
            user.is_active,
            client_ip(request),
        )
        return Response(UserSerializer(_user_queryset().get(pk=user.pk)).data)

    def perform_destroy(self, instance):
        serializer = UserUpdateSerializer(
            instance,
            data={"is_active": False},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(
            "user_deactivated actor=%s user_id=%s email=%s ip=%s",
            actor_label(self.request.user),
            instance.pk,
            instance.email,
            client_ip(self.request),
        )


class RoleListView(ListAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Role.objects.prefetch_related("permissions")
    serializer_class = RoleSerializer


class RoleDetailView(RetrieveUpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Role.objects.prefetch_related("permissions")
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return RoleUpdateSerializer
        return RoleSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        logger.info(
            "role_permissions_updated actor=%s role=%s modules=%s ip=%s",
            actor_label(request.user),
            role.code,
            [item["module"] for item in serializer.validated_data.get("permissions", [])],
            client_ip(request),
        )
        role = Role.objects.prefetch_related("permissions").get(pk=role.pk)
        return Response(RoleSerializer(role).data)


class UserAssignmentListCreateView(ListCreateAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = UserAssignmentSerializer

    def get_user(self):
        return get_object_or_404(User, pk=self.kwargs["user_id"])

    def get_queryset(self):
        return self.get_user().assignments.all()

    def perform_create(self, serializer):
        try:
            assignment = serializer.save(user=self.get_user())
        except IntegrityError as exc:
            raise ValidationError({"object_id": "This assignment already exists."}) from exc
        logger.info(
            "assignment_created actor=%s user_id=%s scope=%s object_id=%s ip=%s",
            actor_label(self.request.user),
            assignment.user_id,
            assignment.scope_type,
            assignment.object_id,
            client_ip(self.request),
        )

    def put(self, request, *args, **kwargs):
        user = self.get_user()
        serializer = UserAssignmentReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.assignments.all().delete()
        created = [
            UserAssignment.objects.create(user=user, **item)
            for item in serializer.validated_data["assignments"]
        ]
        logger.info(
            "assignments_replaced actor=%s user_id=%s count=%s ip=%s",
            actor_label(request.user),
            user.pk,
            len(created),
            client_ip(request),
        )
        return Response(UserAssignmentSerializer(created, many=True).data)


class UserAssignmentDestroyView(DestroyAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = UserAssignmentSerializer

    def get_queryset(self):
        return UserAssignment.objects.filter(user_id=self.kwargs["user_id"])

    def perform_destroy(self, instance):
        logger.info(
            "assignment_deleted actor=%s user_id=%s scope=%s object_id=%s ip=%s",
            actor_label(self.request.user),
            instance.user_id,
            instance.scope_type,
            instance.object_id,
            client_ip(self.request),
        )
        instance.delete()
