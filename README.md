# CECS – BTC/USD Research

## NEU: CECS 3.0 – defensives BTC-Trendsystem mit täglichem Paper-Journal

**Forschungsstatus: Historisch profitabel, aber prospektiv nicht validiert. Keine Echtgeld-Orders.**

- **[Das komplette CECS-3.0-Regelwerk, Renditen und Risiken auf Deutsch](CECS_3_0_STRATEGIE_DE.md)**
- **[Aktuelles virtuelles CECS3-Konto](cecs3_forward/state.json)** und **[datierte Tagesbeobachtungen](cecs3_forward/observations/)**
- **[Erfolgreicher 09:00-UTC-Backtest über acht Bitstamp-Jahrgänge](https://github.com/schakal00/Schakalpository/actions/runs/45030529487)**
- **[Erfolgreicher täglicher Paper-Workflow mit 19 bestandenen Tests und gesperrten Abhängigkeiten](https://github.com/schakal00/Schakalpository/actions/runs/45031089715)**

**So arbeitet die vorab definierte Hauptstrategie:** nur BTC/USD Spot, maximal 25 % BTC wenn Schlusskurs über SMA200 und SMA50 über SMA200. Bei hohem Volatilitätsrisiko (>80 % annualisierte 30-Tage-Volatilität) oder Schlusskurs unter SMA50 wird die BTC-Position auf 12,5 % reduziert. Bei Trendverlust geht sie auf 0 %. Umschichtung montags bzw. schnellere Risikoreduktion, ohne Kredit/Shorts.

**Echte historische Zahlen der Minutenpreis-Simulation 2022–08.09.2026:** **+13,95 %** Rendite nach 15 bps Gebühren/Slippage und zusätzlich 2 bps Halbspread pro Orderseite bei **−9,39 %** maximalem Tages-Drawdown. **2025 aber −6,54 %.** Die Zahlen stammen aus bereits bekannten historischen Kursverläufen und sind **kein zukünftiger Gewinnnachweis**.

**Paper-Stand am 22.11.2026:** 100.000 USD virtuelles Startkapital, 0 BTC, keine simulierte Transaktion. GitHub Actions soll gegen 09:35 UTC täglich prüfen; tatsächliche Startzeit kann variieren. Der Paper-Simulator verwendet *frisch beobachtetes Bitstamp Bid/Ask*, nicht einen bereits vergangenen Kurs. Strategieregeln und alle sechs signalrelevanten Quellen sind gegen unbemerkte Änderungen geschützt.

## Aktuell: CECS 2.8 – Drei echte prospektive **virtuelle** Vergleichskonten

- **[Erster erfolgreicher Forward-Vergleich und Forschungsregeln (Deutsch)](CECS_2_8_FORWARD_VERGLEICH_DE.md)**
- **[Die laufenden, unveränderlich datierten Schattenkonten](slow_shadow/observations/)**
- **[Erfolgreicher Cloud-Lauf #45028041087](https://github.com/schakal00/Schakalpository/actions/runs/45028041087)**

Die drei Modelle (`BuyHold25`, `Trend25`, `TrendVol30Vector`) starteten am 22.11.2026 unabhängig mit je **100.000 USD virtuellem Kapital** und **0 BTC**. GitHub soll täglich nach ca. **09:15 UTC** neue Daten mit nachweislich frischen Bitstamp-Geld-/Briefkursen verarbeiten. **Keine realen Orders, keine Brokeranbindung, keine garantierten Ausführungen oder Gewinne.**

## Ergebnisse der letzten großen Auditläufe

- **[CECS 2.7: Langsame Trendstrategie – historische Nettorendite 2022–2026, Drawdown und Kosten](CECS_2_7_SLOW_DE.md)**: `Trend25` **+16,59 %** bei **−13,06 %** maximalem täglichem Drawdown, `TrendVol30Vector` **+41,09 %** bei **−31,04 %** Drawdown. **Keine echte zukünftige Validierung.** Der Zusatznutzen des Vector-Faktors ist statistisch noch unbewiesen.
- **[CECS 2.6: Traders-Reality-inspirierte W-/M-15m-Strategien – nach Korrektur erneut getestet und verworfen](CECS_2_6_MW_NEGATIV_DE.md)**: alle acht Varianten 2019–September 2026 historisch negativ; **nicht** im aktiven Paper-System.
- **[CECS 2.5: Weiterhin separat eingefrorenes ursprüngliches Zyklus-Paper-Journal](CECS_2_5_PAPER_DE.md)**.

**Der entscheidende Unterschied:** Diese Renditezahlen entstammen einer bekannten historischen Stichprobe. Das neue 2.8-Journal sammelt hingegen ausschließlich **ab Einrichtung** entstandene virtuelle Preisbeobachtungen. Profitabilität ist **nicht nachgewiesen**, und selbst ein positiver Forward-Test wäre kein Gewinnversprechen.

## Neu: CECS 2.5 – echtes prospektives Paper-Journal (ohne Echtgeld)

- **[Aktuellen Paper-Kontostand und sämtliche Einschränkungen lesen](CECS_2_5_PAPER_DE.md)**
- **[Erste datierte Paper-Beobachtung vom 22.11.2026](paper_execution/observations/2026-11-22.json)**
- **[Erster erfolgreicher Paper-Cloud-Lauf, 20 Tests](https://github.com/schakal00/Schakalpository/actions/runs/45012628339)**
- [Virtueller State](paper_execution/state.json) · [Ausführungscode](paper_engine.py)

**Start: 100.000 USD virtuelles Geld, kein Trade, aktuelle Paper-Rendite 0 %.** Einstiegsvorhaben werden frühestens am Folgetag zu einem dann frisch erfassten Bitstamp-Briefkurs virtuell ausgeführt. Verkäufe nutzen den erfassten Geldkurs; 15 Basispunkte Kosten pro Seite sind angenommen. **Die tägliche Abfrage bildet Intraday-Stop-Trigger nicht zuverlässig ab.** Keine echten Orders, keine API-Schlüssel.

## Neu: CECS 2.4 – tägliche Vorwärtsbeobachtung ab 22.11.2026

- **[Warum wir die Strategie jetzt einfrieren, statt die Vergangenheit zu optimieren](CECS_2_4_FORWARD_DE.md)**
- **[Erste echte, datierte Beobachtung](paper_watch/2026-11-22.json)**
- **[Erster erfolgreicher Beobachtungslauf](https://github.com/schakal00/Schakalpository/actions/runs/45011721258)**

Automatisch wird um circa **09:00 UTC** ein BTC/USD-Datenstand in GitHub protokolliert. **Nur Beobachtung: keine Orders, keine tatsächlichen Paper-Trades, keine Gewinnzusage.** Die der Datenverfügbarkeit angepasste `TrendCycleWide6Delayed`-Variante erzielte im bereits eingesehenen historischen Prüfzeitraum **+0,47 %** nach angenommenen Kosten (keine unabhängige Validierung). Der erste protokollierte Marktstatus erfüllt aktuell **nicht** die Long-Trendbedingung.

## Aktuell: CECS 2.3 · Trendfilter statt ständigem 15m-Trading

- **[Ergebnisse inklusive Kostenstress auf Deutsch](CECS_2_3_TREND_AUDIT_DE.md)**
- **[Erfolgreicher GitHub-Actions-Backtest](https://github.com/schakal00/Schakalpository/actions/runs/45009423057)**
- [Trend-/Zyklus-/Elliott-/Vector-Forschungsrunner](cecs_v2_3_trend.py) · [Regressionstests](test_trend.py)

**Vorläufiger Befund:** `TrendCycleWide6`, mit 0,5 % modelliertem Anfangsrisiko je Trade, erzielte im bereits untersuchten BTC/USD-Zeitraum 2022–21.11.2026 **+1,21 %** nach 15 bps pro Orderleg bei **−1,32 %** größtem mark-to-market Drawdown. Auch bei 30 bps pro Leg noch +1,08 %. **Nicht auf unabhängigen künftigen Daten validiert**, nur 15 Trades und 2025/2026 negativ. Kein Live-Handel, keine Renditezusage.

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
