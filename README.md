# CECS – BTC/USD Research

## Neu: CECS 2.2 · Bitstamp-Intraday-Test (2024–2026)

- **[CECS 2.2 – vollständige 15m/1h-Ergebnisse inkl. Kostenstress auf Deutsch](CECS_2_2_INTRADAY_DE.md)**
- **[Erfolgreicher GitHub-Actions-Run für 2.2](https://github.com/schakal00/Schakalpository/actions/runs/45008481583)**
- [CECS 2.2 Python Intraday-Runnner](cecs_v2_2_intraday.py) · [Intraday-Regressionstests](test_intraday.py)

**Ergebnis:** Die untersuchten 15-Minuten-Breakout- und Vector-Strategien sind bei angenommenen 15 bps je Ausführung in 2024, 2025 und 2026 (nur bis 9. September) allesamt negativ. Auch 0-bps-Szenarien liefern keinen stabilen Vorteil über mehrere Jahre. Kein nachgewiesener Trade-Edge; keine echten Orders.

## CECS 2.1 · Tageschart

- **[Tageschart-Ergebnisse 2017–2026](ERGEBNISSE_DE.md)**
- [Erster erfolgreicher Tageschart-Lauf](https://github.com/schakal00/Schakalpository/actions/runs/45006342841)
- [Tageschart-Runner](cecs_v2_1_runner.py) · [7 Regressionstests](test_cecs_runner.py)

## Was das Projekt tatsächlich tut

CECS untersucht mechanisch definierte **Camel-inspirierte DCL-/WCL-Zyklen**, einen **Elliott-Welle-2-Proxy** und **Traders-Reality-inspirierte Vector-Candle-Bedingungen**.

Dies sind **keine** offiziellen oder vollständigen Originalmethoden. Die Prognosevalidität und wirtschaftliche Tragfähigkeit bleiben unbewiesen.

### Für iPhone: Ergebnisse ansehen

Öffne oben den verlinkten Bericht. Du musst nichts installieren oder herunterladen.

### Für Reproduzierbarkeit

GitHub → Actions → CECS BTC research audit → [erfolgreichen Lauf öffnen](https://github.com/schakal00/Schakalpository/actions/runs/45008481583) → Artifact `cecs-btc-research-results`. Im Archiv liegen handelsbezogene CSVs, Datenquellen-Hashes, Zeitabdeckung und Sensitivitätsanalysen.

Keine API-Schlüssel, keine Brokerverbindung, keine Live-Signale, keine echte Ausführung.

## Forschungsnächster Schritt

Ein **daily CECS Set-up** muss vorab eindeutig festgelegt sein; erst dann wird geprüft, ob **15m/1h Vector-Recovery und M/W-Struktur** dessen Entry gegenüber dem Tageschart nach Kosten tatsächlich verbessert. Nicht einfach zusätzliche Indikatoren auf die bisherigen verlustreichen Intraday-Breakouts legen.
