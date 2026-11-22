# CECS – BTC/USD Research

## Status: GitHub Actions erfolgreich

- **[Deutsche Ergebnisse 2017–2026](ERGEBNISSE_DE.md)**
- **[Erster erfolgreicher automatischer Lauf](https://github.com/schakal00/Schakalpository/actions/runs/45006342841)**
- **[Programmcode](cecs_v2_1_runner.py)** und **[7 Regressionstests](test_cecs_runner.py)**

CECS kombiniert mechanische Näherungen der DCL/WCL-Zyklusanalyse, einen Elliott-Welle-2-Proxy und Traders-Reality-inspirierte Vector Candles auf öffentlichen BTC/USD-Tagesdaten.

Der Repo-Runner ist eine eigenständige, bewusst kompakte Version des früheren CECS-2.1-Forschungsprojekts. Er ist **nicht** die vollständige originale Camel-Finance- oder Traders-Reality-Methode.

### Reproduzieren

GitHub → Actions → **CECS BTC research audit** → Run workflow.

Der Workflow prüft die Strategie-Implementierung, lädt den aktuellen öffentlichen Bitstamp-Tagesdatensatz herunter und erstellt ein ZIP mit Trades, Statistiken, Vector-Recovery und Quellen-Hash. Keine API-Schlüssel erforderlich, keine echten Orders.

### Befund (historische Nachrechnung 2022–2026)

Die kombinierten harten CECS-Filter ergaben **0 Trades**. Der separate Vector-Filter lieferte 11 Trades mit +3,35 % Modellrendite bei den hinterlegten Gebühren-/Slippageannahmen. Die Stichprobe ist zu klein für einen Nachweis dauerhafter Profitabilität. [Details und Grenzen](ERGEBNISSE_DE.md).

**Kein Investmentrat und kein Live-Handelssystem.**
