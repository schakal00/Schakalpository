# CECS 2.5 – Papierhandelsjournal mit echten Zeitstempeln

**Technischer Stand: 22. November 2026.** Automatischer Cloud-Lauf [#45012628339](https://github.com/schakal00/Schakalpository/actions/runs/45012628339) erfolgreich, **20 Tests bestanden**.

## Was ab jetzt automatisch protokolliert wird

Ein GitHub-Actions-Workflow wird täglich gegen 09:00 **UTC** angestoßen (GitHub kann später starten). Er:

1. archiviert die aktuell publizierten BTC/USD-Tagesindikatoren `paper_watch/YYYY-MM-DD.json` (Camel-inspirierter DCL-Proxy, langfristige Trendbedingung, Elliott-Welle-2-Proxy und Vector-Proxy);
2. liest den **öffentlichen** Bitstamp-BTC/USD-Ticker mit Zeitstempel und Bid/Ask (`https://www.bitstamp.net/api/v2/ticker/btcusd/`);
3. verwirft ungültige/stale Kurse und doppelte Tagesaufrufe;
4. führt den **rein virtuellen** Paper-Zustand in `paper_execution/state.json` fort;
5. schreibt eine auditierbare Tagesdatei `paper_execution/observations/YYYY-MM-DD.json`.

Keine Brokerverbindung, keine echten Orders, keine privaten API-Schlüssel, keine finanzielle Belastung des Nutzers.

## Eingefrorene Pilotregeln

**Studienvariante:** `TrendCycleWide6Delayed`. **Keine nachträgliche Strategieanpassung auf Basis des ersten Paper-Laufs.**

- BTC/USD Spot, Bitstamp; Long/Flat.
- Trendfilter: letzter abgeschlossener Schlusskurs über SMA200; SMA50 über SMA200.
- DCL-Proxy: bestätigtes Tief im mechanischen 45–85-Tage-Zyklus, zeitlich begrenzt.
- Elliott und Vector werden weiter gespeichert, sind aber **keine zusätzlichen Pflichtbedingungen**.
- Wenn ein Gate am UTC-Tag D nach Verfügbarkeit der Tagesdaten erfüllt ist, erzeugt das **nur eine Einstiegsabsicht**. Diese darf erst am folgenden UTC-Kalendertag D+1 beim tatsächlichen nächsten Workflow-Lauf virtuell ausgeführt werden.
- Der Einstiegskurs ist der **frisch beobachtete Bitstamp-Briefkurs (Ask)**; der Verkaufskurs ist der **frisch beobachtete Geldkurs (Bid)**. Pro Ausführung werden zusätzlich **15 Basispunkte** angenommene Gebühren/Slippage gerechnet. Dies ist eine **Simulation**, keine garantierte tatsächliche Ausführung.
- Startkapital: **100.000 USD virtuell**. Kein Hebel. Nominaler Initialstop 6 × Tages-ATR(14) unter dem beobachteten Einstiegskurs; risikobasierte Positionsgröße auf **höchstens 0,5 % Initialrisiko** bei nicht springenden Kursen begrenzt.
- Trend-Ende oder ein beim nächsten Workflow-Lauf unter Stop notierender Bid führt zu einem **virtuellen Verkauf zum dann beobachteten Bid**.
- Abgeschlossene Tageshochs dürfen den virtuellen Trailing-Stop frühestens bei einer späteren Beobachtung verändern. Bestätigung darf nicht in die Zukunft schauen.
- Nach Verkauf mindestens 10 vollständige Tage Abstand bis zum nächsten neuen Entry-Intent. Keine zwei Trades am selben Tag.

**Wichtig: Dieses Paper-Execution-Modell ist nicht identisch mit dem historischen Backtest, der hypothetische Tages-Open- und Intraday-Stopp-Ausführungen verwendete. Historische +0,47 % dürfen daher ausdrücklich nicht als erwartete Paper-Rendite behandelt werden.**

## Ergebnis des ersten produktiven *virtuellen* Beobachtungslaufs

[Originaleintrag vom 22.11.2026](paper_execution/observations/2026-11-22.json).

- Zeitgestempelter Bitstamp-Ticker: **10:28:53 UTC**, Bid **60.802,93 USD**, Ask **60.802,94 USD**.
- Kein Einstiegskandidat: Trendfilter war aus.
- Paper-Position: **0 BTC**, Kontostand/Equity **100.000 USD**, realisierter Gewinn/Verlust **0 USD**.
- Keine nachträglich erzeugten Trades oder erfundenen Paper-Gewinne.

## Technische Grenzen und nächste Verbesserungen

- **Tägliche Kursabfrage ist keine Stop-Order.** Der Kurs kann intraday den Stop berühren und vor der Abfrage wieder darüber liegen. Verlust bei Verkauf zum nächsten beobachteten Bid kann auch **höher als 0,5 %** ausfallen.
- Die vorgesehene Uhrzeit von GitHub Actions ist eine Best-effort-Planung, kein Echtzeitservice. Wenn der Lauf ausfällt, fehlen Paper-Beobachtungen und ein Einstiegsvorhaben kann verfallen.
- Best Bid/Ask und angenommene Kosten sind kein reales Fill- oder Orderbuch-Replay. Volumen, tatsächliche Liquidität, Execution Queue und Handelsplatzgebühren sind nicht modelliert.
- Tagesdaten aus einer unabhängigen öffentlichen GitHub-CSV sind nicht dieselbe Quelle wie der live abgefragte Bitstamp-Ticker; Abweichungen und Datenverzögerungen sind möglich.
- Mit nur einem echten prospektiv erstellten Beobachtungseintrag ist **keinerlei zukünftige Profitabilität** nachgewiesen.
- Der vollständige Traders-Reality-M-/W-/Session-Ansatz ist hier **noch nicht** implementiert; Vector-Proxys bleiben getrennte Beobachtungsmerkmale.

## Wo auf GitHub

- [Paper-Tagesdateien](paper_execution/observations/)
- [Aktueller virtueller Kontostand](paper_execution/state.json)
- [Der Ausführungsalgorithmus](paper_engine.py)
- [20 erfolgreich getestete Regeln](test_paper_engine.py)
- [Automatischer Workflow](.github/workflows/cecs-paper-watch.yml)

Forschungsversion. Kein Anlageversprechen oder Echtgeldsignal.
