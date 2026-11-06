from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.constants import RoleCode
from accounts.models import Role, UserAssignment
from fleet.constants import (
    AlertType,
    District,
    DocumentType,
    DocumentValidity,
    DutyStatus,
)
from fleet.ingest import snapshot_live_fleet
from fleet.models import (
    AlertEvent,
    Constituency,
    Driver,
    Vehicle,
    VehicleDocument,
    VehicleGpsPoint,
    VehicleTelemetry,
)
from fleet.track360 import map_device_to_telemetry, parse_track360_datetime

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

    @override_settings(TRACK360_USERNAME="", TRACK360_PASSWORD="")
    def test_live_map_counts_markers_and_table(self):
        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.get(f"{API_V1}/live-map/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["counts"]["total"], 4)
        self.assertEqual(response.data["counts"]["active"], 2)
        self.assertEqual(response.data["counts"]["long_halt"], 1)
        self.assertEqual(response.data["counts"]["inactive"], 1)
        self.assertEqual(response.data["counts"]["attention"], 2)
        self.assertEqual(response.data["counts"]["exceeded"], 1)
        self.assertEqual(len(response.data["vehicles"]), 4)
        by_code = {item["code"]: item for item in response.data["vehicles"]}
        self.assertEqual(by_code["GA-NG-AC01-V01"]["status"], "active")
        self.assertEqual(by_code["GA-NG-AC01-V02"]["status"], "long_halt")
        self.assertEqual(by_code["GA-NG-AC11-V01"]["status"], "inactive")
        self.assertEqual(by_code["GA-SG-AC31-V01"]["exceeded"], True)
        self.assertEqual(by_code["GA-NG-AC01-V01"]["location"], "Mandrem depot")
        self.assertEqual(response.data["source"], "stored")

    @override_settings(TRACK360_USERNAME="", TRACK360_PASSWORD="")
    def test_live_map_filters_and_scope(self):
        self.authenticate(self.admin, "AdminPass123!")
        active = self.client.get(f"{API_V1}/live-map/", {"status": "active"})
        self.assertEqual(active.data["counts"]["total"], 4)
        self.assertTrue(all(item["status"] == "active" for item in active.data["vehicles"]))
        search = self.client.get(f"{API_V1}/live-map/", {"q": "ravi"})
        self.assertEqual([item["code"] for item in search.data["vehicles"]], ["GA-NG-AC01-V01"])
        constituency = self.client.get(
            f"{API_V1}/live-map/", {"constituency": str(self.mandrem.id)}
        )
        self.assertEqual(constituency.data["counts"]["total"], 2)
        self.assertEqual(len(constituency.data["vehicles"]), 2)
        bad_status = self.client.get(f"{API_V1}/live-map/", {"status": "moving"})
        self.assertEqual(bad_status.status_code, status.HTTP_400_BAD_REQUEST)
        bad_date = self.client.get(f"{API_V1}/live-map/", {"date": "06-11-2026"})
        self.assertEqual(bad_date.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.credentials()
        self.authenticate(self.head, "HeadPass123!")
        head_map = self.client.get(f"{API_V1}/live-map/")
        self.assertEqual(head_map.data["counts"]["total"], 3)
        self.assertEqual(head_map.data["counts"]["exceeded"], 0)

        self.client.credentials()
        self.authenticate(self.unassigned, "EmptyPass123!")
        empty = self.client.get(f"{API_V1}/live-map/")
        self.assertEqual(empty.data["counts"]["total"], 0)
        self.assertEqual(empty.data["vehicles"], [])

    @override_settings(TRACK360_USERNAME="", TRACK360_PASSWORD="")
    def test_live_map_csv_export(self):
        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.get(f"{API_V1}/live-map/", {"export": "csv"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", response["Content-Type"])
        body = response.content.decode()
        self.assertIn("vehicle,registration,constituency,driver,status", body)
        self.assertIn("GA-NG-AC01-V01", body)

    @override_settings(TRACK360_USERNAME="8010666611", TRACK360_PASSWORD="secret", TRACK360_CACHE_SECONDS=0)
    @patch("fleet.live_map.fetch_devices")
    def test_live_map_overlays_track360_position(self, fetch_devices):
        self.active_vehicle.imei = "864540081600348"
        self.active_vehicle.save(update_fields=["imei"])
        fetch_devices.return_value = (
            [
                {
                    "deviceImei": "864540081600348",
                    "latitude": "15.6611",
                    "longitude": "73.7192",
                    "speed": "18.5",
                    "ignition": "true",
                    "status": "online",
                    "valid": 1,
                    "daily_distance": 18500.0,
                    "lastUpdate": "2026-11-06T10:15:00.000000+0000",
                    "course": "75",
                    "alarm": "null",
                    "vehicle_status": "Dormant",
                }
            ],
            None,
        )
        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.get(f"{API_V1}/live-map/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["source"], "track360")
        self.assertEqual(response.data["feed"]["matched"], 1)
        row = next(item for item in response.data["vehicles"] if item["code"] == "GA-NG-AC01-V01")
        self.assertEqual(row["lat"], 15.6611)
        self.assertEqual(row["lng"], 73.7192)
        self.assertEqual(row["today_km"], 18.5)
        self.assertEqual(row["speed_kmh"], 18.5)
        self.assertEqual(row["course"], 75.0)
        self.assertEqual(row["device_status"], "online")
        self.active_vehicle.telemetry.refresh_from_db()
        self.assertEqual(self.active_vehicle.telemetry.lat, 15.6611)
        self.assertEqual(self.active_vehicle.telemetry.today_km, 18.5)

    @override_settings(TRACK360_USERNAME="8010666611", TRACK360_PASSWORD="secret")
    @patch("fleet.live_map.fetch_devices")
    def test_live_map_yesterday_skips_track360(self, fetch_devices):
        self.authenticate(self.admin, "AdminPass123!")
        response = self.client.get(f"{API_V1}/live-map/", {"date": "yesterday"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["live"])
        self.assertEqual(response.data["source"], "stored")
        fetch_devices.assert_not_called()

    def test_finance_cannot_export_live_map_csv(self):
        self.authenticate(self.finance, "FinancePass123!")
        response = self.client.get(f"{API_V1}/live-map/", {"export": "csv"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_platform_settings_get_put_and_reset(self):
        self.authenticate(self.admin, "AdminPass123!")
        current = self.client.get(f"{API_V1}/settings/")
        self.assertEqual(current.status_code, status.HTTP_200_OK)
        self.assertEqual(current.data["daily_km_limit"], 60)
        self.assertEqual(current.data["long_halt_minutes"], 60)
        self.assertEqual(current.data["min_stop_minutes"], 5)
        self.assertEqual(current.data["stale_gps_minutes"], 15)
        self.assertEqual(current.data["expire_soon_days"], 30)
        self.assertEqual(current.data["expire_watch_days"], 60)
        self.assertEqual(current.data["approach_ratio"], 0.9)
        self.assertEqual(current.data["operating_start_hour"], 8)
        self.assertEqual(current.data["operating_end_hour"], 18)
        self.assertEqual(current.data["live_snapshot_minutes"], 5)

        updated = self.client.put(
            f"{API_V1}/settings/",
            {
                "daily_km_limit": 80,
                "long_halt_minutes": 90,
                "min_stop_minutes": 10,
                "stale_gps_minutes": 20,
                "expire_soon_days": 14,
                "expire_watch_days": 45,
                "approach_ratio": 0.8,
                "operating_start_hour": 7,
                "operating_end_hour": 19,
            },
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["daily_km_limit"], 80)
        self.assertEqual(updated.data["long_halt_minutes"], 90)

        reset = self.client.post(f"{API_V1}/settings/reset/")
        self.assertEqual(reset.status_code, status.HTTP_200_OK)
        self.assertEqual(reset.data["daily_km_limit"], 60)
        self.assertEqual(reset.data["long_halt_minutes"], 60)

    def test_platform_settings_validation_and_permissions(self):
        self.authenticate(self.head, "HeadPass123!")
        self.assertEqual(self.client.get(f"{API_V1}/settings/").status_code, status.HTTP_403_FORBIDDEN)
        self.client.credentials()
        self.authenticate(self.admin, "AdminPass123!")
        invalid = self.client.put(
            f"{API_V1}/settings/",
            {
                "daily_km_limit": 60,
                "long_halt_minutes": 60,
                "min_stop_minutes": 5,
                "stale_gps_minutes": 15,
                "expire_soon_days": 30,
                "expire_watch_days": 20,
                "approach_ratio": 0.9,
                "operating_start_hour": 8,
                "operating_end_hour": 18,
            },
            format="json",
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(TRACK360_USERNAME="", TRACK360_PASSWORD="")
    def test_settings_drive_km_and_halt_alerts(self):
        self.authenticate(self.admin, "AdminPass123!")
        self.client.put(
            f"{API_V1}/settings/",
            {
                "daily_km_limit": 100,
                "long_halt_minutes": 180,
                "min_stop_minutes": 5,
                "stale_gps_minutes": 15,
                "expire_soon_days": 30,
                "expire_watch_days": 60,
                "approach_ratio": 0.9,
                "operating_start_hour": 8,
                "operating_end_hour": 18,
            },
            format="json",
        )
        live = self.client.get(f"{API_V1}/live-map/")
        by_code = {item["code"]: item for item in live.data["vehicles"]}
        self.assertFalse(by_code["GA-SG-AC31-V01"]["exceeded"])
        self.assertEqual(by_code["GA-NG-AC01-V02"]["status"], "active")
        self.assertEqual(live.data["thresholds"]["daily_km_limit"], 100)

        self.client.post(f"{API_V1}/settings/reset/")
        restored = self.client.get(f"{API_V1}/live-map/")
        by_code = {item["code"]: item for item in restored.data["vehicles"]}
        self.assertTrue(by_code["GA-SG-AC31-V01"]["exceeded"])
        self.assertEqual(by_code["GA-NG-AC01-V02"]["status"], "long_halt")

    @override_settings(TRACK360_USERNAME="", TRACK360_PASSWORD="")
    def test_live_snapshot_saves_every_five_minutes(self):
        first = snapshot_live_fleet(force=True)
        self.assertEqual(first["points"], 4)
        self.assertEqual(VehicleGpsPoint.objects.count(), 4)
        second = snapshot_live_fleet(force=False)
        self.assertEqual(second["points"], 0)
        self.assertEqual(second["skipped"], 4)
        forced = snapshot_live_fleet(force=True)
        self.assertEqual(forced["points"], 4)
        self.assertEqual(VehicleGpsPoint.objects.count(), 8)

    @override_settings(TRACK360_USERNAME="", TRACK360_PASSWORD="")
    def test_pull_live_fleet_command_raises_alerts(self):
        call_command("pull_live_fleet", "--force")
        types = set(AlertEvent.objects.values_list("alert_type", flat=True))
        self.assertIn(AlertType.LONG_HALT, types)
        self.assertIn(AlertType.KM_EXCEEDED, types)
        self.assertIn(AlertType.VEHICLE_STARTED, types)

    def test_alerts_list_detail_and_finance_blocked(self):
        self.authenticate(self.admin, "AdminPass123!")
        listing = self.client.get(f"{API_V1}/alerts/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(listing.data["counts"]["total"], 1)
        self.assertGreaterEqual(listing.data["counts"]["long_halt"], 1)
        self.assertGreaterEqual(listing.data["counts"]["km_exceeded"], 1)
        self.assertIn("vehicle_started", listing.data["counts"])
        long_halt = next(item for item in listing.data["alerts"] if item["type"] == AlertType.LONG_HALT)
        detail = self.client.get(f"{API_V1}/alerts/{long_halt['id']}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["type"], AlertType.LONG_HALT)
        self.assertIn("timeline", detail.data)
        self.assertIn("live_map", detail.data["links"])
        self.assertEqual(
            self.client.get(f"{API_V1}/alerts/00000000-0000-0000-0000-000000000000/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.client.credentials()
        self.authenticate(self.finance, "FinancePass123!")
        self.assertEqual(self.client.get(f"{API_V1}/alerts/").status_code, status.HTTP_403_FORBIDDEN)

    def test_history_and_reports_by_role(self):
        snapshot_live_fleet(force=True)
        self.authenticate(self.admin, "AdminPass123!")
        history = self.client.get(f"{API_V1}/history/")
        self.assertEqual(history.status_code, status.HTTP_200_OK)
        self.assertTrue(history.data["vehicles"])
        self.assertEqual(history.data["vehicle"]["id"], history.data["vehicles"][0]["id"])
        vehicle_id = history.data["vehicle"]["id"]
        today = timezone.localdate().isoformat()
        day = self.client.get(f"{API_V1}/history/{vehicle_id}/{today}/")
        self.assertEqual(day.status_code, status.HTTP_200_OK)
        self.assertEqual(day.data["date"], today)

        kinds = self.client.get(f"{API_V1}/reports/")
        self.assertEqual(
            set(kinds.data["kinds"]),
            {"daily", "constituency", "vehicle", "route", "alert", "documents"},
        )
        daily = self.client.get(f"{API_V1}/reports/daily/")
        self.assertEqual(daily.status_code, status.HTTP_200_OK)
        self.assertIn("total_km", daily.data["kpis"])
        csv_response = self.client.get(f"{API_V1}/reports/daily/", {"export": "csv"})
        self.assertEqual(csv_response.status_code, status.HTTP_200_OK)

        self.client.credentials()
        self.authenticate(self.finance, "FinancePass123!")
        self.assertEqual(self.client.get(f"{API_V1}/history/").status_code, status.HTTP_403_FORBIDDEN)
        finance_kinds = self.client.get(f"{API_V1}/reports/")
        self.assertEqual(
            set(finance_kinds.data["kinds"]),
            {"daily", "constituency", "vehicle", "documents"},
        )
        self.assertEqual(self.client.get(f"{API_V1}/reports/alert/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(f"{API_V1}/reports/route/").status_code, status.HTTP_403_FORBIDDEN)


class Track360MappingTests(SimpleTestCase):
    def test_daily_distance_meters_become_km(self):
        fields = map_device_to_telemetry(
            {
                "latitude": "28.631671666666666",
                "longitude": "77.03511111111112",
                "speed": "0.0",
                "ignition": "false",
                "status": "online",
                "valid": 1,
                "daily_distance": 114298.31,
                "lastUpdate": "2026-11-04T15:33:32.000000+0000",
            }
        )
        self.assertEqual(fields["today_km"], 114.3)
        self.assertTrue(fields["trip_started"])
        self.assertTrue(fields["gps_connected"])
        self.assertEqual(fields["speed_kmh"], 0.0)
        self.assertFalse(fields["ignition"])

    def test_parses_track360_offset_without_colon(self):
        parsed = parse_track360_datetime("2026-11-06T11:06:56.000000+0000")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.year, 2026)
        self.assertEqual(parsed.hour, 11)
