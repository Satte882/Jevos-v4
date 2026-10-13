# Validierung der Entscheidungsqualität

Das Modell liefert für jede Frage P(„Ja“) als Zahl von 0 bis 1. **P(„Ja“) ist keine nachgewiesene Kalibrierung** auf die tatsächliche Fehlerquote. Die drei Entscheidungen sind unabhängig; Mehrfachtreffer sind zulässig.

## Kleines lokales Experiment

1. Zuerst `demo` mit synthetischen englischen Sätzen starten und die Antworten plausibilisieren.
2. Danach 20 eigene Notizen auswählen, vorher **selbst** pro Frage mit Ja/Nein markieren.
3. Die 20 Modellantworten mit der manuellen Kennzeichnung vergleichen: Treffer, False Positives, False Negatives je Frage.
4. Die gleichen Aufgaben mit deutschen Notizen wiederholen. Nicht voraussetzen, dass die Güte identisch ist.
5. Erst bei ausreichend guten Ergebnissen weitere Integrationen planen. Ein Schwellenwert von `0.75` ist ein **Testparameter**, kein wissenschaftlich validierter Grenzwert.

## Datenschutz

Die CSV enthält ausschließlich Dateipfade und Scores. Pfade können persönliche Begriffe verraten: keine echten Berichte, Tokens, Outlook-Mails oder Vaults nach GitHub pushen. Auch das öffentlich sichtbare Repo nicht für sensible Mustertexte verwenden.
