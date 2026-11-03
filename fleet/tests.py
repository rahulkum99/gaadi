from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.constants import RoleCode
from accounts.models import Role, UserAssignment
from fleet.constants import (
    District,
    DocumentType,
    DocumentValidity,
    DutyStatus,
)
from fleet.models import Constituency, Driver, Vehicle, VehicleDocument, VehicleTelemetry

User = get_user_model()
API_V1 = "/api/v1"


class FleetAPITests(APITestCase):
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

        self.mandrem = Constituency.objects.create(
            number=1, code="AC01", name="Mandrem", district=District.NORTH_GOA, lat=15.66, lng=73.72
        )
        self.panaji = Constituency.objects.create(
            number=11, code="AC11", name="Panaji", district=District.NORTH_GOA, lat=15.49, lng=73.83
        )
        self.margao = Constituency.objects.create(
            number=31, code="AC31", name="Margao", district=District.SOUTH_GOA, lat=15.27, lng=73.96
        )

        now = timezone.now()
        self.active_vehicle = self._vehicle(
            self.mandrem,
            "GA-NG-AC01-V01",
            "GA08AA1001",
            "Ravi Naik",
            {
                "speed_kmh": 20,
                "led_on": True,
                "gps_connected": True,
                "last_update": now,
                "trip_started": True,
                "today_km": 18,
            },
        )
        self.halt_vehicle = self._vehicle(
            self.mandrem,
            "GA-NG-AC01-V02",
            "GA08AA1002",
            "Suresh Kamat",
            {
                "speed_kmh": 0,
                "led_on": True,
                "gps_connected": True,
                "last_update": now - timedelta(minutes=90),
                "trip_started": True,
                "today_km": 12,
            },
        )
        self.inactive_vehicle = self._vehicle(
            self.panaji,
            "GA-NG-AC11-V01",
            "GA07BB2101",
            "Anita Dessai",
            {
                "speed_kmh": 0,
                "led_on": False,
                "gps_connected": False,
                "last_update": now - timedelta(hours=6),
                "trip_started": False,
                "today_km": 0,
            },
        )
        self.exceeded_vehicle = self._vehicle(
            self.margao,
            "GA-SG-AC31-V01",
            "GA08CC3101",
            "Priya Naik",
            {
                "speed_kmh": 25,
                "led_on": True,
                "gps_connected": True,
                "last_update": now,
                "trip_started": True,
                "today_km": 72,
            },
        )
        VehicleDocument.objects.update_or_create(
            vehicle=self.active_vehicle,
            doc_type=DocumentType.INSURANCE,
            defaults={
                "file_name": "insurance.pdf",
                "end_date": timezone.now().date() + timedelta(days=10),
                "approval": "pending",
            },
        )
        VehicleDocument.objects.update_or_create(
            vehicle=self.inactive_vehicle,
            doc_type=DocumentType.FITNESS,
            defaults={
                "file_name": "fitness.pdf",
                "end_date": timezone.now().date() - timedelta(days=2),
                "approval": "approved",
            },
        )
        VehicleDocument.objects.update_or_create(
            vehicle=self.exceeded_vehicle,
            doc_type=DocumentType.ADVERTISEMENT_LICENSE,
            defaults={
                "file_name": "ad.pdf",
                "end_date": timezone.now().date() + timedelta(days=45),
                "approval": "approved",
            },
        )

        self.finance = User.objects.create_user(
            email="finance@example.com",
            password="FinancePass123!",
            full_name="Finance User",
            role=self.finance_role,
        )
        self.gov = User.objects.create_user(
            email="gov@example.com",
            password="GovPass123!",
            full_name="Gov Viewer",
            role=self.gov_role,
        )
        self.head = User.objects.create_user(
            email="head@example.com",
            password="HeadPass123!",
            full_name="Ward Head",
            role=self.head_role,
        )
        self.unassigned = User.objects.create_user(
            email="empty@example.com",
            password="EmptyPass123!",
            full_name="Empty Head",
            role=self.head_role,
        )
        UserAssignment.objects.create(
            user=self.head,
            scope_type="constituency",
            object_id=str(self.mandrem.id),
        )
        UserAssignment.objects.create(
            user=self.head,
            scope_type="constituency",
            object_id=str(self.panaji.id),
        )
        UserAssignment.objects.create(
            user=self.finance,
            scope_type="constituency",
            object_id=str(self.margao.id),
        )
        UserAssignment.objects.create(
            user=self.gov,
            scope_type="constituency",
            object_id=str(self.mandrem.id),
        )

    def _vehicle(self, constituency, code, registration, driver_name, telemetry):
        driver = Driver.objects.create(
            name=driver_name,
            phone="9822000000",
            licence_number="GA01 1000000001",
            duty_status=DutyStatus.ON_DUTY if telemetry.get("trip_started") else DutyStatus.OFF_DUTY,
        )
        vehicle = Vehicle.objects.create(
            code=code,
            registration=registration,
            constituency=constituency,
            driver=driver,
        )
        VehicleTelemetry.objects.create(
            vehicle=vehicle,
            lat=constituency.lat,
            lng=constituency.lng,
            address=f"{constituency.name} depot",
            ignition=telemetry.get("trip_started", False),
            **telemetry,
        )
        return vehicle

    def authenticate(self, user, password):
        response = self.client.post(
            f"{API_V1}/auth/login/",
            {"email": user.email, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    def test_super_admin_lists_all_constituencies(self):
        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.get(f"{API_V1}/constituencies/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        by_code = {item["code"]: item for item in response.data}
        self.assertEqual(by_code["AC01"]["status"], "needs_attention")
        self.assertEqual(by_code["AC11"]["status"], "inactive")
        self.assertEqual(by_code["AC31"]["status"], "needs_attention")
        self.assertEqual(by_code["AC01"]["total"], 2)
        self.assertEqual(by_code["AC01"]["attention"], 1)

    def test_head_sees_multiple_assigned_constituencies_only(self):
        self.authenticate(self.head, "HeadPass123!")
        response = self.client.get(f"{API_V1}/constituencies/")
        self.assertEqual({item["code"] for item in response.data}, {"AC01", "AC11"})
        vehicles = self.client.get(f"{API_V1}/vehicles/")
        self.assertEqual({item["code"] for item in vehicles.data}, {"GA-NG-AC01-V01", "GA-NG-AC01-V02", "GA-NG-AC11-V01"})
        hidden = self.client.get(f"{API_V1}/constituencies/{self.margao.id}/")
        self.assertEqual(hidden.status_code, status.HTTP_404_NOT_FOUND)

    def test_unassigned_user_sees_empty_lists(self):
        self.authenticate(self.unassigned, "EmptyPass123!")
        self.assertEqual(self.client.get(f"{API_V1}/constituencies/").data, [])
        self.assertEqual(self.client.get(f"{API_V1}/vehicles/").data, [])
        self.assertEqual(
            self.client.get(f"{API_V1}/constituencies/{self.mandrem.id}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_search_filter_and_sort_constituencies(self):
        self.authenticate(self.admin, "AdminPass123!")
        search = self.client.get(f"{API_V1}/constituencies/", {"q": "panaji"})
        self.assertEqual([item["code"] for item in search.data], ["AC11"])
        filtered = self.client.get(f"{API_V1}/constituencies/", {"status": "inactive"})
        self.assertEqual([item["code"] for item in filtered.data], ["AC11"])
        ordered = self.client.get(f"{API_V1}/constituencies/", {"ordering": "name"})
        self.assertEqual([item["name"] for item in ordered.data], ["Mandrem", "Margao", "Panaji"])

    def test_vehicle_filters(self):
        self.authenticate(self.admin, "AdminPass123!")
        active = self.client.get(f"{API_V1}/vehicles/", {"status": "active"})
        self.assertTrue(all(item["status"] == "active" for item in active.data))
        attention = self.client.get(f"{API_V1}/vehicles/", {"status": "attention"})
        self.assertTrue(all(item["attention"] for item in attention.data))
        exceeded = self.client.get(f"{API_V1}/vehicles/", {"status": "exceeded"})
        self.assertEqual([item["code"] for item in exceeded.data], ["GA-SG-AC31-V01"])
        search = self.client.get(f"{API_V1}/vehicles/", {"q": "ravi"})
        self.assertEqual([item["code"] for item in search.data], ["GA-NG-AC01-V01"])

    def test_finance_is_assignment_scoped_and_redacted(self):
        self.authenticate(self.finance, "FinancePass123!")
        constituencies = self.client.get(f"{API_V1}/constituencies/")
        self.assertEqual([item["code"] for item in constituencies.data], ["AC31"])
        detail = self.client.get(f"{API_V1}/vehicles/{self.exceeded_vehicle.id}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertTrue(detail.data["driver"]["contact_restricted"])
        self.assertIsNone(detail.data["driver"]["phone"])
        types = {item["type"] for item in detail.data["documents"]}
        self.assertEqual(types, {DocumentType.INSURANCE, DocumentType.ADVERTISEMENT_LICENSE})
        hidden = self.client.get(f"{API_V1}/vehicles/{self.active_vehicle.id}/")
        self.assertEqual(hidden.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_admin_cannot_assign_constituencies(self):
        self.authenticate(self.head, "HeadPass123!")
        response = self.client.post(
            f"{API_V1}/users/{self.unassigned.id}/assignments/",
            {"scope_type": "constituency", "object_id": str(self.mandrem.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_super_admin_bulk_replace_assignments(self):
        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.put(
            f"{API_V1}/users/{self.head.id}/assignments/",
            {
                "assignments": [
                    {"scope_type": "constituency", "object_id": str(self.margao.id)},
                    {"scope_type": "constituency", "object_id": str(self.panaji.id)},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.client.credentials()
        self.authenticate(self.head, "HeadPass123!")
        codes = {item["code"] for item in self.client.get(f"{API_V1}/constituencies/").data}
        self.assertEqual(codes, {"AC11", "AC31"})

    def test_invalid_assignment_uuid_is_rejected(self):
        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.post(
            f"{API_V1}/users/{self.unassigned.id}/assignments/",
            {"scope_type": "constituency", "object_id": "not-a-constituency"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_constituency_detail_vehicles_map_alerts_and_report(self):
        self.authenticate(self.admin, "AdminPass123!")
        detail = self.client.get(f"{API_V1}/constituencies/{self.mandrem.id}/")
        self.assertEqual(len(detail.data["vehicles"]), 2)
        self.assertGreaterEqual(len(detail.data["alerts"]), 1)
        vehicles = self.client.get(f"{API_V1}/constituencies/{self.mandrem.id}/vehicles/")
        self.assertEqual(len(vehicles.data), 2)
        mapped = self.client.get(f"{API_V1}/constituencies/{self.mandrem.id}/map/")
        self.assertEqual(mapped.data["code"], "AC01")
        self.assertEqual(len(mapped.data["vehicles"]), 2)
        report = self.client.get(f"{API_V1}/constituencies/{self.mandrem.id}/report/")
        self.assertEqual(report.data["vehicles"], 2)
        self.assertEqual(report.data["attention"], 1)

    def test_document_validity_and_finance_filter(self):
        self.authenticate(self.admin, "AdminPass123!")
        rows = self.client.get(f"{API_V1}/compliance/documents/", {"validity": "expired"})
        self.assertTrue(all(item["validity"] == DocumentValidity.EXPIRED for item in rows.data))
        summary = self.client.get(f"{API_V1}/compliance/summary/")
        self.assertGreaterEqual(summary.data["expired"], 1)
        self.client.credentials()
        self.authenticate(self.finance, "FinancePass123!")
        finance_rows = self.client.get(f"{API_V1}/compliance/documents/")
        types = {item["document"]["type"] for item in finance_rows.data}
        self.assertTrue(types.issubset({DocumentType.INSURANCE, DocumentType.ADVERTISEMENT_LICENSE}))

    def test_document_review_is_super_admin_only(self):
        self.authenticate(self.head, "HeadPass123!")
        forbidden = self.client.post(
            f"{API_V1}/vehicles/{self.active_vehicle.id}/documents/{DocumentType.INSURANCE}/review/",
            {"decision": "approved"},
            format="json",
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)
        self.client.credentials()
        self.authenticate(self.admin, "AdminPass123!")
        approved = self.client.post(
            f"{API_V1}/vehicles/{self.active_vehicle.id}/documents/{DocumentType.INSURANCE}/review/",
            {"decision": "approved", "comment": "Looks good"},
            format="json",
        )
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        self.assertEqual(approved.data["approval"], "approved")

    def test_document_report_and_csv_export(self):
        self.authenticate(self.admin, "AdminPass123!")
        report = self.client.get(f"{API_V1}/reports/documents/")
        self.assertIn("counts", report.data)
        self.assertGreaterEqual(report.data["counts"]["total"], 1)
        csv_response = self.client.get(f"{API_V1}/reports/documents/", {"export": "csv"})
        self.assertEqual(csv_response.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", csv_response["Content-Type"])
        self.assertIn("vehicle_code", csv_response.content.decode())

    def test_super_admin_creates_constituency_and_vehicle(self):
        self.authenticate(self.admin, "AdminPass123!")
        created = self.client.post(
            f"{API_V1}/constituencies/",
            {"name": "New Ward", "district": District.NORTH_GOA},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["code"], "AC32")
        vehicle = self.client.post(
            f"{API_V1}/vehicles/",
            {
                "constituency": str(self.mandrem.id),
                "registration": "ga08zz9999",
                "driver_name": "New Driver",
                "driver_phone": "9898989898",
            },
            format="json",
        )
        self.assertEqual(vehicle.status_code, status.HTTP_201_CREATED)
        self.assertEqual(vehicle.data["registration"], "GA08ZZ9999")
        self.assertEqual(len(vehicle.data["documents"]), 8)

    def test_head_cannot_create_constituency_or_vehicle(self):
        self.authenticate(self.head, "HeadPass123!")
        self.assertEqual(
            self.client.post(
                f"{API_V1}/constituencies/",
                {"name": "Blocked", "district": District.NORTH_GOA},
                format="json",
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(
                f"{API_V1}/vehicles/",
                {
                    "constituency": str(self.mandrem.id),
                    "registration": "GA08ZZ0001",
                    "driver_name": "Nope",
                },
                format="json",
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
