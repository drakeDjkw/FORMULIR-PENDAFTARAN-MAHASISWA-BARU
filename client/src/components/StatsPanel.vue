<script setup>
import { formatNumber } from "@/i18n";

defineProps({
  stats: { type: Array, default: () => [] },
});

function show(value) {
  if (value === null || value === undefined) return "—";
  return typeof value === "number" ? formatNumber(value) : value;
}
</script>

<template>
  <div class="card shadow-sm">
    <div class="card-header"><i class="bi bi-bar-chart-line"></i> {{ $t("common.statistics") }}</div>
    <ul class="list-group list-group-flush">
      <li
        v-for="item in stats"
        :key="item.label"
        class="list-group-item d-flex justify-content-between align-items-center gap-2"
      >
        <span>{{ item.label }}</span>
        <strong class="text-nowrap">{{ show(item.value) }}</strong>
      </li>
    </ul>
    <div class="card-footer text-muted small">{{ $t("common.statsFollowFilters") }}</div>
  </div>
</template>
