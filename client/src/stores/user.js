import { defineStore } from "pinia";
import axios from "axios";

// Store with the current user
export const useUserStore = defineStore("user", {
  state: () => ({
    loaded: false,
    isAuthenticated: false,
    id: null,
    username: "",
    isSuperuser: false,
    isStaff: false,
    users: [], // all users (the superuser needs them for the owner filter)
  }),

  actions: {
    setInfo(data) {
      this.isAuthenticated = data.is_authenticated;
      this.id = data.id ?? null;
      this.username = data.username ?? "";
      this.isSuperuser = Boolean(data.is_superuser);
      this.isStaff = Boolean(data.is_staff);
      this.loaded = true;
      if (!this.isSuperuser) {
        this.users = [];
      }
    },

    async fetchInfo() {
      const r = await axios.get("/api/users/info/");
      this.setInfo(r.data);
      if (this.isSuperuser) {
        await this.fetchUsers();
      }
    },

    async fetchUsers() {
      const r = await axios.get("/api/users/");
      this.users = r.data;
    },

    async login(username, password) {
      const r = await axios.post(
        "/api/users/login/",
        { username, password },
        { skipErrorAlert: true }, // the login page shows the error itself
      );
      this.setInfo(r.data);
      if (this.isSuperuser) {
        await this.fetchUsers();
      }
    },

    async logout() {
      await axios.post("/api/users/logout/");
      this.setInfo({ is_authenticated: false });
    },
  },
});
