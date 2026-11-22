# CECS 2.6 – W/M + Vector-Zonen: echter Langzeit-Audit

**Status:** Historisch **nicht profitabel**, nicht für Paper-Trading oder Echtgeld freigegeben.

**GitHub Actions:** [Erfolgreicher Lauf #45028238061](https://github.com/schakal00/Schakalpository/actions/runs/45028238061); 10 synthetische Kausalitäts-/Ausführungstests bestanden. Archiv `cecs-2-6-wm-research` enthält `summary.csv`, `chronological_periods.csv`, `cost_sensitivity.csv`, `trade_log.csv`, `manifest.json`.

## Datenquelle und Zeitabdeckung

- 1-Minuten-Bitstamp-BTC/USD-OHLCV von [alessiostomeo/btc-cycle-data](https://github.com/alessiostomeo/btc-cycle-data), Jahrgänge 2019–2026.
- 269.664 vollständige 15m-Kerzen, 67.415 komplette 1h-Kerzen, 2.808 vollständig beobachtete Tageskerzen. 2026 endet wegen der archivierten Datenquelle **am 09.09.2026**, nicht am 22.11.2026.
- Zeiträume ohne stille Year-Reset-Artefakte; alle Signale werden nach Abschluss der betreffenden Kerze und nach Pivotbestätigung erzeugt.
- Nur Long/Flat-Spot; keine gehebelten Shorts.
- 15 Basispunkte modellierte Gebühr/Slippage **je Ausführung** im Haupttest, auch die Kostenstufen 0, 5 und 30 bps pro Leg wurden exportiert.
- 0,5 % geplantes Anfangsrisiko je Position, maximal volle Spot-Kapitaldeckung ohne Hebel, Stop nach 5 × 15m-ATR, Gewinnziel netto 2,5R, maximal 288 15m-Kerzen Haltedauer.
- Bei Mehrdeutigkeit innerhalb einer Kerze wird zuerst der Stop ausgelöst; Stops bei Preislücken werden zum Öffnungskurs ausgeführt.


**Audit-Korrektur:** Der erste veröffentlichte Lauf wurde durch einen Ausführungs-Audit ersetzt: Gewinnziele werden nun auch **innerhalb der Einstiegskerze** berücksichtigt, wobei ein zugleich berührter Stop Vorrang hat; außerdem ist eine neue Position unmittelbar nach einem Exit in derselben Kerze ausgeschlossen. Der zehnteilige Testsatz und die komplette Achtjahresanalyse wurden danach erneut erfolgreich ausgeführt. Die Werte oben entsprechen **nur dem korrigierten Lauf #45028238061**.

## Exakte mechanische Regeln

**W (Long-Kandidat):** zwei erst nach zwei Folgekerzen bestätigte lokale 15m-Tiefs mit 8–96 15m-Kerzen Abstand; Nähe der Tiefs innerhalb 0,8 ATR; Nackenlinie aus dem höchsten Zwischenhoch mindestens 1,3 ATR über den Tiefs; Einstiegssignal erst nach **Schlusskursbruch der Nackenlinie** innerhalb von 96 15m-Kerzen. Tatsächlich gedachter Einstieg frühestens zur nächsten 15m-Open.

**Vector-Hypothese:** bullische Climax-/High-Volume-Kerze innerhalb der letzten acht vollständig abgeschlossenen 15m-Kerzen oder Rückkehr über die Mitte der Zone einer bärischen Vector Candle im Bereich des zweiten Tiefs.

**M (optional Long-Ausstieg):** spiegelbildliche zwei lokale Hochs, Bestätigung und Bruch der Nackenlinie; Exit erst zur nächsten 15m-Eröffnung. Das ist **keine** Shorting-Strategie.

**Cycle/Elliott:** mechanische, retrospektiv definierte und frühestens nach Pivotbestätigung verfügbare Tages-Proxys; keine originale proprietäre Camel-Finance-Zykluszählung und keine vollständige diskretionäre Elliott-Wellenzählung.

Der Ansatz ist nur **Traders-Reality-inspiriert**, nicht Tinos vollständiges Hybrid-Handelssystem (z. B. Sessions, Marktstruktur und diskretionäre Level fehlen).

## Historische Gesamtergebnisse 2019–09.09.2026 (15 bps pro Leg)

| Modell | Trades | Rendite | Max. mark-to-market Drawdown | Profit Factor | Durchschnittliches R |
|---|---:|---:|---:|---:|---:|
| WOnly | 1.397 | **−57,56 %** | −60,28 % | 0,821 | −0,118 |
| WVector | 1.386 | **−58,56 %** | −61,35 % | 0,815 | −0,123 |
| W1h | 803 | **−30,93 %** | −36,94 % | 0,864 | −0,087 |
| WDaily | 656 | **−40,31 %** | −45,16 % | 0,776 | −0,153 |
| WCycle | 448 | **−31,40 %** | −37,15 % | 0,752 | −0,164 |
| WFusion | 314 | **−17,82 %** | −27,21 % | 0,818 | −0,121 |
| WFusionMExit | 490 | **−36,02 %** | −39,46 % | 0,628 | −0,180 |
| W1hMExit | 1.279 | **−67,63 %** | −68,54 % | 0,654 | −0,174 |

Hier bedeutet die niedrige Anzahl von WFusion-Trades primär eine geringere Kapitalexposition; die Treffer-/R-Qualität wurde **nicht** signifikant besser. `WVector` hat die W-only-Ergebnisse nicht verbessert. Der M-Ausstieg erhöhte die Transaktionshäufigkeit und verschlechterte den gesamten Ertrag deutlich.

## Zeitlich getrennte Rückrechnung (alle negativ)

| Modell | Entwicklung 2019–2021 | Historischer Vergleich 2022–2023 | Bereits eingesehene Prüfung 2024–2026 (bis 09.09.) |
|---|---:|---:|---:|
| WOnly | −22,82 % | −29,34 % | −22,18 % |
| WVector | −22,93 % | −30,40 % | −22,74 % |
| W1h | −13,45 % | −14,83 % | −6,30 % |
| WFusion | −4,24 % | −12,01 % | −2,47 % |
| WFusionMExit | −11,21 % | −17,91 % | −12,23 % |

**Die Trennung ist chronologisch, aber keine echte unberührte Holdout-Validierung**, weil das Projekt dieselben BTC-Jahre zuvor bereits analysiert hat. Sie bestätigt hier aber ein breites negatives Muster.

## Entscheidung

- **Die W/M-15m-Regeln als Handelsstrategie verwerfen; kein stilles Verschieben der Stop-/Target-Parameter, bis der bekannte Kursverlauf positiv aussieht.**
- Das bestehende, **eingefrorene CECS-2.5-Paper-Journal bleibt unverändert** und wird nicht durch die negative 15m-Forschung beeinflusst.
- Mehrwert von Vector-Recovery, M-Ausstieg und kombinierten Zyklusfiltern auf diesem mechanischen Setting **nicht nachgewiesen**.
- Stattdessen eigenständige Forschung einer **langsamen, geringen Handelsfrequenz mit risikogesteuerter Trendexposition**, um die bekannten Kosten- und Handelsfrequenzprobleme zu vermeiden.
- Bevor eine neue Strategie ins Forward-Paper-Journal darf: feste Regeln, Datenqualität und Zeitstempel, validierte Kosten, unabhängige künftige Beobachtungen.

Keine Anlageberatung, keine Gewinnzusage und kein Live-Ordersystem.
