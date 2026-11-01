from copy import deepcopy

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.constants import Level, Module, RoleCode, Scope
from accounts.models import Role, RolePermission
from accounts.services import user_can, user_scope

User = get_user_model()

API_V1 = "/api/v1"


class AccountsRBACTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPass123!",
            full_name="Super Admin",
        )
        self.finance_role = Role.objects.get(code=RoleCode.FINANCE)
        self.gov_role = Role.objects.get(code=RoleCode.GOVERNMENT_VIEWER)
        self.head_role = Role.objects.get(code=RoleCode.CONSTITUENCY_HEAD)

    def authenticate(self, user, password):
        response = self.client.post(
            f"{API_V1}/auth/login/",
            {"email": user.email, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    def test_unversioned_and_unknown_api_versions_are_rejected(self):
        payload = {"email": self.admin.email, "password": "AdminPass123!"}
        self.assertEqual(
            self.client.post("/api/auth/login/", payload, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.post("/api/v2/auth/login/", payload, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_login_is_throttled(self):
        rest = deepcopy(settings.REST_FRAMEWORK)
        rest["DEFAULT_THROTTLE_RATES"] = {
            **rest["DEFAULT_THROTTLE_RATES"],
            "login": "2/minute",
        }
        payload = {"email": self.admin.email, "password": "WrongPass123!"}
        with self.settings(REST_FRAMEWORK=rest):
            cache.clear()
            self.assertEqual(
                self.client.post(f"{API_V1}/auth/login/", payload, format="json").status_code,
                status.HTTP_401_UNAUTHORIZED,
            )
            self.assertEqual(
                self.client.post(f"{API_V1}/auth/login/", payload, format="json").status_code,
                status.HTTP_401_UNAUTHORIZED,
            )
            response = self.client.post(f"{API_V1}/auth/login/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_login_returns_tokens_and_permissions(self):
        response = self.authenticate(self.admin, "AdminPass123!")
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "admin@example.com")
        self.assertEqual(response.data["user"]["role"], RoleCode.SUPER_ADMIN)
        modules = {item["module"] for item in response.data["user"]["permissions"]}
        self.assertIn(Module.USER_MANAGEMENT, modules)

    def test_me_requires_auth_and_returns_current_user(self):
        response = self.client.get(f"{API_V1}/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.get(f"{API_V1}/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.admin.email)

    def test_non_admin_cannot_create_users(self):
        finance = User.objects.create_user(
            email="finance@example.com",
            password="FinancePass123!",
            full_name="Finance User",
            role=self.finance_role,
        )
        self.authenticate(finance, "FinancePass123!")
        response = self.client.post(
            f"{API_V1}/users/",
            {
                "email": "viewer@example.com",
                "password": "ViewerPass123!",
                "full_name": "Gov Viewer",
                "role": RoleCode.GOVERNMENT_VIEWER,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(email="viewer@example.com").exists())

    def test_super_admin_creates_role_users_and_assignments(self):
        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.post(
            f"{API_V1}/users/",
            {
                "email": "head@example.com",
                "password": "HeadPass123!",
                "full_name": "Ward Head",
                "role": RoleCode.CONSTITUENCY_HEAD,
                "assignments": [
                    {"scope_type": "constituency", "object_id": "c-12"},
                    {"scope_type": "vehicle", "object_id": "v-9"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], RoleCode.CONSTITUENCY_HEAD)
        self.assertEqual(len(response.data["assignments"]), 2)

        created = User.objects.get(email="head@example.com")
        self.assertFalse(created.is_superuser)
        self.assertEqual(created.assignments.count(), 2)

    def test_role_defaults_match_seeded_matrix(self):
        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.get(f"{API_V1}/roles/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        roles = {item["code"]: item for item in response.data}
        self.assertEqual(len(roles), 4)

        finance_perms = {
            item["module"]: item for item in roles[RoleCode.FINANCE]["permissions"]
        }
        self.assertEqual(finance_perms[Module.DASHBOARD]["level"], Level.VIEW)
        self.assertEqual(finance_perms[Module.DASHBOARD]["scope"], Scope.FINANCIAL)
        self.assertEqual(finance_perms[Module.USER_MANAGEMENT]["level"], Level.NONE)
        self.assertEqual(finance_perms[Module.FINANCIAL_RECORDS]["level"], Level.FULL)

        head_perms = {
            item["module"]: item for item in roles[RoleCode.CONSTITUENCY_HEAD]["permissions"]
        }
        self.assertEqual(head_perms[Module.VEHICLES]["scope"], Scope.ASSIGNED)
        self.assertEqual(head_perms[Module.DOCUMENT_APPROVALS]["level"], Level.NONE)

    def test_super_admin_can_edit_role_permissions(self):
        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.patch(
            f"{API_V1}/roles/{self.finance_role.pk}/",
            {
                "permissions": [
                    {"module": Module.LIVE_MAP, "level": Level.NONE, "scope": Scope.NONE},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        live_map = next(
            item for item in response.data["permissions"] if item["module"] == Module.LIVE_MAP
        )
        self.assertEqual(live_map["level"], Level.NONE)
        self.assertEqual(
            RolePermission.objects.get(role=self.finance_role, module=Module.LIVE_MAP).level,
            Level.NONE,
        )
        dashboard = RolePermission.objects.get(
            role=self.finance_role,
            module=Module.DASHBOARD,
        )
        self.assertEqual(dashboard.level, Level.VIEW)
        self.assertEqual(dashboard.scope, Scope.FINANCIAL)

    def test_super_admin_role_permissions_are_locked(self):
        self.authenticate(self.admin, "AdminPass123!")
        role = Role.objects.get(code=RoleCode.SUPER_ADMIN)
        response = self.client.patch(
            f"{API_V1}/roles/{role.pk}/",
            {
                "permissions": [
                    {"module": Module.USER_MANAGEMENT, "level": Level.NONE, "scope": Scope.NONE},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_can_and_scope_helpers(self):
        finance = User.objects.create_user(
            email="finance2@example.com",
            password="FinancePass123!",
            role=self.finance_role,
        )
        self.client.force_authenticate(finance)
        self.assertTrue(user_can(finance, Module.FINANCIAL_RECORDS, Level.FULL))
        self.assertFalse(user_can(finance, Module.USER_MANAGEMENT, Level.VIEW))
        self.assertEqual(user_scope(finance, Module.DASHBOARD), Scope.FINANCIAL)
        self.assertTrue(user_can(self.admin, Module.SYSTEM_SETTINGS, Level.FULL))
        self.assertEqual(user_scope(self.admin, Module.VEHICLES), Scope.ALL)

    def test_delete_user_deactivates_instead_of_removing(self):
        target = User.objects.create_user(
            email="temp@example.com",
            password="TempPass123!",
            role=self.gov_role,
        )
        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.delete(f"{API_V1}/users/{target.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        target.refresh_from_db()
        self.assertFalse(target.is_active)
        self.assertTrue(User.objects.filter(pk=target.pk).exists())

    def test_cannot_deactivate_last_super_admin(self):
        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.delete(f"{API_V1}/users/{self.admin.pk}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
