# MVP-Spezifikation – Obsidian Inbox-Assistent

**Stand:** 13.10.2026 · **Status:** MVP implementiert, lokale Integration und Abnahme ausstehend  
**Scope:** Privates Windows-11-Experiment, kein Businessprodukt.

## Zielbild und Entscheidungsverlauf

Eine bereits vorhandene Obsidian-Inbox soll schneller, zuverlässig und **ohne Umstrukturierung des Vaults** geleert werden. Der Assistent liest Inbox-Dateien, lernt die individuelle Ablagelogik aus **ausgewählten bereits einsortierten Referenznotizen**, schlägt einen **primären vorhandenen Zielordner plus höchstens zwei Alternativen** vor und verschiebt bestätigte Dateien **erst nach einer zweiten, ausdrücklichen Freigabe in Obsidian**.

Die Entscheidungen des Eigentümers:
1. Ziel **A**: für jede Inbox-Notiz vorhandenen Zielordner vorschlagen.
2. Lernbasis **B**: bestehende Ordner **und** eingeordnete Notizen verwenden.
3. Referenzen **C**: automatische Auswahl mit Möglichkeit zum **Bevorzugen/Ausschließen**.
4. Mehrdeutigkeit **A**: **ein** Primärordner, höchstens zwei Alternativen.
5. Freigabe **B**: Nach separater Freigabe tatsächliche Verschiebung.
6. Obsidian-Integration **A**: Obsidian ist bei Verschiebungen geöffnet.

## Verbindliche lokale Pfade

| Funktion | Exakter Windows-Pfad |
|---|---|
| Vault | `C:\Users\user\Documents\104_0Admin_Projektordner\1010_Obsidian_0Admin-OS` |
| Inbox | `C:\Users\user\Documents\104_0Admin_Projektordner\1010_Obsidian_0Admin-OS\ZZZZZ_Inbox_noch_Einzuordnen` |
| Repo | `C:\Users\user\Documents\GitHub\Jevos-v4` |

`config.example.json` enthält diese Pfade. Eine optionale `config.json` (ignoriert in Git) überschreibt sie für einen isolierten Test-Vault. **Die Pfade niemals raten oder ungefragt ersetzen.**

## Funktionale Anforderungen

| ID | Anforderung | Implementierter Mechanismus |
|---|---|---|
| F01 | Direkt in der Inbox liegende Markdown-Dateien erkennen, niemals beim Scannen ändern | `VaultIndex` |
| F02 | Vorhandene Zielordner (auch verschachtelt) ermitteln; Inbox und Systemordner ausschließen | `VaultIndex.folders` |
| F03 | Namen und Inhalte der Inbox-Notizen berücksichtigen | Token-basierte Vorauswahl + Modell-Choice |
| F04 | Für relevante Ordner geeignete vorhandene Notizen automatisch als Referenzen vorschlagen | `pick_references` |
| F05 | Referenzen korrigieren, ausschließen, bevorzugen, lokal merken | Referenz-Panel, `assistant-state.json` |
| F06 | Vor der KI-Abfrage wenige Zielkandidaten anhand vorhandener Daten auswählen | maximal 8 + Option `none` |
| F07 | Primärer vorhandener Zielordner und maximal zwei Alternativen | `analyze` |
| F08 | Keine sichere Ablage ausdrücklich zulassen | `manual_review` |
| F09 | Jev Cloud oder jevos-v4 lokal **explizit** auswählen; kein paralleler Betrieb/Fallback | getrennte Clients |
| F10 | Cloud-Übertragung nur mit expliziter Zustimmung | Checkbox und Bestätigungsdialog |
| F11 | Ergebnisse in kompakter lokaler Oberfläche anzeigen; Inhalte bei Bedarf ansehen | `ui.html` |
| F12 | Empfehlung bestätigen, vorhandenen Ordner korrigieren oder zurückstellen | `/api/decide` |
| F13 | Entscheidungen nach Neustart verfügbar halten, bei Notizänderung ungültig | lokaler SHA-256-gebundener Status |
| F14 | Freigegebene Verschiebungen und Ziele vorab zeigen | Browser-Bestätigungsdialog |
| F15 | Vollständigen Vault außerhalb des Vaults sichern, ZIP-Integrität prüfen | `backup_vault` |
| F16 | Erst anschließend einen Ausführungsplan erzeugen, **noch nicht verschieben** | `.local/bridge/pending.json` |
| F17 | Verschiebung im geöffneten Obsidian separat bestätigen | Plugin-Palette-Befehl + Modal |
| F18 | Mit `app.fileManager.renameFile()` verschieben, damit Obsidian interne Links gemäß Einstellung anpasst | `obsidian-plugin/main.js` |
| F19 | Dateien einzeln auf Änderung und Namenskonflikte prüfen; bei Fehler Rest stoppen | Bridge-Preflight + erneuter Check |
| F20 | Ergebnis jeder Operation lokal protokollieren | `.local/bridge/result.json` |
| F21 | Ausstehenden noch nicht ausgeführten Stapel abbrechen können | `/api/cancel` |
| F22 | Freigaben bei geänderten Referenzen zurücksetzen; ausstehende Stapel sperren weitere Änderungen | `InboxService` |

**Bewusste technische Interpretation:** Die „Ablagelogik“ wird nicht durch Fine-Tuning gelernt. Der lokale Algorithmus sucht ein begrenztes Set fachlich ähnlicher Referenznotizen; das gewählte Entscheidungsmodell bewertet die Kandidaten. Die referenzierten Notizen dürfen vor einer neuen Analyse korrigiert werden.

## Nichtfunktionale Anforderungen

| ID | Anspruch | Konkrete Umsetzung |
|---|---|---|
| N01 | Lokal und ohne Cloud nutzbar | `jevos-v4` auf `127.0.0.1:8017`; Server/UI lokal |
| N02 | Getrennte externe Übertragung | Jev nur über `api.typesafe.ai`, explizites Opt-in pro Analyse |
| N03 | Schreibschutz im Normalbetrieb | Scan, Analyse, Vorschau und Freigaben schreiben nicht in den Vault |
| N04 | Schutz bestehender Notizen | Kein Überschreiben; SHA-256 vor Ausführung; ZIP-Backup vor Freigabe |
| N05 | Schutz interner Verknüpfungen | Umzug durch Obsidian-Dateimanager, keine externen Python-Moves |
| N06 | Minimaler Stack | Python-Standardbibliothek für UI/Orchestrierung; Vanilla-JS-Obsidian-Plugin |
| N07 | Bedienbarkeit | Browser-basierter 3-Schritt-Workflow ohne Terminal im Regelbetrieb |
| N08 | Nachvollziehbarkeit | Modelle, Vorschläge, Wahrscheinlichkeiten, Referenzen, Benutzerentscheidungen |
| N09 | Reproduzierbarkeit | Gleiche Ordner-Kandidaten und Entscheidungsprompts für beide Provider |
| N10 | Versionssicherheit | Projektcode Git, Vault-Daten und API-Key niemals in Git |

## Grenzen und zu validierende Annahmen

- Die automatisierte Kandidatenauswahl ist **lexikalisch**, keine Embedding-Suche. Bei unterschiedlichen Schreibweisen, Synonymen oder schwacher thematischer Überlappung kann sie den richtigen Ordner verpassen. Der Benutzer kann jeden vorhandenen Ordner als Korrektur wählen.
- Im MVP werden maximal **50** direkt unter der Inbox liegende Notizen je Analyse ausgewertet. Referenzindex: maximal **50 Markdown-Notizen pro Ordner**. Dieser Rahmen dient der kontrollierten ersten Nutzung, nicht maximaler Skalierbarkeit.
- Die Vorauswahl basiert auf Dateinamen, Ordnerpfaden und Textüberlappung. Pro Kandidatenordner gehen höchstens zwei gekürzte Referenzbeispiele an das gewählte Modell.
- **Nicht als kalibrierte Verlässlichkeit betrachten:** Choice-Wahrscheinlichkeiten und Modell-Confidence reichen allein nicht zur automatischen Dateifreigabe. Werte unter 0,45, knappe Abstände sowie schwache Kandidatenübereinstimmung werden als „Manuell prüfen“ gekennzeichnet. Diese Schwellen sind heuristische Startwerte.
- Das Projekt ist auf Obsidian Desktop ausgelegt. Die Obsidian-Einstellung zum Aktualisieren interner Links muss im Test-Vault validiert werden.
- Lokale Backups sind Kopien **außerhalb** des Vaults; externe Sicherungsstrategie liegt beim Anwender.
- **Keine Outlook-Anbindung im MVP.** Spätere Erweiterung getrennt.
- **Kein generativer Chatbot:** Jev und jevos-v4 treffen strukturierte Entscheidungen. Die Anzeige nennt verwendete Referenzen, aber keine frei generierten Begründungen.
- Es wurden keine echten Vault-Daten in CI verwendet; alle Datensätze sind synthetisch.

## Abnahmetests

| Test | Erwartung |
|---|---|
| T01 – Datenquellen | Echte Inbox und vorhandene Ordner korrekt erkannt, ohne Dateischreibzugriff |
| T02 – Referenzsteuerung | Automatisch gewählte Referenzen erscheinen und können bevorzugt/ausgeschlossen werden |
| T03 – Modellwahl | Jeder Lauf nutzt ausschließlich den explizit gewählten Provider |
| T04 – Cloud-Einwilligung | Ohne ausdrückliche Freigabe keine Übertragung von Vault-Inhalten |
| T05 – Zielordner | Nur vorhandene Ordner, höchstens 3 Vorschläge oder manuelle Prüfung |
| T06 – Benutzereingriff | Hauptvorschlag bestätigen, Ziel ändern, Notiz zurückstellen |
| T07 – Wiederanlauf | Lokale Entscheidungen wiederhergestellt, veränderte Notizen nicht mehr freigegeben |
| T08 – Sicherung | Vollständiges ZIP erstellt, Integrität/Prüfsumme geprüft |
| T09 – Zwei Freigaben | Keine Verschiebung im Python-Prozess; erst Plugin-Befehl mit zusätzlichem Dialog führt aus |
| T10 – Konflikte | Gleichnamige Datei niemals überschrieben |
| T11 – Linkschutz | Bestehende Wikilinks und Markdown-Links im Test-Vault bleiben nach Verschiebung funktionsfähig |
| T12 – Fehlerfall | Ergebnisprotokoll korrekt; bei Fehler keine weiteren Verschiebungen |
| T13 – Abbruch | Nicht ausgeführter Stapel kann verworfen werden, ohne Notizen zu ändern |
| T14 – Datenqualität | 20–30 realen Notizen manuelle Top-1/Top-3-Bewertung gegenüberstellen |

**Zielmessung:** Top-1-Trefferquote, Top-3-Trefferquote, Anteil manueller Prüfungen, Zeitaufwand je Notiz und Unterschiede Jev vs. jevos-v4. Ohne Testdatensatz wird kein pauschales Qualitätsziel behauptet.

## Nicht Bestandteil

Automatisches Verschieben ohne Freigabe, selbstständige Zielordnererzeugung, Modifikation von Notizinhalten, Tags, Outook-Anbindung, Hintergrundüberwachung, Modell-Fine-Tuning, Cloud-Datenspeicher und komplexes Dashboard.
