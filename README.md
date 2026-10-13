# Jevos-v4 – lokale KI-Entscheidungen unter Windows

Kleines privates Experiment: **Obsidian-Notizen nur lesend** untersuchen und mit `jevos-v4` drei Ja/Nein-Fragen beantworten: **Aufgabe**, **Idee**, **offene Entscheidung**. Läuft lokal auf der CPU, ohne Cloud-API, Python-Pakete oder GPU.

> **Abgrenzung:** Dieses Repository ist **nicht** das originale Jev-Modell. Es nutzt das unabhängig entwickelte Open-Source-Projekt [feder-cr/jev](https://github.com/feder-cr/jev). Die proprietäre Jev-API wird nur lokal nachgebildet. Jevos-v4 ist für englische Eingaben ausgelegt; deutsche Obsidian-Notizen sind ein **Experiment**, keine zugesicherte Funktion. Wahrscheinlichkeiten sind **keine kalibrierten Gewissheiten**.

## Windows-Schnellstart (PowerShell)

Voraussetzungen: **Windows 11 x64**, [Git](https://git-scm.com/download/win) und [Python 3.11+](https://www.python.org/downloads/windows/) (Befehl `py`). Installiert wird das offizielle Release vom **4. Oktober 2026**. Rund 650 MB Download, Modell und Binary bleiben in `.local/` (nicht in Git).

```powershell
git clone https://github.com/Satte882/Jevos-v4.git
cd Jevos-v4
py -3 -m venv .venv

# 1. Einmalig: offizielles Windows-Binary + Modell laden; SHA-256 prüfen
powershell -ExecutionPolicy Bypass -File .\scripts\install-jev.ps1

# 2. Lokalen Jevos-Server starten (dieses Fenster geöffnet lassen)
powershell -ExecutionPolicy Bypass -File .\scripts\start-jev.ps1
```

**Ein zweites PowerShell-Fenster** im selben Repository öffnen:

```powershell
.\.venv\Scripts\python.exe -m jevos_local health
.\.venv\Scripts\python.exe -m jevos_local demo
```

**Eigene Obsidian-Notizen testen** (Pfad durch den Speicherort deines Vaults ersetzen; z. B. über Obsidian → Einstellungen → Dateien und Links nachsehen):

```powershell
.\.venv\Scripts\python.exe -m jevos_local vault --vault "C:\Users\DEINNAME\Documents\Obsidian\MeinVault" --limit 20 --report "reports\ergebnis.csv"
```

Angezeigt werden nur **Dateipfad** und die drei **Ja-Wahrscheinlichkeiten**. Bei `--report` schreibt das Programm **ausschließlich** eine lokale CSV mit Dateipfaden und Wahrscheinlichkeiten außerhalb des Vaults; es kopiert **keine Notizinhalte** in diese CSV. Ohne `--report` erfolgt keine Ergebnisspeicherung. Das Tool ändert **niemals** die Notizen.

## Befehle

| Befehl | Funktion |
|---|---|
| `python -m jevos_local health` | Erreichbarkeit des lokalen Servers prüfen |
| `python -m jevos_local demo` | Sechs synthetische englische Beispielsätze klassifizieren |
| `python -m jevos_local vault --vault "C:\Pfad\Vault" --limit 20` | Bis zu 20 Markdown-Notizen nur lesend prüfen |
| `... --threshold 0.8` | Kennzeichnung „Ja“ erst ab 80 % (Standard: 75 %) |
| `... --report "reports\ergebnis.csv"` | Nur Pfad, Scores und Ja/Nein als lokale CSV speichern |

Der Server ist auf `http://127.0.0.1:8017` begrenzt. `JEV_API_KEY` kann optional als Umgebungsvariable für einen lokalen Server mit Bearer-Authentifizierung gesetzt werden. Kein externer Dienst wird aus Python aufgerufen.

## Grenzen und Datenschutz

- **Nur lesen:** Es werden `.md`-Dateien gelesen, jedoch keine geändert, verschoben oder umbenannt. Versteckte Ordner (`.obsidian`, `.git`), symbolische Links und Dateien über 64 KiB werden ignoriert.
- **Lokale Daten:** Dateiinhalte verlassen bei Standardkonfiguration den Rechner nicht; sie werden ausschließlich an `127.0.0.1` gesendet. Die Modelldateien werden einmalig aus dem offiziellen Release heruntergeladen.
- **Kleine Testmenge:** Standardmäßig 20 Notizen, maximal 200. Pro Datei werden höchstens 12.000 Zeichen klassifiziert.
- **Fehlklassifikation möglich:** Drei unabhängige Ja/Nein-Fragen können gleichzeitig „Ja“ ergeben oder alle „Nein“. Ergebnisse immer anhand selbst markierter Beispiele bewerten.
- **Sicherheitsgrenze:** Obsidian-Vaults und vertrauliche Daten dürfen **nicht** in dieses öffentliche GitHub-Repository kopiert werden. `.gitignore` schützt nur typische Verzeichnisse, nicht beliebige, versehentlich eingecheckte Ordner.
- **Upstream-Code:** Die Downloads werden über offizielle Release-URLs bezogen; das Installationsskript prüft ihre für dieses Release veröffentlichten SHA-256-Hashes. Keine automatische Aktualisierung und kein automatischer Start im Hintergrund.

## Nächste Ausbaustufe: Outlook

Eine **lesende** Outlook-Anbindung ist bewusst noch nicht enthalten, weil die Verbindung von **klassischem Outlook** und **neuem Outlook/Microsoft 365** unterschiedlich ist. Im Dokument [docs/OUTLOOK.md](docs/OUTLOOK.md) stehen Anforderungen und sichere Umsetzungsschritte. **Keine Anmeldung, Berechtigung oder Mail-Aktion** wird ohne separate Einrichtung ausgeführt.

## Testen

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Ohne Modell ausführbare Tests nutzen lokale Mock-Antworten; der reale Windows-Modellstart muss auf deinem Rechner geprüft werden.

**Quellen:** [Release jevos-v4](https://github.com/feder-cr/jev/releases/tag/jevos-v4) · [API / README des Entwicklers](https://github.com/feder-cr/jev#api).
