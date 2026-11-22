# CECS 2.3 – Trendfolge, breitere Stops und Kosten-Robustheit

**Datum: 22. November 2026.** Erfolgreicher [GitHub Actions Testlauf #6](https://github.com/schakal00/Schakalpository/actions/runs/45009423057), 19 Regressionstests erfolgreich. Die Dateien des tatsächlichen Laufs sind im Workflow-Artifact `cecs-btc-research-results` enthalten (`results_trend/...`).

## Wichtigste Schlussfolgerung

**Einige langsamere Trendregeln waren in der historischen BTC/USD-Modellsimulation von 2022–21.11.2026 nach Kosten positiv.** Der defensivste vielversprechende explorative Kandidat ist `TrendCycleWide6`: **+1,2072 % Rendite bei −1,3174 % maximalem mark-to-market Drawdown** in diesem fast fünfjährigen Abschnitt (15 Trades). Das bedeutet **nicht**, dass die Strategie eine nachgewiesene profitable Handelsmethode ist. Die Regeln wurden nach dem Einsehen früherer Testergebnisse weiterentwickelt. 2025 und 2026 blieben für diese Variante negativ.

## Daten, Regeln und Interessenkonflikt bei der Modellauswahl

- Originale Bitstamp BTC/USD OHLCV-Tagesdaten, 01.01.2017–21.11.2026, **3.612 Kerzen**, im Lauf per SHA256 archiviert.
- Entry frühestens **nächste Tageseröffnung** nach dem Signal; Markttrend nur bei Tagesclose über SMA200 und SMA50 über SMA200.
- Camel-inspirierter, **bestätigter DCL-Pivot-Proxy**, Intervall 45–85 Tage; ein erfüllter Zyklusfilter erlaubt TrendCycleWide6 einen Einstieg. Keine unverifizierte Camel-Finance-Proprietärzählung.
- **6 × Tages-ATR(14)** für anfänglichen und zum Tagesende nachgezogenen Stop; Positionsgröße maximal **0,5 % modelliertes Initialrisiko**, unverschuldet / ohne Hebel. Nachtlücken können jedoch mehr Verlust verursachen.
- Ausstieg nach bestätigtem Trendverlust oder Stop; bei Tageskerzen darf ein intraday durchlaufener Stop nicht durch eine spätere Tages-Hochmarke verändert werden.
- Gebühren und Slippage im Standard: **15 Basispunkte pro Orderausführung** (= ungefähr 30 bps Roundtrip vor Finanzierung / Steuern).
- **Nicht prospektiv**, weil diese Parameter nach der Prüfung bereits bekannter 2022–2026-Daten gewählt wurden. Unterteilung `development` und `historical_review` ist keine echte unberührte Holdout-Validierung mehr.

## Historischer Vergleich 2022 bis 21.11.2026

| Mechanischer Proxy / Benchmark | Gesamt-Rendite im Zeitraum | Größter Drawdown | Einordnung |
| --- | ---: | ---: | --- |
| BuyHoldSpot (100 % BTC) | **+30,00 %** | **−67,00 %** | Passiver Rendite-/Risiko-Benchmark |
| TrendSpot (100 % BTC im Trend, kein fixer Stop) | **+57,11 %** | **−45,03 %** | Positive Rendite, sehr großes Risiko |
| TrendSpotQuarter (25 % des verfügbaren Kapitals je Einstieg, kein fixer Stop) | **+15,43 %** | **−15,07 %** | Benchmark, **nicht** auf 0,5 % Stop-Risiko begrenzt |
| TrendRisk (3 ATR Stop, 0,5 % Initialrisiko) | **−1,45 %** | **−3,10 %** | Häufiges Ausstoppen, nicht profitabel |
| TrendWide6 (6 ATR, 0,5 %) | **+0,97 %** | **−1,56 %** | Sehr geringer Ertrag |
| TrendWide10 (10 ATR, 0,5 %) | **+0,97 %** | **−1,00 %** | Noch geringere Handelsfrequenz |
| **TrendCycleWide6 (6 ATR + DCL-Proxy, 0,5 %)** | **+1,21 %** | **−1,32 %** | Bisheriger explorativer Kandidat |
| TrendVectorWide6 (6 ATR + bullische Vector-Bestätigung, 0,5 %) | **+0,51 %** | **−1,62 %** | Vector-Filter in diesem Vergleich nicht besser |

Diese Renditen beruhen auf *unterschiedlichen Kapitalexpositionen*. Sie stellen weder Risikogleichheit noch statistische Signifikanz dar. Die Fibonacci-/Elliott-Komponenten haben bislang **keinen belegten zusätzlichen Vorteil** geliefert. `TrendCycleWide6` umfasst im Reviewzeitraum nur **15 Trades**, was für belastbare Prognosen zu wenig ist.

### Einzeljahre für `TrendCycleWide6`

| Jahr | Modellrendite | Drawdown |
| --- | ---: | ---: |
| 2022 | 0,00 % | 0,00 % |
| 2023 | −0,09 % | −0,72 % |
| 2024 | +2,07 % | −1,03 % |
| 2025 | −0,67 % | −1,04 % |
| 2026 bis 21.11. | −0,09 % | −0,38 % |

**Die positive 5-Jahres-Rendite entsteht überwiegend in 2024.** Es besteht bisher keine Jahreskonsistenz. Die Schlüsselfrage lautet also nicht nur 'positiv?', sondern 'künftiger Erwartungswert nach Kosten im Verhältnis zu Handelsaufwand, Drawdown und Marktchance?'.

## Kosten-Sensitivität: `TrendCycleWide6`

| Kosten pro Ausführung (bps) | Review 2022–2026 | Max. Drawdown |
| ---: | ---: | ---: |
| 0 | +1,3417 % | −1,2926 % |
| 5 | +1,2964 % | −1,3009 % |
| **15** | **+1,2072 %** | **−1,3174 %** |
| 30 | +1,0766 % | −1,3415 % |

Auch das ist nur eine retrospektive Modell-Sensitivität: reale Liquidität, Börsenregeln, Kurslücken und verschiedene Datenfeeds sind nicht durchgerechnet.

## Vorläufige Entscheidung

1. **Nicht für Echtgeldhandel freigeben.** Kein garantierter Profit; die Variante ist explorativ und die Stichprobe sehr klein.
2. `TrendCycleWide6` als **Paper-Trading-Kandidat** einfrieren, nicht jede Woche nach aktuellen Renditen nachoptimieren.
3. Vector Candles und Elliott **als getrennt auswertbare Hypothesen**, nicht als starre Pflichtfilter oder behauptete Gewinntreiber. Der Vector-Filter `TrendVectorWide6` war im Prüfzeitraum mit +0,51 % schlechter als `TrendCycleWide6`.
4. Vor der nächsten Optimierungsrunde zusätzliche Märkte und Datenfeeds prüfen; danach prospektives Signalprotokoll anlegen, mit echten Gebühren/Spread und umfassendem Ausführungs-Audit.
5. Langfristig mit gleichem Kapital, gleichem Risiko, gleicher Zeit im Markt und einer einfachen Trend-/Buy&Hold-Alternative vergleichen.

## Reproduzierbarkeit

- [Strategie-Runner](cecs_v2_3_trend.py)
- [Causale Tests](test_trend.py)
- [Erfolgreicher GitHub-Actions-Run #6](https://github.com/schakal00/Schakalpository/actions/runs/45009423057)
- Im Ergebnisarchiv unter `results_trend/`: `summary.csv`, `periods.csv`, `fee_sensitivity.csv`, `trades.csv`, `equity_daily.csv` und `manifest.json`.

Hinweis: Dieser Bericht beschreibt eine historische Forschungs-Simulation, kein Investmentversprechen und keine persönliche Empfehlung.
