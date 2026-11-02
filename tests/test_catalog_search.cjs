const test = require("node:test");
const assert = require("node:assert/strict");
const search = require("../public/assets/js/catalog-search.js");

const apps = [
  {
    id: "paketscope",
    slug: "paketscope",
    name: "PaketScope",
    summary: "Pengelola aplikasi Linux dan inventaris paket.",
    description: "Memeriksa asal paket dan detail aplikasi desktop.",
    category: "Pengelolaan aplikasi",
    status: "testing",
    version: "3.0.0.dev5",
    type: "desktop",
    tags: ["Python", "APT / dpkg", "Flatpak"],
    keywords: ["inventaris paket", "pembaruan", "privasi"],
    features: ["Pemeriksaan pembaruan sesuai permintaan", "Ekspor CSV"],
    platforms: ["Debian 13"]
  },
  {
    id: "sorot",
    slug: "sorot",
    name: "Sorot",
    summary: "Teleprompter desktop Linux dengan mode cermin.",
    description: "Mengelola naskah untuk presentasi dan rekaman video.",
    category: "Produktivitas",
    status: "testing",
    version: "0.7.3 Beta",
    type: "desktop",
    tags: ["Teleprompter", "Overlay", "Mirror mode", "Wayland"],
    keywords: ["membaca naskah", "presentasi"],
    features: ["Mode cermin", "Kontrol pemutaran"],
    platforms: ["Debian 13", "Linux desktop"]
  }
].map(app => ({ ...app, index: search.createIndex(app) }));

test("search tolerates a two-character typo in a product name", () => {
  assert.equal(search.search(apps[0].index, "PaketScpoe").matches, true);
});

test("search expands Indonesian and English synonyms", () => {
  assert.equal(search.search(apps[0].index, "pembaruan").matches, true);
  assert.equal(search.search(apps[1].index, "telepromter").matches, true);
});

test("field operators constrain results to requested metadata", () => {
  assert.equal(search.search(apps[0].index, "tag:apt").matches, true);
  assert.equal(search.search(apps[1].index, "nama:Sorot").matches, true);
  assert.equal(search.search(apps[1].index, "kategori:pengelolaan").matches, false);
});

test("negative field operators exclude matching records", () => {
  assert.equal(search.search(apps[1].index, "teleprompter -tag:wayland").matches, false);
  assert.equal(search.search(apps[0].index, "teleprompter -tag:wayland").matches, false);
});

test("quoted phrases are preserved as one search term", () => {
  const parsed = search.parseQuery('nama:"PaketScope" -tag:flatpak');
  assert.deepEqual(parsed, [
    { field: "name", value: "paketscope", negative: false },
    { field: "tags", value: "flatpak", negative: true }
  ]);
});
