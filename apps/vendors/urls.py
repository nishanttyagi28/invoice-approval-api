from rest_framework.routers import DefaultRouter

from apps.vendors.views import VendorViewSet

router = DefaultRouter()
router.register("vendors", VendorViewSet, basename="vendor")

urlpatterns = router.urls
