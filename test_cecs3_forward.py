import csv
import datetime as dt
import io
import unittest

import cecs3_forward as p

UTC=dt.timezone.utc


def when(day):
    return dt.datetime.combine(day,dt.time(9,35),tzinfo=UTC)


def quote(now,bid=60000.,ask=60012.):
    return dict(exchange="Bitstamp",symbol="BTC/USD",
        exchange_timestamp_utc=now.isoformat(),captured_at_utc=now.isoformat(),
        bid_usd=bid,ask_usd=ask,source="test",quote_sha256="test")


def signal(now,weight=.25):
    return dict(observed_on_utc_day=now.date().isoformat(),
        most_recent_complete_utc_day=(now.date()-dt.timedelta(days=1)).isoformat(),
        last_actionable_signal_day=(now.date()-dt.timedelta(days=2)).isoformat(),
        source_sha256="test",desired_btc_weight=weight,
        actionable_features=dict(trend_regime=weight>0))


class CECS3ForwardTests(unittest.TestCase):
    def test_initial_account_is_not_padded_with_backtest_profits(self):
        s=p.initial_state("sha")
        self.assertEqual(s["cash_usd"],100000)
        self.assertEqual(s["btc_quantity"],0)
        self.assertEqual(s["all_virtual_orders"],0)

    def test_monday_buy_uses_fresh_ask_and_cost(self):
        n=when(dt.date(2026,11,23))  # Monday
        s,a=p.advance(p.initial_state("sha"),signal(n),quote(n),n,"sha")
        self.assertEqual(a["event"]["type"],"SIMULATED_BUY")
        self.assertEqual(a["event"]["price_usd"],60012.)
        self.assertGreater(s["btc_quantity"],0)
        self.assertGreaterEqual(s["cash_usd"],0)
        self.assertLessEqual(a["allocation"]["actual_btc_pct"],25.0001)
        self.assertLess(a["virtual_account"]["liquidation_equity_usd"],100000)

    def test_no_buy_on_tuesday_even_with_long_signal(self):
        n=when(dt.date(2026,11,24))
        s,a=p.advance(p.initial_state("sha"),signal(n),quote(n),n,"sha")
        self.assertEqual(a["event"]["type"],"NO_ACTION")
        self.assertEqual(s["btc_quantity"],0)

    def test_risk_reduction_executes_even_non_monday(self):
        n=when(dt.date(2026,11,23))
        s,_=p.advance(p.initial_state("sha"),signal(n),quote(n),n,"sha")
        tue=n+dt.timedelta(days=1)
        state,a=p.advance(s,signal(tue,weight=.125),quote(tue,bid=57000,ask=57010),tue,"sha")
        self.assertEqual(a["event"]["type"],"SIMULATED_SELL")
        self.assertEqual(a["event"]["price_usd"],57000)
        self.assertGreater(state["cash_usd"],s["cash_usd"])

    def test_above_stop_risk_not_labeled_hard_stop(self):
        n=when(dt.date(2026,11,23))
        s,a=p.advance(p.initial_state("sha"),signal(n),quote(n),n,"sha")
        self.assertTrue(any("NOT covered by a stop" in x for x in a["safeguards"]))
        self.assertTrue(-100<a["virtual_account"]["return_since_start_pct"]<=0)

    def test_no_duplicate_or_tampered_strategy_version(self):
        n=when(dt.date(2026,11,23))
        s,_=p.advance(p.initial_state("sha"),signal(n),quote(n),n,"sha")
        with self.assertRaises(ValueError):
            p.advance(s,signal(n),quote(n),n,"sha")
        with self.assertRaises(ValueError):
            p.advance(p.initial_state("sha"),signal(n),quote(n),n,"changed")

    def test_stale_quote_and_wrong_exchange_fail(self):
        n=when(dt.date(2026,11,23))
        q=quote(n)
        q["exchange_timestamp_utc"]=(n-dt.timedelta(minutes=5)).isoformat()
        with self.assertRaises(ValueError):
            p.advance(p.initial_state("sha"),signal(n),q,n,"sha")
        q=quote(n)
        q["exchange"]="OtherExchange"
        with self.assertRaises(ValueError):
            p.advance(p.initial_state("sha"),signal(n),q,n,"sha")

    def test_future_signal_and_maximum_risk_weight_guard(self):
        n=when(dt.date(2026,11,23))
        bad=signal(n,weight=.5)
        with self.assertRaises(ValueError):
            p.advance(p.initial_state("sha"),bad,quote(n),n,"sha")
        bad=signal(n)
        bad["last_actionable_signal_day"]=(n.date()-dt.timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):
            p.advance(p.initial_state("sha"),bad,quote(n),n,"sha")

    def test_raw_daily_csv_pipeline_uses_exact_day_before_previous(self):
        start=dt.date(2024,1,1)
        rows=[]
        for i in range(620):
            day=start+dt.timedelta(days=i)
            price=20000+i*10
            rows.append(dict(date_utc=str(day),open=price,high=price+60,
                low=price-60,close=price+15,volume=250+i%8))
        buf=io.StringIO()
        writer=csv.DictWriter(buf,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        current=dt.date.fromisoformat(rows[-1]["date_utc"])+dt.timedelta(days=1)
        snap=p.collect_snapshot(buf.getvalue().encode(),current)
        self.assertEqual(snap["last_actionable_signal_day"],
                         str(current-dt.timedelta(days=2)))
        self.assertEqual(snap["most_recent_complete_utc_day"],
                         str(current-dt.timedelta(days=1)))
        self.assertIn(snap["desired_btc_weight"],(0.,.125,.25))


if __name__=="__main__":
    unittest.main()
