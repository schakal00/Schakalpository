# CECS 2.1 – erster vollständig ausgeführter BTC/USD-Cloud-Backtest

**Stand:** 22.11.2026 · GitHub Actions Lauf [#1](https://github.com/schakal00/Schakalpository/actions/runs/45006342841) erfolgreich. 
**Code:** `cecs_v2_1_runner.py` (unabhängiger, gegenüber früheren CECS-Paketen bewusst kompakter Forschungs-Runner); `test_cecs_runner.py` (7 Tests).

## Daten und Annahmen

- Öffentliche Bitstamp-BTC/USD-Tageskerzen (Daten von einem Drittanbieter auf GitHub)
- 01.01.2017–21.11.2026, **3.612 Tageskerzen**; SHA256: `5df757f0266933eed6547c00ae21334d13f1c69c10f6dad7913a40e40e3c75dd`
- Entwicklungsvergleich: 2017–2021; spätere historische Nachrechnung: 2022–2026, **kein echter prospektiver OOS-Nachweis**, weil Konzeption/Regeln zuvor schon anhand historischer Beispiele entwickelt wurden
- 0,15 % modellierter kombinierter Gebühren-/Slippage-Abschlag je Ausführung (Einstieg und Ausstieg)
- Maximal 0,5 % Anfangsrisiko pro Modelltrade; 3R-Ziel nach Kosten; 90 Kalendertage Haltebegrenzung
- DCL/WCL/Elliott sind **vereinfachte, mechanische Proxys**, keine proprietären Originalsignale
- Vector-Candle-Klassifikation: Climax/Rising auf Basis der *10 vorherigen* Volumenkerzen; Tageschart, keine Tino-15-Minuten-Strategie

## Historischer Prüfzeitraum (2022–21.11.2026)

| Modell | Abgeschlossene Trades | Trefferquote | Modellrendite | Durchschnittliches R |
| --- | ---: | ---: | ---: | ---: |
| Breakout | 15 | 40,00 % | +0,62 % | +0,088 |
| Cycle | 6 | 33,33 % | +1,45 % | +0,489 |
| Elliott | 1 | 100,00 % | +1,50 % | +3,000 |
| CECS: Cycle + Elliott | 0 | – | 0 % (uninvestiert) | – |
| Vector | 11 | 54,55 % | +3,35 % | +0,606 |
| Cycle + Vector | 4 | 50,00 % | +2,35 % | +1,173 |
| Elliott + Vector | 1 | 100,00 % | +1,50 % | +3,000 |
| CECS + Vector | 0 | – | 0 % (uninvestiert) | – |

Werte aus GitHub Actions Run #1, `summary.csv`; Modellrenditen auf 100.000 USD hypothetisches Startkapital, ohne Positionshebel. **0 Trades ist keine 0 %-Strategieperformance oder Trefferquote, sondern fehlende Beobachtbarkeit.**

## Historische Vector Recovery (2022–2026)

- 95 rote Kerzen: 50-%-Recovery innerhalb von 10 Folgetagen in **73,68 %**.
- 63 violette Kerzen: **84,13 %**.
- 741 gewöhnliche bärische Kerzen: **93,39 %**.
- Dies ist eine **nicht gematchte Ereignisstudie**: Ohne Anpassung für Kerzengröße, Volatilität, Marktregime und überlappende Beobachtungsfenster liefert sie keinen Kausalbeleg für Vector-Recovery.

## Wesentliche Grenzen und nächste Prüfungen

1. **Zu kleine Stichproben**: 11 Vector-Trades und 4 Cycle+Vector-Trades reichen nicht zum Nachweis eines stabilen statistischen Vorteils.
2. **Kein vollständiger Traders-Reality-Hybridansatz**: M/W-Formationen, Intraday-Session-Logik und 15-Minuten-Vector-Bestätigung fehlen.
3. **Simplifizierte Elliott-Pivots** sind regelbasiert, keine vollständige Wellenzählung mit mehreren Graden.
4. **Drawdown in `summary.csv`** wird nur aus geschlossenen Trades berechnet, **nicht** aus täglicher mark-to-market Equity, daher als echter Risiko-Drawdown unzureichend.
5. Kein Walk-forward-Wahrscheinlichkeitsmodell trainiert; weder Konfidenzintervalle noch korrigierte Hypothesentests wurden berechnet.
6. Frühere CECS-Forschungsdateien liegen als separater Prototyp vor und wurden **nicht** vollständig in diese kompakte Repo-Version übernommen.
7. Zunächst Code-Audit gegen das umfangreichere CECS-2.1-Paket, danach realistische Intraday-Daten, Kosten- und Out-of-sample-Prüfung. Kein echtes Trading, keine API-Keys.

**Reproduzierbarkeit:** GitHub Actions → Run #1 → Artifact `cecs-btc-research-results`: `summary.csv`, `trades.csv`, `vector_recovery_*.csv`, `manifest.json`.
