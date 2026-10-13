# Textbereinigung für externe KI (MVP)

**Ziel:** Einen privaten Text oder ein Dokument einfügen, rein **lokal** personenbezogene Identifikatoren erkennen/ersetzen, die Ausgabe **selbst prüfen** und anschließend als Klartext für ein beliebiges Frontier-LLM kopieren.

**Unabhängig vom Obsidian-Inbox-Modell:** Für positionsgenaue Erkennung und Ersetzung verwenden wir Regeln und ein lokales deutsches spaCy-NER-Modell. Jev und jevos-v4 sind dafür nicht erforderlich. Die Verbindung zu TypeSafe wird in diesem Feature nicht benutzt.

## Ablauf

1. In der bestehenden Web-App **Text für externe KI bereinigen** aufrufen: `http://127.0.0.1:8765/anonymize`.
2. Text einfügen **oder** TXT, MD oder DOCX bis 2 MB auswählen.
3. **Lokal bereinigen** klicken. Ausgabe erscheint neben dem Original; Kategorien und Trefferanzahl werden angezeigt.
4. **Den gesamten Ausgabetext kontrollieren**, bei Bedarf direkt in der rechten Textbox nachbessern.
5. **Prüfung bestätigen**, dann kopieren oder als `bereinigter-text.txt` speichern.
6. Nur den manuell geprüften Ausgabetext an ChatGPT/Claude oder ein anderes externes Modell übergeben.

Keine automatische Weitergabe, kein Frontier-LLM-Schlüssel und kein Export des Originaltexts. Die Bereinigung speichert Original, Ersetzungen und Rückübersetzungstabelle nicht auf der Festplatte.

Für die Windows-Zwischenablage wurde das Kopieren in Microsoft Edge geprüft. Im eingebetteten Codex-Browser kam bei der lokalen Abnahme trotz Erfolgsmeldung kein Text in der Windows-Zwischenablage an; dort den TXT-Export oder einen externen Browser verwenden.

## Einmalige Einrichtung (Windows)

In PowerShell im Repository:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-redaction.ps1
```

Dies installiert `spaCy` und das lokale Sprachmodell `de_core_news_md` in der vorhandenen virtuellen Python-Umgebung (`.venv`). Danach die bereits laufende Web-App **neu starten**:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-ui.ps1
```

Keine separate Webanwendung, kein zusätzlicher Port, keine Cloud-API erforderlich. Die Paketinstallation lädt nur Software/Modell herunter; der später verarbeitete Text wird vom eingebundenen NER-Modell auf dem Rechner analysiert.

## Erkennung und Ersetzung

- Reguläre Ausdrücke: E-Mail-Adressen, URLs, Telefonnummern, deutsche IBAN, IPv4-Adressen, gängige API-Schlüssel und einfache `PASSWORD:`/`API_KEY:`-Zuweisungen.
- Lokale Named Entity Recognition (Deutsch): Personen, Organisationen, Orte.
- Wiederkehrende identische Textstellen bekommen denselben Platzhalter, z. B. `[PERSON_1]`, `[UNTERNEHMEN_1]`, `[EMAIL_1]`.
- Sobald eine Entität erkannt wurde, werden auch ihre wörtlichen Wiederholungen ersetzt (einschließlich Groß-/Kleinschreibung und unterschiedlicher Leerzeichen). Nie erkannte Namen und andere Namensvarianten können weiterhin übersehen werden.
- Überlappende Treffer werden vollständig abgedeckt; die Kategorie mit höherer Priorität bestimmt den Platzhalter. Damit bleiben keine Teile einer E-Mail oder eines Secrets wegen eines überlappenden Namenstreffers ungeschützt.
- Datum, Betrag und sonstiger Sachinhalt bleiben **standardmäßig erhalten**, damit ein Frontier-LLM mit dem Text arbeiten kann.
- DOCX wird **nur als Text** aus dem Hauptdokument extrahiert; Formatierung, Anhänge, Kommentare, Kopf-/Fußzeilen und Dokumentmetadaten werden nicht exportiert. Für Bilder/OCR, PDFs und Tabellenformatierung besteht im MVP kein Anspruch.

## Grenzen und Risiken

**Das Ergebnis ist keine garantierte Anonymisierung.** Personen/Unternehmen können trotz ersetzter Namen über Branche, konkrete Ereignisse, seltene Rollen, Zahlen oder Kombinationen von Details erkennbar sein. SpaCy kann unbekannte deutsche Eigennamen übersehen, zusammengesetzte Bezeichnungen aufteilen oder falsch-positive Treffer liefern.

- **Keine stillschweigende Regex-only-Ausgabe:** Fehlt das lokale deutsche NER-Modell, schlägt die Bereinigung mit einer Installationsmeldung fehl. Es wird kein scheinbar anonymisierter Text freigegeben.
- **Keine Garantie gegen Geheimnislecks:** Manche Zugangsdaten entsprechen nicht den bekannten Tokenformaten. Zugangsdaten sollten generell nicht in externe LLMs kopiert werden.
- **Keine persistente Rückübersetzungstabelle:** Platzhalter sind konsistent pro Bereinigung, die Zuordnung bleibt nicht erhalten.
- **Keine automatische Exportfreigabe:** Nach jeder Bearbeitung der bereinigten Fassung muss die manuelle Bestätigung erneut erfolgen.
- **Keine veralteten Ergebnisse:** Während Import/Bereinigung ist die Exportfreigabe gesperrt. Antworten für inzwischen geänderte oder zurückgesetzte Eingaben werden verworfen.
- **Keine Dokumentautomatisierung:** Es entsteht Klartext, kein editierbares DOCX mit originaler Formatierung.
- **Nur deutsche NER-Pipeline:** Für stark englische oder mehrsprachige Inhalte ist eine weitere Qualitätsprüfung nötig.

## Abnahme für lokalen Coding-Agenten

1. `py -3 -m unittest discover -s tests -v` und PowerShell-/JavaScript-Syntaxprüfungen grün.
2. Einrichtungsskript auf Windows in bestehender `.venv` ausführen und `spaCy`-NER-Modell lokal laden.
3. Bei laufender UI `/anonymize` öffnen; synthetische deutsche Texte mit wiederkehrenden Namen, E-Mail, URL, Telefonnummer, Firmen und Orten testen.
4. DOCX-Import mit synthetischer Testdatei prüfen. Die Ausgabedatei muss reiner Klartext ohne Original-Metadaten sein.
5. Testen, dass Kopieren/Speichern **bis zur manuellen Bestätigung deaktiviert** ist und bei Bearbeitung erneut gesperrt wird.
6. Prüfen, dass beim Redact-Aufruf **keine externen HTTP-Requests** stattfinden.
7. Keine vertraulichen echten Texte ins CI, Repository, Logging oder Modelltrainingsdaten übertragen.

**Nicht Bestandteil:** PDF/OCR, Batch-Dateien, API-Anbindung an Frontier-LLMs, dauerhafte Entitätentabelle, Wiedereinsetzung von Namen, komplexe Risikoscores.
