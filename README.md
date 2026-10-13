# Jev vs. jevos-v4 – Windows-Experiment

Dieses private Experiment vergleicht **zwei unterschiedliche Modelle mit dem gleichen Entscheidungsschema**:

- **Jev (Cloud)** – offizielles Modell von [TypeSafe AI](https://typesafe.ai/), über den API-Key aus [console.typesafe.ai/keys](https://console.typesafe.ai/keys). Texte werden **an TypeSafe übertragen** und Anfragen können kostenpflichtig sein.
- **jevos-v4 (lokal)** – unabhängiges Open-Source-Projekt [feder-cr/jev](https://github.com/feder-cr/jev), ohne Cloud-Anfrage, CPU-tauglich. Nicht mit dem originalen Jev-Modell verwechseln.

**Explizite Wahl:** Pro Aufruf läuft **entweder** `--provider local` **oder** `--provider jev`. Es gibt keine automatische Auswahl, keinen Parallelbetrieb, keinen stillen Fallback.

## Schnellstart unter Windows 11

Benötigt: [Git](https://git-scm.com/download/win) und [Python 3.11+](https://www.python.org/downloads/windows/) mit dem Befehl `py -3`. Keine zusätzlichen Python-Pakete.

```powershell
git clone https://github.com/Satte882/Jevos-v4.git
cd Jevos-v4
powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1
```

Im Menü **1** für Jevos lokal, **2** für Jev Cloud mit sechs synthetischen englischen Notizen. Optionen **3** und **4** lesen Obsidian-Notizen (Option 4 lädt deren Inhalt zur TypeSafe-API hoch und verlangt eine **ausdrückliche Bestätigung**). Kein Anwendertext wird ins Repository geschrieben.

### Für Jevos lokal – vorher einmalig installieren

Das offizielle Windows-Binary + OpenVINO-Modell (~650 MB) werden in den ignorierten Ordner `.local/jev` geladen, **SHA-256** wird gegen veröffentlichte Release-Werte geprüft:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-jev.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-jev.ps1
```

Das Serverfenster geöffnet lassen. Ein zweites PowerShell-Fenster im Projektverzeichnis öffnen und das Auswahlmenü starten (`scripts/run.ps1`). Der lokale Server lauscht nur auf `127.0.0.1:8017`.

### Für Jev Cloud – **keine Modellinstallation**

Menü **2** auswählen. Das Skript fragt den API-Key **verdeckt** ab und setzt ihn nur während dieses Prozesses als Umgebungsvariable `TYPESAFE_API_KEY`. API-Key **niemals** hier in den Chat oder in GitHub einfügen.

Alternativ für fortgeschrittene Nutzer den Schlüssel vorübergehend im aktuellen PowerShell-Prozess setzen (dadurch ist er im Befehlstext sichtbar; für private Keys deshalb **das Menü bevorzugen**) und explizit starten:

```powershell
py -3 -m jevos_local --provider jev demo --mode all
```

Offizieller Cloud-Endpoint: `https://api.typesafe.ai/v1/systemone`. Es werden **ausschließlich** TypeSafe und kein unabhängiger Drittanbieter-Proxy angesprochen. Für den Cloud-Gesundheitscheck wird `GET /v1/models` verwendet.

## Unterstützte KI-Funktionen

| Modus | Bedeutung | Ergebnis |
|---|---|---|
| `noul` | Drei Ja/Nein-Fragen: Aufgabe, Idee, offene Entscheidung | Jeweils eine Wahrscheinlichkeit von 0–1 |
| `choice` | Hauptkategorie wählen: Aufgabe, Idee, Entscheidung, Information | Kategorie + Verteilung + Konfidenz |
| `score` | Dringlichkeit auf Skala 0–3 bewerten | Erwarteter numerischer Wert + Konfidenz |
| `all` | Alle fünf Fragen in **einem** API-Aufruf pro Notiz | Kombinierte Ausgabe |

Beide Provider erhalten **identische Fragen, Kriterien und Testtexte**. Ein Score ist keine automatisch richtige Priorität; Wahrscheinlichkeiten sind keine Garantie. Besonders deutschsprachige Texte müssen anhand eigener Beispiele geprüft werden. Jevos-v4 hat einen anderen Trainingsstand und andere Modellgüte als Jev.

## CLI-Beispiele für gezielte Tests

```powershell
# Prüfung des jeweiligen Anbieters
py -3 -m jevos_local --provider local health
py -3 -m jevos_local --provider jev health

# Für einen fairen späteren Vergleich: einzeln nacheinander starten
py -3 -m jevos_local --provider local demo --mode all
py -3 -m jevos_local --provider jev demo --mode all

# Obsidian: nur lesen, nicht schreiben (Vault-Pfad ersetzen!)
py -3 -m jevos_local --provider local vault --vault "C:\Pfad\MeinVault" --limit 20 --mode all

# Cloud nur bei BEWUSSTER Freigabe der echten Notizen:
py -3 -m jevos_local --provider jev vault --vault "C:\Pfad\MeinVault" --limit 20 --mode all --allow-cloud-vault
```

Optional `--report "reports\ergebnis.csv"` legt eine lokale CSV mit **Dateipfaden, Kategorien und Scores ohne Notizinhalte** an. `reports/` ist von Git ausgeschlossen. Die Skripte schreiben **niemals** in einen Obsidian-Vault, und CSV-Dateien **im Vault** werden blockiert.

## Sicherheit und Grenzen

- Beim lokalen Provider gehen Daten ausschließlich über `localhost` zum Modell. Beim Cloud-Provider **werden die vollständigen jeweils ausgewählten Textausschnitte** an TypeSafe übermittelt.
- Obsidian: maximal 20 Notizen standardmäßig (einstellbar bis 200), maximal 64 KiB Dateigröße und 12.000 Zeichen pro Note; versteckte Ordner, Symlinks und andere Dateien als Markdown werden ignoriert.
- API-Key bleibt ausschließlich in der PowerShell-Prozessumgebung; keine `.env`, kein Key im Repository. Zusätzliche Betriebssystem-/Prozessschutzmaßnahmen sind davon unberührt.
- Keine automatische Weiterleitung, kein Outlook-Zugriff, keine E-Mail-Aktionen. [Outlook bleibt Phase 2](https://github.com/Satte882/Jevos-v4/issues/1).
- Bei `--provider jev` wird ein fehlender API-Key als Fehler gemeldet, **niemals** auf den lokalen Provider zurückgefallen.
- Der erste echte Modellstart unter Windows und die Live-Authentifizierung bei TypeSafe müssen noch auf deinem Rechner getestet werden.

## Tests

```powershell
py -3 -m unittest discover -s tests -v
```

Die GitHub Actions prüfen Python unter Windows und Linux sowie die Syntax der PowerShell-Skripte, **ohne ein Modell herunterzuladen oder einen API-Key zu benötigen**.

Quellen: [offizielle TypeSafe OpenAPI-Spezifikation](https://api.typesafe.ai/openapi.json) · [Open-Source-Release jevos-v4](https://github.com/feder-cr/jev/releases/tag/jevos-v4) · [Herstellerdokumentation](https://github.com/feder-cr/jev#api).
