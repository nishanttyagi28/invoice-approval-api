import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from tests.factories import OrganizationFactory, UserFactory


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def org():
    return OrganizationFactory()


@pytest.fixture
def submitter(org):
    return UserFactory(organization=org, role=User.Role.SUBMITTER)


@pytest.fixture
def approver(org):
    return UserFactory(organization=org, role=User.Role.APPROVER)


@pytest.fixture
def finance_admin(org):
    return UserFactory(organization=org, role=User.Role.FINANCE_ADMIN)


@pytest.fixture
def client_for():
    def make(user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    return make
