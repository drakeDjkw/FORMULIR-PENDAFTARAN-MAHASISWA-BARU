from django.contrib import auth
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.db.models.functions import Lower
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response

from .exporters import DOCX_TYPE, XLSX_TYPE, build_docx, build_xlsx
from .models import Applicant, AdmissionPath, Faculty, Registration, RegistrationDocument, StudyProgram
from .serializers import (
    AdmissionPathSerializer,
    ApplicantSerializer,
    FacultySerializer,
    RegistrationDocumentSerializer,
    RegistrationSerializer,
    StudyProgramSerializer,
    UserSerializer,
)


def stat(label, value):
    """One statistics row: {"label": ..., "value": ...}. Labels follow the request language."""
    if isinstance(value, float):
        value = round(value, 2)
    return {"label": label, "value": value}


def owner_name(obj):
    return obj.user.username if obj.user else ""


class CrudViewSet(
    mixins.CreateModelMixin,    # POST      /api/<model>/       create
    mixins.RetrieveModelMixin,  # GET       /api/<model>/<id>/  one object
    mixins.UpdateModelMixin,    # PUT/PATCH /api/<model>/<id>/  update
    mixins.DestroyModelMixin,   # DELETE    /api/<model>/<id>/  delete
    mixins.ListModelMixin,      # GET       /api/<model>/       list
    viewsets.GenericViewSet,
):
    """Base ViewSet: CRUD, own-data-only access, column filters, statistics, export."""

    permission_classes = [IsAuthenticated]

    # column filters: query parameter -> lookup for .filter()
    filterset = {}

    # export: (column title function, value function); titles are translated per request
    export_fields = []

    def export_title(self):
        return self.queryset.model._meta.verbose_name_plural

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        params = self.request.query_params
        try:
            if user.is_superuser:
                # a superuser sees everything and can filter by owner
                owner = params.get("user")
                if owner:
                    qs = qs.filter(user_id=owner)
            else:
                # an ordinary user sees only their own records
                qs = qs.filter(user=user)

            for param, lookup in self.filterset.items():
                value = params.get(param)
                if value in (None, ""):
                    continue
                if lookup.endswith("__icontains"):
                    # case-insensitive search: compare LOWER(field) with value.lower()
                    field = lookup.removesuffix("__icontains")
                    alias = f"_filter_{param}"
                    qs = qs.annotate(**{alias: Lower(field)}).filter(**{f"{alias}__contains": value.lower()})
                else:
                    qs = qs.filter(**{lookup: value})
        except (ValueError, ValidationError):
            # a malformed filter value (letters instead of an id) gives an empty result
            return qs.none()
        return qs

    def get_stats(self, qs):
        return [stat(_("Total records"), qs.count())]

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """GET /api/<model>/stats/ — aggregate statistics, respecting the filters."""
        return Response(self.get_stats(self.get_queryset()))

    @action(detail=False, methods=["get"])
    def export(self, request):
        """GET /api/<model>/export/?type=xlsx|docx — download the table, respecting the filters."""
        headers = [str(title()) for title, _value in self.export_fields]
        rows = [[value(obj) for _title, value in self.export_fields] for obj in self.get_queryset()]
        title = str(self.export_title())

        if request.query_params.get("type") == "docx":
            content, content_type, ext = build_docx(title, headers, rows), DOCX_TYPE, "docx"
        else:
            content, content_type, ext = build_xlsx(title, headers, rows), XLSX_TYPE, "xlsx"

        response = HttpResponse(content, content_type=content_type)
        filename = f"{self.basename}-{get_language() or 'en'}.{ext}"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# Column titles are functions so that they are translated at request time, in the request's language
def col(text):
    return lambda: _(text)


class FacultyViewSet(CrudViewSet):
    queryset = Faculty.objects.select_related("user")
    serializer_class = FacultySerializer
    filterset = {
        "code": "code__icontains",
        "name": "name__icontains",
        "description": "description__icontains",
    }
    export_fields = [
        (col("ID"), lambda o: o.id),
        (col("Code"), lambda o: o.code),
        (col("Name"), lambda o: o.name),
        (col("Description"), lambda o: o.description),
        (col("Owner"), owner_name),
    ]

    def get_stats(self, qs):
        per_faculty = qs.annotate(n=Count("programs")).aggregate(avg=Avg("n"), max=Max("n"))
        quota = StudyProgram.objects.filter(faculty__in=qs.values("pk")).aggregate(total=Sum("quota"))
        with_logo = qs.exclude(logo="").exclude(logo__isnull=True).count()
        return [
            stat(_("Faculties"), qs.count()),
            stat(_("Avg study programs per faculty"), per_faculty["avg"]),
            stat(_("Most study programs in one faculty"), per_faculty["max"]),
            stat(_("Total quota"), quota["total"]),
            stat(_("Faculties with logo"), with_logo),
        ]


class StudyProgramViewSet(CrudViewSet):
    queryset = StudyProgram.objects.select_related("faculty", "user")
    serializer_class = StudyProgramSerializer
    filterset = {
        "code": "code__icontains",
        "name": "name__icontains",
        "degree": "degree",
        "quota": "quota",
        "faculty": "faculty_id",
    }
    export_fields = [
        (col("ID"), lambda o: o.id),
        (col("Code"), lambda o: o.code),
        (col("Name"), lambda o: o.name),
        (col("Degree"), lambda o: o.get_degree_display()),
        (col("Quota"), lambda o: o.quota),
        (col("Faculty"), lambda o: o.faculty.name),
        (col("Owner"), owner_name),
    ]

    def get_stats(self, qs):
        agg = qs.aggregate(
            total=Count("id"),
            quota=Sum("quota"),
            avg_quota=Avg("quota"),
            min_quota=Min("quota"),
            max_quota=Max("quota"),
            bachelor=Count("id", filter=Q(degree=StudyProgram.Degree.S1)),
        )
        applicants = qs.annotate(n=Count("first_choice_registrations")).aggregate(avg=Avg("n"), max=Max("n"))
        return [
            stat(_("Study programs"), agg["total"]),
            stat(_("Bachelor (S1) programs"), agg["bachelor"]),
            stat(_("Total quota"), agg["quota"]),
            stat(_("Avg quota"), agg["avg_quota"]),
            stat(_("Smallest quota"), agg["min_quota"]),
            stat(_("Largest quota"), agg["max_quota"]),
            stat(_("Avg first-choice applicants"), applicants["avg"]),
            stat(_("Most first-choice applicants"), applicants["max"]),
        ]


class AdmissionPathViewSet(CrudViewSet):
    queryset = AdmissionPath.objects.select_related("user")
    serializer_class = AdmissionPathSerializer
    filterset = {
        "name": "name__icontains",
        "description": "description__icontains",
        "fee": "fee",
    }
    export_fields = [
        (col("ID"), lambda o: o.id),
        (col("Name"), lambda o: o.name),
        (col("Registration fee (IDR)"), lambda o: o.fee),
        (col("Opens on"), lambda o: o.opens_on),
        (col("Closes on"), lambda o: o.closes_on),
        (col("Owner"), owner_name),
    ]

    def get_stats(self, qs):
        agg = qs.aggregate(total=Count("id"), avg_fee=Avg("fee"), min_fee=Min("fee"), max_fee=Max("fee"))
        registrations = qs.annotate(n=Count("registrations")).aggregate(avg=Avg("n"), max=Max("n"))
        return [
            stat(_("Admission paths"), agg["total"]),
            stat(_("Avg fee (IDR)"), agg["avg_fee"]),
            stat(_("Lowest fee (IDR)"), agg["min_fee"]),
            stat(_("Highest fee (IDR)"), agg["max_fee"]),
            stat(_("Avg registrations per path"), registrations["avg"]),
            stat(_("Most registrations on one path"), registrations["max"]),
        ]


class ApplicantViewSet(CrudViewSet):
    queryset = Applicant.objects.select_related("user")
    serializer_class = ApplicantSerializer
    filterset = {
        "full_name": "full_name__icontains",
        "email": "email__icontains",
        "phone": "phone__icontains",
        "gender": "gender",
        "birth_place": "birth_place__icontains",
        "birth_year": "birth_date__year",
        "school_origin": "school_origin__icontains",
    }
    export_fields = [
        (col("ID"), lambda o: o.id),
        (col("Full name"), lambda o: o.full_name),
        (col("E-mail"), lambda o: o.email),
        (col("Phone"), lambda o: o.phone),
        (col("Gender"), lambda o: o.get_gender_display()),
        (col("Place of birth"), lambda o: o.birth_place),
        (col("Date of birth"), lambda o: o.birth_date),
        (col("School of origin"), lambda o: o.school_origin),
        (col("Owner"), owner_name),
    ]

    def get_stats(self, qs):
        agg = qs.aggregate(
            total=Count("id"),
            male=Count("id", filter=Q(gender=Applicant.Gender.MALE)),
            female=Count("id", filter=Q(gender=Applicant.Gender.FEMALE)),
            oldest=Min("birth_date"),
            youngest=Max("birth_date"),
            schools=Count("school_origin", distinct=True),
        )
        registrations = qs.annotate(n=Count("registrations")).aggregate(avg=Avg("n"))
        with_photo = qs.exclude(photo="").exclude(photo__isnull=True).count()
        return [
            stat(_("Applicants"), agg["total"]),
            stat(_("Male"), agg["male"]),
            stat(_("Female"), agg["female"]),
            stat(_("Earliest date of birth"), agg["oldest"]),
            stat(_("Latest date of birth"), agg["youngest"]),
            stat(_("Different schools of origin"), agg["schools"]),
            stat(_("Avg registrations per applicant"), registrations["avg"]),
            stat(_("Applicants with photo"), with_photo),
        ]


class RegistrationViewSet(CrudViewSet):
    queryset = Registration.objects.select_related("applicant", "path", "first_choice", "second_choice", "user")
    serializer_class = RegistrationSerializer
    filterset = {
        "number": "number__icontains",
        "applicant": "applicant__full_name__icontains",
        "path": "path_id",
        "first_choice": "first_choice_id",
        "status": "status",
        "test_score": "test_score",
        "registered_on": "registered_on",
    }
    export_fields = [
        (col("ID"), lambda o: o.id),
        (col("Registration number"), lambda o: o.number),
        (col("Applicant"), lambda o: o.applicant.full_name),
        (col("Admission path"), lambda o: o.path.name),
        (col("First choice"), lambda o: str(o.first_choice)),
        (col("Second choice"), lambda o: str(o.second_choice) if o.second_choice else ""),
        (col("Status"), lambda o: o.get_status_display()),
        (col("Test score"), lambda o: o.test_score),
        (col("Registered on"), lambda o: o.registered_on),
        (col("Owner"), owner_name),
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action != "stats":
            # number of attached documents for the table (not for stats: the join would skew averages)
            qs = qs.annotate(n_documents=Count("documents"))
        return qs

    def get_stats(self, qs):
        agg = qs.aggregate(
            total=Count("id"),
            submitted=Count("id", filter=Q(status=Registration.Status.SUBMITTED)),
            verified=Count("id", filter=Q(status=Registration.Status.VERIFIED)),
            accepted=Count("id", filter=Q(status=Registration.Status.ACCEPTED)),
            rejected=Count("id", filter=Q(status=Registration.Status.REJECTED)),
            avg_score=Avg("test_score"),
            max_score=Max("test_score"),
            applicants=Count("applicant", distinct=True),
        )
        rate = round(100 * agg["accepted"] / agg["total"], 1) if agg["total"] else None
        return [
            stat(_("Registrations"), agg["total"]),
            stat(_("Submitted"), agg["submitted"]),
            stat(_("Verified"), agg["verified"]),
            stat(_("Accepted"), agg["accepted"]),
            stat(_("Rejected"), agg["rejected"]),
            stat(_("Acceptance rate, %"), rate),
            stat(_("Avg test score"), agg["avg_score"]),
            stat(_("Highest test score"), agg["max_score"]),
            stat(_("Distinct applicants"), agg["applicants"]),
        ]


class RegistrationDocumentViewSet(CrudViewSet):
    queryset = RegistrationDocument.objects.select_related("registration", "user")
    serializer_class = RegistrationDocumentSerializer
    filterset = {"registration": "registration_id", "doc_type": "doc_type"}
    export_fields = [
        (col("ID"), lambda o: o.id),
        (col("Registration"), lambda o: o.registration.number),
        (col("Document type"), lambda o: o.get_doc_type_display()),
        (col("Caption"), lambda o: o.caption),
        (col("Uploaded at"), lambda o: o.uploaded_at.strftime("%Y-%m-%d %H:%M")),
        (col("Owner"), owner_name),
    ]

    def get_stats(self, qs):
        agg = qs.aggregate(total=Count("id"), registrations=Count("registration", distinct=True))
        return [
            stat(_("Documents"), agg["total"]),
            stat(_("Registrations with documents"), agg["registrations"]),
        ]


# --- Users and login ---


class IsSuperuser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


def user_info(user):
    if not user.is_authenticated:
        return {"is_authenticated": False}
    return {
        "is_authenticated": True,
        "id": user.id,
        "username": user.username,
        "is_superuser": user.is_superuser,
        "is_staff": user.is_staff,
    }


class UserViewSet(viewsets.GenericViewSet):
    """
    GET  /api/users/         list of users (superuser only)
    GET  /api/users/info/    who is logged in (also sets the csrftoken cookie)
    POST /api/users/login/   log in with username and password
    POST /api/users/logout/  log out
    """

    queryset = get_user_model().objects.order_by("username")
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == "list":
            return [IsSuperuser()]
        return [AllowAny()]

    def list(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    @action(detail=False, methods=["get"])
    def info(self, request):
        get_token(request._request)  # makes sure the browser receives the csrftoken cookie
        return Response(user_info(request.user))

    @action(detail=False, methods=["post"])
    def login(self, request):
        user = auth.authenticate(
            request._request,
            username=request.data.get("username"),
            password=request.data.get("password"),
        )
        if user is None:
            return Response(
                {"detail": _("Invalid username or password.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        auth.login(request._request, user)
        return Response(user_info(user))

    @action(detail=False, methods=["post"])
    def logout(self, request):
        auth.logout(request._request)
        return Response(user_info(request._request.user))
