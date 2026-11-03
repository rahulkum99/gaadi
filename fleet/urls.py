from django.urls import path

from fleet.views import (
    ComplianceDocumentListView,
    ComplianceSummaryView,
    ConstituencyAlertsView,
    ConstituencyDetailView,
    ConstituencyListCreateView,
    ConstituencyMapView,
    ConstituencyReportView,
    ConstituencyVehiclesView,
    DocumentReportView,
    VehicleAlertsView,
    VehicleDetailView,
    VehicleDocumentListView,
    VehicleDocumentReviewView,
    VehicleDocumentUpsertView,
    VehicleListCreateView,
)

urlpatterns = [
    path("constituencies/", ConstituencyListCreateView.as_view(), name="constituency-list"),
    path("constituencies/<uuid:pk>/", ConstituencyDetailView.as_view(), name="constituency-detail"),
    path(
        "constituencies/<uuid:pk>/vehicles/",
        ConstituencyVehiclesView.as_view(),
        name="constituency-vehicles",
    ),
    path("constituencies/<uuid:pk>/map/", ConstituencyMapView.as_view(), name="constituency-map"),
    path(
        "constituencies/<uuid:pk>/alerts/",
        ConstituencyAlertsView.as_view(),
        name="constituency-alerts",
    ),
    path(
        "constituencies/<uuid:pk>/report/",
        ConstituencyReportView.as_view(),
        name="constituency-report",
    ),
    path("vehicles/", VehicleListCreateView.as_view(), name="vehicle-list"),
    path("vehicles/<uuid:pk>/", VehicleDetailView.as_view(), name="vehicle-detail"),
    path("vehicles/<uuid:pk>/alerts/", VehicleAlertsView.as_view(), name="vehicle-alerts"),
    path(
        "vehicles/<uuid:pk>/documents/",
        VehicleDocumentListView.as_view(),
        name="vehicle-documents",
    ),
    path(
        "vehicles/<uuid:pk>/documents/<str:doc_type>/",
        VehicleDocumentUpsertView.as_view(),
        name="vehicle-document-upsert",
    ),
    path(
        "vehicles/<uuid:pk>/documents/<str:doc_type>/review/",
        VehicleDocumentReviewView.as_view(),
        name="vehicle-document-review",
    ),
    path("compliance/documents/", ComplianceDocumentListView.as_view(), name="compliance-documents"),
    path("compliance/summary/", ComplianceSummaryView.as_view(), name="compliance-summary"),
    path("reports/documents/", DocumentReportView.as_view(), name="document-report"),
]
