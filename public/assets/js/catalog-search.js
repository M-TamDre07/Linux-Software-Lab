(function attachCatalogSearch(root, factory) {
  "use strict";
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.LSL_CATALOG_SEARCH = api;
})(typeof window !== "undefined" ? window : null, function createCatalogSearch() {
  "use strict";

  const FIELD_ALIASES = Object.freeze({
    nama: "name", name: "name", id: "id",
    tag: "tags", tags: "tags", label: "tags",
    kategori: "category", category: "category",
    platform: "platforms", distro: "platforms", os: "platforms",
    status: "status", versi: "version", version: "version",
    jenis: "type", type: "type", fitur: "features", feature: "features"
  });

  const SYNONYMS = Object.freeze({
    paket: ["package", "apt", "dpkg", "software", "aplikasi"],
    package: ["paket", "apt", "dpkg", "software"],
    instalasi: ["install", "installer", "pemasangan", "pasang"],
    install: ["instalasi", "installer", "pemasangan", "pasang"],
    installer: ["instalasi", "install", "pemasangan"],
    pembaruan: ["update", "upgrade", "perbarui"],
    update: ["pembaruan", "upgrade", "perbarui"],
    upgrade: ["pembaruan", "update"],
    inventaris: ["inventory", "daftar aplikasi", "paket"],
    inventory: ["inventaris", "daftar aplikasi"],
    teleprompter: ["prompter", "naskah", "presentasi", "gulir teks"],
    telepromter: ["teleprompter", "prompter", "naskah"],
    prompter: ["teleprompter", "naskah", "presentasi"],
    mirror: ["cermin", "flip", "balik"],
    cermin: ["mirror", "flip", "balik"],
    jaringan: ["network", "wifi", "wi-fi"],
    network: ["jaringan", "wifi", "wi-fi"],
    desain: ["design", "poster", "grafis"],
    design: ["desain", "poster", "grafis"],
    cadangan: ["backup", "restore", "pemulihan"],
    backup: ["cadangan", "restore", "pemulihan"],
    keamanan: ["security", "privasi", "permission"],
    security: ["keamanan", "privasi", "permission"]
  });

  const normalise = value => String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("id-ID")
    .trim();

  function words(value) {
    return normalise(value).split(/[^a-z0-9.+-]+/).filter(Boolean);
  }

  function boundedDistance(left, right, limit) {
    if (Math.abs(left.length - right.length) > limit) return limit + 1;
    let previous = Array.from({ length: right.length + 1 }, (_, i) => i);
    for (let i = 1; i <= left.length; i += 1) {
      const current = [i];
      let rowMinimum = i;
      for (let j = 1; j <= right.length; j += 1) {
        const cost = left[i - 1] === right[j - 1] ? 0 : 1;
        current[j] = Math.min(
          current[j - 1] + 1,
          previous[j] + 1,
          previous[j - 1] + cost
        );
        rowMinimum = Math.min(rowMinimum, current[j]);
      }
      if (rowMinimum > limit) return limit + 1;
      previous = current;
    }
    return previous[right.length];
  }

  function parseQuery(value) {
    const source = String(value ?? "");
    const parts = source.match(/(?:[^\s"]+|"[^"]*")+/g) || [];
    return parts.map(part => {
      let token = part;
      const negative = token.startsWith("-");
      if (negative) token = token.slice(1);
      const separator = token.indexOf(":");
      let field = "all";
      if (separator > 0) {
        const candidate = normalise(token.slice(0, separator));
        if (FIELD_ALIASES[candidate]) {
          field = FIELD_ALIASES[candidate];
          token = token.slice(separator + 1);
        }
      }
      token = normalise(token.replace(/^"+|"+$/g, ""));
      return token ? { field, value: token, negative } : null;
    }).filter(Boolean);
  }

  function createIndex(app) {
    return Object.freeze({
      id: normalise(app.id),
      name: normalise(app.name),
      summary: normalise(app.summary),
      description: normalise(app.description),
      category: normalise(app.category),
      tags: normalise([...(app.tags || []), ...(app.keywords || [])].join(" ")),
      features: normalise((app.features || []).join(" ")),
      platforms: normalise((app.platforms || []).join(" ")),
      status: normalise(app.status),
      version: normalise(app.version),
      type: normalise(app.type),
      all: normalise([
        app.id, app.slug, app.name, app.summary, app.description, app.category,
        app.status, app.version, app.type,
        ...(app.tags || []), ...(app.keywords || []), ...(app.features || []),
        ...(app.platforms || [])
      ].join(" ")),
      words: Array.from(new Set(words([
        app.id, app.slug, app.name, app.summary, app.description, app.category,
        app.status, app.version, app.type,
        ...(app.tags || []), ...(app.keywords || []), ...(app.features || []),
        ...(app.platforms || [])
      ].join(" "))))
    });
  }

  function termScore(term, fieldText) {
    if (!fieldText) return 0;
    if (fieldText.includes(term)) return 1;
    const candidates = words(fieldText);
    if (candidates.some(word => word.startsWith(term) && term.length >= 3)) return 0.82;
    if (term.length < 5) return 0;
    const threshold = term.length >= 8 ? 2 : 1;
    let best = threshold + 1;
    for (const word of candidates) {
      if (Math.abs(word.length - term.length) > threshold) continue;
      best = Math.min(best, boundedDistance(term, word, threshold));
      if (best === 0) return 1;
    }
    return best <= threshold ? (best === 1 ? 0.62 : 0.42) : 0;
  }

  function expandedTerms(term) {
    const aliases = SYNONYMS[term] || [];
    return [term, ...aliases.map(normalise)];
  }

  function scoreField(index, field, term) {
    const fields = field === "all"
      ? [
          ["id", 90], ["name", 85], ["tags", 38], ["features", 25],
          ["category", 22], ["summary", 18], ["platforms", 12],
          ["version", 10], ["status", 8], ["type", 7], ["description", 5]
        ]
      : [[field, field === "name" || field === "id" ? 85 : 30]];
    let best = 0;
    for (const [key, weight] of fields) {
      const quality = termScore(term, index[key] || "");
      if (quality) best = Math.max(best, quality * weight);
    }
    return best;
  }

  function search(index, query) {
    if (!index || typeof index !== "object") return { matches: false, score: 0 };
    const terms = Array.isArray(query) ? query : parseQuery(query);
    let score = 0;
    for (const token of terms) {
      const candidates = expandedTerms(token.value);
      let best = 0;
      for (const candidate of candidates) {
        best = Math.max(best, scoreField(index, token.field, candidate));
      }
      if (token.negative) {
        if (best > 0) return { matches: false, score: 0 };
      } else {
        if (best === 0) return { matches: false, score: 0 };
        score += best;
      }
    }
    return { matches: true, score };
  }

  return Object.freeze({ normalise, parseQuery, createIndex, search, boundedDistance });
});
