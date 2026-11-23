import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def owner_field():
    """The user who created the record (every model has its own ForeignKey to User)."""
    return models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("User"),
    )


def make_registration_number():
    """Registration number such as PMB-2026-3F9A1C2B."""
    return f"PMB-{timezone.now():%Y}-{uuid.uuid4().hex[:8].upper()}"


class Faculty(models.Model):
    """Fakultas: a faculty that runs study programs."""

    code = models.CharField(_("Code"), max_length=10, unique=True)
    name = models.CharField(_("Name"), max_length=150, unique=True)
    description = models.TextField(_("Description"), blank=True)
    logo = models.ImageField(_("Logo"), upload_to="faculties", null=True, blank=True)
    user = owner_field()

    class Meta:
        verbose_name = _("Faculty")
        verbose_name_plural = _("Faculties")
        ordering = ["name"]

    def __str__(self):
        return self.name


class StudyProgram(models.Model):
    """Program studi: a study program inside a faculty."""

    class Degree(models.TextChoices):
        D3 = "D3", _("Diploma (D3)")
        S1 = "S1", _("Bachelor (S1)")
        S2 = "S2", _("Master (S2)")

    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.PROTECT,
        related_name="programs",
        verbose_name=_("Faculty"),
    )
    code = models.CharField(_("Code"), max_length=20, unique=True)
    name = models.CharField(_("Name"), max_length=200)
    degree = models.CharField(_("Degree"), max_length=2, choices=Degree.choices, default=Degree.S1)
    quota = models.PositiveIntegerField(_("Quota"), default=100)
    user = owner_field()

    class Meta:
        verbose_name = _("Study program")
        verbose_name_plural = _("Study programs")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class AdmissionPath(models.Model):
    """Jalur pendaftaran: an admission path such as SNBP, SNBT or Mandiri."""

    name = models.CharField(_("Name"), max_length=100, unique=True)
    description = models.TextField(_("Description"), blank=True)
    fee = models.PositiveIntegerField(_("Registration fee (IDR)"), default=0)
    opens_on = models.DateField(_("Opens on"), null=True, blank=True)
    closes_on = models.DateField(_("Closes on"), null=True, blank=True)
    user = owner_field()

    class Meta:
        verbose_name = _("Admission path")
        verbose_name_plural = _("Admission paths")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Applicant(models.Model):
    """Calon mahasiswa: a person applying to the university."""

    class Gender(models.TextChoices):
        MALE = "M", _("Male")
        FEMALE = "F", _("Female")

    full_name = models.CharField(_("Full name"), max_length=150)
    email = models.EmailField(_("E-mail"), unique=True)
    phone = models.CharField(_("Phone"), max_length=30, blank=True)
    gender = models.CharField(_("Gender"), max_length=1, choices=Gender.choices)
    birth_place = models.CharField(_("Place of birth"), max_length=100, blank=True)
    birth_date = models.DateField(_("Date of birth"), null=True, blank=True)
    address = models.TextField(_("Address"), blank=True)
    school_origin = models.CharField(_("School of origin"), max_length=150, blank=True)
    photo = models.ImageField(_("Photo"), upload_to="applicants", null=True, blank=True)
    user = owner_field()

    class Meta:
        verbose_name = _("Applicant")
        verbose_name_plural = _("Applicants")
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Registration(models.Model):
    """Pendaftaran: one applicant applying through one admission path."""

    class Status(models.TextChoices):
        SUBMITTED = "submitted", _("Submitted")
        VERIFIED = "verified", _("Verified")
        ACCEPTED = "accepted", _("Accepted")
        REJECTED = "rejected", _("Rejected")

    number = models.CharField(
        _("Registration number"), max_length=30, unique=True, default=make_registration_number, editable=False
    )
    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        related_name="registrations",
        verbose_name=_("Applicant"),
    )
    path = models.ForeignKey(
        AdmissionPath,
        on_delete=models.PROTECT,
        related_name="registrations",
        verbose_name=_("Admission path"),
    )
    first_choice = models.ForeignKey(
        StudyProgram,
        on_delete=models.PROTECT,
        related_name="first_choice_registrations",
        verbose_name=_("First choice"),
    )
    second_choice = models.ForeignKey(
        StudyProgram,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="second_choice_registrations",
        verbose_name=_("Second choice"),
    )
    registered_on = models.DateField(_("Registered on"), auto_now_add=True)
    status = models.CharField(_("Status"), max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    test_score = models.PositiveSmallIntegerField(
        _("Test score"),
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    user = owner_field()

    class Meta:
        verbose_name = _("Registration")
        verbose_name_plural = _("Registrations")
        ordering = ["-registered_on", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["applicant", "path"], name="unique_applicant_path")
        ]

    def __str__(self):
        return self.number


class RegistrationDocument(models.Model):
    """Berkas pendaftaran: scanned documents attached to a registration (many per registration)."""

    class DocType(models.TextChoices):
        DIPLOMA = "diploma", _("School diploma")
        REPORT = "report", _("Report card")
        ID_CARD = "id_card", _("ID card")
        CERTIFICATE = "certificate", _("Certificate")
        OTHER = "other", _("Other")

    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("Registration"),
    )
    doc_type = models.CharField(_("Document type"), max_length=20, choices=DocType.choices, default=DocType.OTHER)
    image = models.ImageField(_("Scan"), upload_to="documents")
    caption = models.CharField(_("Caption"), max_length=200, blank=True)
    uploaded_at = models.DateTimeField(_("Uploaded at"), auto_now_add=True)
    user = owner_field()

    class Meta:
        verbose_name = _("Registration document")
        verbose_name_plural = _("Registration documents")
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.caption or f"{self.get_doc_type_display()} #{self.pk}"
