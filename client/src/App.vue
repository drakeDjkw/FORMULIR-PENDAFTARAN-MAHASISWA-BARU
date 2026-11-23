<script setup>
import { useRouter } from "vue-router";
import { useUserStore } from "@/stores/user";
import LanguageSwitch from "@/components/LanguageSwitch.vue";

const user = useUserStore();
const router = useRouter();

const links = [
  { to: "/faculties", key: "nav.faculties", icon: "bi-building" },
  { to: "/programs", key: "nav.programs", icon: "bi-journal-bookmark" },
  { to: "/paths", key: "nav.paths", icon: "bi-signpost-split" },
  { to: "/applicants", key: "nav.applicants", icon: "bi-person-vcard" },
  { to: "/registrations", key: "nav.registrations", icon: "bi-clipboard-check" },
];

async function onLogout() {
  await user.logout();
  router.push({ name: "login" });
}
</script>

<template>
  <nav v-if="user.isAuthenticated" class="navbar navbar-expand bg-white border-bottom mb-4">
    <div class="container-fluid px-4 flex-wrap gap-2">
      <span class="navbar-brand"><i class="bi bi-mortarboard-fill text-primary"></i> {{ $t("app.title") }}</span>
      <ul class="navbar-nav me-auto flex-wrap">
        <li v-for="link in links" :key="link.to" class="nav-item">
          <RouterLink class="nav-link" :to="link.to">
            <i class="bi" :class="link.icon"></i> {{ $t(link.key) }}
          </RouterLink>
        </li>
      </ul>
      <LanguageSwitch />
      <span class="navbar-text mx-2">
        <i class="bi bi-person-circle"></i> {{ user.username }}
        <span v-if="user.isSuperuser" class="badge text-bg-warning">{{ $t("app.superuser") }}</span>
      </span>
      <!-- /admin/ is proxied to Django (see vite.config.js); it uses the same language cookie -->
      <a v-if="user.isStaff" href="/admin/" target="_blank" class="btn btn-outline-secondary btn-sm">
        <i class="bi bi-gear"></i> {{ $t("app.adminPanel") }}
      </a>
      <button class="btn btn-outline-danger btn-sm" @click="onLogout">
        <i class="bi bi-box-arrow-right"></i> {{ $t("app.logout") }}
      </button>
    </div>
  </nav>
  <main class="container-fluid px-4 pb-5">
    <RouterView />
  </main>
</template>
