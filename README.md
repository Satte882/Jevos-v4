# Obsidian Inbox-Assistent – Jev Cloud oder jevos-v4 lokal

**Privates Windows-11-MVP.** Der Assistent empfiehlt für noch nicht eingeordnete Obsidian-Markdown-Notizen einen **bestehenden** Zielordner (bis zu zwei Alternativen), lernt die Ablagelogik aus ausgewählten bestehenden Notizen und verschiebt **ausschließlich nach zwei expliziten Freigaben** über Obsidian. Keine automatische Verarbeitung im Hintergrund.

**Status:** GitHub-Unit-Tests werden automatisiert ausgeführt. **Windows-Modellstart, echte Jev-API-Abfragen, Obsidian-Plugin und Link-Aktualisierung müssen lokal getestet werden.** Vor produktiven Verschiebungen einen synthetischen Test-Vault verwenden.

## Neu: Text für externe KI bereinigen

Unter `http://127.0.0.1:8765/anonymize` gibt es eine **eigenständige lokale Textbereinigung**. Text einfügen oder TXT/MD/DOCX importieren, mit deutschem spaCy-NER und Erkennungsregeln bereinigen, Ergebnis manuell kontrollieren und als reinen Text kopieren oder speichern. **Kein Frontier-LLM, Jev oder TypeSafe wird dazu kontaktiert.** Der Obsidian-Inbox-Assistent bleibt unverändert.

**Einmalig spaCy und das lokale deutsche Modell installieren:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-redaction.ps1
```

Danach `scripts/start-ui.ps1` neu starten. Details, Grenzen und lokales Abnahmeverfahren: [Textbereinigung – Anleitung](docs/TEXTBEREINIGUNG.md).

**Datenschutz-Hinweis:** Automatisches Ersetzen identifizierender Stellen ist keine nachgewiesene vollständige Anonymisierung. Vor der Weitergabe des Textes an ChatGPT, Claude oder andere Cloud-Modelle ist eine manuelle Prüfung erforderlich.

## Vorhandene Pfade (bereits festgelegt)

| Verwendung | Pfad |
|---|---|
| Obsidian-Vault | `C:\Users\user\Documents\104_0Admin_Projektordner\1010_Obsidian_0Admin-OS` |
| Inbox | `C:\Users\user\Documents\104_0Admin_Projektordner\1010_Obsidian_0Admin-OS\ZZZZZ_Inbox_noch_Einzuordnen` |
| Lokales Git-Repo (derzeit leer) | `C:\Users\user\Documents\GitHub\Jevos-v4` |

In `config.example.json` vorkonfiguriert. Für den sicheren Test-Vault optional `config.json` anlegen; sie wird nicht in Git eingecheckt.

## Einmaliger Windows-Start

**Voraussetzungen:** Git, Python 3.11+, Obsidian Desktop. Node ist nur für den Plugin-Syntaxcheck in CI nötig.

In **PowerShell**:

```powershell
cd C:\Users\user\Documents\GitHub\Jevos-v4
git clone https://github.com/Satte882/Jevos-v4.git .
py -3 -m unittest discover -s tests -v
powershell -ExecutionPolicy Bypass -File .\scripts\start-ui.ps1
```

Dann `http://127.0.0.1:8765` im Browser öffnen.

Das Skript fragt **optional** verdeckt nach deinem TypeSafe-Key, falls Jev Cloud in dieser Sitzung benutzt werden soll. Ohne Key läuft nur der lokale Anbieter (nach separater Modellinstallation). **API-Schlüssel niemals ins Repo oder in den Chat schreiben.**

### TypeSafe-Key dauerhaft lokal hinterlegen (.env)

Lege im Repository-Hauptordner eine Datei mit dem **exakten** Namen `.env` an:

```dotenv
TYPESAFE_API_KEY=DEIN_PERSOENLICHER_API_KEY
```

Beim nächsten Start mit `scripts/start-ui.ps1` wird **nur** diese Variable eingelesen. Die Eingabeaufforderung entfällt; der Wert wird weder angezeigt noch nach dem Beenden als von diesem Skript gesetzte Umgebungsvariable behalten. Eine bereits gesetzte Umgebungsvariable `TYPESAFE_API_KEY` hat Vorrang. `.env` ist bereits in `.gitignore` ausgeschlossen und darf niemals eingecheckt oder geteilt werden. Der Schlüssel liegt darin **unverschlüsselt** und sollte nur unter deinem Windows-Benutzerkonto zugänglich sein.

Die Checkbox und Freigabe für die tatsächliche Übertragung von Inbox-Daten an **Jev · TypeSafe Cloud** bleiben unverändert notwendig. Für die neue lokale Textbereinigung ist kein API-Key erforderlich.

### Jev Cloud testen – ohne lokale Modellinstallation

Beim Start `J` auswählen und den privaten TypeSafe-Key verdeckt eingeben. Im Browser **Jev Cloud** wählen und bei der Analyse die Cloud-Übertragung explizit freigeben. Bei Bedarf zunächst nur fünf **synthetische** Notizen in einem Test-Vault verwenden. An TypeSafe gesendete Notizen und Referenztexte verlassen den Rechner; mögliche API-Kosten beachten.

### jevos-v4 lokal testen – einmalig installieren

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-jev.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-jev.ps1
```

Das zweite Kommando **im eigenen PowerShell-Fenster geöffnet lassen**. Es startet den CPU-Modellserver unter `127.0.0.1:8017`. Im Browser anschließend **jevos-v4 lokal** wählen. Das Installationsskript lädt offizielle Release-Dateien vom 04.10.2026 herunter und prüft SHA-256-Prüfsummen.

## Ablauf in drei Schritten

1. **Inbox analysieren.** Modellanbieter explizit wählen. Der lokale Index untersucht Ordner, ausgewählte Referenznotizen und ermittelt maximal acht Zielkandidaten. Das Modell trifft eine Choice-Entscheidung. Eine schwache oder mehrdeutige Entscheidung wird mit „Manuell prüfen“ markiert.
2. **Vorschläge prüfen.** Hauptordner bestätigen, beliebigen existierenden Ordner als Korrektur wählen oder zurückstellen. Automatisch gewählte Referenznotizen im Panel bevorzugen/ausschließen; anschließend neu analysieren.
3. **Freigegebene Notizen verschieben.** Im Browser Stapel bestätigen und vollständigen Vault als ZIP außerhalb des Vaults sichern. Dann in **geöffnetem Obsidian** den Befehl **„Freigegebene Inbox-Verschiebungen anwenden“** aufrufen und **dort separat bestätigen**. Erst das Obsidian-Plugin führt `app.fileManager.renameFile()` aus und schreibt das Ergebnis.

**Ohne aktiviertes Obsidian-Plugin werden niemals Dateien verschoben.**

### Obsidian-Plugin installieren (erst Test-Vault!)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-obsidian-plugin.ps1
```

Das Skript liest den Vault-Pfad aus `config.json` (falls vorhanden), ansonsten aus `config.example.json`, und kopiert `manifest.json` und `main.js` in `.obsidian\plugins\jev-inbox-bridge`. In Obsidian **Community-Plugins aktivieren** und die Erweiterung **Jev Inbox Bridge** anschalten. Bei einem späteren bewussten Plugin-Update `-Force` angeben.

**Vor dem ersten echten Einsatz:** Im Test-Vault zwei verlinkte Notizen erstellen, eine zur Verschiebung freigeben und die Links prüfen. Die vorhandene Obsidian-Einstellung zur automatischen Link-Aktualisierung beeinflusst das Ergebnis.

## Sicherheit und Datenhaltung

- Die Oberfläche ist nur auf `127.0.0.1:8765` erreichbar; API-Änderungen erfordern ein Sitzungstoken, Cloud zusätzlich ein ausdrückliches Opt-in.
- Die **Originalnotizen** werden beim Scannen, Vorschlagen und Freigeben niemals verändert. Dateien dürfen nur direkt in der konfigurierten Inbox liegen.
- Vor dem Versand eines Plans werden Kollisionen und SHA-256-Prüfsummen geprüft; das **vollständige** Vault-Backup wird lokal als ZIP geprüft. Das Obsidian-Plugin prüft Plan, Backup und Dateien nochmals und stoppt beim ersten Fehler.
- Ordner werden nicht neu angelegt; bestehende Dateien nicht überschrieben. Bei Abbruch bleibt das Backup erhalten.
- Lokale Ergebnisse, Backups, Schlüssel und Vault-Konfiguration dürfen nicht nach Git. `.local/` und `config.json` sind ignoriert.
- Jev/jevos-v4 bieten strukturierte **Noul, Choice, Score**-Entscheidungen. Hier nutzt das MVP hauptsächlich **Choice**. Das frühere CLI-Experiment bleibt optional erreichbar: `py -3 -m jevos_local --provider local demo --mode all` (oder `jev`).

## Dokumentation

- [Verbindliche fachliche und nichtfunktionale MVP-Spezifikation](docs/MVP-SPEZIFIKATION.md)
- [Konkreter Auftrag für den lokalen Coding-Agenten](docs/CODING_AGENT_HANDOFF.md)
- [Separate Outlook-Phase](docs/OUTLOOK.md)
- [Entscheidungsmodell-Verifikation](docs/VALIDIERUNG.md)

**Wichtigste Qualitätsprüfung:** Ob die lexikalische Zielkandidaten-Vorauswahl bei 20–30 echten Notizen den tatsächlich passenden Ordner überhaupt unter die acht Vorschläge bringt. Erst danach die KI-Qualität (Top-1/Top-3) beurteilen.

**Quellen:** [TypeSafe Console](https://console.typesafe.ai/keys) · [jevos-v4 Release](https://github.com/feder-cr/jev/releases/tag/jevos-v4) · [Obsidian API](https://github.com/obsidianmd/obsidian-api).
