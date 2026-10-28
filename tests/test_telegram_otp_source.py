"""Source-level regression checks for the Telegram admin OTP boundary."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TelegramOtpSourceTests(unittest.TestCase):
    def test_request_posts_a_formatted_notice_to_the_restricted_group(self):
        source = (ROOT / "api/admin/otp/request.js").read_text(encoding="utf-8")
        self.assertIn("chat_id: GROUP_ID", source)
        self.assertIn("protect_content: true", source)
        self.assertIn(r"VERIFIKASI LOGIN ADMIN\n\nAkun:", source)
        self.assertNotIn(r"VERIFIKASI LOGIN ADMIN\\n\\nAkun:", source)
        self.assertIn("telegram_group_membership_required", source)
        self.assertIn("TELEGRAM_GROUP_ID sesuai", source)

    def test_otp_challenge_is_bound_to_the_authenticated_admin(self):
        request = (ROOT / "api/admin/otp/request.js").read_text(encoding="utf-8")
        verify = (ROOT / "api/admin/otp/verify.js").read_text(encoding="utf-8")
        shared = (ROOT / "api/admin/_shared.js").read_text(encoding="utf-8")
        self.assertIn("activeAdmin(user.id)", request)
        self.assertIn("codeHash(user.id, code)", request)
        self.assertIn("p_auth_user_id: user.id", verify)
        self.assertIn("HttpOnly; Secure; SameSite=Strict", verify)
        self.assertIn("lsl_admin_telegram_otp_sessions", shared)
        self.assertIn("revoked_at=is.null", shared)


if __name__ == "__main__":
    unittest.main()
