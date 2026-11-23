import datetime
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from faker import Faker

from admission.models import Applicant, AdmissionPath, Faculty, Registration, StudyProgram

# Faculty: (code, name, [study programs])
FACULTIES = [
    ("FT", "Fakultas Teknik", ["Teknik Sipil", "Teknik Mesin", "Teknik Elektro", "Teknik Industri", "Arsitektur"]),
    ("FIK", "Fakultas Ilmu Komputer", ["Informatika", "Sistem Informasi", "Teknologi Informasi", "Sains Data"]),
    ("FEB", "Fakultas Ekonomi dan Bisnis", ["Manajemen", "Akuntansi", "Ekonomi Pembangunan", "Bisnis Digital"]),
    ("FH", "Fakultas Hukum", ["Ilmu Hukum"]),
    ("FK", "Fakultas Kedokteran", ["Pendidikan Dokter", "Ilmu Keperawatan", "Farmasi", "Kesehatan Masyarakat"]),
    ("FMIPA", "Fakultas Matematika dan Ilmu Pengetahuan Alam", ["Matematika", "Fisika", "Kimia", "Biologi", "Statistika"]),
    ("FISIP", "Fakultas Ilmu Sosial dan Ilmu Politik", ["Ilmu Komunikasi", "Hubungan Internasional", "Sosiologi", "Ilmu Pemerintahan"]),
    ("FKIP", "Fakultas Keguruan dan Ilmu Pendidikan", ["Pendidikan Bahasa Inggris", "Pendidikan Matematika", "PGSD"]),
    ("FP", "Fakultas Pertanian", ["Agroteknologi", "Agribisnis", "Ilmu Tanah"]),
    ("FPSI", "Fakultas Psikologi", ["Psikologi"]),
]

# Admission path: (name, description, fee in IDR)
PATHS = [
    ("SNBP", "Seleksi Nasional Berdasarkan Prestasi (rapor)", 0),
    ("SNBT", "Seleksi Nasional Berdasarkan Tes (UTBK)", 200000),
    ("Mandiri", "Seleksi Mandiri oleh universitas", 300000),
    ("Prestasi", "Jalur prestasi akademik dan non-akademik", 150000),
    ("Kerja Sama", "Jalur kerja sama daerah dan instansi", 250000),
]

SCHOOL_TYPES = ["SMA Negeri", "SMA Swasta", "SMK Negeri", "MA Negeri"]


def unique_name(model, name, owner):
    """Names are unique across all users: add the username when another user already has this name."""
    if model.objects.filter(name=name).exists():
        return f"{name} ({owner.username})"
    return name


class Command(BaseCommand):
    help = "Fills the database with random Indonesian data (1000+ applicants and registrations by default)"

    def add_arguments(self, parser):
        parser.add_argument("--user", help="owner's username (default: the first superuser)")
        parser.add_argument("--applicants", type=int, default=1000)
        parser.add_argument("--registrations", type=int, default=1500)
        parser.add_argument("--clear", action="store_true", help="delete this user's existing data first")

    @transaction.atomic
    def handle(self, *args, **options):
        owner = self.get_owner(options["user"])
        fake = Faker(["id_ID"])

        if options["clear"]:
            # order matters: Faculty, StudyProgram and AdmissionPath are protected by PROTECT
            for model in (Registration, Applicant, StudyProgram, AdmissionPath, Faculty):
                model.objects.filter(user=owner).delete()
            self.stdout.write(f"Old data of '{owner.username}' deleted")

        # --- faculties and study programs (codes include the owner's id so they stay unique per user) ---
        degrees = [StudyProgram.Degree.S1] * 6 + [StudyProgram.Degree.D3, StudyProgram.Degree.S2]
        faculties, programs = [], []
        for code, name, program_names in FACULTIES:
            faculty, _ = Faculty.objects.get_or_create(
                code=f"{code}-{owner.id}",
                defaults={"name": unique_name(Faculty, name, owner),
                          "description": fake.sentence(nb_words=10), "user": owner},
            )
            faculties.append(faculty)
            for i, program_name in enumerate(program_names, start=1):
                program, _ = StudyProgram.objects.get_or_create(
                    code=f"{code}{i:02d}-{owner.id}",
                    defaults={
                        "name": program_name,
                        "faculty": faculty,
                        "degree": random.choice(degrees),
                        "quota": random.choice([40, 60, 80, 100, 120, 150]),
                        "user": owner,
                    },
                )
                programs.append(program)

        # --- admission paths ---
        year = datetime.date.today().year
        paths = []
        for name, description, fee in PATHS:
            path = AdmissionPath.objects.filter(user=owner, name__startswith=name).first()
            if path:
                paths.append(path)
                continue
            path = AdmissionPath.objects.create(
                name=unique_name(AdmissionPath, name, owner),
                description=description,
                fee=fee,
                opens_on=datetime.date(year, random.randint(1, 4), 1),
                closes_on=datetime.date(year, random.randint(5, 7), 28),
                user=owner,
            )
            paths.append(path)

        # --- applicants ---
        existing = Applicant.objects.count()
        applicants = []
        for i in range(options["applicants"]):
            male = random.random() < 0.5
            name = fake.name_male() if male else fake.name_female()
            city = fake.city()
            applicants.append(
                Applicant(
                    full_name=name,
                    email=f"{fake.user_name()}.{existing + i + 1}@mail.example",
                    phone=fake.phone_number(),
                    gender=Applicant.Gender.MALE if male else Applicant.Gender.FEMALE,
                    birth_place=city,
                    birth_date=fake.date_of_birth(minimum_age=17, maximum_age=22),
                    address=fake.address().replace("\n", ", "),
                    school_origin=f"{random.choice(SCHOOL_TYPES)} {random.randint(1, 20)} {fake.city()}",
                    user=owner,
                )
            )
        created = Applicant.objects.bulk_create(applicants, batch_size=500)
        applicant_ids = list(
            Applicant.objects.filter(user=owner).order_by("-id").values_list("id", flat=True)[: len(created)]
        )

        # --- registrations: unique (applicant, path) pairs ---
        wanted = min(options["registrations"], len(applicant_ids) * len(paths))
        pairs = set()
        while len(pairs) < wanted:
            pairs.add((random.choice(applicant_ids), random.choice(paths).id))

        statuses = list(Registration.Status)
        registrations = []
        for applicant_id, path_id in pairs:
            first, second = random.sample(programs, 2)
            status = random.choices(statuses, weights=[3, 3, 3, 1])[0]
            score = None if status == Registration.Status.SUBMITTED else random.randint(35, 100)
            registrations.append(
                Registration(
                    applicant_id=applicant_id,
                    path_id=path_id,
                    first_choice=first,
                    second_choice=second if random.random() < 0.7 else None,
                    status=status,
                    test_score=score,
                    user=owner,
                )
            )
        Registration.objects.bulk_create(registrations, batch_size=500)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created for user '{owner.username}': {len(faculties)} faculties, {len(programs)} study programs, "
                f"{len(paths)} admission paths, {len(created)} applicants, {len(registrations)} registrations"
            )
        )

    def get_owner(self, username):
        User = get_user_model()
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"User '{username}' not found")
        owner = User.objects.filter(is_superuser=True).order_by("id").first()
        if owner is None:
            raise CommandError("No superuser found: run createsuperuser first or pass --user <username>")
        return owner
