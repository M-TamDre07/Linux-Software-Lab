(function attachCatalogContract(root, factory) {
  "use strict";
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.LSL_CATALOG_CONTRACT = api;
})(typeof window !== "undefined" ? window : null, function createCatalogContract() {
  "use strict";

  const TOP_LEVEL_KEYS = new Set(["schemaVersion", "catalog", "software"]);
  const CATALOG_KEYS = new Set(["name", "description", "searchMode", "pageSize", "updatedAt"]);
  const APP_KEYS = new Set([
    "id", "slug", "name", "version", "summary", "description", "category", "status", "type",
    "platforms", "tags", "keywords", "features", "detailUrl", "sourceUrl", "releaseUrl",
    "icon", "iconImage", "previewImage", "previewAlt", "updatedAt"
  ]);
  const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
  const DETAIL_PATH = /^\/software\/[a-z0-9-]+\.html$/;
  const ASSET_PATH = /^\/assets\/images\/[a-z0-9-]+\.svg$/;
  const STATUSES = new Set(["released", "testing", "planned", "archived"]);
  const TYPES = new Set(["desktop", "web", "cli", "library", "extension"]);

  const isRecord = value => value !== null && typeof value === "object" && !Array.isArray(value);
  const hasExactKeys = (value, keys) => {
    const actual = Object.keys(value);
    return actual.length === keys.size && actual.every(key => keys.has(key));
  };
  const nonEmptyText = value => typeof value === "string" && value.trim().length > 0;
  const isDate = value => {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const date = new Date(value + "T00:00:00Z");
    return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
  };
  const isStringArray = (value, minimum = 0) =>
    Array.isArray(value)
    && value.length >= minimum
    && value.every(item => nonEmptyText(item))
    && new Set(value).size === value.length;
  const isHttpsOrEmpty = value => {
    if (value === "") return true;
    if (typeof value !== "string") return false;
    try {
      const url = new URL(value);
      return url.protocol === "https:" && url.hostname.length > 0 && !url.username && !url.password;
    } catch (_) {
      return false;
    }
  };

  function validateCatalogPayload(payload) {
    const errors = [];
    const add = message => errors.push(message);

    if (!isRecord(payload)) {
      return { valid: false, errors: ["Katalog harus berupa objek JSON."] };
    }
    if (!hasExactKeys(payload, TOP_LEVEL_KEYS)) add("Struktur tingkat atas tidak sesuai dengan skema katalog v2.");
    if (payload.schemaVersion !== 2) add("schemaVersion harus bernilai 2.");

    const catalog = payload.catalog;
    if (!isRecord(catalog)) {
      add("Bagian catalog tidak tersedia atau bukan objek.");
    } else {
      if (!hasExactKeys(catalog, CATALOG_KEYS)) add("Bagian catalog memiliki field yang hilang atau tidak dikenal.");
      if (!nonEmptyText(catalog.name)) add("catalog.name wajib berupa teks.");
      if (!nonEmptyText(catalog.description)) add("catalog.description wajib berupa teks.");
      if (catalog.searchMode !== "client-side") add("catalog.searchMode harus client-side.");
      if (!Number.isInteger(catalog.pageSize) || catalog.pageSize < 1 || catalog.pageSize > 100) {
        add("catalog.pageSize harus berupa integer antara 1 dan 100.");
      }
      if (!isDate(catalog.updatedAt)) add("catalog.updatedAt harus berupa tanggal valid YYYY-MM-DD.");
    }

    if (!Array.isArray(payload.software) || payload.software.length < 1) {
      add("software harus berisi setidaknya satu aplikasi.");
      return { valid: false, errors };
    }

    const ids = new Set();
    const slugs = new Set();
    const details = new Set();

    payload.software.forEach((app, index) => {
      const at = "software[" + index + "]";
      if (!isRecord(app)) {
        add(at + " harus berupa objek.");
        return;
      }
      if (!hasExactKeys(app, APP_KEYS)) add(at + " memiliki field yang hilang atau tidak dikenal.");

      if (!nonEmptyText(app.id) || app.id.length > 64 || !SLUG.test(app.id)) add(at + ".id bukan slug yang valid.");
      if (!nonEmptyText(app.slug) || app.slug.length > 64 || !SLUG.test(app.slug)) add(at + ".slug bukan slug yang valid.");
      if (typeof app.id === "string" && typeof app.slug === "string" && app.id !== app.slug) {
        add(at + ".id dan slug harus sama.");
      }
      if (typeof app.id === "string") {
        if (ids.has(app.id)) add(at + ".id duplikat.");
        ids.add(app.id);
      }
      if (typeof app.slug === "string") {
        if (slugs.has(app.slug)) add(at + ".slug duplikat.");
        slugs.add(app.slug);
      }

      for (const field of ["name", "version", "summary", "description", "category", "icon", "previewAlt"]) {
        if (!nonEmptyText(app[field])) add(at + "." + field + " wajib berupa teks.");
      }
      if (typeof app.summary === "string" && app.summary.length > 320) add(at + ".summary melebihi 320 karakter.");
      if (typeof app.status !== "string" || !STATUSES.has(app.status)) add(at + ".status tidak dikenal.");
      if (typeof app.type !== "string" || !TYPES.has(app.type)) add(at + ".type tidak dikenal.");

      if (!isStringArray(app.platforms, 1)) add(at + ".platforms harus berupa daftar teks unik.");
      if (!isStringArray(app.tags, 1)) add(at + ".tags harus berupa daftar teks unik.");
      if (!isStringArray(app.keywords)) add(at + ".keywords harus berupa daftar teks unik.");
      if (!isStringArray(app.features)) add(at + ".features harus berupa daftar teks unik.");

      if (typeof app.slug === "string") {
        const expectedDetail = "/software/" + app.slug + ".html";
        if (app.detailUrl !== expectedDetail || !DETAIL_PATH.test(String(app.detailUrl))) {
          add(at + ".detailUrl harus menunjuk ke halaman detail kanonis untuk slug ini.");
        }
        if (typeof app.detailUrl === "string") {
          if (details.has(app.detailUrl)) add(at + ".detailUrl duplikat.");
          details.add(app.detailUrl);
        }
      }

      if (typeof app.sourceUrl !== "string" || !isHttpsOrEmpty(app.sourceUrl)) add(at + ".sourceUrl harus berupa URL HTTPS atau teks kosong.");
      if (typeof app.releaseUrl !== "string" || !isHttpsOrEmpty(app.releaseUrl)) add(at + ".releaseUrl harus berupa URL HTTPS atau teks kosong.");
      if (typeof app.iconImage !== "string" || !ASSET_PATH.test(app.iconImage)) add(at + ".iconImage harus berupa path SVG lokal.");
      if (typeof app.previewImage !== "string" || !ASSET_PATH.test(app.previewImage)) add(at + ".previewImage harus berupa path SVG lokal.");
      if (!isDate(app.updatedAt)) add(at + ".updatedAt harus berupa tanggal valid YYYY-MM-DD.");

      if (app.status === "released" && (!nonEmptyText(app.releaseUrl) || !/^https:\/\//.test(app.releaseUrl))) {
        add(at + " berstatus released tetapi tidak memiliki URL rilis HTTPS.");
      }
    });

    return { valid: errors.length === 0, errors };
  }

  return Object.freeze({ validateCatalogPayload });
});
