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

- **Bot** – Inbox-Assistent im Browser öffnen.
- **Schild** – Textbereinigung im Browser öffnen.

Beide lösen denselben lokalen Launcher aus. Es wird kein separates Obsidian-Fenster für die Weboberfläche benötigt.

**Wichtig:** Ein Obsidian-Plugin wird immer pro Vault installiert. Wenn deine `config.json` noch auf den Test-Vault zeigt, installiert der bisherige Standardbefehl das Plugin ausschließlich dort.

### Plugin im derzeit konfigurierten Test-Vault aktualisieren

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-obsidian-plugin.ps1 -Force
```

### Buttons im tatsächlich genutzten Obsidian-Vault anzeigen

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-obsidian-plugin.ps1 -VaultPath "C:\Users\user\Documents\104_0Admin_Projektordner\1010_Obsidian_0Admin-OS" -Force
```

Dieser zweite Befehl kopiert ausschließlich die Plugin-Dateien nach `.obsidian\plugins\jev-inbox-bridge`. Er verändert keine Notizen und ändert **nicht** die `config.json`, die weiterhin auf den Test-Vault zeigen darf.

Im richtigen Vault unter **Einstellungen → Community-Plugins** die Erweiterung **Jev Inbox Bridge** aktivieren oder nach dem Update einmal deaktivieren und wieder aktivieren. Danach erscheinen die zwei Symbole. Zusätzlich lassen sie sich über die Obsidian-Befehlspalette aufrufen.

## Betriebsweise und Sicherheit

- Die Oberfläche läuft weiterhin nur unter `http://127.0.0.1:8765/` und `/anonymize`.
- Deine vorhandene `.env` wird beim Serverstart von `start-ui.ps1` gelesen. Das Plugin liest den Schlüssel selbst nicht.
- Der lokale jevos-v4-**Modellserver** ist unabhängig und muss bei Bedarf weiterhin separat gestartet werden; die **Textbereinigung** braucht ihn nicht.
- Der gestartete Python-Webserver bleibt im Hintergrund, bis er beendet oder Windows neu gestartet wird.
- Die neue Obsidian-Bedienfunktion verändert **keine** Notizen. Verschiebungen bleiben durch den bestehenden Zwei-Freigaben-Prozess geschützt.
- Die Windows- und Obsidian-Einbindung ist erst nach Test auf dem eigenen PC vollständig abgenommen.

## Fehlerbehebung

- **Kein Symbol in Obsidian:** Wurde das Plugin im aktuell geöffneten Vault installiert und danach aktiviert bzw. neu geladen?
- **Ein Terminal statt Browser:** Die alte Desktop-Verknüpfung zeigt noch auf `start-ui.ps1`; neue Verknüpfung erzeugen oder das Ziel korrigieren.
- **Server öffnet sich nicht:** Port 8765, PowerShell und Python prüfen. Der Ein-Klick-Launcher zeigt bei Fehlern eine Windows-Meldung an.
- **Klick ohne Reaktion:** Das Plugin meldet auch PowerShell-Startfehler und fehlgeschlagene Exitcodes direkt in Obsidian. Nach einem Plugin-Update die Erweiterung neu laden.
- **Nur Test-Vault-Daten sichtbar:** Das liegt an deiner lokalen `config.json`, nicht am Launcher. Produktiven Vault nur nach separater Entscheidung konfigurieren.

Der Hintergrundstart fragt nicht nach einem API-Schlüssel. Ohne vorhandenen Schlüssel bleibt die Oberfläche lokal nutzbar; der manuelle Start mit `start-ui.ps1` behält seine optionale Abfrage. Die Skripte werden in CI auch unter Windows PowerShell 5.1 geprüft, das Obsidian tatsächlich aufruft. In ausführbarem PowerShell-Text sind insbesondere typografische Zeichen in UTF-8-Dateien ohne BOM zu vermeiden.
