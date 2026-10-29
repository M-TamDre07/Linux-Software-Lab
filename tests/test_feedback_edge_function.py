"""Static security regression checks for the feedback Edge Function draft."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUNCTION = ROOT / "supabase" / "functions" / "feedback-create" / "index.ts"
MIGRATION = ROOT / "supabase" / "migrations" / "20261029120000_admin_security_feedback_foundation.sql"


class FeedbackEdgeFunctionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = FUNCTION.read_text(encoding="utf-8")
        cls.migration = MIGRATION.read_text(encoding="utf-8")

    def test_captcha_is_verified_server_side(self) -> None:
        self.assertIn("challenges.cloudflare.com/turnstile/v0/siteverify", self.script)
        self.assertIn('captchaOk = verifyResponse.ok && verifyResult.success === true', self.script)
        self.assertIn("TURNSTILE_SECRET_KEY", self.script)

    def test_sensitive_fields_are_encrypted_before_database_insert(self) -> None:
        self.assertIn('name: "AES-GCM"', self.script)
        self.assertIn("encryptField(encryptionKey, subject)", self.script)
        self.assertIn("encryptField(encryptionKey, message)", self.script)
        self.assertIn("encryptField(encryptionKey, contact)", self.script)
        self.assertIn('subject: "Feedback ticket"', self.script)
        self.assertIn("subject_ciphertext: toBytea(subjectCiphertext)", self.script)
        self.assertIn("body_ciphertext: toBytea(bodyCiphertext)", self.script)

    def test_formspree_copy_does_not_include_contact_details(self) -> None:
        form_section = self.script.split("const form = new FormData();", 1)[1]
        form_section = form_section.split("const response = await fetch(FORMSPREE_ENDPOINT", 1)[0]
        self.assertIn('form.set("message", message)', form_section)
        self.assertIn('form.set("subject", subject)', form_section)
        self.assertNotIn('form.set("contact", contact)', form_section)

    def test_browser_access_to_feedback_tables_is_revoked(self) -> None:
        self.assertIn("alter table public.site_feedback enable row level security", self.migration)
        self.assertIn("revoke all on table public.site_feedback from public, anon, authenticated", self.migration)
        self.assertIn("revoke all on table public.site_feedback_messages from public, anon, authenticated", self.migration)

    def test_ticket_code_constraint_matches_generated_code(self) -> None:
        self.assertIn('return "LSL-" + hex(bytes).toUpperCase()', self.script)
        self.assertIn("ticket_code ~ '^LSL-[A-Z0-9]{10}' and length(ticket_code) = 14", self.migration)

    def test_function_is_not_claimed_as_deployed(self) -> None:
        docs = (ROOT / "supabase" / "functions" / "README.md").read_text(encoding="utf-8")
        self.assertIn("not wired into the public website yet", docs)
        self.assertIn("not wired into the public website yet", docs)


if __name__ == "__main__":
    unittest.main()
