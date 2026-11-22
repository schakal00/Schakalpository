# CECS 2.4 – Vorwärtsbeobachtung ab 22.11.2026

**Status: Beobachtungsprotokoll aktiv, kein Paper-Orderbuch, keine Brokeranbindung.**

- [Erster bestätigter Lauf (erfolgreich)](https://github.com/schakal00/Schakalpository/actions/runs/45011721258)
- [Erste unveränderbare Tagesbeobachtung vom 22.11.2026](paper_watch/2026-11-22.json)
- [GitHub-Workflow für täglich 09:00 UTC](.github/workflows/cecs-paper-watch.yml)
- [Programm](daily_watch.py) und [Regressionstests](test_daily_watch.py)

## Warum wir nicht einfach auf möglichst positive vergangene Ergebnisse optimieren

Die vorangegangene BTC/USD-Variante `TrendCycleWide6` war von 2022 bis November 2026 etwa **+1,2072 %** im Plus nach 15 Basispunkten Kosten je Leg, bei **−1,3174 %** maximalem mark-to-market Drawdown. Dieser Zeitraum wurde bereits während der Entwicklung wiederholt eingesehen; er ist **kein unberührter Testzeitraum**.

Die öffentliche Tages-CSV wird erst Stunden nach dem Abschluss der UTC-Tageskerze aktualisiert. Der ursprünglich angenommene Einstieg am nächsten 00:00-Open wäre zum Zeitpunkt der Datenverfügbarkeit schon vorbei. Darum gibt es den expliziten Zwei-Tage-Kerzen-zu-Ausführung-Proxy `TrendCycleWide6Delayed` mit zusätzlichen Tests.

**Resultat der verzögerten historischen Nachrechnung im bereits eingesehenen Zeitraum 2022–21.11.2026:** **+0,4741 %**, maximaler mark-to-market Drawdown **−1,3649 %**. Das ist ein kleiner, wirtschaftlich fraglicher Effekt, **kein nachgewiesener Trading-Edge**. Auch die verzögerte Variante ist noch eine reine Tageskerzen-Simulation und repliziert keine minutengenaue Marktausführung.

## Ab 22.11.2026: täglich dokumentierte Beobachtung statt Ergebnis-Kosmetik

An jedem Tag um ca. 09:00 UTC (GitHub Actions Schedule ist best-effort und kann sich verspäten) ruft der Workflow die jüngste verfügbare öffentliche Bitstamp-OHLCV-Tagesreihe ab und schreibt eine Datei `paper_watch/YYYY-MM-DD.json`. Bestehende Tagesdateien werden **nicht überschrieben**. Wenn die Daten zu alt sind, scheitert die Prüfung, statt eine aktuelle Aussage zu erfinden.

Der Eintrag dokumentiert:
- verwendetes UTC-Datum, letztes vollständig abgeschlossenes Kursdatum und Daten-SHA256;
- SHA256 des lokalen Strategiemoduls;
- SMA50/SMA200, ATR14, bestätigten DCL-Proxy, Welle-2-Proxy und Vector-Candle-Proxy;
- ob das **Signal-Gate** erfüllt wäre, und eine aus der Historie rekonstruierte Modellposition.

**Achtung:** Ein Gate ist **keine Order**. Zwischen CSV-Verfügbarkeit und hypothetischer Ausführung bleibt ein unbekannter Markttag. Ein *echter* prospektiver Paper-Trade erfordert einen separaten persistierten Orderzustand, eine klar definierte realistische Ausführungszeit, simulierte tatsächliche Fills und eine unveränderliche Trade-Historie. **Die historischen Modellpositionen und ihr Cashstand sind nicht prospektiver Paper-P&L.**

## Erste protokollierte Beobachtung 22.11.2026

- Datenstand: Schlusskurs 21.11.2026 **60.078,34 USD**, ATR14 **3.218,79 USD**.
- SMA50 **77.137,86 USD**, SMA200 **72.427,40 USD**.
- DCL-Proxy: Ja. Vector-Proxy: Ja. Elliott-Welle-2-Proxy: Nein.
- **Trendbedingung: Nein, daher kein Einstiegskandidat.**
- Historisch rekonstruierte Modellposition: Flat. Das ist noch kein erfasster Paper-Trade.
- [Originaldatensatz-Snapshot-Hash und vollständiger Eintrag](paper_watch/2026-11-22.json).

## Nächste fachliche Priorität

1. **Risikofreie Forward-Protokollierung** ohne Änderungen an der Strategie; noch keine Optimierung auf neue Einzelwochen.
2. **Besseres Paper-Execution-Modell**, das nach beobachteter Ausführung tatsächliche Fills, Positionszustand, Handelskosten und die historische Regelversion dauerhaft speichert. Ohne dieses Modell keine angebliche Paper-Performance.
3. **Parallel und separat** mechanische Tino-M-/W-Strukturen und Vector-Recovery als Alternativstrategie entwickeln. Diese nicht ungeprüft in das eingefrorene Trendmodell mischen.
4. Neue Ergebnisse gegen einfacher erklärbare Benchmarks (Buy & Hold, Trendfilter, risikogleiche Exposition) prüfen. Statistische Unsicherheit und Marktwechsel berücksichtigen.

Das Ziel ist weiterhin ein positiver *prospektiver* Netto-Erwartungswert, nicht eine möglichst schön aussehende historische Rendite.
