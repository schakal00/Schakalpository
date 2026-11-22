# CECS 2.2 – BTC/USD Intraday-Forschungsbericht

**22. November 2026 · Reproduzierbarer Cloud-Backtest:** [GitHub Actions Lauf #3](https://github.com/schakal00/Schakalpository/actions/runs/45008481583) (Erfolg).

## Forschungsfrage

Liefern aus Bitstamp-BTC/USD-Minutenkerzen abgeleitete **15-Minuten-Vector-Candles** zusammen mit einem **vollständig abgeschlossenen 1h-Trendfilter** und optionalen Camel-inspirierten DCL-/Elliott-Proxys höhere Handelsqualität als 15-Minuten-Breakouts allein?

**Status:** Kein nachgewiesener profitabler Vorteil. Die vorliegende 15m-Regel ist im untersuchten Zeitraum bei realistisch zu prüfenden Ausführungskosten deutlich negativ.

## Authentische OHLCV-Daten

- Börse / Währung: **Bitstamp BTC/USD**; keine Vermischung mit BTC/USDT.
- Quelle: [Öffentliches Bitstamp-Minutenarchiv von alessiostomeo/btc-cycle-data](https://github.com/alessiostomeo/btc-cycle-data) (wiederum aus einem Community-Mirror).
- 2024: **527.040 Minuten → 35.136 gültige 15m-Kerzen**; 100 % Abdeckung.
- 2025: **525.600 Minuten → 35.040 gültige 15m-Kerzen**; 100 % Abdeckung.
- 2026: **362.880 Minuten → 24.192 gültige 15m-Kerzen**, nur **01.01.–09.09.2026**; 100 % Abdeckung bis dahin. Die Minutequelle ist **nicht bis zum 22.11.2026 aktuell**.
- Alle drei Archive: 0 ungültige Minutenzeilen, 0 verworfene unvollständige 15m-Intervalle im Lauf #2. Individuelle SHA256-Hashes in `results_intraday/intraday_manifest.json`.

## Festgelegter, einfacher Vergleich

1. **Breakout**: Schlusskurs 15m oberhalb der acht vorangegangenen 15m-Hochs; letzter vollständig verfügbarer 1h-EMA50 über EMA200.
2. **BreakoutVector**: zusätzlich mindestens eine bullische Climax-/High-Volume-Vector-Candle innerhalb der letzten vier abgeschlossenen 15m-Kerzen, **oder** bärische Vector-Zone wird über 50 % zurückerobert.
3. **CycleVector**: außerdem letzter bestätigter DCL-Proxy innerhalb von 30 Tagen.
4. **ElliottVector**: außerdem letzter bestätigter mechanischer Welle-2-Proxy innerhalb von 30 Tagen.
5. **AllConfluence**: Vector + Cycle + Elliott zugleich im 30-Tage-Fenster, **nicht** zwingend derselbe zyklische Pivot.

Entry **nächste** 15m-Eröffnung; Stop 1,5 ATR(14) unter dem Einstieg; Target netto 2R; Haltedauer höchstens 96 15m-Bars; Anfangsrisiko 0,25 % Modellkapital, ohne Hebel. Stop hat Vorrang, wenn Stop und Target in derselben Kerze getroffen werden. Kein echter Orderflow oder Spread-Replay. Die Handelskosten **je Leg** enthalten geschätzte Gebühren und Slippage; 15 bps je Leg bedeutet etwa 30 bps Roundtrip.

## Ergebnisse bei 15 Basispunkten je Ausführung

| Marktjahr | Breakout | BreakoutVector | CycleVector | ElliottVector | AllConfluence |
| --- | ---: | ---: | ---: | ---: | ---: |
| **2024** | −37,71 % (580 Trades) | −35,37 % (540) | −14,84 % (154) | −8,20 % (121) | −8,18 % (94) |
| **2025** | −42,04 % (477) | −39,44 % (435) | −15,37 % (135) | −15,10 % (111) | −5,84 % (33) |
| **2026 bis 09.09.** | −29,32 % (329) | −24,11 % (286) | −6,92 % (126) | −6,22 % (120) | −5,74 % (112) |

Alle Modellrenditen starten **jeweils** mit hypothetischen 100.000 USD Anfangskapital pro Jahr; jährliche Werte dürfen nicht ohne weiteres addiert werden. Unterschiede der Filter zeigen auch unterschiedliche **Marktexposition**; weniger absoluter Verlust ist nicht automatisch bessere Signalselektion.

Die mark-to-market Drawdowns aus 15m-Kursen betrugen für das AllConfluence-Modell **−9,69 % (2024), −6,21 % (2025), −6,70 % (2026 bis 09.09.)**.

## Kosten-Sensitivität: gleiche Grundregeln, erneute Simulation

**Modellrendite – BreakoutVector:**

| Jahr | 0 bps/Leg | 5 bps/Leg | 15 bps/Leg |
| --- | ---: | ---: | ---: |
| 2024 | +11,41 % | −21,11 % | −35,37 % |
| 2025 | −10,55 % | −31,08 % | −39,44 % |
| 2026 bis 09.09. | −2,42 % | −15,68 % | −24,11 % |

**Modellrendite – AllConfluence:**

| Jahr | 0 bps/Leg | 5 bps/Leg | 15 bps/Leg |
| --- | ---: | ---: | ---: |
| 2024 | +1,98 % | −6,05 % | −8,18 % |
| 2025 | −4,32 % | −5,52 % | −5,84 % |
| 2026 bis 09.09. | +6,13 % | +0,56 % | −5,74 % |

Bei jeder Kostenstufe werden Positionsgröße und Netto-Kursziel neu berechnet. Deshalb ändern sich auch Ausstiegszeit und Trade-Anzahl; dies ist **kein identischer Fixed-Trade-Sample-Vergleich**, sondern eine realistische Kosten-Szenarioanalyse.

## Schlussfolgerungen

- **Keine Freigabe** für Echtgeldhandel oder vermeintlich verlässliche Vector-Candle-Signale.
- 2025 verfehlt selbst das kostenfreie AllConfluence-Modell einen positiven Erwartungswert.
- Das bisherige Vector-Modul implementiert **nicht** Tinos vollständigen Traders-Reality-Hybridansatz, insbesondere noch keine quantifizierte M-/W-Pattern-Logik, Handelszeiten/Sessions oder Volumenverschiebungen unterhalb von 15m.
- Filter, die weniger Trades erzeugen, müssen auf **Erwartungswert pro R, Drawdown, Exposure und unabhängige Signalinformation** verglichen werden, nicht ausschließlich auf Gesamtrendite.
- Ausführungspreise werden anhand aggregierter 15m OHLC angenommen, nicht auf Basis echter Orderbuchfills. Dies kann die effektiven Kosten und Stop-/Target-Reihenfolge verfälschen.
- Rückblickende Forschungsentwicklung ≠ prospektiver, unberührter Out-of-sample-Test.

## Weiterentwicklung (ohne nachträgliche Renditeoptimierung)

A. **Daten- und Codeaudit**: Prefix-Invarianz/Look-ahead-Test; separate Quellverifikation gegen Börsenfeed; harte Prüfungen für Gap-Märkte.

B. **Tino-Setup präzisieren**: klar erkennbare M-/W-Strukturen, Vector-Recovery *mit* Kontext und Session-Regeln. Erst feste Definitionen, dann historische Ausführung.

C. **Tageschart-Signale und Intraday-Entry getrennt vergleichen**: identische übergeordnete Setups, dann 15m-Entry versus Standard-Tageschart-Entry; nicht alle 15m-Breakouts der Welt handeln.

D. **Walk-forward und Paper-Trading** erst nach Stabilitätsprüfung; keine Echtgeldanbindung.

## Reproduzierbarkeit

- Skript: [cecs_v2_2_intraday.py](cecs_v2_2_intraday.py).
- Tests: [test_intraday.py](test_intraday.py).
- Vollständiger Lauf inkl. Archive-Hashes, `intraday_summary.csv`, `intraday_sensitivity.csv`, `intraday_trades.csv` und `intraday_coverage.csv`: [GitHub Actions Lauf #3](https://github.com/schakal00/Schakalpository/actions/runs/45008481583) → Artifact `cecs-btc-research-results`.

**Hinweis:** Keine persönliche Anlageempfehlung, sondern ein reproduzierbarer, experimenteller Backtest.
