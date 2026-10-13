# Jevos-v4 – Obsidian Inbox-Assistent und lokale Textbereinigung

**Privates Windows-11-Projekt mit zwei Funktionen:**

1. **Obsidian Inbox-Assistent:** Jev Cloud oder das lokale Modell `jevos-v4` schlägt für noch nicht eingeordnete Markdown-Notizen einen **bestehenden Zielordner** vor. Ein lokaler Index wählt dafür relevante Referenznotizen aus; **das Modell wird nicht trainiert**. Unsichere Zuordnungen bleiben offen. Verschiebungen erfolgen ausschließlich nach einer Freigabe im Browser **und** einer weiteren Freigabe im Obsidian-Plugin.
2. **Text für externe KI bereinigen:** spaCy (`de_core_news_md`), Regex und Python erkennen und ersetzen lokal ausgewählte personenbezogene bzw. sensible Angaben. **Hier kommt kein Jev zum Einsatz.** Die bereinigte Fassung muss vor dem Kopieren oder Speichern geprüft und ausdrücklich freigegeben werden.

**Status (Oktober 2026):** Windows-Start, lokaler Modellbetrieb, Jev-Cloud-Anbindung, Obsidian-Plugin und Notizverschiebungen einschließlich Backup und Link-Aktualisierung wurden lokal mit synthetischen Testdaten abgenommen. Wiederholungstests für drei Notizen/Dateien wurden erfolgreich berichtet; Originaldateien blieben unverändert. GitHub Actions prüfen Python-, JavaScript-, Plugin- und PowerShell-Regressionsfälle unter Windows und Ubuntu. **Die fachliche Qualität jeder neuen Ordnerempfehlung ist damit nicht garantiert** – gerade mehrdeutige Ziele erfordern weiterhin deine Entscheidung.

## Tägliche Nutzung – ohne VS Code

Den **Jevos – KI-Assistent**-Button auf dem Windows-Desktop oder das **Bot-Symbol** im Obsidian-Plugin **Jev Inbox Bridge** anklicken. Falls nötig, startet der lokale Webserver im Hintergrund; anschließend öffnet sich die Oberfläche im Standardbrowser:

- **Inbox:** http://127.0.0.1:8765/
- **Textbereinigung:** http://127.0.0.1:8765/anonymize (auch über das Schild-Symbol in Obsidian)

Der lokale Modellserver `jevos-v4` unter `127.0.0.1:8017` ist **ein separater Prozess**. Er muss für Inbox-Analysen mit `jevos-v4 · lokal` laufen; die Textbereinigung und die Jev-Cloud-Variante benötigen ihn nicht.

Einmalig einen Desktop-Button erzeugen oder aktualisieren (PowerShell im Repository):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\create-desktop-shortcut.ps1 -Force
```

Die Obsidian-Erweiterung muss im **tatsächlich geöffneten Vault** installiert und unter **Einstellungen → Community-Plugins** aktiviert sein. Die Symbole öffnen die Browseroberflächen; das Plugin übernimmt weiterhin die gesondert freigegebenen Datei-Verschiebungen. **[Details zu Start, Plugin-Installation und Fehlerbehebung](docs/STARTEN-OHNE-VSCODE.md).**

## Installations- und Projektpfade

| Verwendung | Pfad |
|---|---|
| Obsidian-Vault | `C:\Users\user\Documents\104_0Admin_Projektordner\1010_Obsidian_0Admin-OS` |
| Inbox | `C:\Users\user\Documents\104_0Admin_Projektordner\1010_Obsidian_0Admin-OS\ZZZZZ_Inbox_noch_Einzuordnen` |
| Lokales Git-Repository | `C:\Users\user\Documents\GitHub\Jevos-v4` |

Die Pfade sind in `config.example.json` hinterlegt. Die **tatsächlich verwendeten** Vault- und Inbox-Pfade kommen aus der lokalen `config.json` (falls vorhanden) und werden oben im Inbox-Dashboard angezeigt. Eine Installation des Plugins in einem anderen Vault ändert diese Backend-Konfiguration **nicht**. `config.json` gehört nicht nach GitHub.

**Voraussetzungen für eine Neuinstallation:** Git, Python 3.11+, Obsidian Desktop; Node.js ist für die JavaScript-/Plugin-Tests hilfreich. Ist das Repository bereits geklont, **nicht erneut `git clone` im bestehenden Ordner ausführen**.

```powershell
cd C:\Users\user\Documents\GitHub\Jevos-v4
git pull --ff-only origin main
py -3 -m unittest discover -s tests -v
```

Manueller Start der Browseroberfläche, falls der Launcher nicht verwendet wird:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-ui.ps1
```

### Lokales Entscheidungsmodell installieren oder starten

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-jev.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-jev.ps1
```

Der zweite Befehl startet den Modellserver unter `127.0.0.1:8017` und bleibt in einem eigenen PowerShell-Fenster aktiv. `start-jev.ps1` verwendet vier CPU-Threads und kein Vorwärmen im Leerlauf. Das Installationsskript verifiziert die SHA-256-Prüfsummen der heruntergeladenen Release-Dateien. Für bereits installierte Modelle genügt der **Startbefehl**.

### TypeSafe-Key dauerhaft lokal hinterlegen

Optional eine Datei `.env` im Repository-Hauptordner anlegen:

```dotenv
TYPESAFE_API_KEY=DEIN_PERSOENLICHER_API_KEY
```

`start-ui.ps1` lädt den Key beim Start automatisch; eine bereits gesetzte Umgebungsvariable hat Vorrang. Beim manuellen Start kann ohne vorhandenen Key eine verdeckte Eingabe erfolgen; beim Ein-Klick-Hintergrundstart gibt es **keine Eingabeaufforderung**. `.env` ist gitignoriert, speichert den Schlüssel aber **unverschlüsselt**. Niemals committen, in Tickets kopieren oder teilen.

**Jev · TypeSafe Cloud** sendet ausgewählte Notizinhalte und Referenzpassagen erst nach ausdrücklicher Zustimmung und einer zusätzlichen Bestätigung. Dabei können API-Kosten entstehen. Es gibt keinen automatischen Modellwechsel.

### Textbereinigung einmalig einrichten

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-redaction.ps1
```

Dadurch werden spaCy und das deutsche Sprachmodell `de_core_news_md` in der lokalen Python-Umgebung installiert. TXT, MD und DOCX können eingelesen werden; die bereinigte Fassung ist manuell editierbar und als Text kopierbar oder als TXT exportierbar.

**Wichtig:** Das Verfahren bietet keine Garantie vollständiger Anonymität. Es kann Namen, indirekte Identifikatoren oder Geschäftsgeheimnisse übersehen. Vor der Weitergabe an ChatGPT, Claude oder andere externe Modelle ist der **gesamte Ausgabetext** manuell zu prüfen. Kein automatischer Versand an ein externes KI-Modell. [Anleitung und Grenzen](docs/TEXTBEREINIGUNG.md).

## Inbox-Workflow: Analysieren → Prüfen → Verschieben

1. **Analyse starten:** Jev-Provider und maximale Notizzahl wählen. Der lokale Index ermittelt zunächst bis zu **acht** Zielkandidaten; maximal **fünf** davon gehen an das Entscheidungsmodell. Je Ziel werden höchstens **zwei** Referenzpassagen à 180 Zeichen berücksichtigt. Bei langen Notizen werden relevante Originalpassagen aus dem gesamten Text (maximal 1.400 Zeichen) ausgewählt. Die Analyse läuft **nach manuellem Start** in einem Hintergrund-Thread mit Fortschritt pro Notiz, ohne dass die Oberfläche blockiert.
2. **Fundstellen und Vorschläge prüfen:** Links eine Inbox-Datei wählen; rechts Originalauszüge, bis zu drei Zielalternativen samt **Modellwerten (keine empirisch gemessenen Trefferquoten)** und die tatsächlich an das Modell übergebenen Referenzpassagen vergleichen. Der vollständige Notiztext lässt sich separat öffnen. Bei mehrdeutigen Zielen wird **kein Ordner vorausgewählt**. Bestätigen, einen anderen vorhandenen Ordner wählen oder zurückstellen. Referenznotizen können optional bevorzugt oder ausgeschlossen werden; danach erneut analysieren.
3. **Verschiebung vorbereiten und in Obsidian freigeben:** Nach Browser-Bestätigung wird ein vollständiges Vault-Backup als ZIP erstellt und ein Ausführungsplan gespeichert. Die tatsächliche Verschiebung erfolgt **erst** über den Obsidian-Befehl **„Freigegebene Inbox-Verschiebungen anwenden“** mit zweiter ausdrücklicher Bestätigung. Das Plugin übernimmt Verschieben und Aktualisieren interner Links.

Weitere Details: Archiv- und Backlog-Ordner sind bei der **automatischen Vorauswahl** standardmäßig ausgeschlossen, lassen sich aber explizit einbeziehen oder manuell als Ziel auswählen. Bei einer Neuanalyse werden alte Vorschläge und Freigaben der erneut analysierten Notizen zurückgesetzt; Fehler werden pro Notiz angezeigt. Die lokalen Ergebnisse sind unter `.local/vault-state/` **je Vault getrennt** gespeichert. Das Zeitlimit für eine lokale Modellabfrage beträgt 90 Sekunden; bei Verbindungs-/Zeitproblemen wird nicht unkontrolliert weiter angefragt.

**Ohne aktiviertes Obsidian-Plugin und zweite Freigabe werden keine Notizen verschoben.** Die Originaldateien bleiben während Analyse und Prüfung unverändert. Sicherheitsprüfungen umfassen Pfadgrenzen, Hashes, Zielkollisionen und Backup-Prüfung; es werden keine Zielordner angelegt oder Dateien überschrieben.

### Plugin installieren oder aktualisieren

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-obsidian-plugin.ps1 -Force
```

Standardmäßig liest der Installer den Vault-Pfad aus `config.json` (falls vorhanden), sonst aus `config.example.json`. Soll die Erweiterung in einem **anderen, ausdrücklich gewählten Vault** erscheinen, kann `-VaultPath "C:\Pfad\Zum\Vault"` ergänzt werden. Danach die Erweiterung in Obsidian aktivieren beziehungsweise einmal neu laden. Die lokale Abnahme mit Testnotizen und Link-Aktualisierung ist erfolgt; neue produktive Verschiebungen bleiben trotzdem freigabepflichtig.

## Sicherheit, Qualität und Dokumentation

- Lokale Oberfläche ausschließlich auf `127.0.0.1:8765`. API-Anfragen sind durch ein Sitzungstoken geschützt; Cloud-Zugriffe benötigen zusätzlich das Opt-in.
- Keine Änderung an Originalnotizen bei Vorschlag, Prüfung oder Zurückstellung. Backups, Schlüssel, lokale Ergebnisse und `config.json` bleiben außerhalb der Git-Versionsverwaltung.
- Das Projekt verwendet für die Ordnerauswahl `Choice`; `Noul` und `Score` sind weitere Jev-Primitives, werden hier aber nicht für diese Ablageentscheidung benötigt.
- Für Qualitätsvergleiche mit realistischen Beispielen bleibt wichtig: Ist der korrekte Zielordner überhaupt unter den vorausgewählten Kandidaten? Erst danach die Qualität der Jev-Reihung bewerten. Mehrdeutige Ziele werden bewusst nicht automatisch freigegeben.

**Dokumentation:** [MVP-Spezifikation](docs/MVP-SPEZIFIKATION.md) · [Coding-Agent-Handoff](docs/CODING_AGENT_HANDOFF.md) · [Modellvalidierung](docs/VALIDIERUNG.md) · [Lokaler Start](docs/STARTEN-OHNE-VSCODE.md) · [Textbereinigung](docs/TEXTBEREINIGUNG.md).

**Nicht geplant:** Die früher vorgesehene lesende Outlook-Anbindung ist kein Bestandteil der aktuellen Lösung; der Entwurf bleibt als [optionale Ideenskizze](docs/OUTLOOK.md) dokumentiert.

**Referenzen:** [TypeSafe Console](https://console.typesafe.ai/keys) · [jevos-v4 Release](https://github.com/feder-cr/jev/releases/tag/jevos-v4) · [Obsidian API](https://github.com/obsidianmd/obsidian-api).
