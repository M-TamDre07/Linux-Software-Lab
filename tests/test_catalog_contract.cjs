const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { validateCatalogPayload } = require("../public/assets/js/catalog-contract.js");

const catalogPath = path.join(__dirname, "..", "public", "data", "software.json");
const canonicalCatalog = JSON.parse(fs.readFileSync(catalogPath, "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));

test("canonical checked-in catalogue satisfies the browser contract", () => {
  const result = validateCatalogPayload(canonicalCatalog);
  assert.deepEqual(result, { valid: true, errors: [] });
});

test("rejects a wrong schema version and unknown top-level keys", () => {
  const wrongVersion = clone(canonicalCatalog);
  wrongVersion.schemaVersion = 999;
  assert.ok(validateCatalogPayload(wrongVersion).errors.some(message => message.includes("schemaVersion")));

  const unknownField = clone(canonicalCatalog);
  unknownField.debug = "must not be part of the public contract";
  assert.ok(validateCatalogPayload(unknownField).errors.some(message => message.includes("tingkat atas")));
});

test("rejects duplicate IDs, mismatched slugs and detail routes", () => {
  const duplicate = clone(canonicalCatalog);
  duplicate.software[1].id = duplicate.software[0].id;
  assert.ok(validateCatalogPayload(duplicate).errors.some(message => message.includes("duplikat")));

  const mismatchedSlug = clone(canonicalCatalog);
  mismatchedSlug.software[0].slug = "different-app";
  assert.ok(validateCatalogPayload(mismatchedSlug).errors.some(message => message.includes("id dan slug harus sama")));

  const wrongDetail = clone(canonicalCatalog);
  wrongDetail.software[0].detailUrl = "https://evil.example/app";
  assert.ok(validateCatalogPayload(wrongDetail).errors.some(message => message.includes("detailUrl")));
});

test("rejects script URLs, unsafe remote assets and non-HTTPS sources", () => {
  const badSource = clone(canonicalCatalog);
  badSource.software[0].sourceUrl = "javascript:alert(1)";
  assert.ok(validateCatalogPayload(badSource).errors.some(message => message.includes("sourceUrl")));

  const badRelease = clone(canonicalCatalog);
  badRelease.software[0].releaseUrl = "//evil.example/binary";
  assert.ok(validateCatalogPayload(badRelease).errors.some(message => message.includes("releaseUrl")));

  const badAsset = clone(canonicalCatalog);
  badAsset.software[0].previewImage = "https://evil.example/preview.svg";
  assert.ok(validateCatalogPayload(badAsset).errors.some(message => message.includes("previewImage")));
});

test("rejects unknown states, duplicate tags and invalid calendar dates", () => {
  const badStatus = clone(canonicalCatalog);
  badStatus.software[0].status = "available-ish";
  assert.ok(validateCatalogPayload(badStatus).errors.some(message => message.includes("status tidak dikenal")));

  const duplicateTags = clone(canonicalCatalog);
  duplicateTags.software[0].tags.push(duplicateTags.software[0].tags[0]);
  assert.ok(validateCatalogPayload(duplicateTags).errors.some(message => message.includes(".tags")));

  const badDate = clone(canonicalCatalog);
  badDate.software[0].updatedAt = "2026-02-31";
  assert.ok(validateCatalogPayload(badDate).errors.some(message => message.includes(".updatedAt")));
});

test("a released application must carry a verified HTTPS release URL", () => {
  const badReleased = clone(canonicalCatalog);
  badReleased.software[0].status = "released";
  badReleased.software[0].releaseUrl = "";
  assert.ok(validateCatalogPayload(badReleased).errors.some(message => message.includes("status released")));
});

test("null, arrays, malformed records and missing catalogue blocks fail closed", () => {
  assert.equal(validateCatalogPayload(null).valid, false);
  assert.equal(validateCatalogPayload([]).valid, false);
  assert.equal(validateCatalogPayload({ schemaVersion: 2, catalog: {}, software: [null] }).valid, false);
});
