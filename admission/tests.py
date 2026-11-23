import shutil
import tempfile
from io import BytesIO, StringIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.utils import translation
from model_bakery import baker
from openpyxl import load_workbook
from PIL import Image
from rest_framework.test import APIClient, APITestCase

from .models import Applicant, AdmissionPath, Faculty, Registration, RegistrationDocument, StudyProgram

User = get_user_model()
MEDIA_ROOT = tempfile.mkdtemp()  # images from tests never land in the real media folder


def make_image(name="photo.png"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "blue").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def stat_value(stats, label):
    return next(s["value"] for s in stats if s["label"] == label)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class BaseAPITestCase(APITestCase):
    """Every request in these tests is made by a logged-in ordinary user."""

    def setUp(self):
        self.user = baker.make(User)
        self.client.force_authenticate(self.user)

    def mine(self, model, **kwargs):
        return baker.make(model, user=self.user, **kwargs)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()


class FacultiesTestCase(BaseAPITestCase):
    def test_get_list(self):
        faculties = baker.make(Faculty, user=self.user, _quantity=3)

        r = self.client.get("/api/faculties/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 3)
        for faculty in faculties:
            item = next(f for f in r.json() if f["id"] == faculty.id)
            self.assertEqual(item["name"], faculty.name)
            self.assertEqual(item["user"], self.user.username)

    def test_create_with_logo(self):
        r = self.client.post(
            "/api/faculties/",
            {"code": "FT", "name": "Fakultas Teknik", "description": "Teknik", "logo": make_image("ft.png")},
            format="multipart",
        )
        self.assertEqual(r.status_code, 201)

        faculty = Faculty.objects.get(id=r.json()["id"])
        self.assertEqual(faculty.user, self.user)  # the owner is filled in automatically
        self.assertTrue(faculty.logo.name.startswith("faculties/"))

    def test_update(self):
        faculty = self.mine(Faculty)

        r = self.client.patch(f"/api/faculties/{faculty.id}/", {"name": "Fakultas Hukum"})
        self.assertEqual(r.status_code, 200)
        faculty.refresh_from_db()
        self.assertEqual(faculty.name, "Fakultas Hukum")

    def test_delete(self):
        faculties = baker.make(Faculty, user=self.user, _quantity=10)

        faculty_id = faculties[3].id
        r = self.client.delete(f"/api/faculties/{faculty_id}/")
        self.assertEqual(r.status_code, 204)

        r = self.client.get("/api/faculties/")
        self.assertEqual(len(r.json()), 9)
        self.assertNotIn(faculty_id, [f["id"] for f in r.json()])

    def test_filter_is_case_insensitive(self):
        self.mine(Faculty, name="Fakultas Teknik")
        self.mine(Faculty, name="Fakultas Hukum")

        r = self.client.get("/api/faculties/", {"name": "TEKNIK"})
        self.assertEqual([f["name"] for f in r.json()], ["Fakultas Teknik"])

    def test_stats(self):
        faculty = self.mine(Faculty)
        baker.make(StudyProgram, faculty=faculty, user=self.user, quota=50, _quantity=4)
        self.mine(Faculty)

        r = self.client.get("/api/faculties/stats/")
        self.assertEqual(stat_value(r.json(), "Faculties"), 2)
        self.assertEqual(stat_value(r.json(), "Avg study programs per faculty"), 2)
        self.assertEqual(stat_value(r.json(), "Total quota"), 200)


class StudyProgramsTestCase(BaseAPITestCase):
    def test_get_list(self):
        programs = baker.make(StudyProgram, user=self.user, _quantity=3)

        r = self.client.get("/api/programs/")
        self.assertEqual(len(r.json()), 3)
        for program in programs:
            item = next(p for p in r.json() if p["id"] == program.id)
            self.assertEqual(item["code"], program.code)
            self.assertEqual(item["faculty"]["id"], program.faculty.id)  # nested object

    def test_create(self):
        faculty = self.mine(Faculty)

        r = self.client.post(
            "/api/programs/",
            {"code": "IF01", "name": "Informatika", "degree": "S1", "quota": 120, "faculty_id": faculty.id},
        )
        self.assertEqual(r.status_code, 201)
        program = StudyProgram.objects.get(id=r.json()["id"])
        self.assertEqual(program.faculty, faculty)
        self.assertEqual(r.json()["faculty"]["name"], faculty.name)

    def test_update(self):
        program = self.mine(StudyProgram)
        new_faculty = self.mine(Faculty)

        r = self.client.patch(f"/api/programs/{program.id}/", {"quota": 75, "faculty_id": new_faculty.id})
        self.assertEqual(r.status_code, 200)
        program.refresh_from_db()
        self.assertEqual(program.quota, 75)
        self.assertEqual(program.faculty, new_faculty)

    def test_delete(self):
        programs = baker.make(StudyProgram, user=self.user, _quantity=10)

        r = self.client.delete(f"/api/programs/{programs[0].id}/")
        self.assertEqual(r.status_code, 204)
        self.assertEqual(len(self.client.get("/api/programs/").json()), 9)

    def test_filters(self):
        faculty = self.mine(Faculty)
        self.mine(StudyProgram, faculty=faculty, degree="S1")
        self.mine(StudyProgram, faculty=faculty, degree="D3")
        self.mine(StudyProgram, degree="S1")

        self.assertEqual(len(self.client.get("/api/programs/", {"faculty": faculty.id}).json()), 2)
        self.assertEqual(len(self.client.get("/api/programs/", {"faculty": faculty.id, "degree": "S1"}).json()), 1)

    def test_stats(self):
        faculty = self.mine(Faculty)
        self.mine(StudyProgram, faculty=faculty, degree="S1", quota=40)
        self.mine(StudyProgram, faculty=faculty, degree="D3", quota=80)

        stats = self.client.get("/api/programs/stats/").json()
        self.assertEqual(stat_value(stats, "Study programs"), 2)
        self.assertEqual(stat_value(stats, "Bachelor (S1) programs"), 1)
        self.assertEqual(stat_value(stats, "Total quota"), 120)
        self.assertEqual(stat_value(stats, "Avg quota"), 60)
        self.assertEqual(stat_value(stats, "Largest quota"), 80)

    def test_bad_filter_value_returns_empty_list(self):
        self.mine(StudyProgram)
        r = self.client.get("/api/programs/", {"faculty": "abc"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])


class AdmissionPathsTestCase(BaseAPITestCase):
    def test_create_and_list(self):
        r = self.client.post(
            "/api/paths/",
            {"name": "SNBT", "fee": 200000, "opens_on": "2026-01-10", "closes_on": "2026-03-31"},
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(self.client.get("/api/paths/").json()), 1)

    def test_closing_before_opening_is_rejected(self):
        r = self.client.post(
            "/api/paths/", {"name": "Mandiri", "opens_on": "2026-05-01", "closes_on": "2026-04-01"}
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("closes_on", r.json())

    def test_update_and_delete(self):
        path = self.mine(AdmissionPath)

        r = self.client.patch(f"/api/paths/{path.id}/", {"fee": 300000})
        self.assertEqual(r.status_code, 200)
        path.refresh_from_db()
        self.assertEqual(path.fee, 300000)

        self.assertEqual(self.client.delete(f"/api/paths/{path.id}/").status_code, 204)

    def test_stats(self):
        self.mine(AdmissionPath, fee=100000)
        self.mine(AdmissionPath, fee=300000)

        r = self.client.get("/api/paths/stats/")
        self.assertEqual(stat_value(r.json(), "Admission paths"), 2)
        self.assertEqual(stat_value(r.json(), "Avg fee (IDR)"), 200000)


class ApplicantsTestCase(BaseAPITestCase):
    def test_get_list(self):
        applicants = baker.make(Applicant, user=self.user, _quantity=3)

        r = self.client.get("/api/applicants/")
        self.assertEqual(len(r.json()), 3)
        for applicant in applicants:
            item = next(a for a in r.json() if a["id"] == applicant.id)
            self.assertEqual(item["full_name"], applicant.full_name)
            self.assertEqual(item["email"], applicant.email)

    def test_create_with_photo(self):
        r = self.client.post(
            "/api/applicants/",
            {
                "full_name": "Siti Rahmawati",
                "email": "siti@test.example",
                "gender": "F",
                "birth_place": "Bandung",
                "birth_date": "2007-04-12",
                "school_origin": "SMA Negeri 3 Bandung",
                "photo": make_image(),
            },
            format="multipart",
        )
        self.assertEqual(r.status_code, 201)
        applicant = Applicant.objects.get(id=r.json()["id"])
        self.assertTrue(applicant.photo.name.startswith("applicants/"))
        self.assertIn("/media/applicants/", r.json()["photo"])

    def test_empty_birth_date_from_form_becomes_null(self):
        r = self.client.post(
            "/api/applicants/",
            {"full_name": "Budi Santoso", "email": "budi@test.example", "gender": "M", "birth_date": ""},
            format="multipart",
        )
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(Applicant.objects.get(id=r.json()["id"]).birth_date)

    def test_update_photo(self):
        applicant = self.mine(Applicant)

        r = self.client.patch(f"/api/applicants/{applicant.id}/", {"photo": make_image("new.png")}, format="multipart")
        self.assertEqual(r.status_code, 200)
        applicant.refresh_from_db()
        self.assertTrue(applicant.photo)

    def test_delete(self):
        applicants = baker.make(Applicant, user=self.user, _quantity=10)

        applicant_id = applicants[5].id
        self.assertEqual(self.client.delete(f"/api/applicants/{applicant_id}/").status_code, 204)
        r = self.client.get("/api/applicants/")
        self.assertEqual(len(r.json()), 9)
        self.assertNotIn(applicant_id, [a["id"] for a in r.json()])

    def test_filters(self):
        self.mine(Applicant, full_name="Siti Aminah", gender="F")
        self.mine(Applicant, full_name="Siti Nurhaliza", gender="F")
        self.mine(Applicant, full_name="Agus Siswanto", gender="M")

        self.assertEqual(len(self.client.get("/api/applicants/", {"full_name": "siti"}).json()), 2)
        self.assertEqual(len(self.client.get("/api/applicants/", {"gender": "M"}).json()), 1)

    def test_stats(self):
        baker.make(Applicant, user=self.user, gender="F", _quantity=3)
        baker.make(Applicant, user=self.user, gender="M", _quantity=1)

        r = self.client.get("/api/applicants/stats/")
        self.assertEqual(stat_value(r.json(), "Applicants"), 4)
        self.assertEqual(stat_value(r.json(), "Female"), 3)

    def test_export_excel_and_word(self):
        baker.make(Applicant, user=self.user, _quantity=3)

        r = self.client.get("/api/applicants/export/", {"type": "xlsx"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheetml", r["Content-Type"])
        sheet = load_workbook(BytesIO(r.content)).active
        self.assertEqual(sheet.max_row, 4)  # header + 3 rows
        self.assertEqual(sheet["B1"].value, "Full name")

        r = self.client.get("/api/applicants/export/", {"type": "docx"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("wordprocessingml", r["Content-Type"])
        self.assertTrue(r.content.startswith(b"PK"))


class RegistrationsTestCase(BaseAPITestCase):
    def make_registration(self, **kwargs):
        return self.mine(
            Registration,
            applicant=kwargs.pop("applicant", None) or self.mine(Applicant),
            path=kwargs.pop("path", None) or self.mine(AdmissionPath),
            first_choice=kwargs.pop("first_choice", None) or self.mine(StudyProgram),
            **kwargs,
        )

    def test_get_list(self):
        registration = self.make_registration()

        r = self.client.get("/api/registrations/")
        item = r.json()[0]
        self.assertEqual(item["number"], registration.number)
        self.assertTrue(item["number"].startswith("PMB-"))
        self.assertEqual(item["applicant"]["id"], registration.applicant.id)
        self.assertEqual(item["documents_count"], 0)

    def test_create(self):
        applicant, path = self.mine(Applicant), self.mine(AdmissionPath)
        first, second = self.mine(StudyProgram), self.mine(StudyProgram)

        r = self.client.post(
            "/api/registrations/",
            {
                "applicant_id": applicant.id,
                "path_id": path.id,
                "first_choice_id": first.id,
                "second_choice_id": second.id,
            },
        )
        self.assertEqual(r.status_code, 201)
        registration = Registration.objects.get(id=r.json()["id"])
        self.assertEqual(registration.status, Registration.Status.SUBMITTED)
        self.assertEqual(registration.second_choice, second)
        self.assertTrue(registration.number.startswith("PMB-"))

    def test_same_first_and_second_choice_is_rejected(self):
        program = self.mine(StudyProgram)
        r = self.client.post(
            "/api/registrations/",
            {
                "applicant_id": self.mine(Applicant).id,
                "path_id": self.mine(AdmissionPath).id,
                "first_choice_id": program.id,
                "second_choice_id": program.id,
            },
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("second_choice_id", r.json())

    def test_duplicate_applicant_and_path_is_rejected(self):
        registration = self.make_registration()

        r = self.client.post(
            "/api/registrations/",
            {
                "applicant_id": registration.applicant.id,
                "path_id": registration.path.id,
                "first_choice_id": self.mine(StudyProgram).id,
            },
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Registration.objects.count(), 1)

    def test_update_status_and_score(self):
        registration = self.make_registration()

        r = self.client.patch(f"/api/registrations/{registration.id}/", {"status": "accepted", "test_score": 87})
        self.assertEqual(r.status_code, 200)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.ACCEPTED)
        self.assertEqual(registration.test_score, 87)

    def test_score_above_100_is_rejected(self):
        registration = self.make_registration()
        r = self.client.patch(f"/api/registrations/{registration.id}/", {"test_score": 120})
        self.assertEqual(r.status_code, 400)

    def test_delete(self):
        registrations = [self.make_registration() for _ in range(3)]

        self.assertEqual(self.client.delete(f"/api/registrations/{registrations[1].id}/").status_code, 204)
        self.assertEqual(len(self.client.get("/api/registrations/").json()), 2)

    def test_filters(self):
        self.make_registration(status="accepted", applicant=self.mine(Applicant, full_name="Dewi Lestari"))
        self.make_registration(status="rejected", applicant=self.mine(Applicant, full_name="Dewi Sartika"))
        self.make_registration(status="accepted")

        self.assertEqual(len(self.client.get("/api/registrations/", {"applicant": "dewi"}).json()), 2)
        r = self.client.get("/api/registrations/", {"applicant": "dewi", "status": "accepted"})
        self.assertEqual([x["applicant"]["full_name"] for x in r.json()], ["Dewi Lestari"])

    def test_stats(self):
        self.make_registration(status="accepted", test_score=90)
        self.make_registration(status="accepted", test_score=80)
        self.make_registration(status="rejected", test_score=40)
        self.make_registration(status="submitted")

        stats = self.client.get("/api/registrations/stats/").json()
        self.assertEqual(stat_value(stats, "Registrations"), 4)
        self.assertEqual(stat_value(stats, "Accepted"), 2)
        self.assertEqual(stat_value(stats, "Acceptance rate, %"), 50.0)
        self.assertEqual(stat_value(stats, "Avg test score"), 70)

    def test_stats_are_not_skewed_by_documents(self):
        registration = self.make_registration(test_score=100)
        self.make_registration(test_score=50)
        baker.make(RegistrationDocument, registration=registration, user=self.user, image="documents/a.png", _quantity=3)

        stats = self.client.get("/api/registrations/stats/").json()
        self.assertEqual(stat_value(stats, "Registrations"), 2)
        self.assertEqual(stat_value(stats, "Avg test score"), 75)


class DocumentsTestCase(BaseAPITestCase):
    def test_album_upload_list_and_delete(self):
        registration = baker.make(Registration, user=self.user)
        other = baker.make(Registration, user=self.user)

        for doc_type in ["diploma", "id_card"]:
            r = self.client.post(
                "/api/documents/",
                {"registration": registration.id, "doc_type": doc_type, "image": make_image(f"{doc_type}.png")},
                format="multipart",
            )
            self.assertEqual(r.status_code, 201)
        baker.make(RegistrationDocument, registration=other, user=self.user, image="documents/x.png")

        r = self.client.get("/api/documents/", {"registration": registration.id})
        self.assertEqual(len(r.json()), 2)

        # the registrations table shows how many documents each registration has
        counts = {x["id"]: x["documents_count"] for x in self.client.get("/api/registrations/").json()}
        self.assertEqual(counts, {registration.id: 2, other.id: 1})

        self.assertEqual(self.client.delete(f"/api/documents/{r.json()[0]['id']}/").status_code, 204)
        self.assertEqual(RegistrationDocument.objects.filter(registration=registration).count(), 1)


class EveryEndpointTestCase(BaseAPITestCase):
    """Stats and both exports answer 200 on every model, empty or with data, as user and as superuser."""

    ENDPOINTS = ["faculties", "programs", "paths", "applicants", "registrations", "documents"]

    def check_all(self):
        for name in self.ENDPOINTS:
            for url in [f"/api/{name}/", f"/api/{name}/stats/", f"/api/{name}/export/?type=xlsx", f"/api/{name}/export/?type=docx"]:
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_empty(self):
        self.check_all()

    def test_with_data(self):
        registration = baker.make(Registration, user=self.user, test_score=70, status="accepted")
        baker.make(StudyProgram, user=self.user, faculty=registration.first_choice.faculty)
        baker.make(RegistrationDocument, registration=registration, user=self.user, image="documents/a.png")
        self.check_all()
        self.client.force_authenticate(baker.make(User, is_superuser=True))
        self.check_all()


class OwnershipTestCase(BaseAPITestCase):
    def test_anonymous_has_no_access(self):
        self.assertIn(APIClient().get("/api/applicants/").status_code, (401, 403))

    def test_user_sees_only_own_data(self):
        baker.make(Applicant, user=self.user, _quantity=2)
        foreign = baker.make(Applicant, user=baker.make(User))

        self.assertEqual(len(self.client.get("/api/applicants/").json()), 2)
        self.assertEqual(self.client.get(f"/api/applicants/{foreign.id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/applicants/{foreign.id}/").status_code, 404)

    def test_cannot_link_to_another_users_record(self):
        foreign_faculty = baker.make(Faculty, user=baker.make(User))

        r = self.client.post("/api/programs/", {"code": "X01", "name": "X", "faculty_id": foreign_faculty.id})
        self.assertEqual(r.status_code, 400)
        self.assertIn("faculty_id", r.json())

    def test_superuser_sees_all_and_filters_by_user(self):
        other = baker.make(User)
        baker.make(Applicant, user=self.user, _quantity=2)
        baker.make(Applicant, user=other, _quantity=3)

        self.client.force_authenticate(baker.make(User, is_superuser=True))
        self.assertEqual(len(self.client.get("/api/applicants/").json()), 5)
        self.assertEqual(len(self.client.get("/api/applicants/", {"user": other.id}).json()), 3)

    def test_users_list_only_for_superuser(self):
        self.assertEqual(self.client.get("/api/users/").status_code, 403)
        self.client.force_authenticate(baker.make(User, is_superuser=True))
        self.assertEqual(self.client.get("/api/users/").status_code, 200)


class LanguageTestCase(BaseAPITestCase):
    """The API answers in English by default and in Indonesian when the client asks for it."""

    def test_stats_labels_follow_accept_language(self):
        baker.make(Applicant, user=self.user, gender="F")

        r = self.client.get("/api/applicants/stats/", HTTP_ACCEPT_LANGUAGE="id")
        self.assertEqual(stat_value(r.json(), "Calon mahasiswa"), 1)
        self.assertEqual(stat_value(r.json(), "Perempuan"), 1)

    def test_language_cookie_wins(self):
        self.client.cookies["django_language"] = "id"
        r = self.client.get("/api/paths/stats/")
        self.assertIn("Jalur pendaftaran", [s["label"] for s in r.json()])

    def test_validation_message_in_indonesian(self):
        r = self.client.post(
            "/api/paths/",
            {"name": "Mandiri", "opens_on": "2026-05-01", "closes_on": "2026-04-01"},
            HTTP_ACCEPT_LANGUAGE="id",
        )
        self.assertEqual(r.json()["closes_on"], ["Tanggal penutupan harus setelah tanggal pembukaan."])

    def test_export_headers_in_indonesian(self):
        baker.make(Applicant, user=self.user)
        r = self.client.get("/api/applicants/export/", {"type": "xlsx"}, HTTP_ACCEPT_LANGUAGE="id")
        sheet = load_workbook(BytesIO(r.content)).active
        self.assertEqual(sheet["B1"].value, "Nama lengkap")
        self.assertIn("applicants-id.xlsx", r["Content-Disposition"])

    def test_model_names_are_translated(self):
        with translation.override("id"):
            self.assertEqual(str(Applicant._meta.verbose_name_plural), "Calon mahasiswa")
            self.assertEqual(str(RegistrationDocument.DocType.DIPLOMA.label), "Ijazah")
        with translation.override("en"):
            self.assertEqual(str(Applicant._meta.verbose_name_plural), "Applicants")


class AuthTestCase(APITestCase):
    def test_login_info_logout(self):
        User.objects.create_user("andi", password="secret-pass-123")
        client = APIClient()

        r = client.get("/api/users/info/")
        self.assertFalse(r.json()["is_authenticated"])
        self.assertIn("csrftoken", r.cookies)

        r = client.post("/api/users/login/", {"username": "andi", "password": "wrong"}, HTTP_ACCEPT_LANGUAGE="id")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"], "Nama pengguna atau kata sandi salah.")

        r = client.post("/api/users/login/", {"username": "andi", "password": "secret-pass-123"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(client.get("/api/users/info/").json()["is_authenticated"])
        self.assertEqual(client.get("/api/applicants/").status_code, 200)

        client.post("/api/users/logout/")
        self.assertFalse(client.get("/api/users/info/").json()["is_authenticated"])


class CsrfThroughViteProxyTestCase(APITestCase):
    """A POST that comes through the Vite proxy (Origin localhost:5173, Host 127.0.0.1:8000) is accepted."""

    def test_post_with_front_end_origin(self):
        user = User.objects.create_user("rina", password="secret-pass-123")
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(user)  # a real session, so DRF enforces CSRF
        token = client.get("/api/users/info/").cookies["csrftoken"].value

        r = client.post(
            "/api/faculties/",
            {"code": "FT", "name": "Fakultas Teknik"},
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://localhost:5173",
            HTTP_HOST="127.0.0.1:8000",
        )
        self.assertEqual(r.status_code, 201)

        r = client.post(
            "/api/faculties/",
            {"code": "FH", "name": "Fakultas Hukum"},
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://evil.example",
            HTTP_HOST="127.0.0.1:8000",
        )
        self.assertEqual(r.status_code, 403)


class GenerateDataTestCase(APITestCase):
    def test_generates_records_for_user(self):
        user = baker.make(User)

        call_command("generate_data", user=user.username, applicants=20, registrations=30, stdout=StringIO())

        self.assertEqual(Faculty.objects.filter(user=user).count(), 10)
        self.assertGreater(StudyProgram.objects.filter(user=user).count(), 30)
        self.assertEqual(AdmissionPath.objects.filter(user=user).count(), 5)
        self.assertEqual(Applicant.objects.filter(user=user).count(), 20)
        self.assertEqual(Registration.objects.filter(user=user).count(), 30)

        # running it again for the same user reuses faculties, programs and paths
        call_command("generate_data", user=user.username, applicants=5, registrations=5, stdout=StringIO())
        self.assertEqual(Faculty.objects.filter(user=user).count(), 10)
        self.assertEqual(Applicant.objects.filter(user=user).count(), 25)
