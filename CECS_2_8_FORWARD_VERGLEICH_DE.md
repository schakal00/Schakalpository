# CECS 2.8 – Eingefrorener Forward-Vergleich mit drei Schattenportfolios

**Stand: 22. November 2026.** Der [erste GitHub-Cloud-Lauf #45028041087](https://github.com/schakal00/Schakalpository/actions/runs/45028041087) war erfolgreich, **14 Regressionstests bestanden**.

Das Experiment ergänzt das bestehende [CECS-2.5-Paper-Journal](CECS_2_5_PAPER_DE.md), **verändert es aber nicht**. Kein Brokerzugang, kein echtes Trading und kein Anlageversprechen.

## Ziel

Historische Ergebnisse aus 2022–2026 waren bereits während der Modellentwicklung bekannt. Um uns nicht weiter an denselben Kursen festzuoptimieren, beobachten wir **ab jetzt neu entstehende Marktentscheidungen und Preisstände**, ohne die Regeln zwischenzeitlich anzupassen.

Drei unabhängig gerechnete virtuelle Spot-Konten mit je **100.000 USD Startkapital**:

| Konto | Einfrierungsregel | Ziel / Risikofaktor |
|---|---|---|
| `BuyHold25` | 25 % BTC, sonst USD, regelmäßig rebalanciert | Einfacher Referenzbenchmark, Marktanteil dauerhaft ca. 25 % |
| `Trend25` | 25 % BTC nur bei Schlusskurs über SMA200 **und** SMA50 über SMA200 | Defensiver Trendkandidat ohne garantierten Verlustdeckel |
| `TrendVol30Vector` | Aufwärtstrend + anhand der letzten 30 abgeschlossenen Tage annualisierte Volatilität + bereits bekannter Vector-Candle-Proxy | Max. 75 % Spot-BTC, deutlich höheres Risiko. Vector-Mehrwert ist statistisch **nicht** nachgewiesen |

## Wie tägliche Daten verwendet werden

GitHub Actions soll gegen **09:15 UTC** täglich das separat gespeicherte Script `slow_shadow.py` ausführen; GitHub-Startzeiten sind **nicht garantiert**.

- Verlangt einen neuen, vollständig abgeschlossenen UTC-Tagesdatensatz: Tag `D−1`.
- Handelsentscheidung wird absichtlich nur aus dem **noch älteren, vollständig abgeschlossenen** Tag `D−2` abgeleitet, damit die historische Publikationsverzögerung berücksichtigt wird.
- Die virtuelle Ausführung erfolgt am Tag `D` **zum neu abgefragten, zeitgestempelten Bitstamp-Geld- oder Briefkurs**, nicht rückwirkend zu einem früheren Midnight-Open.
- Wöchentlich montags Positionen auf Zielexposition zurückführen, sofern das Gewicht um mindestens 5 Prozentpunkte abweicht; bei Trendverlust auch an anderen Tagen Ausstieg.
- Bei Käufen gilt der beobachtete **Ask**, bei Verkäufen der beobachtete **Bid**, jeweils plus angenommene **15 Basispunkte Kosten pro Orderseite**.
- Kein Hebel, keine Shorts und keine echten API-Orders.
- Simulierter Marktwert wird konservativ zum Geldkurs nach angenommenen Verkaufskosten bewertet.
- Jede Tagesdatei `slow_shadow/observations/YYYY-MM-DD.json` ist separat datiert. Doppelte Verarbeitung ist gesperrt.
- Die SHA256 der Strategiequelle ist beim ersten Lauf eingefroren; nachträgliche Änderungen an dieser Quelle führen zum Abbruch, statt das bestehende Experiment still zu verändern.
- Bei unvollständigen oder zu alten Kursen wird der Lauf abgebrochen, nicht mit fingierten Schlusskursen fortgesetzt.

## Erste prospektive Beobachtung vom 22.11.2026

[Originaldatensatz hier](slow_shadow/observations/2026-11-22.json).

- Frischer Bitstamp-Ticker: **13:32:56 UTC**, Bid **60.734,04 USD**, Ask **60.734,05 USD**.
- Bestätigte Signale stammen vom **20.11.2026**, der letzte verfügbare abgeschlossene Tagesdatensatz vom **21.11.2026**.
- Übergeordneter Aufwärtstrend: **nein**.
- Zielgewicht `BuyHold25`: 25 %; erster Start am Sonntag, ein geplantes wöchentliches Rebalancing findet deshalb erst am nächsten Montag statt.
- Zielgewichte `Trend25` und `TrendVol30Vector`: **0 %**.
- Alle drei virtuellen Konten: **100.000 USD**, **0 BTC**, **0 % neue Paper-Rendite**, keine rückwirkend gefüllten Aufträge.

## Was dieses Journal NICHT kann

- Tägliches Sampling kann Stop- und Kurssprünge innerhalb des Tages übersehen.
- Die Portfolios haben **keine festen Stop-Orders**. Historisch war bei `TrendVol30Vector` ein mark-to-market Drawdown von über 30 % möglich. Ein hartes Verlustlimit oder die 0,5-%-Anfangsrisikoregel der anderen CECS-Strategie gelten hier **nicht**.
- Die übernommenen historischen Renditen [aus CECS 2.7](CECS_2_7_SLOW_DE.md) sind **keine Paper-Renditen**; Konto-P&L wird erst ab dem tatsächlichen Einführungsdatum gesammelt.
- Positiver Ausgang darf nicht nach wenigen Tagen behauptet werden. Für eine belastbare Beurteilung benötigen wir längere, unterschiedliche Trend- und Volatilitätsregime, genügend voneinander unabhängige Entscheidungen und einen Vergleich mit identischer Exposition.
- Selbst ein über mehrere Jahre vorteilhafter Paper-Test garantiert keine reale Handelbarkeit oder künftige Gewinne.

## Wissenschaftliche Entscheidungsschwelle

Eine Strategie wird **nicht** für echtes Trading vorgeschlagen, solange ihre prospektive Netto-Performance, Drawdowns, Ausführungslatenzen, Handelskosten und ihr Mehrwert gegenüber dem einfachen Benchmark nicht über einen ausreichend langen Zeitraum bewertet werden können.

Aktueller Status für alle drei: **nur virtuelles Beobachtungs-/Forschungsportfolio**.

## GitHub-Links

- [Erster erfolgreicher CECS-2.8-Testlauf](https://github.com/schakal00/Schakalpository/actions/runs/45028041087)
- [Original-Einträge der täglichen Schattenportfolios](slow_shadow/observations/)
- [Aktueller virtueller Kontostand aller drei Modelle](slow_shadow/state.json)
- [Vorwärts-Paper-Engine](slow_shadow.py), [Tests](test_slow_shadow.py), [Zeitplan](.github/workflows/cecs-slow-shadow.yml)
- [Frühere positive und negative BTC-Backtests mit Unsicherheitsanalyse](CECS_2_7_SLOW_DE.md)
