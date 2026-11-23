import { onBeforeMount, ref, watch } from "vue";
import axios from "axios";

import { locale } from "@/i18n";

/**
 * Shared CRUD logic for one model:
 * load the list and statistics with filters, create, update, delete, export link.
 *
 * url — the ViewSet address, e.g. "/api/applicants/"
 * initialFilters — column filters, e.g. { full_name: "", gender: "" }
 */
export function useResource(url, initialFilters = {}) {
  const items = ref([]);
  const stats = ref([]);
  const loading = ref(false);
  const filters = ref({ ...initialFilters, user: "" });

  // only filled-in filters are sent to the server
  function activeFilters() {
    return Object.fromEntries(
      Object.entries(filters.value).filter(([, value]) => value !== "" && value !== null && value !== undefined),
    );
  }

  async function fetchItems() {
    loading.value = true;
    try {
      const params = activeFilters();
      const [list, stat] = await Promise.all([
        axios.get(url, { params }),
        axios.get(`${url}stats/`, { params }),
      ]);
      items.value = list.data;
      stats.value = stat.data;
    } finally {
      loading.value = false;
    }
  }

  // reload when a filter changes (with a short delay while the user is typing)
  let timer;
  watch(
    filters,
    () => {
      clearTimeout(timer);
      timer = setTimeout(fetchItems, 300);
    },
    { deep: true },
  );

  // statistics labels come from Django in the chosen language: reload them when it changes
  watch(locale, fetchItems);

  async function create(data) {
    await axios.post(url, data);
    await fetchItems(); // reload
  }

  async function update(id, data) {
    await axios.patch(`${url}${id}/`, data);
    await fetchItems(); // reload
  }

  async function remove(id) {
    await axios.delete(`${url}${id}/`);
    await fetchItems(); // reload
  }

  // Excel/Word download link with the current filters; the file comes in the current language
  function exportUrl(type) {
    const query = new URLSearchParams({ ...activeFilters(), type });
    return `${url}export/?${query}`;
  }

  function resetFilters() {
    filters.value = { ...initialFilters, user: "" };
  }

  onBeforeMount(fetchItems);

  return { items, stats, loading, filters, fetchItems, create, update, remove, exportUrl, resetFilters };
}

/** Options for drop-down lists (faculties, programs, ...) */
export function useOptions(url) {
  const options = ref([]);
  async function load() {
    const r = await axios.get(url);
    options.value = r.data;
  }
  onBeforeMount(load);
  return { options, reload: load };
}
