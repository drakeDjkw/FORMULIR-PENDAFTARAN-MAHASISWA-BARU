<script setup>
import { ref } from "vue";
import { useResource } from "@/composables/useResource";
import { useUserStore } from "@/stores/user";
import { t } from "@/i18n";
import { toFormData } from "@/utils/formData";
import ImageModal from "@/components/ImageModal.vue";
import StatsPanel from "@/components/StatsPanel.vue";
import TableToolbar from "@/components/TableToolbar.vue";

const user = useUserStore();
const {
  items: applicants, stats, loading, filters, create, update, remove, exportUrl, resetFilters,
} = useResource("/api/applicants/", {
  full_name: "",
  email: "",
  phone: "",
  gender: "",
  birth_place: "",
  birth_year: "",
  school_origin: "",
});

const genders = ["M", "F"];

// --- add ---
const emptyApplicant = () => ({
  full_name: "",
  email: "",
  phone: "",
  gender: "F",
  birth_place: "",
  birth_date: "",
  address: "",
  school_origin: "",
});
const applicantToAdd = ref(emptyApplicant());
const addPhotoRef = ref(); // the <input type="file"> of the add form
const addPhotoPreview = ref("");

function onAddPhotoChange() {
  const file = addPhotoRef.value.files[0];
  addPhotoPreview.value = file ? URL.createObjectURL(file) : "";
}

async function onApplicantAdd() {
  await create(toFormData(applicantToAdd.value, { photo: addPhotoRef.value.files[0] }));
  applicantToAdd.value = emptyApplicant();
  addPhotoRef.value.value = "";
  addPhotoPreview.value = "";
}

// --- edit ---
const applicantToEdit = ref({});
const editPhotoRef = ref();
const editPhotoPreview = ref("");

function onApplicantEditClick(applicant) {
  applicantToEdit.value = {
    id: applicant.id,
    full_name: applicant.full_name,
    email: applicant.email,
    phone: applicant.phone,
    gender: applicant.gender,
    birth_place: applicant.birth_place,
    birth_date: applicant.birth_date ?? "",
    address: applicant.address,
    school_origin: applicant.school_origin,
  };
  editPhotoPreview.value = applicant.photo ?? "";
  editPhotoRef.value.value = "";
}

function onEditPhotoChange() {
  const file = editPhotoRef.value.files[0];
  if (file) editPhotoPreview.value = URL.createObjectURL(file);
}

async function onUpdateApplicant() {
  const { id, ...data } = applicantToEdit.value;
  await update(id, toFormData(data, { photo: editPhotoRef.value.files[0] }));
}

async function onRemoveClick(applicant) {
  if (!confirm(t("common.confirmDelete", { name: applicant.full_name }))) return;
  await remove(applicant.id);
}

// --- view the photo large ---
const photoToShow = ref({ src: "", title: "" });
function onPhotoClick(applicant) {
  photoToShow.value = { src: applicant.photo, title: applicant.full_name };
}
</script>

<template>
  <div class="row g-4">
    <div class="col-xl-9">
      <h2 class="mb-3">{{ $t("applicants.title") }}</h2>

      <form class="card card-body shadow-sm mb-3" @submit.prevent.stop="onApplicantAdd">
        <div class="row g-2 align-items-center">
          <div class="col-md-3">
            <div class="form-floating">
              <input v-model="applicantToAdd.full_name" type="text" class="form-control" :placeholder="$t('applicants.fullName')" required />
              <label>{{ $t("applicants.fullName") }}</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-floating">
              <input v-model="applicantToAdd.email" type="email" class="form-control" :placeholder="$t('applicants.email')" required />
              <label>{{ $t("applicants.email") }}</label>
            </div>
          </div>
          <div class="col-md-2">
            <div class="form-floating">
              <input v-model="applicantToAdd.phone" type="tel" class="form-control" :placeholder="$t('applicants.phone')" />
              <label>{{ $t("applicants.phone") }}</label>
            </div>
          </div>
          <div class="col-md-2">
            <div class="form-floating">
              <select v-model="applicantToAdd.gender" class="form-select">
                <option v-for="g in genders" :key="g" :value="g">{{ $t(`gender.${g}`) }}</option>
              </select>
              <label>{{ $t("applicants.gender") }}</label>
            </div>
          </div>
          <div class="col-md-2">
            <div class="form-floating">
              <input v-model="applicantToAdd.birth_place" type="text" class="form-control" :placeholder="$t('applicants.birthPlace')" />
              <label>{{ $t("applicants.birthPlace") }}</label>
            </div>
          </div>
          <div class="col-md-2">
            <div class="form-floating">
              <input v-model="applicantToAdd.birth_date" type="date" class="form-control" />
              <label>{{ $t("applicants.birthDate") }}</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-floating">
              <input v-model="applicantToAdd.school_origin" type="text" class="form-control" :placeholder="$t('applicants.school')" />
              <label>{{ $t("applicants.school") }}</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-floating">
              <input v-model="applicantToAdd.address" type="text" class="form-control" :placeholder="$t('applicants.address')" />
              <label>{{ $t("applicants.address") }}</label>
            </div>
          </div>
          <div class="col-md-2">
            <input ref="addPhotoRef" type="file" accept="image/*" class="form-control" :title="$t('applicants.photo')" @change="onAddPhotoChange" />
          </div>
          <div v-if="addPhotoPreview" class="col-auto">
            <img :src="addPhotoPreview" class="thumb" alt="" />
          </div>
          <div class="col-auto">
            <button class="btn btn-primary"><i class="bi bi-plus-lg"></i> {{ $t("common.add") }}</button>
          </div>
        </div>
      </form>

      <TableToolbar
        v-model:owner="filters.user"
        :count="applicants.length"
        :loading="loading"
        :export-url="exportUrl"
        @reset="resetFilters"
      />

      <div class="card shadow-sm table-scroll">
        <table class="table table-hover align-middle mb-0 data-table">
          <thead class="table-light">
            <tr>
              <th>{{ $t("applicants.photo") }}</th>
              <th>{{ $t("applicants.fullName") }}</th>
              <th>{{ $t("applicants.email") }}</th>
              <th>{{ $t("applicants.phone") }}</th>
              <th>{{ $t("applicants.gender") }}</th>
              <th>{{ $t("applicants.birthPlace") }}</th>
              <th>{{ $t("applicants.birthDate") }}</th>
              <th>{{ $t("applicants.school") }}</th>
              <th v-if="user.isSuperuser">{{ $t("common.owner") }}</th>
              <th></th>
            </tr>
            <tr class="filters">
              <th></th>
              <th><input v-model="filters.full_name" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th><input v-model="filters.email" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th><input v-model="filters.phone" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th>
                <select v-model="filters.gender" class="form-select form-select-sm">
                  <option value="">{{ $t("common.all") }}</option>
                  <option v-for="g in genders" :key="g" :value="g">{{ $t(`gender.${g}`) }}</option>
                </select>
              </th>
              <th><input v-model="filters.birth_place" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th><input v-model="filters.birth_year" type="number" class="form-control form-control-sm" :placeholder="$t('applicants.birthYear')" /></th>
              <th><input v-model="filters.school_origin" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th v-if="user.isSuperuser"></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in applicants" :key="item.id">
              <td>
                <img
                  v-if="item.photo"
                  :src="item.photo"
                  class="thumb"
                  alt=""
                  data-bs-toggle="modal"
                  data-bs-target="#applicantPhotoModal"
                  @click="onPhotoClick(item)"
                />
                <span v-else class="thumb-placeholder"><i class="bi bi-person"></i></span>
              </td>
              <td>{{ item.full_name }}</td>
              <td>{{ item.email }}</td>
              <td class="text-nowrap">{{ item.phone }}</td>
              <td>{{ $t(`gender.${item.gender}`) }}</td>
              <td>{{ item.birth_place }}</td>
              <td class="text-nowrap">{{ item.birth_date ?? "—" }}</td>
              <td>{{ item.school_origin }}</td>
              <td v-if="user.isSuperuser"><span class="badge text-bg-light">{{ item.user ?? "—" }}</span></td>
              <td class="actions">
                <button
                  class="btn btn-sm btn-success me-1"
                  data-bs-toggle="modal"
                  data-bs-target="#editApplicantModal"
                  @click="onApplicantEditClick(item)"
                >
                  <i class="bi bi-pen-fill"></i>
                </button>
                <button class="btn btn-sm btn-danger" @click="onRemoveClick(item)">
                  <i class="bi bi-x-lg"></i>
                </button>
              </td>
            </tr>
            <tr v-if="!applicants.length && !loading">
              <td colspan="10" class="text-center text-muted py-4">{{ $t("common.noData") }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="col-xl-3">
      <StatsPanel :stats="stats" />
    </div>
  </div>

  <div id="editApplicantModal" class="modal fade" tabindex="-1">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h1 class="modal-title fs-5">{{ $t("applicants.edit") }}</h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" :aria-label="$t('common.close')"></button>
        </div>
        <div class="modal-body">
          <div class="row g-2">
            <div class="col-md-6">
              <div class="form-floating">
                <input v-model="applicantToEdit.full_name" type="text" class="form-control" :placeholder="$t('applicants.fullName')" />
                <label>{{ $t("applicants.fullName") }}</label>
              </div>
            </div>
            <div class="col-md-6">
              <div class="form-floating">
                <input v-model="applicantToEdit.email" type="email" class="form-control" :placeholder="$t('applicants.email')" />
                <label>{{ $t("applicants.email") }}</label>
              </div>
            </div>
            <div class="col-md-4">
              <div class="form-floating">
                <input v-model="applicantToEdit.phone" type="tel" class="form-control" :placeholder="$t('applicants.phone')" />
                <label>{{ $t("applicants.phone") }}</label>
              </div>
            </div>
            <div class="col-md-4">
              <div class="form-floating">
                <select v-model="applicantToEdit.gender" class="form-select">
                  <option v-for="g in genders" :key="g" :value="g">{{ $t(`gender.${g}`) }}</option>
                </select>
                <label>{{ $t("applicants.gender") }}</label>
              </div>
            </div>
            <div class="col-md-4">
              <div class="form-floating">
                <input v-model="applicantToEdit.birth_date" type="date" class="form-control" />
                <label>{{ $t("applicants.birthDate") }}</label>
              </div>
            </div>
            <div class="col-md-6">
              <div class="form-floating">
                <input v-model="applicantToEdit.birth_place" type="text" class="form-control" :placeholder="$t('applicants.birthPlace')" />
                <label>{{ $t("applicants.birthPlace") }}</label>
              </div>
            </div>
            <div class="col-md-6">
              <div class="form-floating">
                <input v-model="applicantToEdit.school_origin" type="text" class="form-control" :placeholder="$t('applicants.school')" />
                <label>{{ $t("applicants.school") }}</label>
              </div>
            </div>
            <div class="col-12">
              <div class="form-floating">
                <textarea v-model="applicantToEdit.address" class="form-control" :placeholder="$t('applicants.address')" style="height: 80px"></textarea>
                <label>{{ $t("applicants.address") }}</label>
              </div>
            </div>
            <div class="col-12">
              <label class="form-label">{{ $t("applicants.photo") }} ({{ $t("common.photoReplace") }})</label>
              <input ref="editPhotoRef" type="file" accept="image/*" class="form-control" @change="onEditPhotoChange" />
            </div>
            <div v-if="editPhotoPreview" class="col-12 text-center">
              <img :src="editPhotoPreview" class="preview-img" alt="" />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{{ $t("common.close") }}</button>
          <button type="button" class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateApplicant">{{ $t("common.save") }}</button>
        </div>
      </div>
    </div>
  </div>

  <ImageModal id="applicantPhotoModal" :src="photoToShow.src" :title="photoToShow.title" />
</template>
