<script setup>
import { LOCALES, locale, setLocale } from "@/i18n";
</script>

<template>
  <div class="btn-group btn-group-sm" role="group" aria-label="Language">
    <button
      v-for="l in LOCALES"
      :key="l.code"
      type="button"
      class="btn"
      :class="locale === l.code ? 'btn-primary' : 'btn-outline-primary'"
      :title="l.label"
      @click="setLocale(l.code)"
    >
      {{ l.short }}
    </button>
  </div>
</template>
