# CECS 2.6 – W/M + Vector-Zonen: echter Langzeit-Audit

**Status:** Historisch **nicht profitabel**, nicht für Paper-Trading oder Echtgeld freigegeben.

**GitHub Actions:** [Erfolgreicher Lauf #45027402149](https://github.com/schakal00/Schakalpository/actions/runs/45027402149); 8 synthetische Kausalitäts-/Ausführungstests bestanden. Archiv `cecs-2-6-wm-research` enthält `summary.csv`, `chronological_periods.csv`, `cost_sensitivity.csv`, `trade_log.csv`, `manifest.json`.

## Datenquelle und Zeitabdeckung

- 1-Minuten-Bitstamp-BTC/USD-OHLCV von [alessiostomeo/btc-cycle-data](https://github.com/alessiostomeo/btc-cycle-data), Jahrgänge 2019–2026.
- 269.664 vollständige 15m-Kerzen, 67.415 komplette 1h-Kerzen, 2.808 vollständig beobachtete Tageskerzen. 2026 endet wegen der archivierten Datenquelle **am 09.09.2026**, nicht am 22.11.2026.
- Zeiträume ohne stille Year-Reset-Artefakte; alle Signale werden nach Abschluss der betreffenden Kerze und nach Pivotbestätigung erzeugt.
- Nur Long/Flat-Spot; keine gehebelten Shorts.
- 15 Basispunkte modellierte Gebühr/Slippage **je Ausführung** im Haupttest, auch die Kostenstufen 0, 5 und 30 bps pro Leg wurden exportiert.
- 0,5 % geplantes Anfangsrisiko je Position, maximal volle Spot-Kapitaldeckung ohne Hebel, Stop nach 5 × 15m-ATR, Gewinnziel netto 2,5R, maximal 288 15m-Kerzen Haltedauer.
- Bei Mehrdeutigkeit innerhalb einer Kerze wird zuerst der Stop ausgelöst; Stops bei Preislücken werden zum Öffnungskurs ausgeführt.

## Exakte mechanische Regeln

**W (Long-Kandidat):** zwei erst nach zwei Folgekerzen bestätigte lokale 15m-Tiefs mit 8–96 15m-Kerzen Abstand; Nähe der Tiefs innerhalb 0,8 ATR; Nackenlinie aus dem höchsten Zwischenhoch mindestens 1,3 ATR über den Tiefs; Einstiegssignal erst nach **Schlusskursbruch der Nackenlinie** innerhalb von 96 15m-Kerzen. Tatsächlich gedachter Einstieg frühestens zur nächsten 15m-Open.

**Vector-Hypothese:** bullische Climax-/High-Volume-Kerze innerhalb der letzten acht vollständig abgeschlossenen 15m-Kerzen oder Rückkehr über die Mitte der Zone einer bärischen Vector Candle im Bereich des zweiten Tiefs.

**M (optional Long-Ausstieg):** spiegelbildliche zwei lokale Hochs, Bestätigung und Bruch der Nackenlinie; Exit erst zur nächsten 15m-Eröffnung. Das ist **keine** Shorting-Strategie.

**Cycle/Elliott:** mechanische, retrospektiv definierte und frühestens nach Pivotbestätigung verfügbare Tages-Proxys; keine originale proprietäre Camel-Finance-Zykluszählung und keine vollständige diskretionäre Elliott-Wellenzählung.

Der Ansatz ist nur **Traders-Reality-inspiriert**, nicht Tinos vollständiges Hybrid-Handelssystem (z. B. Sessions, Marktstruktur und diskretionäre Level fehlen).

## Historische Gesamtergebnisse 2019–09.09.2026 (15 bps pro Leg)

| Modell | Trades | Rendite | Max. mark-to-market Drawdown | Profit Factor | Durchschnittliches R |
|---|---:|---:|---:|---:|---:|
| WOnly | 1.408 | **−57,38 %** | −60,07 % | 0,821 | −0,117 |
| WVector | 1.397 | **−58,39 %** | −61,15 % | 0,815 | −0,121 |
| W1h | 809 | **−30,34 %** | −35,46 % | 0,867 | −0,085 |
| WDaily | 658 | **−38,81 %** | −43,49 % | 0,785 | −0,145 |
| WCycle | 449 | **−29,32 %** | −35,24 % | 0,768 | −0,151 |
| WFusion | 315 | **−16,79 %** | −25,93 % | 0,828 | −0,112 |
| WFusionMExit | 491 | **−36,34 %** | −39,76 % | 0,624 | −0,182 |
| W1hMExit | 1.287 | **−67,65 %** | −68,51 % | 0,653 | −0,173 |

Hier bedeutet die niedrige Anzahl von WFusion-Trades primär eine geringere Kapitalexposition; die Treffer-/R-Qualität wurde **nicht** signifikant besser. `WVector` hat die W-only-Ergebnisse nicht verbessert. Der M-Ausstieg erhöhte die Transaktionshäufigkeit und verschlechterte den gesamten Ertrag deutlich.

## Zeitlich getrennte Rückrechnung (alle negativ)

| Modell | Entwicklung 2019–2021 | Historischer Vergleich 2022–2023 | Bereits eingesehene Prüfung 2024–2026 (bis 09.09.) |
|---|---:|---:|---:|
| WOnly | −24,44 % | −29,17 % | −20,38 % |
| WVector | −24,55 % | −30,23 % | −20,96 % |
| W1h | −15,17 % | −13,77 % | −4,78 % |
| WFusion | −4,72 % | −12,01 % | −0,75 % |
| WFusionMExit | −11,65 % | −17,91 % | −12,23 % |

**Die Trennung ist chronologisch, aber keine echte unberührte Holdout-Validierung**, weil das Projekt dieselben BTC-Jahre zuvor bereits analysiert hat. Sie bestätigt hier aber ein breites negatives Muster.

## Entscheidung

- **Die W/M-15m-Regeln als Handelsstrategie verwerfen; kein stilles Verschieben der Stop-/Target-Parameter, bis der bekannte Kursverlauf positiv aussieht.**
- Das bestehende, **eingefrorene CECS-2.5-Paper-Journal bleibt unverändert** und wird nicht durch die negative 15m-Forschung beeinflusst.
- Mehrwert von Vector-Recovery, M-Ausstieg und kombinierten Zyklusfiltern auf diesem mechanischen Setting **nicht nachgewiesen**.
- Stattdessen eigenständige Forschung einer **langsamen, geringen Handelsfrequenz mit risikogesteuerter Trendexposition**, um die bekannten Kosten- und Handelsfrequenzprobleme zu vermeiden.
- Bevor eine neue Strategie ins Forward-Paper-Journal darf: feste Regeln, Datenqualität und Zeitstempel, validierte Kosten, unabhängige künftige Beobachtungen.

Keine Anlageberatung, keine Gewinnzusage und kein Live-Ordersystem.
