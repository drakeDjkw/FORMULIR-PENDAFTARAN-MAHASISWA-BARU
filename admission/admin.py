from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Applicant, AdmissionPath, Faculty, Registration, RegistrationDocument, StudyProgram


def image_preview(field_name, title):
    """A thumbnail column for an image field in the admin list."""

    @admin.display(description=title)
    def preview(modeladmin, obj):
        image = getattr(obj, field_name)
        if not image:
            return "—"
        return format_html('<img src="{}" style="height:40px;border-radius:4px">', image.url)

    return preview


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    logo_preview = image_preview("logo", _("Logo"))
    list_display = ["id", "logo_preview", "code", "name", "user"]
    list_filter = ["user"]
    search_fields = ["code", "name"]


@admin.register(StudyProgram)
class StudyProgramAdmin(admin.ModelAdmin):
    # faculty__code: a field of the related model through a double underscore
    list_display = ["id", "code", "name", "degree", "quota", "faculty", "faculty__code", "user"]
    list_filter = ["degree", "faculty", "user"]
    search_fields = ["code", "name"]


@admin.register(AdmissionPath)
class AdmissionPathAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "fee", "opens_on", "closes_on", "user"]
    list_filter = ["user"]
    search_fields = ["name"]


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    photo_preview = image_preview("photo", _("Photo"))
    list_display = ["id", "photo_preview", "full_name", "email", "gender", "birth_date", "school_origin", "user"]
    list_filter = ["gender", "user"]
    search_fields = ["full_name", "email", "school_origin"]


class RegistrationDocumentInline(admin.TabularInline):
    model = RegistrationDocument
    extra = 0
    fields = ["doc_type", "image", "caption", "user"]


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ["number", "applicant", "path", "first_choice", "second_choice", "status", "test_score", "registered_on", "user"]
    list_filter = ["status", "path", "first_choice__faculty", "user"]
    search_fields = ["number", "applicant__full_name", "first_choice__name"]
    list_select_related = ["applicant", "path", "first_choice", "second_choice", "user"]
    inlines = [RegistrationDocumentInline]


@admin.register(RegistrationDocument)
class RegistrationDocumentAdmin(admin.ModelAdmin):
    scan_preview = image_preview("image", _("Scan"))
    list_display = ["id", "scan_preview", "registration", "doc_type", "caption", "uploaded_at", "user"]
    list_filter = ["doc_type", "user"]
    search_fields = ["caption", "registration__number"]
