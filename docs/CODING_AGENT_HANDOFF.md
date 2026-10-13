# Handoff an lokalen Windows-Coding-Agenten

**Arbeitsmodus:** Bestehendes Repository `Satte882/Jevos-v4` auf lokalen Windows-Rechner holen, installieren, gegen isolierten Test-Vault prüfen, anschließend erst mit echten Daten verwenden. **Kein Redesign und keine Scope-Erweiterung.**

## Bereits bekannte Pfade – nicht erneut fragen

- **Original-Vault:** `C:\Users\user\Documents\104_0Admin_Projektordner\1010_Obsidian_0Admin-OS`
- **Original-Inbox:** `C:\Users\user\Documents\104_0Admin_Projektordner\1010_Obsidian_0Admin-OS\ZZZZZ_Inbox_noch_Einzuordnen`
- **Leerer lokaler Repo-Ordner:** `C:\Users\user\Documents\GitHub\Jevos-v4`
- **Remote:** `https://github.com/Satte882/Jevos-v4`

Diese exakten Pfade stehen in `config.example.json`. Lokale Abweichungen nur nach tatsächlicher Prüfung, nicht durch Vermutung.

## Auftrag

1. Im **bereits existierenden leeren Repo-Ordner** das GitHub-Projekt holen: `cd C:\Users\user\Documents\GitHub\Jevos-v4` und `git clone https://github.com/Satte882/Jevos-v4.git .`. Falls der Ordner entgegen der Angabe nicht leer ist, **nichts überschreiben**; Zustand prüfen und `git fetch` verwenden, wenn bereits der richtige Klon existiert.
2. `py -3 -m unittest discover -s tests -v` und `node --check obsidian-plugin/main.js` ausführen. Python 3.11+ und Node sind für den Syntaxcheck nötig; Node wird zur Laufzeit des Python-Servers **nicht** benötigt.
3. `config.example.json` und `docs/MVP-SPEZIFIKATION.md` lesen; verifizieren, dass Vault und Inbox wirklich vorhanden sind.
4. Für gefahrlose Ende-zu-Ende-Abnahme zunächst **synthetischen Test-Vault** z. B. unter `.local\test-vault` samt `.obsidian`, Inbox und mindestens zwei Zielordnern erstellen; mit einfachen Markdown-Notizen und internen Links bestücken.
5. Eine **ignorierte** `config.json` mit Test-Vault-Pfaden anlegen. Erst damit UI und Plugin testen; beim Test `scripts/install-obsidian-plugin.ps1` nutzt ebenfalls `config.json`. Originaldateien dürfen nicht verschoben oder verändert werden.
6. Für **Jev Cloud** kann mit synthetischen Beispielen ohne lokale Modellinstallation gearbeitet werden. Der Anwender hat einen API-Key; diesen beim Start über `scripts/start-ui.ps1` **verdeckt eingeben**, **niemals** im Chat, Quellcode oder Git ablegen. Provider `jev` und explizite Cloud-Zustimmung wählen.
7. Für **jevos-v4 lokal** `scripts/install-jev.ps1` (SHA-256-geprüfter Download) und `scripts/start-jev.ps1` in eigenem PowerShell-Fenster ausführen. Browser-App separat über `scripts/start-ui.ps1` starten.
8. Plugin im Test-Vault installieren und in Obsidian unter Community-Plugins aktivieren. Im Browser erst freigeben und vorbereiten; im Obsidian-Kommandomenü `Freigegebene Inbox-Verschiebungen anwenden` separat bestätigen. Link-Integrität und `.local/bridge/result.json` prüfen.
9. Nach grünem Test eine manuell kontrollierte **lesende** Bestandsaufnahme des Original-Vaults durchführen. Für den produktiven Betrieb `config.json` auf die oben exakt genannten Pfade umstellen und Plugin bewusst im Original-Vault installieren und aktivieren.
10. Zunächst im echten Vault **nur analysieren und prüfen**. Eine tatsächliche Verschiebung erst nach Benutzerbestätigung und vorhandenem Backup.

## Fehlerbehandlung und technische Prüfung

- Die Verwendung der **offiziellen** TypeSafe-API `https://api.typesafe.ai/v1/systemone` und die Jev-kompatible lokale Schnittstelle `127.0.0.1:8017` anhand echter Antworten verifizieren. Bei API-Schemaabweichungen nur den betreffenden Client anpassen, keine Modellresultate erfinden.
- Obsidian-Links nach `app.fileManager.renameFile()` gemäß Vault-Einstellung mit `[[...]]` und `[...](...)` im Test-Vault prüfen.
- Wenn das Repo nach Clonen neue Commits enthält: aktuelle Version und CI prüfen, nicht blind frühere Dateien überschreiben.
- Python-Seite erzeugt nur ein Backup und einen Plan; echte Verschiebung findet **ausschließlich** im Plugin nach eigener Bestätigung statt.
- `config.json`, `.local/`, Vault-Dateien, TypeSafe-Key und Backups niemals committen.
- Keine neuen Features (Outlook, Tags, Agentensysteme, n8n) ohne ausdrücklichen Auftrag.

## Eine erste echte Validierungsfrage

**Wie gut schlägt die Vorauswahl die richtigen Zielordner deines tatsächlichen Vaults vor?** Das vorliegende Lexical Matching ist bewusst klein und einfach. Wenn der richtige Ordner nicht unter den acht Kandidaten ist, zuerst an repräsentativen Beispielen die Kandidatenauswahl verbessern statt das KI-Modell zu wechseln.

## Aktueller Codeaufbau

- `inbox_assistant/index.py`: Inbox, Ordner, Referenzen und lexikalische Kandidaten
- `inbox_assistant/service.py`: Provideraufrufe, Ablageempfehlung, Freigaben
- `inbox_assistant/bridge.py`: Backup, Vorschau und Obsidian-Stapel
- `inbox_assistant/web.py` / `ui.html`: lokaler Browser-Workflow
- `obsidian-plugin/main.js`: Obsidian-Ausführung über `FileManager.renameFile`
- `jevos_local/client.py`: Jev Cloud / jevos-v4 Client
- `tests/test_inbox.py`: synthetische funktionale Tests

**Erfolgreiche Arbeit gilt erst dann als abgeschlossen, wenn die lokale Installation und Test-Vault-Abnahme tatsächlich grün sind.** GitHub-CI allein prüft nicht die lokale Obsidian-Installation oder echte TypeSafe-Zugangsdaten.
