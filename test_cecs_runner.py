import csv
import datetime as dt
import io
import unittest

import cecs_v2_1_runner as r


class CECSResearchTests(unittest.TestCase):
    def make_prices(self, n=620):
        start = dt.date(2020, 1, 1)
        rows = []
        for i in range(n):
            c = 100 + i * .05
            rows.append(dict(date=start + dt.timedelta(days=i), open=c, high=c + 1,
                             low=c - 1, close=c + .2, volume=50 + i % 10))
        return rows

    def to_csv(self, rows):
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["date_utc", "open", "high", "low", "close", "volume"])
        w.writeheader()
        for x in rows:
            w.writerow(dict(date_utc=x["date"], **{k: x[k] for k in ("open", "high", "low", "close", "volume")}))
        return buf.getvalue().encode()

    def test_data_validation_and_gap(self):
        data = self.make_prices()
        parsed = r.parse_data(self.to_csv(data))
        self.assertEqual(len(parsed), 620)
        del data[10]
        with self.assertRaises(ValueError):
            r.parse_data(self.to_csv(data))

    def test_volume_vector_is_causal(self):
        data = self.make_prices()
        r.enrich(data)
        first = [x["vector"] for x in data[:-1]]
        data[-1]["volume"] = 100000000
        r.enrich(data)
        self.assertEqual(first, [x["vector"] for x in data[:-1]])
        self.assertIn(data[-1]["vector"], ("green", "red"))

    def test_no_pivot_before_three_following_bars(self):
        candles = self.make_prices(630)
        candles[15]["low"] = 50
        events = r.confirmed_pivots(candles, 7, 3)
        self.assertFalse(any(k == "L" and i == 15 for tick in events[:18] for k, i, _ in tick))
        self.assertTrue(any(k == "L" and i == 15 for k, i, _ in events[18]))

    def test_weekly_data_available_only_next_monday(self):
        bars = self.make_prices(660)
        weeks, _ = r.weekly_events(bars)
        self.assertTrue(weeks)
        for w in weeks:
            self.assertEqual(w["available"].weekday(), 0)
            self.assertEqual(w["available"] - w["monday"], dt.timedelta(days=7))
            self.assertEqual(w["count"], 7)

    def test_recovery_excludes_current_candle(self):
        bars = self.make_prices(620)
        for x in bars:
            x["vector"] = "ordinary"
        bars[20]["open"] = 100
        bars[20]["close"] = 99
        bars[20]["high"] = 104
        bars[20]["low"] = 96
        bars[20]["vector"] = "red"
        for x in bars[21:31]:
            x["high"] = 101
        st = r.study_vector_recovery(bars, 0, 620)
        red = next(x for x in st if x["label"] == "red")
        self.assertEqual(red["n"], 1)
        self.assertEqual(red["mid_recovery_pct"], 100)
        self.assertEqual(red["full_recovery_pct"], 0)

    def test_no_trade_does_not_claim_winrate(self):
        bars = self.make_prices(620)
        stats, trades = r.simulate(bars, [], "CECS", 0, 619)
        self.assertEqual(stats["trades"], 0)
        self.assertIsNone(stats["win_rate_pct"])
        self.assertFalse(trades)

    def test_vector_confirmation_uses_closed_past_only(self):
        data = self.make_prices(620)
        for x in data:
            x["vector"] = "ordinary"
        data[98]["vector"] = "blue"
        self.assertTrue(r.vector_confirmation(data, 100))
        data[98]["vector"] = "ordinary"
        self.assertFalse(r.vector_confirmation(data, 100))


if __name__ == "__main__":
    unittest.main()
