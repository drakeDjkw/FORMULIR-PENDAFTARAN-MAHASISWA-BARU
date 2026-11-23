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
  items: faculties, stats, loading, filters, create, update, remove, exportUrl, resetFilters,
} = useResource("/api/faculties/", { code: "", name: "", description: "" });

// --- add ---
const emptyFaculty = () => ({ code: "", name: "", description: "" });
const facultyToAdd = ref(emptyFaculty());
const addLogoRef = ref(); // the <input type="file"> of the add form
const addLogoPreview = ref("");

function onAddLogoChange() {
  const file = addLogoRef.value.files[0];
  addLogoPreview.value = file ? URL.createObjectURL(file) : "";
}

async function onFacultyAdd() {
  await create(toFormData(facultyToAdd.value, { logo: addLogoRef.value.files[0] }));
  facultyToAdd.value = emptyFaculty();
  addLogoRef.value.value = "";
  addLogoPreview.value = "";
}

// --- edit ---
const facultyToEdit = ref({});
const editLogoRef = ref();
const editLogoPreview = ref("");

function onFacultyEditClick(faculty) {
  facultyToEdit.value = { id: faculty.id, code: faculty.code, name: faculty.name, description: faculty.description };
  editLogoPreview.value = faculty.logo ?? "";
  editLogoRef.value.value = "";
}

function onEditLogoChange() {
  const file = editLogoRef.value.files[0];
  if (file) editLogoPreview.value = URL.createObjectURL(file);
}

async function onUpdateFaculty() {
  const { id, ...data } = facultyToEdit.value;
  await update(id, toFormData(data, { logo: editLogoRef.value.files[0] }));
}

async function onRemoveClick(faculty) {
  if (!confirm(t("common.confirmDelete", { name: faculty.name }))) return;
  await remove(faculty.id);
}

// --- view the logo large ---
const logoToShow = ref({ src: "", title: "" });
function onLogoClick(faculty) {
  logoToShow.value = { src: faculty.logo, title: faculty.name };
}
</script>

<template>
  <div class="row g-4">
    <div class="col-xl-9">
      <h2 class="mb-3">{{ $t("faculties.title") }}</h2>

      <form class="card card-body shadow-sm mb-3" @submit.prevent.stop="onFacultyAdd">
        <div class="row g-2 align-items-center">
          <div class="col-md-2">
            <div class="form-floating">
              <input v-model="facultyToAdd.code" type="text" class="form-control" :placeholder="$t('faculties.code')" required />
              <label>{{ $t("faculties.code") }}</label>
            </div>
          </div>
          <div class="col-md-4">
            <div class="form-floating">
              <input v-model="facultyToAdd.name" type="text" class="form-control" :placeholder="$t('faculties.name')" required />
              <label>{{ $t("faculties.name") }}</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-floating">
              <input v-model="facultyToAdd.description" type="text" class="form-control" :placeholder="$t('faculties.description')" />
              <label>{{ $t("faculties.description") }}</label>
            </div>
          </div>
          <div class="col-md-2">
            <input ref="addLogoRef" type="file" accept="image/*" class="form-control" :title="$t('faculties.logo')" @change="onAddLogoChange" />
          </div>
          <div v-if="addLogoPreview" class="col-auto">
            <img :src="addLogoPreview" class="thumb" alt="" />
          </div>
          <div class="col-auto">
            <button class="btn btn-primary"><i class="bi bi-plus-lg"></i> {{ $t("common.add") }}</button>
          </div>
        </div>
      </form>

      <TableToolbar
        v-model:owner="filters.user"
        :count="faculties.length"
        :loading="loading"
        :export-url="exportUrl"
        @reset="resetFilters"
      />

      <div class="card shadow-sm table-scroll">
        <table class="table table-hover align-middle mb-0 data-table">
          <thead class="table-light">
            <tr>
              <th>{{ $t("faculties.logo") }}</th>
              <th>{{ $t("faculties.code") }}</th>
              <th>{{ $t("faculties.name") }}</th>
              <th>{{ $t("faculties.description") }}</th>
              <th v-if="user.isSuperuser">{{ $t("common.owner") }}</th>
              <th></th>
            </tr>
            <tr class="filters">
              <th></th>
              <th><input v-model="filters.code" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th><input v-model="filters.name" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th><input v-model="filters.description" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th v-if="user.isSuperuser"></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in faculties" :key="item.id">
              <td>
                <img
                  v-if="item.logo"
                  :src="item.logo"
                  class="thumb"
                  alt=""
                  data-bs-toggle="modal"
                  data-bs-target="#facultyLogoModal"
                  @click="onLogoClick(item)"
                />
                <span v-else class="thumb-placeholder"><i class="bi bi-building"></i></span>
              </td>
              <td><span class="badge text-bg-primary">{{ item.code }}</span></td>
              <td>{{ item.name }}</td>
              <td class="text-muted">{{ item.description }}</td>
              <td v-if="user.isSuperuser"><span class="badge text-bg-light">{{ item.user ?? "—" }}</span></td>
              <td class="actions">
                <button
                  class="btn btn-sm btn-success me-1"
                  data-bs-toggle="modal"
                  data-bs-target="#editFacultyModal"
                  @click="onFacultyEditClick(item)"
                >
                  <i class="bi bi-pen-fill"></i>
                </button>
                <button class="btn btn-sm btn-danger" @click="onRemoveClick(item)">
                  <i class="bi bi-x-lg"></i>
                </button>
              </td>
            </tr>
            <tr v-if="!faculties.length && !loading">
              <td colspan="6" class="text-center text-muted py-4">{{ $t("common.noData") }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="col-xl-3">
      <StatsPanel :stats="stats" />
    </div>
  </div>

  <div id="editFacultyModal" class="modal fade" tabindex="-1">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h1 class="modal-title fs-5">{{ $t("faculties.edit") }}</h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" :aria-label="$t('common.close')"></button>
        </div>
        <div class="modal-body">
          <div class="row g-2">
            <div class="col-4">
              <div class="form-floating">
                <input v-model="facultyToEdit.code" type="text" class="form-control" :placeholder="$t('faculties.code')" />
                <label>{{ $t("faculties.code") }}</label>
              </div>
            </div>
            <div class="col-8">
              <div class="form-floating">
                <input v-model="facultyToEdit.name" type="text" class="form-control" :placeholder="$t('faculties.name')" />
                <label>{{ $t("faculties.name") }}</label>
              </div>
            </div>
            <div class="col-12">
              <div class="form-floating">
                <textarea v-model="facultyToEdit.description" class="form-control" :placeholder="$t('faculties.description')" style="height: 90px"></textarea>
                <label>{{ $t("faculties.description") }}</label>
              </div>
            </div>
            <div class="col-12">
              <label class="form-label">{{ $t("faculties.logo") }} ({{ $t("common.photoReplace") }})</label>
              <input ref="editLogoRef" type="file" accept="image/*" class="form-control" @change="onEditLogoChange" />
            </div>
            <div v-if="editLogoPreview" class="col-12 text-center">
              <img :src="editLogoPreview" class="preview-img" alt="" />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{{ $t("common.close") }}</button>
          <button type="button" class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateFaculty">{{ $t("common.save") }}</button>
        </div>
      </div>
    </div>
  </div>

  <ImageModal id="facultyLogoModal" :src="logoToShow.src" :title="logoToShow.title" />
</template>
