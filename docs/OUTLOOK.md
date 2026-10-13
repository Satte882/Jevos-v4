# Outlook – optionale zweite Ausbaustufe (noch nicht implementiert)

## Ziel

Outlook-**E-Mails nur lesend** abrufen und dieselben drei lokalen Ja/Nein-Fragen beantworten: Aufgabe, Idee, offene Entscheidung. Kein automatisches Senden, Verschieben, Löschen, Klassifizieren in Outlook oder Erstellen von Obsidian-Dateien.

## Wichtige Vorentscheidung

- **Neues Outlook / Microsoft 365 / Outlook.com:** regulär über **Microsoft Graph** + OAuth 2.0 / MSAL, mit minimalen delegierten Leserechten (z. B. `Mail.Read`, soweit vom Kontotyp unterstützt). Die Registrierung und eventuelle Admin-Zustimmung sind kontenabhängig.
- **Klassisches Outlook (lokal installiert):** unter Windows ist alternativ ein rein lokaler Zugriff auf das Outlook Object Model über COM möglich (würde ein zusätzliches Paket wie `pywin32` erfordern).
- Ein **PST-Import** ist hier nicht vorgesehen.

## Umsetzungsschritte (später)

1. Outlook-Version und verwendeten Kontotyp feststellen.
2. Passende **lesende** Schnittstelle konfigurieren, Secrets/Tokens ausschließlich lokal sichern.
3. Höchstens zehn E-Mails in einem benannten Ordner lesen; Quelltext niemals loggen.
4. Inhalte in den bereits existierenden lokalen JevosClient einspeisen.
5. Ergebnis lokal ausgeben; bei Bedarf CSV mit Betreff-Kürzel, Scores und ID – **keine Mail-Bodies**.
6. Qualität gegen manuelle Stichprobe prüfen, bevor weitere Automatisierung in Betracht kommt.

**Status:** Nicht eingerichtet; keine Microsoft-Berechtigungen erteilt. Das aktuelle Projekt kann komplett ohne Outlook gestartet werden.
