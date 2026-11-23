<script setup>
import { ref } from "vue";
import { useOptions, useResource } from "@/composables/useResource";
import { useUserStore } from "@/stores/user";
import { formatNumber, t } from "@/i18n";
import StatsPanel from "@/components/StatsPanel.vue";
import TableToolbar from "@/components/TableToolbar.vue";

const user = useUserStore();
const {
  items: programs, stats, loading, filters, create, update, remove, exportUrl, resetFilters,
} = useResource("/api/programs/", { code: "", name: "", degree: "", quota: "", faculty: "" });
const { options: faculties } = useOptions("/api/faculties/");

const degrees = ["D3", "S1", "S2"];

// --- add ---
const emptyProgram = () => ({ code: "", name: "", degree: "S1", quota: 100, faculty_id: "" });
const programToAdd = ref(emptyProgram());

async function onProgramAdd() {
  await create({ ...programToAdd.value });
  programToAdd.value = emptyProgram();
}

// --- edit ---
const programToEdit = ref({});

function onProgramEditClick(program) {
  programToEdit.value = {
    id: program.id,
    code: program.code,
    name: program.name,
    degree: program.degree,
    quota: program.quota,
    faculty_id: program.faculty.id,
  };
}

async function onUpdateProgram() {
  const { id, ...data } = programToEdit.value;
  await update(id, data);
}

async function onRemoveClick(program) {
  if (!confirm(t("common.confirmDelete", { name: program.name }))) return;
  await remove(program.id);
}
</script>

<template>
  <div class="row g-4">
    <div class="col-xl-9">
      <h2 class="mb-3">{{ $t("programs.title") }}</h2>

      <form class="card card-body shadow-sm mb-3" @submit.prevent.stop="onProgramAdd">
        <div class="row g-2 align-items-center">
          <div class="col-md-2">
            <div class="form-floating">
              <input v-model="programToAdd.code" type="text" class="form-control" :placeholder="$t('programs.code')" required />
              <label>{{ $t("programs.code") }}</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-floating">
              <input v-model="programToAdd.name" type="text" class="form-control" :placeholder="$t('programs.name')" required />
              <label>{{ $t("programs.name") }}</label>
            </div>
          </div>
          <div class="col-md-2">
            <div class="form-floating">
              <select v-model="programToAdd.degree" class="form-select">
                <option v-for="d in degrees" :key="d" :value="d">{{ $t(`degree.${d}`) }}</option>
              </select>
              <label>{{ $t("programs.degree") }}</label>
            </div>
          </div>
          <div class="col-md-1">
            <div class="form-floating">
              <input v-model.number="programToAdd.quota" type="number" min="0" class="form-control" :placeholder="$t('programs.quota')" />
              <label>{{ $t("programs.quota") }}</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-floating">
              <select v-model="programToAdd.faculty_id" class="form-select" required>
                <option v-for="f in faculties" :key="f.id" :value="f.id">{{ f.name }}</option>
              </select>
              <label>{{ $t("programs.faculty") }}</label>
            </div>
          </div>
          <div class="col-auto">
            <button class="btn btn-primary"><i class="bi bi-plus-lg"></i> {{ $t("common.add") }}</button>
          </div>
        </div>
      </form>

      <TableToolbar
        v-model:owner="filters.user"
        :count="programs.length"
        :loading="loading"
        :export-url="exportUrl"
        @reset="resetFilters"
      />

      <div class="card shadow-sm table-scroll">
        <table class="table table-hover align-middle mb-0 data-table">
          <thead class="table-light">
            <tr>
              <th>{{ $t("programs.code") }}</th>
              <th>{{ $t("programs.name") }}</th>
              <th>{{ $t("programs.degree") }}</th>
              <th>{{ $t("programs.quota") }}</th>
              <th>{{ $t("programs.faculty") }}</th>
              <th v-if="user.isSuperuser">{{ $t("common.owner") }}</th>
              <th></th>
            </tr>
            <tr class="filters">
              <th><input v-model="filters.code" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th><input v-model="filters.name" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th>
                <select v-model="filters.degree" class="form-select form-select-sm">
                  <option value="">{{ $t("common.all") }}</option>
                  <option v-for="d in degrees" :key="d" :value="d">{{ $t(`degree.${d}`) }}</option>
                </select>
              </th>
              <th><input v-model="filters.quota" type="number" class="form-control form-control-sm" placeholder="=" /></th>
              <th>
                <select v-model="filters.faculty" class="form-select form-select-sm">
                  <option value="">{{ $t("common.all") }}</option>
                  <option v-for="f in faculties" :key="f.id" :value="f.id">{{ f.name }}</option>
                </select>
              </th>
              <th v-if="user.isSuperuser"></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in programs" :key="item.id">
              <td><span class="badge text-bg-primary">{{ item.code }}</span></td>
              <td>{{ item.name }}</td>
              <td>{{ $t(`degree.${item.degree}`) }}</td>
              <td>{{ formatNumber(item.quota) }}</td>
              <td>{{ item.faculty.name }}</td>
              <td v-if="user.isSuperuser"><span class="badge text-bg-light">{{ item.user ?? "—" }}</span></td>
              <td class="actions">
                <button
                  class="btn btn-sm btn-success me-1"
                  data-bs-toggle="modal"
                  data-bs-target="#editProgramModal"
                  @click="onProgramEditClick(item)"
                >
                  <i class="bi bi-pen-fill"></i>
                </button>
                <button class="btn btn-sm btn-danger" @click="onRemoveClick(item)">
                  <i class="bi bi-x-lg"></i>
                </button>
              </td>
            </tr>
            <tr v-if="!programs.length && !loading">
              <td colspan="7" class="text-center text-muted py-4">{{ $t("common.noData") }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="col-xl-3">
      <StatsPanel :stats="stats" />
    </div>
  </div>

  <div id="editProgramModal" class="modal fade" tabindex="-1">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h1 class="modal-title fs-5">{{ $t("programs.edit") }}</h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" :aria-label="$t('common.close')"></button>
        </div>
        <div class="modal-body">
          <div class="row g-2">
            <div class="col-4">
              <div class="form-floating">
                <input v-model="programToEdit.code" type="text" class="form-control" :placeholder="$t('programs.code')" />
                <label>{{ $t("programs.code") }}</label>
              </div>
            </div>
            <div class="col-8">
              <div class="form-floating">
                <input v-model="programToEdit.name" type="text" class="form-control" :placeholder="$t('programs.name')" />
                <label>{{ $t("programs.name") }}</label>
              </div>
            </div>
            <div class="col-6">
              <div class="form-floating">
                <select v-model="programToEdit.degree" class="form-select">
                  <option v-for="d in degrees" :key="d" :value="d">{{ $t(`degree.${d}`) }}</option>
                </select>
                <label>{{ $t("programs.degree") }}</label>
              </div>
            </div>
            <div class="col-6">
              <div class="form-floating">
                <input v-model.number="programToEdit.quota" type="number" min="0" class="form-control" :placeholder="$t('programs.quota')" />
                <label>{{ $t("programs.quota") }}</label>
              </div>
            </div>
            <div class="col-12">
              <div class="form-floating">
                <select v-model="programToEdit.faculty_id" class="form-select">
                  <option v-for="f in faculties" :key="f.id" :value="f.id">{{ f.name }}</option>
                </select>
                <label>{{ $t("programs.faculty") }}</label>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{{ $t("common.close") }}</button>
          <button type="button" class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdateProgram">{{ $t("common.save") }}</button>
        </div>
      </div>
    </div>
  </div>
</template>
