"""Static UI checks: desktop layout, shared design tokens, local assets, favicon."""
from pathlib import Path
from unittest import TestCase
from xml.etree import ElementTree

from inbox_assistant.web import FAVICON, HTML, REDACTION_HTML, UI_CSS


class DesktopThemeTests(TestCase):
    def test_shared_theme_and_full_desktop_width(self):
        css = UI_CSS.read_text(encoding="utf-8")
        self.assertIn("--surface-0: #080a0d", css)
        self.assertIn("--ice: #9fddff", css)
        self.assertIn("max-width: none;", css)
        self.assertIn(".workspace { display: grid;", css)
        self.assertIn("grid-template-columns: minmax(0, 43fr) minmax(0, 57fr)", css)
        self.assertIn(".app-header", css)
        self.assertIn("justify-self: center;", css)
        self.assertNotIn("purple", css.lower())

    def test_inbox_button_in_same_header_row(self):
        html = HTML.read_text(encoding="utf-8")
        header = html.split('<header class="app-header">', 1)[1].split("</header>", 1)[0]
        self.assertLess(header.index("Obsidian Inbox-Assistent"), header.index('class="view-switch"'))
        self.assertLess(header.index('class="view-switch"'), header.index('id="refresh"'))
        self.assertIn('href="/anonymize"', header)
        self.assertIn(">Text bereinigen ", header)
        self.assertIn('<main class="workspace">', html)

    def test_shared_css_and_icon_linked_by_both_pages(self):
        for page in (HTML, REDACTION_HTML):
            html = page.read_text(encoding="utf-8")
            self.assertIn('rel="stylesheet" href="/assets/ui.css"', html)
            self.assertIn('rel="icon" type="image/svg+xml" href="/favicon.svg"', html)

    def test_icon_is_svg_without_letters(self):
        icon = ElementTree.fromstring(FAVICON.read_text(encoding="utf-8"))
        self.assertEqual(icon.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertTrue(any(node.tag.endswith("path") for node in icon.iter()))
        self.assertFalse(any((node.text or "").strip() for node in icon.iter()))

    def test_only_fixed_asset_routes_are_exposed(self):
        from inspect import getsource
        from inbox_assistant.web import handler_factory
        routes = getsource(handler_factory)
        self.assertIn('parsed.path == "/assets/ui.css"', routes)
        self.assertIn('parsed.path == "/favicon.svg"', routes)
        self.assertIn("style-src 'self' 'unsafe-inline'", routes)
