import csv
import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import actor_label, client_ip
from accounts.constants import Level, Module
from accounts.permissions import HasModuleAccess
from fleet.alerts import build_alerts
from fleet.constants import (
    CONSTITUENCY_STATUSES,
    DOCUMENT_TYPES,
    DOCUMENT_VALIDITIES,
    FILTER_STATUSES,
    DocumentValidity,
)
from fleet.models import Constituency, Vehicle, VehicleDocument
from fleet.scoping import (
    can_access_constituency,
    can_access_vehicle,
    scoped_constituencies,
    scoped_vehicles,
)
from fleet.serializers import (
    ConstituencyWriteSerializer,
    DocumentReviewSerializer,
    DocumentUpsertSerializer,
    VehicleCreateSerializer,
    VehicleUpdateSerializer,
)
from fleet.services import (
    allowed_document_types,
    compose_documents,
    compose_vehicle_detail,
    ensure_vehicle_documents,
    filter_constituencies,
    filter_vehicles,
    rollup_constituency,
    serialize_document,
    vehicle_rows_for,
)

logger = logging.getLogger("fleet")


def _constituency_queryset():
    return Constituency.objects.prefetch_related(
        "vehicles__driver",
        "vehicles__telemetry",
        "vehicles__documents",
    )


def _vehicle_queryset():
    return Vehicle.objects.select_related("constituency", "driver", "telemetry").prefetch_related(
        "documents__reviewed_by"
    )


def _require_constituency(user, pk):
    constituency = get_object_or_404(_constituency_queryset(), pk=pk)
    if not can_access_constituency(user, constituency.id):
        return None
    return constituency


def _require_vehicle(user, pk):
    vehicle = get_object_or_404(_vehicle_queryset(), pk=pk)
    if not can_access_vehicle(user, vehicle):
        return None
    return vehicle


class ConstituencyListCreateView(APIView):
    def get_permissions(self):
        min_level = Level.EDIT if self.request.method == "POST" else Level.VIEW
        return [HasModuleAccess(Module.CONSTITUENCIES, min_level)()]

    def get(self, request, **kwargs):
        query = request.query_params.get("q", "")
        status_filter = request.query_params.get("status", "all")
        ordering = request.query_params.get("ordering", "code")
        if status_filter not in ("all", *CONSTITUENCY_STATUSES):
            return Response({"detail": "Unknown status filter."}, status=status.HTTP_400_BAD_REQUEST)
        if ordering.lstrip("-") not in ("code", "name"):
            return Response({"detail": "Unknown ordering."}, status=status.HTTP_400_BAD_REQUEST)

        rows = [
            {
                key: value
                for key, value in rollup_constituency(
                    constituency,
                    constituency.vehicles.all(),
                    user=request.user,
                    request=request,
                ).items()
                if key != "vehicles"
            }
            for constituency in scoped_constituencies(request.user).prefetch_related(
                "vehicles__driver",
                "vehicles__telemetry",
                "vehicles__documents",
            )
        ]
        return Response(filter_constituencies(rows, query, status_filter, ordering))

    def post(self, request, **kwargs):
        serializer = ConstituencyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        constituency = serializer.save()
        logger.info(
            "constituency_created actor=%s constituency_id=%s code=%s ip=%s",
            actor_label(request.user),
            constituency.pk,
            constituency.code,
            client_ip(request),
        )
        payload = rollup_constituency(constituency, [], user=request.user, request=request)
        payload.pop("vehicles", None)
        return Response(payload, status=status.HTTP_201_CREATED)


class ConstituencyDetailView(APIView):
    def get_permissions(self):
        min_level = Level.EDIT if self.request.method == "PATCH" else Level.VIEW
        return [HasModuleAccess(Module.CONSTITUENCIES, min_level)()]

    def get(self, request, pk, **kwargs):
        constituency = _require_constituency(request.user, pk)
        if constituency is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = rollup_constituency(
            constituency,
            constituency.vehicles.all(),
            user=request.user,
            request=request,
        )
        payload["alerts"] = []
        for vehicle in constituency.vehicles.all():
            payload["alerts"].extend(build_alerts(vehicle))
        return Response(payload)

    def patch(self, request, pk, **kwargs):
        constituency = _require_constituency(request.user, pk)
        if constituency is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ConstituencyWriteSerializer(constituency, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        constituency = serializer.save()
        logger.info(
            "constituency_updated actor=%s constituency_id=%s ip=%s",
            actor_label(request.user),
            constituency.pk,
            client_ip(request),
        )
        payload = rollup_constituency(
            constituency,
            constituency.vehicles.all(),
            user=request.user,
            request=request,
        )
        payload.pop("vehicles", None)
        return Response(payload)


class ConstituencyVehiclesView(APIView):
    permission_classes = [HasModuleAccess(Module.VEHICLES, Level.VIEW)]

    def get(self, request, pk, **kwargs):
        constituency = _require_constituency(request.user, pk)
        if constituency is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            vehicle_rows_for(constituency.vehicles.all(), user=request.user, request=request)
        )


class ConstituencyMapView(APIView):
    permission_classes = [HasModuleAccess(Module.CONSTITUENCIES, Level.VIEW)]

    def get(self, request, pk, **kwargs):
        constituency = _require_constituency(request.user, pk)
        if constituency is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        rows = vehicle_rows_for(constituency.vehicles.all(), user=request.user, request=request)
        return Response(
            {
                "id": str(constituency.id),
                "code": constituency.code,
                "name": constituency.name,
                "lat": constituency.lat,
                "lng": constituency.lng,
                "vehicles": [
                    {
                        "id": row["id"],
                        "code": row["code"],
                        "registration": row["registration"],
                        "status": row["status"],
                        "attention": row["attention"],
                        "lat": row["telemetry"]["lat"],
                        "lng": row["telemetry"]["lng"],
                        "address": row["telemetry"]["address"],
                    }
                    for row in rows
                ],
            }
        )


class ConstituencyAlertsView(APIView):
    permission_classes = [HasModuleAccess(Module.ALERTS, Level.VIEW)]

    def get(self, request, pk, **kwargs):
        constituency = _require_constituency(request.user, pk)
        if constituency is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        alerts = []
        for vehicle in constituency.vehicles.all():
            alerts.extend(build_alerts(vehicle))
        return Response(alerts)


class ConstituencyReportView(APIView):
    permission_classes = [HasModuleAccess(Module.REPORTS, Level.VIEW)]

    def get(self, request, pk, **kwargs):
        constituency = _require_constituency(request.user, pk)
        if constituency is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        rollup = rollup_constituency(
            constituency,
            constituency.vehicles.all(),
            user=request.user,
            request=request,
        )
        alerts = []
        for vehicle in constituency.vehicles.all():
            alerts.extend(build_alerts(vehicle))
        return Response(
            {
                "id": rollup["id"],
                "code": rollup["code"],
                "name": rollup["name"],
                "status": rollup["status"],
                "vehicles": rollup["total"],
                "active": rollup["active"],
                "inactive": rollup["inactive"],
                "attention": rollup["attention"],
                "exceeded": rollup["exceeded"],
                "today_km": rollup["today_km"],
                "alerts": len(alerts),
            }
        )


class VehicleListCreateView(APIView):
    def get_permissions(self):
        min_level = Level.EDIT if self.request.method == "POST" else Level.VIEW
        return [HasModuleAccess(Module.VEHICLES, min_level)()]

    def get(self, request, **kwargs):
        query = request.query_params.get("q", "")
        constituency_id = request.query_params.get("constituency", "all")
        status_filter = request.query_params.get("status", "all")
        if status_filter not in ("all", *FILTER_STATUSES):
            return Response({"detail": "Unknown status filter."}, status=status.HTTP_400_BAD_REQUEST)
        rows = vehicle_rows_for(
            scoped_vehicles(request.user),
            user=request.user,
            request=request,
        )
        return Response(filter_vehicles(rows, query, constituency_id, status_filter))

    def post(self, request, **kwargs):
        serializer = VehicleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vehicle = serializer.save()
        vehicle = _vehicle_queryset().get(pk=vehicle.pk)
        logger.info(
            "vehicle_created actor=%s vehicle_id=%s code=%s ip=%s",
            actor_label(request.user),
            vehicle.pk,
            vehicle.code,
            client_ip(request),
        )
        return Response(
            compose_vehicle_detail(vehicle, request.user, request=request),
            status=status.HTTP_201_CREATED,
        )


class VehicleDetailView(APIView):
    def get_permissions(self):
        min_level = Level.EDIT if self.request.method == "PATCH" else Level.VIEW
        return [HasModuleAccess(Module.VEHICLES, min_level)()]

    def get(self, request, pk, **kwargs):
        vehicle = _require_vehicle(request.user, pk)
        if vehicle is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(compose_vehicle_detail(vehicle, request.user, request=request))

    def patch(self, request, pk, **kwargs):
        vehicle = _require_vehicle(request.user, pk)
        if vehicle is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = VehicleUpdateSerializer(vehicle, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        vehicle = _vehicle_queryset().get(pk=vehicle.pk)
        logger.info(
            "vehicle_updated actor=%s vehicle_id=%s ip=%s",
            actor_label(request.user),
            vehicle.pk,
            client_ip(request),
        )
        return Response(compose_vehicle_detail(vehicle, request.user, request=request))


class VehicleAlertsView(APIView):
    permission_classes = [HasModuleAccess(Module.ALERTS, Level.VIEW)]

    def get(self, request, pk, **kwargs):
        vehicle = _require_vehicle(request.user, pk)
        if vehicle is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(build_alerts(vehicle))


class VehicleDocumentListView(APIView):
    permission_classes = [HasModuleAccess(Module.COMPLIANCE_DOCUMENTS, Level.VIEW)]

    def get(self, request, pk, **kwargs):
        vehicle = _require_vehicle(request.user, pk)
        if vehicle is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        ensure_vehicle_documents(vehicle)
        vehicle = _vehicle_queryset().get(pk=vehicle.pk)
        return Response(compose_documents(vehicle, user=request.user, request=request))


class VehicleDocumentUpsertView(APIView):
    permission_classes = [HasModuleAccess(Module.COMPLIANCE_DOCUMENTS, Level.EDIT)]

    def put(self, request, pk, doc_type, **kwargs):
        if doc_type not in DOCUMENT_TYPES:
            return Response({"detail": "Unknown document type."}, status=status.HTTP_400_BAD_REQUEST)
        vehicle = _require_vehicle(request.user, pk)
        if vehicle is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        document, _ = VehicleDocument.objects.get_or_create(vehicle=vehicle, doc_type=doc_type)
        serializer = DocumentUpsertSerializer(document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        logger.info(
            "document_upserted actor=%s vehicle_id=%s type=%s ip=%s",
            actor_label(request.user),
            vehicle.pk,
            doc_type,
            client_ip(request),
        )
        return Response(serialize_document(document, doc_type, request=request))


class VehicleDocumentReviewView(APIView):
    permission_classes = [HasModuleAccess(Module.DOCUMENT_APPROVALS, Level.MANAGE)]

    def post(self, request, pk, doc_type, **kwargs):
        if doc_type not in DOCUMENT_TYPES:
            return Response({"detail": "Unknown document type."}, status=status.HTTP_400_BAD_REQUEST)
        vehicle = _require_vehicle(request.user, pk)
        if vehicle is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        document = get_object_or_404(VehicleDocument, vehicle=vehicle, doc_type=doc_type)
        serializer = DocumentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document.approval = serializer.validated_data["decision"]
        document.review_comment = serializer.validated_data.get("comment", "")
        document.reviewed_at = timezone.now()
        document.reviewed_by = request.user
        document.save()
        logger.info(
            "document_reviewed actor=%s vehicle_id=%s type=%s decision=%s ip=%s",
            actor_label(request.user),
            vehicle.pk,
            doc_type,
            document.approval,
            client_ip(request),
        )
        return Response(serialize_document(document, doc_type, request=request))


def _compliance_rows(user, request):
    allowed = allowed_document_types(user)
    rows = []
    for vehicle in scoped_vehicles(user):
        ensure_vehicle_documents(vehicle)
        by_type = {item.doc_type: item for item in vehicle.documents.all()}
        for doc_type in DOCUMENT_TYPES:
            if doc_type not in allowed:
                continue
            document = by_type.get(doc_type)
            payload = serialize_document(document, doc_type, request=request)
            rows.append(
                {
                    "vehicle_id": str(vehicle.id),
                    "vehicle_code": vehicle.code,
                    "registration": vehicle.registration,
                    "constituency_id": str(vehicle.constituency_id),
                    "constituency": vehicle.constituency.name,
                    "document": payload,
                    "validity": payload["validity"],
                }
            )
    return rows


def _filter_compliance_rows(rows, params):
    query = (params.get("q") or "").strip().lower()
    doc_type = params.get("type", "all")
    validity = params.get("validity", "all")
    approval = params.get("approval", "all")
    constituency = params.get("constituency", "all")
    if doc_type not in ("all", *DOCUMENT_TYPES):
        return None, "Unknown document type."
    if validity not in ("all", *DOCUMENT_VALIDITIES):
        return None, "Unknown validity filter."
    filtered = []
    for row in rows:
        document = row["document"]
        if doc_type != "all" and document["type"] != doc_type:
            continue
        if validity != "all" and row["validity"] != validity:
            continue
        if approval == "none" and document["approval"] is not None:
            continue
        if approval not in ("all", "none") and document["approval"] != approval:
            continue
        if constituency not in ("", "all") and str(row["constituency_id"]) != str(constituency):
            continue
        haystack = f"{row['vehicle_code']} {row['registration']} {row['constituency']}".lower()
        if query and query not in haystack:
            continue
        filtered.append(row)
    return filtered, None


class ComplianceDocumentListView(APIView):
    permission_classes = [HasModuleAccess(Module.COMPLIANCE_DOCUMENTS, Level.VIEW)]

    def get(self, request, **kwargs):
        rows, error = _filter_compliance_rows(_compliance_rows(request.user, request), request.query_params)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(rows)


class ComplianceSummaryView(APIView):
    permission_classes = [HasModuleAccess(Module.COMPLIANCE_DOCUMENTS, Level.VIEW)]

    def get(self, request, **kwargs):
        rows = _compliance_rows(request.user, request)
        return Response(
            {
                "pending": sum(1 for row in rows if row["document"]["approval"] == "pending"),
                "rejected": sum(1 for row in rows if row["document"]["approval"] == "rejected"),
                "expired": sum(1 for row in rows if row["validity"] == DocumentValidity.EXPIRED),
                "expiring30": sum(1 for row in rows if row["validity"] == DocumentValidity.EXPIRING_30),
                "expiring60": sum(1 for row in rows if row["validity"] == DocumentValidity.EXPIRING_60),
                "missingUpload": sum(1 for row in rows if not row["document"]["file"]),
            }
        )


class DocumentReportView(APIView):
    def get_permissions(self):
        if self.request.query_params.get("export") == "csv":
            return [HasModuleAccess(Module.EXPORT_DATA, Level.VIEW)()]
        return [HasModuleAccess(Module.REPORTS, Level.VIEW)()]

    def get(self, request, **kwargs):
        rows, error = _filter_compliance_rows(_compliance_rows(request.user, request), request.query_params)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        report_rows = [
            {
                "vehicle_id": row["vehicle_id"],
                "vehicle_code": row["vehicle_code"],
                "registration": row["registration"],
                "constituency": row["constituency"],
                "type": row["document"]["type"],
                "label": row["document"]["label"],
                "start_date": row["document"]["start_date"],
                "end_date": row["document"]["end_date"],
                "validity": row["validity"],
                "approval": row["document"]["approval"],
            }
            for row in rows
        ]
        counts = {
            "total": len(report_rows),
            "valid": sum(1 for row in report_rows if row["validity"] == DocumentValidity.VALID),
            "expiring_30": sum(1 for row in report_rows if row["validity"] == DocumentValidity.EXPIRING_30),
            "expiring_60": sum(1 for row in report_rows if row["validity"] == DocumentValidity.EXPIRING_60),
            "expired": sum(1 for row in report_rows if row["validity"] == DocumentValidity.EXPIRED),
        }
        if request.query_params.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="document-expiry.csv"'
            writer = csv.DictWriter(
                response,
                fieldnames=[
                    "vehicle_id",
                    "vehicle_code",
                    "registration",
                    "constituency",
                    "type",
                    "label",
                    "start_date",
                    "end_date",
                    "validity",
                    "approval",
                ],
            )
            writer.writeheader()
            writer.writerows(report_rows)
            return response
        return Response({"rows": report_rows, "counts": counts})
