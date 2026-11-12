from django.urls import path

from apps.reports.views import SummaryView

urlpatterns = [path("reports/summary/", SummaryView.as_view(), name="report-summary")]
