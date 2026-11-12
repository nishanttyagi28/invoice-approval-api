from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from tests.factories import InvoiceFactory, OrganizationFactory, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(submitter):
    InvoiceFactory(created_by=submitter, invoice_date=date(2026, 9, 5), total=Decimal("1180.00"))
    InvoiceFactory(created_by=submitter, invoice_date=date(2026, 9, 20), total=Decimal("2000.00"))
    InvoiceFactory(
        created_by=submitter, invoice_date=date(2026, 10, 2), total=Decimal("500.00"), status="paid"
    )


def test_summary_groups_counts_and_totals_by_status_and_month(client_for, approver, seeded):
    response = client_for(approver).get("/api/reports/summary/")

    assert response.status_code == 200
    body = response.json()
    assert body["by_status"] == [
        {"status": "draft", "count": 2, "total": "3180.00"},
        {"status": "paid", "count": 1, "total": "500.00"},
    ]
    assert body["by_month"] == [
        {"month": "2026-09", "count": 2, "total": "3180.00"},
        {"month": "2026-10", "count": 1, "total": "500.00"},
    ]


def test_summary_only_counts_own_organization(client_for, approver, seeded):
    InvoiceFactory(created_by=UserFactory(organization=OrganizationFactory()))

    body = client_for(approver).get("/api/reports/summary/").json()

    assert sum(row["count"] for row in body["by_status"]) == 3


def test_summary_is_not_open_to_submitters(client_for, submitter):
    assert client_for(submitter).get("/api/reports/summary/").status_code == 403


def test_summary_needs_login():
    assert APIClient().get("/api/reports/summary/").status_code == 401


def test_summary_uses_a_fixed_number_of_queries(
    client_for, approver, seeded, django_assert_num_queries
):
    with django_assert_num_queries(2):
        client_for(approver).get("/api/reports/summary/")
