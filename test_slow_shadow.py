import datetime as dt
import unittest

import slow_shadow as s

UTC=dt.timezone.utc


def at(day):
    return dt.datetime.combine(day,dt.time(9,18),tzinfo=UTC)


def snapshot(now,weight=.25,trend=.25):
    return dict(observation_day=now.date().isoformat(),
        source_last_completed_day=(now.date()-dt.timedelta(days=1)).isoformat(),
        source_signal_day=(now.date()-dt.timedelta(days=2)).isoformat(),
        source_sha256="test",
        weights={"BuyHold25":weight,"Trend25":trend,"TrendVol30Vector":.5})


def quote(now,bid=60000,ask=60010):
    return dict(exchange="Bitstamp",symbol="BTC/USD",
        exchange_timestamp_utc=now.isoformat(),
        captured_at_utc=now.isoformat(),
        bid_usd=bid,ask_usd=ask,quote_sha256="fake")


class ShadowLedgerTests(unittest.TestCase):
    def test_initial_sunday_no_buys_and_no_lookahead(self):
        now=at(dt.date(2026,11,22))
        state,log=s.advance(s.new_state("abc"),snapshot(now),quote(now),now,"abc")
        self.assertEqual(len(state["processed_dates"]),1)
        for x in log["portfolios"].values():
            self.assertEqual(x["event"]["side"],"NO_ACTION")
            self.assertEqual(x["paper_liquidation_equity_usd"],100000)

    def test_monday_buys_next_published_quote(self):
        initial=s.new_state("abc")
        sunday=at(dt.date(2026,11,22))
        initial,_=s.advance(initial,snapshot(sunday),quote(sunday),sunday,"abc")
        monday=at(dt.date(2026,11,23))
        state,log=s.advance(initial,snapshot(monday),quote(monday,bid=62000,ask=62012),monday,"abc")
        for name in s.MODELS:
            row=log["portfolios"][name]
            self.assertEqual(row["event"]["side"],"VIRTUAL_BUY")
            self.assertEqual(row["event"]["ask_usd"],62012)
            self.assertGreater(row["paper_qty_btc"],0)
            self.assertGreaterEqual(state["models"][name]["cash_usd"],-1e-8)

    def test_trend_exit_on_non_monday(self):
        mon=at(dt.date(2026,11,23))
        st,_=s.advance(s.new_state("abc"),snapshot(mon),quote(mon),mon,"abc")
        tue=mon+dt.timedelta(days=1)
        sp=snapshot(tue,weight=.25,trend=0)
        nxt,log=s.advance(st,sp,quote(tue,bid=58000,ask=58005),tue,"abc")
        self.assertEqual(log["portfolios"]["Trend25"]["event"]["side"],"VIRTUAL_SELL")
        self.assertEqual(log["portfolios"]["BuyHold25"]["event"]["side"],"NO_ACTION")
        self.assertEqual(nxt["models"]["Trend25"]["qty_btc"],0)

    def test_sha_change_fails_closed(self):
        mon=at(dt.date(2026,11,23))
        with self.assertRaises(ValueError):
            s.advance(s.new_state("fixed"),snapshot(mon),quote(mon),mon,"changed")

    def test_reject_duplicate_date_and_backdated_signal(self):
        now=at(dt.date(2026,11,23))
        first,_=s.advance(s.new_state("a"),snapshot(now),quote(now),now,"a")
        with self.assertRaises(ValueError):
            s.advance(first,snapshot(now),quote(now),now,"a")
        fake=snapshot(now)
        fake["source_signal_day"]=(now.date()-dt.timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):
            s.advance(s.new_state("a"),fake,quote(now),now,"a")

    def test_stale_exchange_quote_rejected(self):
        now=at(dt.date(2026,11,23))
        q=quote(now)
        q["exchange_timestamp_utc"]=(now-dt.timedelta(minutes=10)).isoformat()
        with self.assertRaises(ValueError):
            s.advance(s.new_state("a"),snapshot(now),q,now,"a")

    def test_rebalanced_allocation_not_levered(self):
        now=at(dt.date(2026,11,23))
        x=s.snapshot if False else snapshot(now,weight=1,trend=1)
        x["weights"]["TrendVol30Vector"]=1
        state,audit=s.advance(s.new_state("a"),x,quote(now),now,"a")
        for name in s.MODELS:
            self.assertLessEqual(audit["portfolios"][name]["observed_weight_pct"],100.001)
            self.assertGreaterEqual(state["models"][name]["cash_usd"],-1e-7)


if __name__=="__main__":
    unittest.main()
