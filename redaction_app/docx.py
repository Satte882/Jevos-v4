"""DOCX ausschließlich lesend in Klartext umwandeln, ohne Dokument-Metadaten zu exportieren."""
from __future__ import annotations

import io
import zipfile
from xml.etree import ElementTree

MAX_DOCX_BYTES = 2_000_000
MAX_UNCOMPRESSED_XML = 8_000_000
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_docx(data: bytes) -> str:
    if not isinstance(data, bytes) or not data or len(data) > MAX_DOCX_BYTES:
        raise ValueError("DOCX ist leer oder größer als 2 MB.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 1000:
                raise ValueError("Zu viele Bestandteile im DOCX.")
            info = archive.getinfo("word/document.xml")
            if info.file_size > MAX_UNCOMPRESSED_XML:
                raise ValueError("DOCX-Haupttext überschreitet die Sicherheitsgrenze.")
            with archive.open(info) as part:
                xml = part.read(MAX_UNCOMPRESSED_XML + 1)
                if len(xml) > MAX_UNCOMPRESSED_XML:
                    raise ValueError("DOCX-Haupttext ist zu groß.")
    except (zipfile.BadZipFile, KeyError, OSError) as exc:
        raise ValueError("Keine gültige DOCX-Datei mit lesbarem Haupttext.") from exc
    if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
        raise ValueError("XML-Entitäten im Dokument werden nicht unterstützt.")
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise ValueError("DOCX-Haupttext enthält ungültiges XML.") from exc
    lines: list[str] = []
    for paragraph in root.iter(W + "p"):
        fragments = []
        for node in paragraph.iter():
            if node.tag == W + "t" and node.text:
                fragments.append(node.text)
            elif node.tag == W + "tab":
                fragments.append("\t")
            elif node.tag in (W + "br", W + "cr"):
                fragments.append("\n")
        line = "".join(fragments).strip()
        if line:
            lines.append(line)
    result = "\n\n".join(lines)
    if not result:
        raise ValueError("Keine Textabsätze im DOCX gefunden.")
    if len(result) > 100_000:
        raise ValueError("Extrahierter Dokumenttext übersteigt 100.000 Zeichen.")
    return result
