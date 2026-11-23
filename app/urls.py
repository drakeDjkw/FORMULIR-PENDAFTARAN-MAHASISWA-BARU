from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from admission.api import (
    AdmissionPathViewSet,
    ApplicantViewSet,
    FacultyViewSet,
    RegistrationDocumentViewSet,
    RegistrationViewSet,
    StudyProgramViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register("faculties", FacultyViewSet, basename="faculties")
router.register("programs", StudyProgramViewSet, basename="programs")
router.register("paths", AdmissionPathViewSet, basename="paths")
router.register("applicants", ApplicantViewSet, basename="applicants")
router.register("registrations", RegistrationViewSet, basename="registrations")
router.register("documents", RegistrationDocumentViewSet, basename="documents")
router.register("users", UserViewSet, basename="users")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),  # login for DRF's browsable API
    path("i18n/", include("django.conf.urls.i18n")),  # POST /i18n/setlang/ switches the language
]

# serve uploaded images during development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
