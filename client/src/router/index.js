import { createRouter, createWebHistory } from "vue-router";

import { useUserStore } from "@/stores/user";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  linkActiveClass: "active",
  routes: [
    { path: "/", redirect: "/registrations" },
    { path: "/login", name: "login", component: () => import("@/views/LoginView.vue") },
    { path: "/faculties", name: "faculties", component: () => import("@/views/FacultiesView.vue") },
    { path: "/programs", name: "programs", component: () => import("@/views/ProgramsView.vue") },
    { path: "/paths", name: "paths", component: () => import("@/views/PathsView.vue") },
    { path: "/applicants", name: "applicants", component: () => import("@/views/ApplicantsView.vue") },
    { path: "/registrations", name: "registrations", component: () => import("@/views/RegistrationsView.vue") },
  ],
});

// without login, only the login page is allowed
router.beforeEach(async (to) => {
  const user = useUserStore();
  if (!user.loaded) {
    await user.fetchInfo();
  }
  if (to.name !== "login" && !user.isAuthenticated) {
    return { name: "login" };
  }
  if (to.name === "login" && user.isAuthenticated) {
    return { path: "/" };
  }
});

export default router;
