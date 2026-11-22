# CECS 2.7 – Trend-/Volatilitätssteuerung: ergebnisoffener Audit

**Stand:** 22.11.2026. [Erfolgreicher automatisierter GitHub-Backtest #45028497287](https://github.com/schakal00/Schakalpository/actions/runs/45028497287), 10 Unit-Tests bestanden.

## Warum wir diese Richtung testen

Die mechanische, Traders-Reality-inspirierte W-/M-15-Minuten-Strategie war 2019–September 2026 bei 15 bps Kosten pro Orderseite durchweg negativ. [CECS-2.6-Ablehnungsbericht](CECS_2_6_MW_NEGATIV_DE.md).

Daher vergleichen wir jetzt **wenig Handelsfrequenz, keine Hebel, Positionsgrößensteuerung** gegenüber dem wichtigsten Gegenbeispiel: gewöhnlicher Bitcoin-Haltung. Keine M/W- oder Vector-Einstiegsoptimierung.

## Abbildung / Daten

- Daten: historische öffentliche Bitstamp-BTC/USD-OHLCV-Tageskerzen 2017–21.11.2026 (3.612 Tage). Im archivierten `manifest.json` mit SHA256 belegt.
- Alle Entscheidungen nur aus voll abgeschlossenen Tageskerzen. Signal vom Tag `t` frühestens zur simulierten Eröffnung `t+2` implementiert, als Proxy für erst am Folgetag publizierte CSV-Daten. Reale 09:00-UTC-Ausführung auf Bitstamp wird dadurch **nicht exakt** nachgebildet.
- Long/Flat-Spot, kein Hebel. Wöchentliche Umschichtung montags, wenn Zielgewicht um mindestens **5 Prozentpunkte** vom aktuellen Gewicht abweicht; bei Trendverlust dagegen zeitnaher Exit.
- Auf jede simulierte Kauf- und Verkaufs-Ausführung **15 Basispunkte Kosten/Slippage** angenommen; Sensitivität bei 0, 5, 15 und 30 bps je Seite.
- Langfristiges Aufwärtssignal: Schluss über SMA200 und SMA50 über SMA200.
- Volatilitätssteuerung: 30-Tage-Standardabweichung der logarithmischen BTC-Tagesrendite, annualisiert mit √365. Zielvolatilität 20 oder 30 %, maximal 75 % BTC-Portfolioexposition; keine Futures/Leverage.
- Bei Cycle- bzw. Vector-Tilt wird die Positionsgröße mit 1,2 bzw. 0,8 gewichtet, begrenzt auf die identische maximale Exposition. **Dieses Faktor-Overlay ist nicht als kausal erfolgreicher Alpha-Beitrag bestätigt.**
- 10 vorher festgelegte Vergleichsvarianten; alle wurden am selben bereits historisch bekannten Kursverlauf untersucht. Mehrfachtest-Risiko berücksichtigen.

## Ergebnis, historischer Teilzeitraum 2022–21.11.2026

| Strategie | Simulierte Nettorendite | Max. täglicher mark-to-market Drawdown | Durchschnittliche BTC-Exposition |
|---|---:|---:|---:|
| 25 % BTC, regelmäßig rebalanciert | **+19,78 %** | **−21,95 %** | 25,06 % |
| 50 % BTC, regelmäßig rebalanciert | +31,75 % | −40,86 % | 50,13 % |
| 100 % BTC, gehalten | +30,00 % | −67,00 % | 100,00 % |
| **Trend25**: 25 % BTC nur im langfristigen Aufwärtstrend | **+16,59 %** | **−13,06 %** | 11,62 % |
| Trend50: 50 % im langfristigen Aufwärtstrend | +32,65 % | −24,48 % | 22,70 % |
| TrendVol20: 20 % Zielvolatilität | +15,43 % | −25,69 % | 21,77 % |
| TrendVol30: 30 % Zielvolatilität | +33,57 % | −33,56 % | 29,27 % |
| TrendVol30Cycle | +24,53 % | −32,92 % | 28,75 % |
| **TrendVol30Vector** | **+41,09 %** | **−31,04 %** | 27,57 % |

Die scheinbar hohe Rendite von Volatilitäts- und Vector-Varianten kam **mit größerem Marktrisiko** zustande. Ohne Risikonormalisierung und unabhängiges Forward-Experiment kann man den Vector-Tilt **nicht** als Alpha-Effekt bezeichnen.

### Einzeljahre

| Variante | 2022 | 2023 | 2024 | 2025 | 2026 bis 21.11. |
|---|---:|---:|---:|---:|---:|
| 25 % BTC, rebalanciert | −20,10 % | +28,26 % | +24,95 % | +0,01 % | −6,47 % |
| **Trend25** | 0,00 % | +10,51 % | +17,23 % | **−7,35 %** | **−2,86 %** |
| Trend50 | 0,00 % | +21,49 % | +35,13 % | −14,30 % | −5,72 % |
| TrendVol30 | 0,00 % | +26,52 % | +45,86 % | −20,16 % | −9,34 % |
| TrendVol30Vector | 0,00 % | +24,81 % | +49,25 % | −18,72 % | −6,81 % |

**Kein konstantes Plus pro Jahr:** 2025/2026 belasten die meisten Trendstrategien. 2022 war die Trendregel überwiegend nicht im Markt. Die 2022–2026-Rendite entstand wesentlich 2023/2024.

### Belastung mit 30 Basispunkten Kosten pro Seite

- Trend25: **+15,80 %**, Drawdown −13,37 %.
- Trend50: **+30,83 %**, Drawdown −25,02 %.
- TrendVol30: **+30,55 %**, Drawdown −34,22 %.
- TrendVol30Vector: **+36,63 %**, Drawdown −31,89 %.
- Rebalancierte 25-%-BTC-Benchmark: **+19,66 %**, Drawdown −21,95 %.

## Interpretation und Entscheidung

**Aktuell gibt es zwei wirtschaftlich sinnvolle, klar unterschiedliche Forschungsoptionen:**

1. **Trend25**: defensivere Marktbeteiligung, begrenzte historische Verluste, ca. 12 % durchschnittliche Exposition im Review. Gegenüber der immer investierten 25-%-Benchmark weniger Rendite, aber erheblich geringerer maximaler Drawdown.
2. **TrendVol30Vector**: höhere historische Rendite, allerdings rund −31 % maximaler Drawdown und deutlich mehr Umschichtungen. Der zusätzliche Vector-Beitrag ist unbewiesen.

Wir werden **keine** als „optimal“ benennen, ohne dass die zulässige Drawdown-Grenze und die künftigen Daten die Auswahl rechtfertigen. Als nächste Validierung werden beide sowie ein konventioneller Benchmark **parallel und eingefroren prospektiv** im separaten virtuellen Journal beobachtet.

Das bestehende `TrendCycleWide6Delayed`-Paper-Modell bleibt unverändert und als unabhängiger Vergleich bestehen. Keine Echtgeldfreigabe.

### Reproduzierbarkeit

- [Runner](cecs_v2_7_slow.py) und [Unit-Tests](test_slow.py).
- [Actions Run #45028497287](https://github.com/schakal00/Schakalpository/actions/runs/45028497287) → Artifact `cecs-2-7-slow-results`.
- Artefaktinhalt: `summary.csv`, `periods.csv`, `orders.csv`, `daily_equity.csv`, `cost_sensitivity.csv`, `manifest.json`.

**Warnung:** Alle oben berichteten Jahre wurden bereits bei der Strategieentwicklung betrachtet. Der Entwicklungs- und der historische Reviewteil sind kein wirklicher Out-of-sample- oder Walk-forward-Leistungsnachweis. Finanzresearch ohne Zukunftsgarantie.


## Explorative Unsicherheit: Bringt der Vector-Faktor zusätzlichen Ertrag?

Aus den **täglich synchronisierten, nach Kosten modellierten Equity-Reihen** für den bereits untersuchten Zeitraum 2022–21.11.2026 wurde der logarithmische Renditeunterschied zwischen `TrendVol30Vector` und `TrendVol30` berechnet.

- Beobachtet: ca. **+1,12 Prozentpunkte annualisierte logarithmische Überrendite** in dieser historischen Stichprobe.
- Grobe *Kalendermonatsblock-Bootstrap*-Prüfung mit 4.000 Replikaten und festem Pseudozufalls-Seed: ca. **−1,66 bis +3,80 Prozentpunkte** für ein nominales 95-%-Intervall.
- Das Intervall schließt **null** ein. Zudem wurden die Strategien bereits anhand derselben historischen Daten entworfen und verglichen; der Bootstrap korrigiert **nicht** für dieses nachträgliche Auswahlproblem. Kalendermonate sind außerdem nicht wirklich unabhängig. Das Intervall ist nur explorative Unsicherheitsinformation, **kein formal gültiger Signifikanznachweis**.
- Gegen `Trend50` lag die annualisierte Log-Überrendite bei ca. **+1,26 Prozentpunkten**, gleichfalls mit sehr breitem Monatsblock-Bootstrap-Intervall von ungefähr **−3,66 bis +6,34**.

**Entscheidung:** Den Vector-Tilt nicht als erfolgreiche Verbesserung vermarkten. Die Baseline bleibt die unveränderte Trend-/Exposure-Regel. Erst künftige datierte Beobachtungen können helfen, einen unabhängigen Nutzen zu prüfen.

**Reproduzierbarer Nachtest:** Der erfolgreiche [Cloud-Lauf #45028497287](https://github.com/schakal00/Schakalpository/actions/runs/45028497287) enthält die Datei `exploratory_bootstrap.csv` mit den oben genannten Monatsblock-Stichprobenintervallen sowie die vollständigen Equity-Kurven und Quellen-Hashes. Implementierung: [cecs_uncertainty.py](cecs_uncertainty.py), Tests: [test_uncertainty.py](test_uncertainty.py). Die resultierenden Intervalle werden ausdrücklich **nicht** als formale Signifikanztests oder als Auswahlbias-Korrektur interpretiert.
