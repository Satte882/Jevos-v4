import io
import zipfile
import unittest
from unittest.mock import patch

from redaction_app.core import Finding, redact
from redaction_app.docx import extract_docx


class RedactionTests(unittest.TestCase):
    def test_regex_replaces_email_url_phone_and_iban(self):
        text = (
            "Kontakt mail@example.de, mail@example.de. "
            "Website https://secret.example.de/project?id=7, "
            "Telefon +49 89 12345678, IBAN DE89 3704 0044 0532 0130 00."
        )
        result = redact(text, entities=[])
        output = result["text"]
        self.assertNotIn("mail@example.de", output)
        self.assertNotIn("secret.example.de", output)
        self.assertNotIn("+49 89 12345678", output)
        self.assertNotIn("3704 0044", output)
        self.assertIn("[EMAIL_1], [EMAIL_1]", output)
        self.assertIn("[URL_1]", output)
        self.assertIn("[PHONE_1]", output)
        self.assertIn("[IBAN_1]", output)
        self.assertNotIn("mail@example.de", repr(result))

    def test_names_organisations_places_and_meaning_preserved(self):
        source = "Anna Meier von ABC GmbH in München. Anna Meier erhielt ein Angebot über 45.000 €."
        entities = [
            Finding(0, 10, "PERSON", "Anna Meier", 10),
            Finding(15, 23, "UNTERNEHMEN", "ABC GmbH", 10),
            Finding(27, 34, "ORT", "München", 10),
            Finding(36, 46, "PERSON", "Anna Meier", 10),
        ]
        result = redact(source, entities=entities)
        self.assertIn("[PERSON_1]", result["text"])
        self.assertEqual(result["text"].count("[PERSON_1]"), 2)
        self.assertIn("[UNTERNEHMEN_1]", result["text"])
        self.assertIn("[ORT_1]", result["text"])
        self.assertIn("45.000 €", result["text"])

    def test_secret_priority_over_name(self):
        text = "API_KEY: abcdefghijklmnop und Bob."
        token = text.index("abcdefghijklmnop")
        result = redact(text, entities=[
            Finding(token, token+16, "PERSON", "abcdefghijklmnop", 10),
            Finding(text.index("Bob"), text.index("Bob")+3, "PERSON", "Bob", 10),
        ])
        self.assertIn("[SECRET_1]", result["text"])
        self.assertIn("[PERSON_1]", result["text"])
        self.assertNotIn("abcdefghijklmnop", result["text"])

    def test_no_default_export_if_nlp_missing(self):
        with patch("redaction_app.core._ner", side_effect=RuntimeError("no local NLP")):
            with self.assertRaisesRegex(RuntimeError, "no local NLP"):
                redact("Anna Meier schreibt.")

    def test_empty_and_size_guard(self):
        for val in ("", "  ", None):
            with self.assertRaises(ValueError):
                redact(val, entities=[])
        with self.assertRaises(ValueError):
            redact("A" * 100001, entities=[])

    def test_entities_can_overlap_regex(self):
        text = "Mail: anna@example.de"
        result = redact(text, entities=[Finding(6, 21, "PERSON", "anna@example.de", 10)])
        self.assertEqual(result["text"], "Mail: [EMAIL_1]")

    def test_docx_extraction_text_paragraphs(self):
        xml = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
               '<w:body><w:p><w:r><w:t>Hallo Anna</w:t></w:r></w:p>'
               '<w:p><w:r><w:t>ABC GmbH</w:t></w:r></w:p></w:body></w:document>')
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", xml)
        self.assertEqual(extract_docx(out.getvalue()), "Hallo Anna\n\nABC GmbH")

    def test_docx_invalid(self):
        with self.assertRaises(ValueError):
            extract_docx(b"not a document")
        with self.assertRaises(ValueError):
            extract_docx(b"x" * 2_000_001)

    def test_earlier_ner_span_does_not_leave_email_suffix(self):
        text = "Anna anna@example.de meldet sich."
        result = redact(text, entities=[Finding(0, 9, "PERSON", text[:9], 10)])
        self.assertEqual(result["text"], "[EMAIL_1] meldet sich.")
        self.assertNotIn("example.de", result["text"])

    def test_overlapping_name_cannot_hide_secret(self):
        text = "Anna API_KEY: abcdefghijklmnop meldet sich."
        result = redact(text, entities=[Finding(0, 8, "PERSON", text[:8], 10)])
        self.assertEqual(result["text"], "[SECRET_1] meldet sich.")

    def test_docx_utf16_entities_rejected(self):
        xml = ('<?xml version="1.0" encoding="UTF-16"?>'
               '<!DOCTYPE document [<!ENTITY secret "sensitive">]>'
               '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
               '<w:body><w:p><w:r><w:t>&secret;</w:t></w:r></w:p></w:body></w:document>')
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", xml.encode("utf-16"))
        with self.assertRaisesRegex(ValueError, "XML-Entitäten"):
            extract_docx(out.getvalue())

    def test_repeat_name_when_ner_only_detects_second_occurrence(self):
        text = "Anna Meier schreibt. ANNA  MEIER antwortet."
        start = text.index("ANNA")
        result = redact(text, entities=[Finding(start, start+11, "PERSON", "ANNA  MEIER", 10)])
        self.assertEqual(result["text"], "[PERSON_1] schreibt. [PERSON_1] antwortet.")

    def test_known_name_is_not_replaced_inside_longer_word(self):
        text = "Anna trifft Annabelle."
        result = redact(text, entities=[Finding(0, 4, "PERSON", "Anna", 10)])
        self.assertEqual(result["text"], "[PERSON_1] trifft Annabelle.")


if __name__ == "__main__":
    unittest.main()
