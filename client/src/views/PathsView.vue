<script setup>
import { ref } from "vue";
import { useResource } from "@/composables/useResource";
import { useUserStore } from "@/stores/user";
import { formatNumber, t } from "@/i18n";
import StatsPanel from "@/components/StatsPanel.vue";
import TableToolbar from "@/components/TableToolbar.vue";

const user = useUserStore();
const {
  items: paths, stats, loading, filters, create, update, remove, exportUrl, resetFilters,
} = useResource("/api/paths/", { name: "", description: "", fee: "" });

// empty date inputs are sent as null, not ""
function cleanDates(data) {
  return { ...data, opens_on: data.opens_on || null, closes_on: data.closes_on || null };
}

// --- add ---
const emptyPath = () => ({ name: "", description: "", fee: 0, opens_on: "", closes_on: "" });
const pathToAdd = ref(emptyPath());

async function onPathAdd() {
  await create(cleanDates(pathToAdd.value));
  pathToAdd.value = emptyPath();
}

// --- edit ---
const pathToEdit = ref({});

function onPathEditClick(path) {
  pathToEdit.value = {
    id: path.id,
    name: path.name,
    description: path.description,
    fee: path.fee,
    opens_on: path.opens_on ?? "",
    closes_on: path.closes_on ?? "",
  };
}

async function onUpdatePath() {
  const { id, ...data } = pathToEdit.value;
  await update(id, cleanDates(data));
}

async function onRemoveClick(path) {
  if (!confirm(t("common.confirmDelete", { name: path.name }))) return;
  await remove(path.id);
}
</script>

<template>
  <div class="row g-4">
    <div class="col-xl-9">
      <h2 class="mb-3">{{ $t("paths.title") }}</h2>

      <form class="card card-body shadow-sm mb-3" @submit.prevent.stop="onPathAdd">
        <div class="row g-2 align-items-center">
          <div class="col-md-2">
            <div class="form-floating">
              <input v-model="pathToAdd.name" type="text" class="form-control" :placeholder="$t('paths.name')" required />
              <label>{{ $t("paths.name") }}</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-floating">
              <input v-model="pathToAdd.description" type="text" class="form-control" :placeholder="$t('paths.description')" />
              <label>{{ $t("paths.description") }}</label>
            </div>
          </div>
          <div class="col-md-2">
            <div class="form-floating">
              <input v-model.number="pathToAdd.fee" type="number" min="0" step="1000" class="form-control" :placeholder="$t('paths.fee')" />
              <label>{{ $t("paths.fee") }}</label>
            </div>
          </div>
          <div class="col-md-2">
            <div class="form-floating">
              <input v-model="pathToAdd.opens_on" type="date" class="form-control" />
              <label>{{ $t("paths.opensOn") }}</label>
            </div>
          </div>
          <div class="col-md-2">
            <div class="form-floating">
              <input v-model="pathToAdd.closes_on" type="date" class="form-control" />
              <label>{{ $t("paths.closesOn") }}</label>
            </div>
          </div>
          <div class="col-auto">
            <button class="btn btn-primary"><i class="bi bi-plus-lg"></i> {{ $t("common.add") }}</button>
          </div>
        </div>
      </form>

      <TableToolbar
        v-model:owner="filters.user"
        :count="paths.length"
        :loading="loading"
        :export-url="exportUrl"
        @reset="resetFilters"
      />

      <div class="card shadow-sm table-scroll">
        <table class="table table-hover align-middle mb-0 data-table">
          <thead class="table-light">
            <tr>
              <th>{{ $t("paths.name") }}</th>
              <th>{{ $t("paths.description") }}</th>
              <th>{{ $t("paths.fee") }}</th>
              <th>{{ $t("paths.opensOn") }}</th>
              <th>{{ $t("paths.closesOn") }}</th>
              <th v-if="user.isSuperuser">{{ $t("common.owner") }}</th>
              <th></th>
            </tr>
            <tr class="filters">
              <th><input v-model="filters.name" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th><input v-model="filters.description" class="form-control form-control-sm" :placeholder="$t('common.filter')" /></th>
              <th><input v-model="filters.fee" type="number" class="form-control form-control-sm" placeholder="=" /></th>
              <th></th>
              <th></th>
              <th v-if="user.isSuperuser"></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in paths" :key="item.id">
              <td><strong>{{ item.name }}</strong></td>
              <td class="text-muted">{{ item.description }}</td>
              <td>
                <span v-if="item.fee === 0" class="badge text-bg-success">{{ $t("paths.free") }}</span>
                <template v-else>{{ formatNumber(item.fee) }}</template>
              </td>
              <td>{{ item.opens_on ?? "—" }}</td>
              <td>{{ item.closes_on ?? "—" }}</td>
              <td v-if="user.isSuperuser"><span class="badge text-bg-light">{{ item.user ?? "—" }}</span></td>
              <td class="actions">
                <button
                  class="btn btn-sm btn-success me-1"
                  data-bs-toggle="modal"
                  data-bs-target="#editPathModal"
                  @click="onPathEditClick(item)"
                >
                  <i class="bi bi-pen-fill"></i>
                </button>
                <button class="btn btn-sm btn-danger" @click="onRemoveClick(item)">
                  <i class="bi bi-x-lg"></i>
                </button>
              </td>
            </tr>
            <tr v-if="!paths.length && !loading">
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

  <div id="editPathModal" class="modal fade" tabindex="-1">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h1 class="modal-title fs-5">{{ $t("paths.edit") }}</h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" :aria-label="$t('common.close')"></button>
        </div>
        <div class="modal-body">
          <div class="row g-2">
            <div class="col-12">
              <div class="form-floating">
                <input v-model="pathToEdit.name" type="text" class="form-control" :placeholder="$t('paths.name')" />
                <label>{{ $t("paths.name") }}</label>
              </div>
            </div>
            <div class="col-12">
              <div class="form-floating">
                <textarea v-model="pathToEdit.description" class="form-control" :placeholder="$t('paths.description')" style="height: 90px"></textarea>
                <label>{{ $t("paths.description") }}</label>
              </div>
            </div>
            <div class="col-12">
              <div class="form-floating">
                <input v-model.number="pathToEdit.fee" type="number" min="0" step="1000" class="form-control" :placeholder="$t('paths.fee')" />
                <label>{{ $t("paths.fee") }}</label>
              </div>
            </div>
            <div class="col-6">
              <div class="form-floating">
                <input v-model="pathToEdit.opens_on" type="date" class="form-control" />
                <label>{{ $t("paths.opensOn") }}</label>
              </div>
            </div>
            <div class="col-6">
              <div class="form-floating">
                <input v-model="pathToEdit.closes_on" type="date" class="form-control" />
                <label>{{ $t("paths.closesOn") }}</label>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{{ $t("common.close") }}</button>
          <button type="button" class="btn btn-primary" data-bs-dismiss="modal" @click="onUpdatePath">{{ $t("common.save") }}</button>
        </div>
      </div>
    </div>
  </div>
</template>
