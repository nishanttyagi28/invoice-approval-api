from django.urls import path

from apps.approvals import views

urlpatterns = [
    path("invoices/<int:pk>/submit/", views.SubmitView.as_view(), name="invoice-submit"),
    path("invoices/<int:pk>/approve/", views.ApproveView.as_view(), name="invoice-approve"),
    path("invoices/<int:pk>/reject/", views.RejectView.as_view(), name="invoice-reject"),
    path("invoices/<int:pk>/mark-paid/", views.MarkPaidView.as_view(), name="invoice-mark-paid"),
    path("invoices/<int:pk>/audit/", views.InvoiceAuditView.as_view(), name="invoice-audit"),
]
