# CECS 3.0 – Defensive BTC/USD-Trendstrategie

**Stand: 22. November 2026.** Historisch nach modellierten Kosten positiv. **Echter künftiger Gewinn ist nicht nachgewiesen.**

- [Erfolgreicher 09:00-UTC-Backtest](https://github.com/schakal00/Schakalpository/actions/runs/45030529487)
- [Erster prospektiver Paper-Lauf mit echtem Bitstamp-Zeitstempel](https://github.com/schakal00/Schakalpository/actions/runs/45030813685)
- [Strategiecode](cecs_v3_0_strategy.py) · [Kausalitätstests](test_cecs3.py)
- [Separates, unverändertes Modell-Paperkonto](cecs3_forward/state.json) · [Tagebucheinträge](cecs3_forward/observations/)

## Die Handelssystematik

**Long/Flat BTC/USD an Bitstamp, maximal 25 % Spot-BTC-Exposure, niemals Short, Futures oder Kredit.**

Alle Indikatoren beruhen ausschließlich auf bereits abgeschlossenen BTC/USD-Tageskerzen:

1. **Trendfilter:** Tages-Schlusskurs über SMA200 und SMA50 über SMA200. Andernfalls BTC-Zielgewicht **0 %**, Cash USD.
2. **Normales Marktregime:** Bei positivem Trend **25 %** des virtuellen Portfoliowerts in BTC.
3. **Defensive Reduktion:** Wenn der letzte abgeschlossene BTC-Kurs **unter SMA50** fällt *oder* die annualisierte historische Volatilität der letzten 30 Tage **80 % übersteigt**, wird das BTC-Zielgewicht auf **12,5 %** halbiert.
4. **Rebalancing:** Montags, sofern die Abweichung des tatsächlichen BTC-Gewichts vom Sollgewicht mindestens **3 Prozentpunkte** beträgt. Risikoabbau bei Sollgewicht unter Istgewicht um mehr als 3 Prozentpunkte auch an anderen Tagen.
5. **Kausalität:** Das Signal stammt aus dem vollständig abgeschlossenen UTC-Tag `D−2`. Historische Ausführung am Tag `D` um **09:00 UTC** zum Eröffnungspreis der 09:00-15m-Kerze aus demselben Bitstamp-Minutenarchiv. Niemals historischer Kauf zum bereits verpassten Mitternachts-Open.
6. **Kosten:** 15 Basispunkte für Gebühren/Slippage **plus zusätzlich** 2 Basispunkte pauschaler halber Spread **je Orderseite**. Der Haupttest nimmt damit 17 bps je Seite an. Sensitivität für Gebühren/Slippage: 0, 15, 30, 50 bps je Seite **zuzüglich** der 2 bps angenommenem Spread.

**Wichtig:** Die Strategie hat **keine harte Stop-Loss-Order** und keinen garantierten maximalen Drawdown. Ein künftiger Crash kann deutlich größere Verluste verursachen als die historische Simulation. Die Begrenzung auf 25 % BTC verhindert Hebel, garantiert aber keinen bestimmten Gesamtkapitalverlust.

## Historischer Daten- und Ausführungs-Audit

- Quelle: öffentliche Bitstamp-BTC/USD-Minutenarchive von [alessiostomeo/btc-cycle-data](https://github.com/alessiostomeo/btc-cycle-data).
- **269.664 vollständige 15m-Kerzen**, **2.808 vollständig abgeschlossene Tageskerzen**.
- **01.01.2019 bis 08.09.2026**. Die 2026-Minutenarchive enden Anfang September, **nicht** am 22. November; seitdem liegen dem Forward-Paper-Simulator separate, jüngere tägliche Bitstamp-OHLCV-Daten und frische Bitstamp-Ticker vor.
- Einfrierung der **primären CECS3-Defensive-Regel vor dem ersten vollständigen 09:00-Backtest**. Vier zusätzliche Varianten sind als explorative Vergleiche separat ausgewiesen.
- 17 automatische Tests im historischen Research-Workflow, darunter Preiszeitpunkt, vollständige Kerzen, Preislücken, Volatilität, Buchhaltung und Risikoexposition.
- Enthält `summary.csv`, `periods.csv`, `order_log.csv`, `equity_daily.csv`, `cost_stress.csv` und Datenquellen-SHA256-Hashes im reproduzierbaren GitHub-Actions-Artifact `cecs-3-0-research`.

## Ergebnis nach Kosten (2022–08.09.2026)

| Strategie | Rendite über gesamten Zeitraum | Größter Tages-Drawdown | Durchschnittlich investierter Portfolioanteil |
| --- | ---: | ---: | ---: |
| **CECS3_Defensive (Hauptkandidat)** | **+13,95 %** | **−9,39 %** | **8,59 %** |
| Trend25, einfacher Trendvergleich | +17,65 % | −10,08 % | 10,71 % |
| BuyHold25, regelmäßig rebalancierte 25-%-BTC-Benchmark | +27,60 % | −21,83 % | 24,81 % |
| CECS3_Balanced (30/15 % BTC) | +16,89 % | −10,98 % | 10,30 % |
| CECS3_Volatility | +20,66 % | −12,79 % | 11,81 % |
| CECS3_Momentum | +17,90 % | −11,15 % | 9,24 % |
| TrendVol30Vector (riskanter Vergleich) | +40,09 % | −25,37 % | 25,49 % |

**CECS3_Defensive maximiert gerade nicht die rohe Rendite.** Die konservativere Kapitalexposition erklärt einen großen Teil des niedrigeren Drawdowns und ebenfalls der geringeren Rendite. Ein echter risikogleicher Alpha-Vorteil gegenüber simpler Trendfolge ist **nicht** nachgewiesen.

### Zerlegung der CECS3-Defensive-Historie

| Zeitraum | Modellrendite | Max. Drawdown |
| --- | ---: | ---: |
| 2019 | −2,81 % | −4,54 % |
| 2020 | +30,06 % | −4,42 % |
| 2021 | +5,68 % | −10,00 % |
| 2022 | 0,00 % | 0,00 % |
| 2023 | +7,49 % | −3,92 % |
| 2024 | +13,44 % | −8,65 % |
| **2025** | **−6,54 %** | **−7,98 %** |
| 2026 bis 08.09. | 0,00 % | 0,00 % |
| **2022–2023** | **+7,49 %** | **−3,92 %** |
| **2024–08.09.2026** | **+6,02 %** | **−9,39 %** |
| **2022–08.09.2026** | **+13,95 %** | **−9,39 %** |

Die positive Gesamtrendite beruht besonders auf **2023 und 2024**; 2025 war negativ. Die bekannten historischen Jahre sind **nicht** unabhängige neue Marktdaten. Vorzeitige Optimierung auf dieses Ergebnis würde den Aussagewert weiter verschlechtern.

### Kostenstress der Hauptvariante, 2022–08.09.2026

| Gebühren + Slippage je Seite, zusätzlich zum pauschalen 2-bps-Halbspread | Nettorendite | Max. Drawdown |
| ---: | ---: | ---: |
| 0 bps | +15,10 % | −9,04 % |
| **15 bps** | **+13,95 %** | **−9,39 %** |
| 30 bps | +12,82 % | −9,74 % |
| 50 bps | +11,54 % | −10,19 % |

Eine schmal positive Rendite bleibt selbst bei höheren Kosten erhalten. Aber das ist nur eine **historische Sensitivitätsanalyse**, keine bestätigte realisierbare Ausführung.

## Unabhängiger Datenabgleich: bestanden

**Zusätzlicher erfolgreicher [Bitstamp-Datenkonsistenz-Audit #45031312052](https://github.com/schakal00/Schakalpository/actions/runs/45031312052)** mit 4 zusätzlichen Regressionstests. Es wurden zwei getrennte öffentliche Datensätze verglichen: die aktuelle Bitstamp-BTC/USD-Tages-CSV und die aus 1-Minuten-Bitstamp-BTC/USD-Kursen erzeugten täglichen OHLC-Werte.

| Preisfeld | Überlappende UTC-Tage | Median der absoluten Abweichung | Größte Abweichung |
| --- | ---: | ---: | ---: |
| **Schlusskurs** | **2.808** | **0,000 %** | **0,000 %** |
| Tageseröffnung | 2.808 | 0,000 % | 0,231 % |
| Tageshoch | 2.808 | 0,000 % | 0,082 % |
| Tagestief | 2.808 | 0,000 % | 0,024 % |

**Die Schlusskurse stimmen auf allen 2.808 Tagen exakt überein.** Das stärkt die Datengrundlage, ersetzt aber keine Prüfung realer Orderausführungen, Gebühren oder künftig unbekannter Kurse. Die 09:00-Preise stammen aus den 1-Minuten-Archiven, nicht aus dem Tages-Open. Der Audit enthält Einzelbeispiele der größten Preisabweichungen.

[Audit-Code](cecs3_data_audit.py) · [Tests](test_cecs3_data_audit.py). CSV-Resultate und Quell-Hashes im Artifact `cecs3-bitstamp-data-integrity`.

## Neues eigenständiges prospektives Paper-Konto

Am 22.11.2026 erfolgreich initialisiert (separat von CECS2.5 und den drei CECS2.8-Modellen).

- Konto: **100.000 USD virtuelles Startkapital**; **keine historischen Gewinne importiert**.
- Erster frisch erfasster Bitstamp-Quote-Zeitpunkt: **22.11.2026, 14:04:35 UTC**.
- Erster beobachteter Bid **60.674,38 USD**, Ask **60.674,39 USD**.
- Signalquelle Tag `D−2`: **20.11.2026**, Tagesdaten aktuell bis **21.11.2026**.
- Langfristiger Aufwärtstrend nicht erfüllt → **0 % BTC-Ziel**, **0 BTC**, **0 virtuelle Transaktionen**, Kapitalkonto **100.000 USD**.
- GitHub Actions beobachtet künftig täglich gegen **09:35 UTC**. GitHub ist kein garantierter Echtzeitdienst; ein ausgefallener Lauf kann eine geplante Rebalancierung verzögern.
- Kauf nur an einem erlaubten Rebalancing-Tag zum **frisch beobachteten Ask**, Verkauf zum **frisch beobachteten Bid**, jeweils **15 bps zusätzliche Kosten**. Keine echten Börsen-Fills, keine Orders.
- Jede datierte Beobachtung wird gespeichert. Doppelte Verarbeitung wird unterbunden. Ein Versions- oder Quellwechsel in der Strategie-, Buchhaltungs- oder Kursauswertungslogik führt zum Abbruch, statt ein Experiment still zu ändern.
- Tagesinterne Preisschwankungen oder Stop-Berührungen können **nicht** vollständig erkannt werden.

**Einsatzentscheidung:** Stand 22.11.2026 **nur Paper-Trading**. Für eine Echtgeldeinführung fehlen echte, neu entstehende Performance-Daten über unterschiedliche Regime, verifizierte Ausführungspreise und ein harter Risikorahmen nach realen Portfolioverlusten.

## Die nächsten harten Erfolgskriterien

1. Historische Aufzeichnungen, CSV-Hashes, alle angenommenen Gebühren und Code-Versionen bleiben reproduzierbar.
2. Prospektive CECS3-Defensive-Nettorendite wird fortlaufend gegen **gleiches Kapital** und die bestehenden Trend25- und BuyHold25-Schattenkonten verglichen.
3. Drawdown und Marktanteil müssen stets zusammen mit der Rendite berichtet werden.
4. Nach mehreren Monaten und später Jahren neuer Signale wird statistische Unsicherheit neu bewertet; keine kurzfristige Optimierung anhand eines einzigen glücklichen Trade-Ergebnisses.
5. **Keine Garantie und keine Echtgeldfreigabe**, bis die prospektiven Daten einen praktisch relevanten Vorteil zeigen.

## Direkte GitHub-Verweise

- [CECS3-Research-Backtest #45030529487](https://github.com/schakal00/Schakalpository/actions/runs/45030529487)
- [CECS3-Forward-Paper-Initialisierung #45030813685](https://github.com/schakal00/Schakalpository/actions/runs/45030813685)
- [Die tägliche Forward-Datei](cecs3_forward/observations/2026-11-22.json)
- [Aktueller virtueller Kontostand](cecs3_forward/state.json)
- [CECS3-Forward-Simulator](cecs3_forward.py)
- [Ausführungs- und Kausalitätstests](test_cecs3_forward.py)

**Rechtlicher Hinweis:** Technischer Strategieforschungsstand. Weder persönliche Anlageberatung noch ein Beweis für dauerhaft positive zukünftige Rendite.
