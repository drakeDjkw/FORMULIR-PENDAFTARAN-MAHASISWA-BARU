from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from rest_framework import serializers

from .models import Applicant, AdmissionPath, Faculty, Registration, RegistrationDocument, StudyProgram


class OwnedSerializer(serializers.ModelSerializer):
    """
    Base serializer:
    - on create, stores the current user as the owner;
    - related ids can only point to the current user's own records (superusers: any).
    """

    user = serializers.SlugRelatedField(slug_field="username", read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated or user.is_superuser:
            return
        for field in self.fields.values():
            queryset = getattr(field, "queryset", None)
            if queryset is not None and any(f.name == "user" for f in queryset.model._meta.fields):
                field.queryset = queryset.filter(user=user)

    def create(self, validated_data):
        if "request" in self.context:
            validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


# --- Short serializers for nested output ---


class FacultyBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ["id", "code", "name"]


class StudyProgramBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyProgram
        fields = ["id", "code", "name", "degree"]


class AdmissionPathBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionPath
        fields = ["id", "name"]


class ApplicantBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = ["id", "full_name", "email"]


# --- Main serializers ---


class FacultySerializer(OwnedSerializer):
    class Meta:
        model = Faculty
        fields = ["id", "code", "name", "description", "logo", "user"]


class StudyProgramSerializer(OwnedSerializer):
    # reading: nested faculty object; writing: its id
    faculty = FacultyBriefSerializer(read_only=True)
    faculty_id = serializers.PrimaryKeyRelatedField(
        source="faculty", queryset=Faculty.objects.all(), write_only=True
    )

    class Meta:
        model = StudyProgram
        fields = ["id", "code", "name", "degree", "quota", "faculty", "faculty_id", "user"]


class AdmissionPathSerializer(OwnedSerializer):
    class Meta:
        model = AdmissionPath
        fields = ["id", "name", "description", "fee", "opens_on", "closes_on", "user"]

    def validate(self, attrs):
        opens = attrs.get("opens_on", getattr(self.instance, "opens_on", None))
        closes = attrs.get("closes_on", getattr(self.instance, "closes_on", None))
        if opens and closes and closes < opens:
            raise serializers.ValidationError({"closes_on": _("The closing date must be after the opening date.")})
        return attrs


class ApplicantSerializer(OwnedSerializer):
    class Meta:
        model = Applicant
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "gender",
            "birth_place",
            "birth_date",
            "address",
            "school_origin",
            "photo",
            "user",
        ]


class RegistrationSerializer(OwnedSerializer):
    applicant = ApplicantBriefSerializer(read_only=True)
    applicant_id = serializers.PrimaryKeyRelatedField(
        source="applicant", queryset=Applicant.objects.all(), write_only=True
    )
    path = AdmissionPathBriefSerializer(read_only=True)
    path_id = serializers.PrimaryKeyRelatedField(
        source="path", queryset=AdmissionPath.objects.all(), write_only=True
    )
    first_choice = StudyProgramBriefSerializer(read_only=True)
    first_choice_id = serializers.PrimaryKeyRelatedField(
        source="first_choice", queryset=StudyProgram.objects.all(), write_only=True
    )
    second_choice = StudyProgramBriefSerializer(read_only=True)
    second_choice_id = serializers.PrimaryKeyRelatedField(
        source="second_choice",
        queryset=StudyProgram.objects.all(),
        write_only=True,
        allow_null=True,
        required=False,
    )
    documents_count = serializers.SerializerMethodField()

    class Meta:
        model = Registration
        fields = [
            "id",
            "number",
            "applicant",
            "applicant_id",
            "path",
            "path_id",
            "first_choice",
            "first_choice_id",
            "second_choice",
            "second_choice_id",
            "registered_on",
            "status",
            "test_score",
            "documents_count",
            "user",
        ]
        read_only_fields = ["number", "registered_on"]

    def get_documents_count(self, obj):
        # the list query annotates n_documents; a freshly created object counts directly
        count = getattr(obj, "n_documents", None)
        return count if count is not None else obj.documents.count()

    def validate(self, attrs):
        def current(name):
            return attrs.get(name, getattr(self.instance, name, None))

        applicant, path = current("applicant"), current("path")
        first, second = current("first_choice"), current("second_choice")

        if first and second and first == second:
            raise serializers.ValidationError(
                {"second_choice_id": _("The second choice must differ from the first choice.")}
            )

        # one registration per applicant per admission path
        duplicates = Registration.objects.filter(applicant=applicant, path=path)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if applicant and path and duplicates.exists():
            raise serializers.ValidationError(_("This applicant is already registered through this admission path."))
        return attrs


class RegistrationDocumentSerializer(OwnedSerializer):
    class Meta:
        model = RegistrationDocument
        fields = ["id", "registration", "doc_type", "image", "caption", "uploaded_at", "user"]
        read_only_fields = ["uploaded_at"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "username", "is_superuser"]
