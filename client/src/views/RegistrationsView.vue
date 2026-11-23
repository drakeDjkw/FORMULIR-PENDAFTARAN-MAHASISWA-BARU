<script setup>
import { ref } from "vue";
import axios from "axios";
import { useOptions, useResource } from "@/composables/useResource";
import { useUserStore } from "@/stores/user";
import { t } from "@/i18n";
import { toFormData } from "@/utils/formData";
import StatsPanel from "@/components/StatsPanel.vue";
import TableToolbar from "@/components/TableToolbar.vue";

const user = useUserStore();
const {
  items: registrations, stats, loading, filters, fetchItems, create, update, remove, exportUrl, resetFilters,
} = useResource("/api/registrations/", {
  number: "",
  applicant: "",
  path: "",
  first_choice: "",
  status: "",
  test_score: "",
  registered_on: "",
});
const { options: applicants } = useOptions("/api/applicants/");
const { options: paths } = useOptions("/api/paths/");
const { options: programs } = useOptions("/api/programs/");

const statuses = [
  { value: "submitted", badge: "text-bg-secondary" },
  { value: "verified", badge: "text-bg-info" },
  { value: "accepted", badge: "text-bg-success" },
  { value: "rejected", badge: "text-bg-danger" },
];
const badgeByStatus = Object.fromEntries(statuses.map((s) => [s.value, s.badge]));
const docTypes = ["diploma", "report", "id_card", "certificate", "other"];

// --- add ---
const emptyRegistration = () => ({ applicant_id: "", path_id: "", first_choice_id: "", second_choice_id: null });
const registrationToAdd = ref(emptyRegistration());

async function onRegistrationAdd() {
  await create({ ...registrationToAdd.value });
  registrationToAdd.value = emptyRegistration();
}

// --- edit ---
const registrationToEdit = ref({});

function onRegistrationEditClick(registration) {
  registrationToEdit.value = {
    id: registration.id,
    number: registration.number,
    applicant_id: registration.applicant.id,
    path_id: registration.path.id,
    first_choice_id: registration.first_choice.id,
    second_choice_id: registration.second_choice?.id ?? null,
    status: registration.status,
    test_score: registration.test_score,
  };
}

async function onUpdateRegistration() {
  const { id, number, ...data } = registrationToEdit.value;
  if (data.test_score === "") data.test_score = null;
  await update(id, data);
}

async function onRemoveClick(registration) {
  if (!confirm(t("registrations.confirmDelete", { number: registration.number }))) return;
  await remove(registration.id);
}

// --- documents album of a registration ---
const albumRegistration = ref(null);
const documents = ref([]);
const currentDocument = ref(null);
const albumFilesRef = ref();
const albumType = ref("diploma");
const albumCaption = ref("");
const uploading = ref(false);

async function fetchDocuments() {
  const r = await axios.get("/api/documents/", { params: { registration: albumRegistration.value.id } });
  documents.value = r.data;
  if (!documents.value.some((d) => d.id === currentDocument.value?.id)) {
    currentDocument.value = documents.value[0] ?? null;
  }
}

async function onAlbumClick(registration) {
  albumRegistration.value = registration;
  documents.value = [];
  currentDocument.value = null;
  await fetchDocuments();
}

async function onDocumentsUpload() {
  const files = [...albumFilesRef.value.files];
  if (!files.length) return;
  uploading.value = true;
  try {
    // one file = one POST; several files can be chosen at once
    for (const file of files) {
      await axios.post(
        "/api/documents/",
        toFormData(
          { registration: albumRegistration.value.id, doc_type: albumType.value, caption: albumCaption.value },
          { image: file },
        ),
      );
    }
  } finally {
    uploading.value = false;
    albumFilesRef.value.value = "";
    albumCaption.value = "";
  }
  await fetchDocuments();
  await fetchItems(); // refresh the documents count in the table
}

async function onDocumentRemove(document) {
  if (!confirm(t("documents.confirmDelete"))) return;
  await axios.delete(`/api/documents/${document.id}/`);
  await fetchDocuments();
  await fetchItems();
}

function showDocument(step) {
  const index = documents.value.findIndex((d) => d.id === currentDocument.value?.id);
  const next = (index + step + documents.value.length) % documents.value.length;
  currentDocument.value = documents.value[next];
}
</script>

<template>
  <div class="row g-4">
    <div class="col-xl-9">
      <h2 class="mb-3">{{ $t("registrations.title") }}</h2>

      <form class="card card-body shadow-sm mb-3" @submit.prevent.stop="onRegistrationAdd">
        <div class="row g-2 align-items-center">
          <div class="col-md-3">
            <div class="form-floating">
              <select v-model="registrationToAdd.applicant_id" class="form-select" required>
                <option v-for="a in applicants" :key="a.id" :value="a.id">{{ a.full_name }}</option>
              </select>
              <label>{{ $t("registrations.applicant") }}</label>
            </div>
          </div>
          <div class="col-md-2">
            <div class="form-floating">
              <select v-model="registrationToAdd.path_id" class="form-select" required>
                <option v-for="p in paths" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
              <label>{{ $t("registrations.path") }}</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-floating">
              <select v-model="registrationToAdd.first_choice_id" class="form-select" required>
                <option v-for="p in programs" :key="p.id" :value="p.id">{{ p.code }} — {{ p.name }}</option>
              </select>
              <label>{{ $t("registrations.firstChoice") }}</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-floating">
              <select v-model="registrationToAdd.second_choice_id" class="form-select">
                <option :value="null">{{ $t("registrations.noSecondChoice") }}</option>
                <option v-for="p in programs" :key="p.id" :value="p.id">{{ p.code }} — {{ p.name }}</option>
              </select>
              <label>{{ $t("registrations.secondChoice") }}</label>
            </div>
          </div>
          <div class="col-auto">
            <button class="btn btn-primary"><i class="bi bi-plus-lg"></i> {{ $t("registrations.register") }}</button>
          </div>
        </div>
      </form>

      <TableToolbar
        v-model:owner="filters.user"
        :count="registrations.length"
        :loading="loading"
        :export-url="exportUrl"
        @reset="resetFilters"
      />

      <div class="card shadow-sm table-scroll">
        <table class="table table-hover align-middle mb-0 data-table">
          <thead class="table-light">
            <tr>
              <th>{{ $t("registrations.number") }}</th>
              <th>{{ $t("registrations.applicant") }}</th>
              <th>{{ $t("registrations.path") }}</th>
              <th>{{ $t("registrations.firstChoice") }}</th>
              <th>{{ $t("registrations.secondChoice") }}</th>
              <th>{{ $t("registrations.status") }}</th>
              <th>{{ $t("registrations.score") }}</th>
              <th>{{ $t("registrations.registeredOn") }}</th>
              <th v-if="user.isSuperuser">{{ $t("common.owner") }}</th>
              <th></th>
            </tr>
            <tr class="filters">
              <th><input v-model="filters.number" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th><input v-model="filters.applicant" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th>
                <select v-model="filters.path" class="form-select form-select-sm">
                  <option value="">{{ $t("common.all") }}</option>
                  <option v-for="p in paths" :key="p.id" :value="p.id">{{ p.name }}</option>
                </select>
              </th>
              <th>
                <select v-model="filters.first_choice" class="form-select form-select-sm">
                  <option value="">{{ $t("common.all") }}</option>
                  <option v-for="p in programs" :key="p.id" :value="p.id">{{ p.code }} — {{ p.name }}</option>
                </select>
              </th>
              <th></th>
              <th>
                <select v-model="filters.status" class="form-select form-select-sm">
                  <option value="">{{ $t("common.all") }}</option>
                  <option v-for="s in statuses" :key="s.value" :value="s.value">{{ $t(`status.${s.value}`) }}</option>
                </select>
              </th>
              <th><input v-model="filters.test_score" type="number" min="0" max="100" class="form-control form-control-sm" placeholder="=" /></th>
              <th><input v-model="filters.registered_on" type="date" class="form-control form-control-sm" /></th>
              <th v-if="user.isSuperuser"></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in registrations" :key="item.id">
              <td class="text-nowrap"><code>{{ item.number }}</code></td>
              <td>{{ item.applicant.full_name }}</td>
              <td>{{ item.path.name }}</td>
              <td>{{ item.first_choice.name }}</td>
              <td>
                <template v-if="item.second_choice">{{ item.second_choice.name }}</template>
                <span v-else class="text-muted">—</span>
              </td>
              <td><span class="badge" :class="badgeByStatus[item.status]">{{ $t(`status.${item.status}`) }}</span></td>
              <td>{{ item.test_score ?? "—" }}</td>
              <td class="text-nowrap">{{ item.registered_on }}</td>
              <td v-if="user.isSuperuser"><span class="badge text-bg-light">{{ item.user ?? "—" }}</span></td>
              <td class="actions">
                <button
                  class="btn btn-sm btn-outline-primary me-1"
                  :title="$t('registrations.documents')"
                  data-bs-toggle="modal"
                  data-bs-target="#documentsModal"
                  @click="onAlbumClick(item)"
                >
                  <i class="bi bi-file-earmark-image"></i>
                  <span v-if="item.documents_count" class="ms-1">{{ item.documents_count }}</span>
                </button>
                <button
                  class="btn btn-sm btn-success me-1"
                  data-bs-toggle="modal"
                  data-bs-target="#editRegistrationModal"
                  @click="onRegistrationEditClick(item)"
                >
                  <i class="bi bi-pen-fill"></i>
                </button>
                <button class="btn btn-sm btn-danger" @click="onRemoveClick(item)">
                  <i class="bi bi-x-lg"></i>
                </button>
              </td>
            </tr>
            <tr v-if="!registrations.length && !loading">
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

  <div id="editRegistrationModal" class="modal fade" tabindex="-1">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h1 class="modal-title fs-5">{{ $t("registrations.edit") }} <code>{{ registrationToEdit.number }}</code></h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" :aria-label="$t('common.close')"></button>
        </div>
        <div class="modal-body">
          <div class="row g-2">
            <div class="col-12">
              <div class="form-floating">
                <select v-model="registrationToEdit.applicant_id" class="form-select">
                  <option v-for="a in applicants" :key="a.id" :value="a.id">{{ a.full_name }}</option>
                </select>
                <label>{{ $t("registrations.applicant") }}</label>
              </div>
            </div>
            <div class="col-12">
              <div class="form-floating">
                <select v-model="registrationToEdit.path_id" class="form-select">
                  <option v-for="p in paths" :key="p.id" :value="p.id">{{ p.name }}</option>
                </select>
                <label>{{ $t("registrations.path") }}</label>
              </div>
            </div>
            <div class="col-12">
              <div class="form-floating">
                <select v-model="registrationToEdit.first_choice_id" class="form-select">
                  <option v-for="p in programs" :key="p.id" :value="p.id">{{ p.code }} — {{ p.name }}</option>
                </select>
                <label>{{ $t("registrations.firstChoice") }}</label>
              </div>
            </div>
            <div class="col-12">
              <div class="form-floating">
                <select v-model="registrationToEdit.second_choice_id" class="form-select">
                  <option :value="null">{{ $t("registrations.noSecondChoice") }}</option>
                  <option v-for="p in programs" :key="p.id" :value="p.id">{{ p.code }} — {{ p.name }}</option>
                </select>
                <label>{{ $t("registrations.secondChoice") }}</label>
              </div>
            </div>
            <div class="col-7">
              <div class="form-floating">
                <select v-model="registrationToEdit.status" class="form-select">
                  <option v-for="s in statuses" :key="s.value" :value="s.value">{{ $t(`status.${s.value}`) }}</option>
                </select>
                <label>{{ $t("registrations.status") }}</label>
              </div>
            </div>
            <div class="col-5">
              <div class="form-floating">
                <input v-model.number="registrationToEdit.test_score" type="number" min="0" max="100" class="form-control" :placeholder="$t('registrations.score')" />
                <label>{{ $t("registrations.score") }}</label>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{{ $t("common.close") }}</button>
          <button type="button" class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateRegistration">{{ $t("common.save") }}</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Documents album of a registration -->
  <div id="documentsModal" class="modal fade" tabindex="-1">
    <div class="modal-dialog modal-xl modal-dialog-scrollable">
      <div class="modal-content">
        <div class="modal-header">
          <h1 class="modal-title fs-5">
            <i class="bi bi-file-earmark-image"></i>
            {{ $t("documents.title") }}<template v-if="albumRegistration">:
              <code>{{ albumRegistration.number }}</code> — {{ albumRegistration.applicant.full_name }}</template>
          </h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" :aria-label="$t('common.close')"></button>
        </div>
        <div class="modal-body">
          <form class="row g-2 align-items-center mb-3" @submit.prevent.stop="onDocumentsUpload">
            <div class="col-md-4">
              <input ref="albumFilesRef" type="file" accept="image/*" multiple class="form-control" required />
            </div>
            <div class="col-md-3">
              <select v-model="albumType" class="form-select" :title="$t('documents.type')">
                <option v-for="d in docTypes" :key="d" :value="d">{{ $t(`docType.${d}`) }}</option>
              </select>
            </div>
            <div class="col-md-3">
              <input v-model="albumCaption" type="text" class="form-control" :placeholder="$t('documents.caption')" />
            </div>
            <div class="col-auto">
              <button class="btn btn-primary" :disabled="uploading">
                <span v-if="uploading" class="spinner-border spinner-border-sm"></span>
                <i v-else class="bi bi-upload"></i> {{ $t("documents.upload") }}
              </button>
            </div>
          </form>

          <div v-if="!documents.length" class="text-center text-muted py-5">
            <i class="bi bi-file-earmark fs-1"></i>
            <div>{{ $t("documents.empty") }}</div>
          </div>

          <template v-else>
            <!-- the selected document, large -->
            <div v-if="currentDocument" class="text-center mb-3">
              <img :src="currentDocument.image" class="img-fluid album-main" :alt="currentDocument.caption" />
              <div class="mt-2 d-flex justify-content-center align-items-center gap-2 flex-wrap">
                <button class="btn btn-sm btn-outline-secondary" @click="showDocument(-1)">
                  <i class="bi bi-chevron-left"></i>
                </button>
                <span class="badge text-bg-primary">{{ $t(`docType.${currentDocument.doc_type}`) }}</span>
                <span class="text-muted">{{ currentDocument.caption || $t("documents.untitled") }}</span>
                <button class="btn btn-sm btn-outline-secondary" @click="showDocument(1)">
                  <i class="bi bi-chevron-right"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger ms-3" @click="onDocumentRemove(currentDocument)">
                  <i class="bi bi-trash"></i> {{ $t("documents.delete") }}
                </button>
              </div>
            </div>

            <div class="row g-2">
              <div v-for="doc in documents" :key="doc.id" class="col-3 col-md-2 text-center">
                <img
                  :src="doc.image"
                  class="album-thumb"
                  :class="{ selected: doc.id === currentDocument?.id }"
                  :alt="doc.caption"
                  @click="currentDocument = doc"
                />
                <div class="small text-muted text-truncate">{{ $t(`docType.${doc.doc_type}`) }}</div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
