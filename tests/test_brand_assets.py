import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
PAKETSCOPE_ICON = PUBLIC / "assets/images/paketscope-icon.svg"
DESKTOP_ICON = ROOT / "apps/paketscope/paketscope/assets/paketscope.svg"


class BrandAssetTests(unittest.TestCase):
    def test_paketscope_svg_is_shared_by_website_and_native_app(self):
        self.assertTrue(PAKETSCOPE_ICON.is_file())
        self.assertTrue(DESKTOP_ICON.is_file())
        self.assertEqual(PAKETSCOPE_ICON.read_bytes(), DESKTOP_ICON.read_bytes())
        ET.parse(PAKETSCOPE_ICON)
        ET.parse(PUBLIC / "assets/images/home-icon.svg")

    def test_desktop_launcher_and_debian_package_install_the_icon(self):
        desktop = (ROOT / "apps/paketscope/packaging/paketscope.desktop").read_text(encoding="utf-8")
        rules = (ROOT / "apps/paketscope/debian/rules").read_text(encoding="utf-8")
        app = (ROOT / "apps/paketscope/paketscope/app.py").read_text(encoding="utf-8")
        self.assertIn("Icon=paketscope", desktop)
        self.assertIn("usr/share/icons/hicolor/scalable/apps/paketscope.svg", rules)
        self.assertIn("app.setWindowIcon(QIcon(str(icon_path)))", app)

    def test_website_uses_the_shared_icon_where_paketscope_is_promoted(self):
        data = json.loads((PUBLIC / "data/software.json").read_text(encoding="utf-8"))
        paketscope = next(item for item in data["software"] if item["id"] == "paketscope")
        self.assertEqual(paketscope["iconImage"], "/assets/images/paketscope-icon.svg")
        self.assertTrue((PUBLIC / paketscope["iconImage"].lstrip("/")).is_file())

        homepage = (PUBLIC / "index.html").read_text(encoding="utf-8")
        catalog = (PUBLIC / "software/index.html").read_text(encoding="utf-8")
        detail = (PUBLIC / "software/paketscope.html").read_text(encoding="utf-8")
        self.assertGreaterEqual(homepage.count("/assets/images/paketscope-icon.svg"), 2)
        self.assertIn("/assets/images/paketscope-icon.svg", detail)
        self.assertIn("iconImage", (PUBLIC / "assets/js/site.js").read_text(encoding="utf-8"))
        self.assertIn("/assets/images/home-icon.svg", catalog)
        self.assertIn('href="/"', catalog)

    def test_public_contribution_route_does_not_require_personal_contact_details(self):
        homepage = (PUBLIC / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="kontribusi"', homepage)
        self.assertIn("https://github.com/M-TamDre07/Linux-Software-Lab/issues", homepage)


if __name__ == "__main__":
    unittest.main()
