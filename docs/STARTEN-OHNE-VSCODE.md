# Jevos starten – ohne VS Code

Der Windows-Ein-Klick-Launcher startet den lokalen Python-Server bei Bedarf **im Hintergrund** und öffnet anschließend die Oberfläche im Standardbrowser. Läuft der Server bereits, wird nur der Browser geöffnet.

## Desktop-Button

Einmal in PowerShell im Repository ausführen:

```powershell
cd C:\Users\user\Documents\GitHub\Jevos-v4
powershell -ExecutionPolicy Bypass -File .\scripts\create-desktop-shortcut.ps1 -Force
```

Danach **Jevos - KI-Assistent** auf dem Desktop doppelklicken. Die Inbox-Ansicht öffnet sich im Standardbrowser. Über den Link in der Oberfläche kannst du die Textbereinigung erreichen.

Der alte Desktop-Button zu `start-ui.ps1` öffnete nur ein Terminal. Mit dem obigen Befehl erhältst du eine Verknüpfung zum neuen `launch-ui.ps1`. Eine Verknüpfung unter anderem Namen bleibt bestehen und muss manuell gelöscht werden, wenn du sie nicht mehr willst.

## Direkt aus Obsidian

Das bestehende Plugin **Jev Inbox Bridge** besitzt nun zwei anklickbare Symbole in der linken Leiste:

- **Bot** – aktuelle Inbox-Notiz in Obsidian einordnen.
- **Schild** – Textauswahl oder aktuelle Notiz für KI vorbereiten.

Beide Aktionen stehen außerdem in der Befehlspalette und im Editor-Kontextmenü. Ohne Markdown-Notiz erscheint eine Meldung. Der lokale Dienst startet bei Bedarf ohne zusätzliche Browserseite.

**Einordnen:** Nur Markdown-Dateien direkt in der konfigurierten Inbox des konfigurierten Vaults sind erlaubt. Aktuelle Editoränderungen werden vorher über Obsidian gespeichert. Im Dialog „Vorschlag berechnen“ wählen und die Zielordner sowie verwendeten Originalpassagen prüfen. Bei Unsicherheit einen vorhandenen Zielordner selbst auswählen. „Bestätigen und sichern“ bestätigt ausschließlich diese Notiz und erstellt ein Notiz- und Canvas-Backup. Erst im zweiten Dialog „Jetzt verschieben“ wählen. Abbrechen entfernt den Einzelplan; das Backup bleibt erhalten. Änderungen nach der Analyse und vorhandene Zieldateien verhindern eine unzulässige Verschiebung.

**Für KI vorbereiten:** Eine nicht leere Markierung hat Vorrang, andernfalls wird der gesamte aktuelle Editorinhalt übernommen; die Leseansicht übergibt die ganze Notiz. Die Bereinigungsansicht öffnet sich mit Herkunftsanzeige und automatischer Vorschau. Originalnotizen werden durch diese Aktion weder gespeichert noch ersetzt. Die Übergabe liegt ausschließlich im Arbeitsspeicher, ist einmalig und verfällt nach fünf Minuten. Die URL enthält nur eine zufällige ID. Maximal 100.000 Zeichen sind erlaubt. Die bereinigte Arbeitskopie kann korrigiert werden und muss vor Kopieren oder Export geprüft werden. Fehlende Dienste oder spaCy-Modelle werden als Fehler angezeigt; es gibt keine automatische Cloud-Umschaltung und keine Garantie vollständiger Anonymität.

Die bisherigen allgemeinen Webansichten bleiben über „Jevos Inbox-Assistent öffnen“ und „Jevos Textbereinigung öffnen“ in der Befehlspalette erreichbar.

**Wichtig:** Ein Obsidian-Plugin wird immer pro Vault installiert. Wenn deine `config.json` noch auf den Test-Vault zeigt, installiert der bisherige Standardbefehl das Plugin ausschließlich dort.

### Plugin im konfigurierten Vault aktualisieren

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-obsidian-plugin.ps1 -Force
```

### Buttons im tatsächlich genutzten Obsidian-Vault anzeigen

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-obsidian-plugin.ps1 -VaultPath "C:\Users\user\Documents\104_0Admin_Projektordner\1010_Obsidian_0Admin-OS" -Force
```

Dieser zweite Befehl kopiert ausschließlich die Plugin-Dateien nach `.obsidian\plugins\jev-inbox-bridge`. Er verändert keine Notizen und ändert **nicht** die `config.json`. Für die Einordnung müssen geöffneter und konfigurierter Vault übereinstimmen; die Textbereinigung funktioniert unabhängig davon.

Im richtigen Vault unter **Einstellungen → Community-Plugins** die Erweiterung **Jev Inbox Bridge** aktivieren oder nach dem Update einmal deaktivieren und wieder aktivieren. Danach erscheinen die zwei Symbole. Zusätzlich lassen sie sich über die Obsidian-Befehlspalette aufrufen.

## Betriebsweise und Sicherheit

- Die Oberfläche läuft weiterhin nur unter `http://127.0.0.1:8765/` und `/anonymize`.
- Deine vorhandene `.env` wird beim Serverstart von `start-ui.ps1` gelesen. Das Plugin liest den Schlüssel selbst nicht.
- Der lokale jevos-v4-**Modellserver** ist unabhängig und muss bei Bedarf weiterhin separat gestartet werden; die **Textbereinigung** braucht ihn nicht.
- Der gestartete Python-Webserver bleibt im Hintergrund, bis er beendet oder Windows neu gestartet wird.
- Beim Einordnen werden Editoränderungen vor der Analyse gespeichert. Verschiebungen bleiben durch den bestehenden Zwei-Freigaben-Prozess geschützt. Die Textbereinigung verändert die Originalnotiz nicht.
- Die Windows- und Obsidian-Einbindung ist erst nach Test auf dem eigenen PC vollständig abgenommen.

## Fehlerbehebung

- **Kein Symbol in Obsidian:** Wurde das Plugin im aktuell geöffneten Vault installiert und danach aktiviert bzw. neu geladen?
- **Ein Terminal statt Browser:** Die alte Desktop-Verknüpfung zeigt noch auf `start-ui.ps1`; neue Verknüpfung erzeugen oder das Ziel korrigieren.
- **Server öffnet sich nicht:** Port 8765, PowerShell und Python prüfen. Der Ein-Klick-Launcher zeigt bei Fehlern eine Windows-Meldung an.
- **Klick ohne Reaktion:** Das Plugin meldet auch PowerShell-Startfehler und fehlgeschlagene Exitcodes direkt in Obsidian. Nach einem Plugin-Update die Erweiterung neu laden.
- **Nur Test-Vault-Daten sichtbar:** Das liegt an deiner lokalen `config.json`, nicht am Launcher. Produktiven Vault nur nach separater Entscheidung konfigurieren.

Der Hintergrundstart fragt nicht nach einem API-Schlüssel. Ohne vorhandenen Schlüssel bleibt die Oberfläche lokal nutzbar; der manuelle Start mit `start-ui.ps1` behält seine optionale Abfrage. Die Skripte werden in CI auch unter Windows PowerShell 5.1 geprüft, das Obsidian tatsächlich aufruft. In ausführbarem PowerShell-Text sind insbesondere typografische Zeichen in UTF-8-Dateien ohne BOM zu vermeiden.
