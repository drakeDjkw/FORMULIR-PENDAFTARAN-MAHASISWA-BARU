# Formulir Pendaftaran Mahasiswa Baru — New Student Registration Form

[English](#english) · [Bahasa Indonesia](#bahasa-indonesia)

---

## English

Coursework: a Django + Django REST Framework backend with a Vue 3 front end for registering new university students. The whole app works in **English and Bahasa Indonesia**: the interface, the Django admin, API messages, statistics and Excel/Word exports all follow the language switch (EN / ID) in the top bar.

### Data model

| Model | Fields | Foreign keys |
|---|---|---|
| Faculty (Fakultas) | code, name, description, **logo** | user |
| StudyProgram (Program studi) | code, name, degree (D3/S1/S2), quota | faculty → Faculty, user |
| AdmissionPath (Jalur pendaftaran) | name, description, fee (IDR), opens_on, closes_on | user |
| Applicant (Calon mahasiswa) | full_name, email, phone, gender, birth place and date, address, school of origin, **photo** | user |
| Registration (Pendaftaran) | number (auto, `PMB-2026-XXXXXXXX`), status, test_score, registered_on | applicant → Applicant, path → AdmissionPath, first_choice → StudyProgram, second_choice → StudyProgram, user |
| RegistrationDocument (Berkas) | document type, **image** (scan), caption, uploaded_at | registration → Registration, user |

- One applicant can register once per admission path (unique applicant + path).
- The second choice must differ from the first choice; the test score is 0–100.
- A registration can have many documents (diploma, report card, ID card, …): the document album.
- Every record has an owner (`user`), filled in automatically.

### Access rules

- Without logging in, the API is closed.
- An ordinary user sees and edits only their own records, and can only link to their own records.
- A superuser sees everyone's records and can filter by owner (`?user=<id>`).

### Run the backend

```bash
pip install -r requirements.txt
python manage.py makemigrations admission
python manage.py migrate
python manage.py createsuperuser
python manage.py generate_data      # 10 faculties, 34 study programs, 5 paths, 1000 applicants, 1500 registrations
python manage.py runserver
python -m pytest                    # 47 tests
```

`generate_data` options: `--user <username>`, `--applicants 1000`, `--registrations 1500`, `--clear` (delete that user's data first). The names come from Faker's Indonesian locale.

### Run the front end

Needs Node.js 20.19+ or 22+.

```bash
cd client
npm install
npm run dev
```

Open http://localhost:5173. Vite forwards `/api`, `/admin`, `/static` and `/media` to Django on port 8000, so both servers must run.

### How the two languages work

| Part | How |
|---|---|
| Vue interface | `client/src/i18n/en.js` and `id.js` dictionaries; `$t("nav.faculties")` in templates |
| Choosing a language | The EN / ID switch saves the choice and sets the `django_language` cookie; axios also sends `Accept-Language` |
| Django | `LocaleMiddleware` reads the cookie or header; model names, choices, messages, statistics and export headers use `gettext` |
| Indonesian text | `locale/id/LC_MESSAGES/django.po` (source) and `django.mo` (compiled) |

After editing `django.po`, compile it with `python tools/compile_messages.py` (no extra tools needed), or `python manage.py compilemessages` if GNU gettext is installed.

### API

Every model endpoint supports list, create, retrieve, update (PUT/PATCH) and delete, plus:

| Extra endpoint | What it does |
|---|---|
| `GET /api/<model>/stats/` | Aggregate statistics (Count, Avg, Min, Max, Sum), respecting the filters |
| `GET /api/<model>/export/?type=xlsx` | Download the table as Excel, respecting the filters |
| `GET /api/<model>/export/?type=docx` | Download the table as Word, respecting the filters |

Models: `faculties`, `programs`, `paths`, `applicants`, `registrations`, `documents`.

Users: `GET /api/users/info/`, `POST /api/users/login/`, `POST /api/users/logout/`, `GET /api/users/` (superuser only).

Filters are query parameters, for example `/api/applicants/?full_name=siti&gender=F`, `/api/registrations/?status=accepted&path=2`.

---

## Bahasa Indonesia

Tugas kuliah: backend Django + Django REST Framework dengan frontend Vue 3 untuk pendaftaran mahasiswa baru. Seluruh aplikasi tersedia dalam **bahasa Inggris dan bahasa Indonesia**: antarmuka, panel admin Django, pesan API, statistik, serta ekspor Excel/Word mengikuti tombol bahasa (EN / ID) di bilah atas.

### Model data

| Model | Kolom | Foreign key |
|---|---|---|
| Faculty (Fakultas) | kode, nama, deskripsi, **logo** | user |
| StudyProgram (Program studi) | kode, nama, jenjang (D3/S1/S2), kuota | faculty → Faculty, user |
| AdmissionPath (Jalur pendaftaran) | nama, deskripsi, biaya (Rp), tanggal dibuka, tanggal ditutup | user |
| Applicant (Calon mahasiswa) | nama lengkap, e-mail, telepon, jenis kelamin, tempat dan tanggal lahir, alamat, asal sekolah, **foto** | user |
| Registration (Pendaftaran) | nomor (otomatis, `PMB-2026-XXXXXXXX`), status, nilai tes, tanggal daftar | applicant → Applicant, path → AdmissionPath, first_choice → StudyProgram, second_choice → StudyProgram, user |
| RegistrationDocument (Berkas) | jenis berkas, **gambar** (pindaian), keterangan, waktu unggah | registration → Registration, user |

- Satu calon mahasiswa hanya bisa mendaftar sekali per jalur pendaftaran.
- Pilihan kedua harus berbeda dari pilihan pertama; nilai tes 0–100.
- Satu pendaftaran bisa memiliki banyak berkas (ijazah, rapor, KTP, …): album berkas.
- Setiap data memiliki pemilik (`user`) yang diisi otomatis.

### Hak akses

- Tanpa login, API tertutup.
- Pengguna biasa hanya melihat dan mengubah datanya sendiri, dan hanya bisa menautkan ke datanya sendiri.
- Superuser melihat data semua pengguna dan bisa menyaring berdasarkan pemilik (`?user=<id>`).

### Menjalankan backend

```bash
pip install -r requirements.txt
python manage.py makemigrations admission
python manage.py migrate
python manage.py createsuperuser
python manage.py generate_data      # 10 fakultas, 34 program studi, 5 jalur, 1000 calon mahasiswa, 1500 pendaftaran
python manage.py runserver
python -m pytest                    # 47 tes
```

Opsi `generate_data`: `--user <nama pengguna>`, `--applicants 1000`, `--registrations 1500`, `--clear` (hapus data pengguna tersebut terlebih dahulu). Nama dibuat dengan Faker berbahasa Indonesia.

### Menjalankan frontend

Membutuhkan Node.js 20.19+ atau 22+.

```bash
cd client
npm install
npm run dev
```

Buka http://localhost:5173. Vite meneruskan `/api`, `/admin`, `/static`, dan `/media` ke Django di port 8000, jadi kedua server harus berjalan.

### Cara kerja dua bahasa

| Bagian | Cara |
|---|---|
| Antarmuka Vue | Kamus `client/src/i18n/en.js` dan `id.js`; `$t("nav.faculties")` di template |
| Memilih bahasa | Tombol EN / ID menyimpan pilihan dan mengatur cookie `django_language`; axios juga mengirim `Accept-Language` |
| Django | `LocaleMiddleware` membaca cookie atau header; nama model, pilihan, pesan, statistik, dan judul kolom ekspor memakai `gettext` |
| Teks bahasa Indonesia | `locale/id/LC_MESSAGES/django.po` (sumber) dan `django.mo` (hasil kompilasi) |

Setelah mengubah `django.po`, kompilasi dengan `python tools/compile_messages.py` (tanpa alat tambahan), atau `python manage.py compilemessages` jika GNU gettext terpasang.

### API

Setiap endpoint model mendukung daftar, tambah, lihat, ubah (PUT/PATCH), dan hapus, ditambah:

| Endpoint tambahan | Fungsi |
|---|---|
| `GET /api/<model>/stats/` | Statistik agregat (Count, Avg, Min, Max, Sum) sesuai filter |
| `GET /api/<model>/export/?type=xlsx` | Unduh tabel sebagai Excel sesuai filter |
| `GET /api/<model>/export/?type=docx` | Unduh tabel sebagai Word sesuai filter |

Model: `faculties`, `programs`, `paths`, `applicants`, `registrations`, `documents`.

Pengguna: `GET /api/users/info/`, `POST /api/users/login/`, `POST /api/users/logout/`, `GET /api/users/` (khusus superuser).

Filter berupa parameter query, misalnya `/api/applicants/?full_name=siti&gender=F`, `/api/registrations/?status=accepted&path=2`.
