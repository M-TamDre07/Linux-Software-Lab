// Supabase Edge Function: feedback-create
// Required secrets: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
// TURNSTILE_SECRET_KEY, FEEDBACK_ENCRYPTION_KEY (base64-encoded 32 bytes),
// FEEDBACK_LOOKUP_HMAC_KEY (base64-encoded 32+ bytes).
// Deploy only after applying the reviewed migration and configuring secrets.
// No secrets belong in client-side JavaScript.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.57.4";

const ALLOWED_ORIGINS = new Set([
  "https://linux-software-lab.vercel.app",
]);
const FORMSPREE_ENDPOINT = "https://formspree.io/f/xjyyokow";
const MAX_BODY_BYTES = 12_000;
const RATE_LIMIT_WINDOW_MINUTES = 15;
const RATE_LIMIT_MAX = 5;

const json = (status: number, body: Record<string, unknown>, origin: string | null) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "Vary": "Origin",
      ...(origin && ALLOWED_ORIGINS.has(origin)
        ? {
          "Access-Control-Allow-Origin": origin,
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "content-type",
        }
        : {}),
    },
  });

function b64bytes(value: string): Uint8Array {
  const raw = atob(value);
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}
function hex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
function toBytea(bytes: Uint8Array): string {
  return String.fromCharCode(92) + "x" + hex(bytes);
}
function safeString(value: unknown, max: number): string {
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}
function randomTicketCode(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(5));
  return "LSL-" + hex(bytes).toUpperCase();
}
async function hmacLookup(key: CryptoKey, value: string): Promise<string> {
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value));
  return hex(new Uint8Array(sig));
}
async function encryptField(key: CryptoKey, value: string): Promise<Uint8Array> {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv, tagLength: 128 },
    key,
    new TextEncoder().encode(value),
  );
  // Envelope: version byte (1), 12-byte nonce, AES-GCM ciphertext+tag.
  const ciphertext = new Uint8Array(encrypted);
  const envelope = new Uint8Array(1 + iv.length + ciphertext.length);
  envelope[0] = 1;
  envelope.set(iv, 1);
  envelope.set(ciphertext, 13);
  return envelope;
}
async function sha256(value: string): Promise<string> {
  return hex(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value))));
}
async function logSecurity(
  supabase: ReturnType<typeof createClient>,
  eventType: string,
  ipHash: string | null,
  details: Record<string, unknown> = {},
) {
  // Details must never contain raw IPs, contact values, CAPTCHA tokens, or message bodies.
  await supabase.from("admin_security_events").insert({
    event_type: eventType,
    ip_lookup_hash: ipHash,
    details,
  });
}

Deno.serve(async (req: Request) => {
  const origin = req.headers.get("origin");
  if (req.method === "OPTIONS") {
    if (!origin || !ALLOWED_ORIGINS.has(origin)) return new Response(null, { status: 403 });
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "content-type",
        "Access-Control-Max-Age": "600",
        "Vary": "Origin",
      },
    });
  }
  if (req.method !== "POST") return json(405, { error: "method_not_allowed" }, origin);
  if (!origin || !ALLOWED_ORIGINS.has(origin)) return json(403, { error: "origin_not_allowed" }, origin);

  const contentType = req.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return json(415, { error: "json_required" }, origin);
  }
  const declaredLength = Number(req.headers.get("content-length") || "0");
  if (declaredLength > MAX_BODY_BYTES) return json(413, { error: "payload_too_large" }, origin);

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const captchaSecret = Deno.env.get("TURNSTILE_SECRET_KEY");
  const encryptionB64 = Deno.env.get("FEEDBACK_ENCRYPTION_KEY");
  const lookupB64 = Deno.env.get("FEEDBACK_LOOKUP_HMAC_KEY");
  if (!supabaseUrl || !serviceKey || !captchaSecret || !encryptionB64 || !lookupB64) {
    return json(503, { error: "feedback_service_not_configured" }, origin);
  }

  let rawBody = "";
  try {
    rawBody = await req.text();
    if (new TextEncoder().encode(rawBody).length > MAX_BODY_BYTES) {
      return json(413, { error: "payload_too_large" }, origin);
    }
  } catch {
    return json(400, { error: "invalid_request" }, origin);
  }

  let payload: Record<string, unknown>;
  try {
    const parsed = JSON.parse(rawBody);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("bad_json");
    payload = parsed as Record<string, unknown>;
  } catch {
    return json(400, { error: "invalid_json" }, origin);
  }

  const category = safeString(payload.category, 30);
  const subject = safeString(payload.subject, 160);
  const message = safeString(payload.message, 4000);
  const contact = safeString(payload.contact, 320);
  const source = safeString(payload.source, 30) || "website";
  const productSlug = safeString(payload.product_slug, 100) || null;
  const captchaToken = safeString(payload.captcha_token, 4096);

  if (!["website", "launcher", "application", "security", "other"].includes(category) ||
      !["website", "launcher", "application"].includes(source) ||
      subject.length < 3 || message.length < 10 ||
      (contact && (contact.length > 320 || /[\r\n]/.test(contact))) ||
      !captchaToken) {
    return json(400, { error: "invalid_fields" }, origin);
  }

  const supabase = createClient(supabaseUrl, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { headers: { "X-Client-Info": "lsl-feedback-edge/1" } },
  });

  // Hash the platform-provided client address with a secret HMAC key; never store raw IP.
  const forwarded = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  let ipHash: string | null = null;
  try {
    const lookupKey = await crypto.subtle.importKey(
      "raw",
      b64bytes(lookupB64),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"],
    );
    ipHash = await hmacLookup(lookupKey, forwarded);
  } catch {
    return json(503, { error: "feedback_service_not_configured" }, origin);
  }

  const since = new Date(Date.now() - RATE_LIMIT_WINDOW_MINUTES * 60_000).toISOString();
  const { count, error: rateError } = await supabase
    .from("admin_security_events")
    .select("id", { count: "exact", head: true })
    .eq("event_type", "suspicious_request")
    .eq("ip_lookup_hash", ipHash)
    .contains("details", { route: "feedback-create" })
    .gte("created_at", since);
  // Count every attempt, not only requests already blocked. This is a best-effort
  // limit; a later atomic DB RPC should replace it before public launch.
  if (rateError) return json(503, { error: "security_check_unavailable" }, origin);
  if ((count || 0) >= RATE_LIMIT_MAX) {
    await logSecurity(supabase, "rate_limited", ipHash, { route: "feedback-create" });
    return json(429, { error: "rate_limited", retry_after_seconds: 900 }, origin);
  }
  await logSecurity(supabase, "suspicious_request", ipHash, { route: "feedback-create", stage: "attempt" });

  const verifyForm = new URLSearchParams();
  verifyForm.set("secret", captchaSecret);
  verifyForm.set("response", captchaToken);
  if (forwarded !== "unknown") verifyForm.set("remoteip", forwarded);
  let captchaOk = false;
  try {
    const verifyResponse = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: verifyForm,
      signal: AbortSignal.timeout(5000),
    });
    const verifyResult = await verifyResponse.json();
    captchaOk = verifyResponse.ok && verifyResult.success === true;
  } catch {
    return json(503, { error: "captcha_verification_unavailable" }, origin);
  }
  if (!captchaOk) {
    await logSecurity(supabase, "captcha_failed", ipHash, { route: "feedback-create" });
    return json(400, { error: "captcha_failed" }, origin);
  }

  let encryptionKey: CryptoKey;
  let lookupKey: CryptoKey;
  try {
    const encBytes = b64bytes(encryptionB64);
    if (encBytes.length !== 32) throw new Error("encryption_key_must_be_32_bytes");
    encryptionKey = await crypto.subtle.importKey("raw", encBytes, "AES-GCM", false, ["encrypt"]);
    lookupKey = await crypto.subtle.importKey(
      "raw",
      b64bytes(lookupB64),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"],
    );
  } catch {
    return json(503, { error: "feedback_service_not_configured" }, origin);
  }

  const ticketCode = randomTicketCode();
  const [bodyCiphertext, contactCiphertext, contactHash] = await Promise.all([
    encryptField(encryptionKey, message),
    contact ? encryptField(encryptionKey, contact) : Promise.resolve(null),
    contact ? hmacLookup(lookupKey, contact.toLowerCase()) : Promise.resolve(null),
  ]);

  const { data: ticket, error: insertError } = await supabase
    .from("site_feedback")
    .insert({
      ticket_code: ticketCode,
      category,
      product_slug: productSlug,
      subject,
      body_ciphertext: toBytea(bodyCiphertext),
      contact_ciphertext: contactCiphertext ? toBytea(contactCiphertext) : null,
      contact_lookup_hash: contactHash,
      source,
      status: "open",
      formspree_delivery_status: "pending",
    })
    .select("id,ticket_code,created_at")
    .single();

  if (insertError || !ticket) {
    return json(503, { error: "ticket_storage_failed" }, origin);
  }

  // Formspree is a second destination. Send only the fields needed for the admin to act.
  // The contact field is deliberately omitted from this external copy.
  let formspreeStatus = "failed";
  try {
    const form = new FormData();
    form.set("ticket_code", ticketCode);
    form.set("category", category);
    form.set("source", source);
    form.set("subject", subject);
    form.set("message", message);
    form.set("product_slug", productSlug || "");
    form.set("_subject", `Linux Software Lab feedback: ${ticketCode}`);
    const response = await fetch(FORMSPREE_ENDPOINT, {
      method: "POST",
      headers: { "Accept": "application/json" },
      body: form,
      signal: AbortSignal.timeout(7000),
    });
    formspreeStatus = response.ok ? "sent" : "failed";
  } catch {
    formspreeStatus = "failed";
  }

  await supabase.from("site_feedback")
    .update({ formspree_delivery_status: formspreeStatus, updated_at: new Date().toISOString() })
    .eq("id", ticket.id);

  return json(201, {
    ok: true,
    ticket_code: ticketCode,
    formspree_delivery: formspreeStatus,
    message: formspreeStatus === "sent"
      ? "feedback_received"
      : "feedback_saved_notification_pending",
  }, origin);
});
