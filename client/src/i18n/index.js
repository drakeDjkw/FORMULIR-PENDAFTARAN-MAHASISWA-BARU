import { ref } from "vue";
import Cookies from "js-cookie";

import en from "./en.js";
import id from "./id.js";

// Simple translation module: two dictionaries and a reactive current language.
const messages = { en, id };

export const LOCALES = [
  { code: "en", label: "English", short: "EN" },
  { code: "id", label: "Bahasa Indonesia", short: "ID" },
];

function savedLocale() {
  try {
    return localStorage.getItem("locale");
  } catch {
    return null; // private window or blocked storage
  }
}

export const locale = ref(savedLocale() === "id" ? "id" : "en");

function lookup(dict, key) {
  return key.split(".").reduce((node, part) => node?.[part], dict);
}

/**
 * t("nav.faculties") → "Faculties" / "Fakultas"
 * t("common.records", { n: 5 }) → "5 records" / "5 data"
 * Because it reads locale.value, every template that calls it re-renders when the language changes.
 */
export function t(key, params = {}) {
  const text = lookup(messages[locale.value], key) ?? lookup(messages.en, key) ?? key;
  return String(text).replace(/\{(\w+)\}/g, (_, name) => params[name] ?? `{${name}}`);
}

/** Numbers in the local style: 200,000 (en) / 200.000 (id) */
export function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "—";
  return new Intl.NumberFormat(locale.value === "id" ? "id-ID" : "en-US").format(value);
}

export function setLocale(code) {
  locale.value = code;
  try {
    localStorage.setItem("locale", code);
  } catch {
    // nothing to do: the language just won't be remembered
  }
  // Django's LocaleMiddleware reads this cookie, so the API, the admin and the exports switch too
  Cookies.set("django_language", code, { path: "/", sameSite: "Lax" });
  document.documentElement.lang = code;
}

// apply the saved language to the cookie and <html lang> on start
setLocale(locale.value);
