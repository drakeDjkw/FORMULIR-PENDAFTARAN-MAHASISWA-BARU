import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-icons/font/bootstrap-icons.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import "./assets/main.css";

import { createApp } from "vue";
import { createPinia } from "pinia";
import axios from "axios";
import Cookies from "js-cookie";

import App from "./App.vue";
import router from "./router";
import { useUserStore } from "./stores/user";
import { locale, t } from "./i18n";

const app = createApp(App);
const pinia = createPinia();
app.use(pinia);
app.use(router);

// $t("...") in every template
app.config.globalProperties.$t = t;

axios.interceptors.request.use((config) => {
  // Django needs the CSRF token for POST/PUT/PATCH/DELETE; it changes after login, so read it every time
  const token = Cookies.get("csrftoken");
  if (token) {
    config.headers["X-CSRFToken"] = token;
  }
  // ask Django to answer (errors, statistics, exports) in the chosen language
  config.headers["Accept-Language"] = locale.value;
  return config;
});

function formatError(error) {
  const data = error.response?.data;
  if (!data || typeof data === "string") {
    return error.response ? t("common.serverError", { status: error.response.status }) : error.message;
  }
  if (data.detail) {
    return data.detail;
  }
  return Object.entries(data)
    .map(([field, messages]) => `${field}: ${[].concat(messages).join(" ")}`)
    .join("\n");
}

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url ?? "";
    if ((status === 401 || status === 403) && !url.startsWith("/api/users/")) {
      // the session has ended: back to the login page
      useUserStore(pinia).setInfo({ is_authenticated: false });
      router.push({ name: "login" });
    } else if (!error.config?.skipErrorAlert) {
      alert(formatError(error));
    }
    return Promise.reject(error);
  },
);

app.mount("#app");
