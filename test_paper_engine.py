import copy
import datetime as dt
import json
import unittest

import paper_engine as p


def sample_at(day=dt.date(2026,11,22)):
    return dt.datetime.combine(day,dt.time(9,2),tzinfo=dt.timezone.utc)


def quote(now,bid=60000.,ask=60010.):
    return {"exchange":"Bitstamp","symbol":"BTC/USD",
        "exchange_timestamp_utc":now.isoformat(),
        "captured_at_utc":now.isoformat(),
        "bid_usd":bid,"ask_usd":ask,"source":p.TICKER_URL,
        "quote_sha256":"test"}


def observation(now,gate=False,trend=True,high=61500,atr=2000.):
    day=(now.date()-dt.timedelta(days=1)).isoformat()
    return {
        "recorded_utc_date":now.date().isoformat(),
        "source_last_completed_day":day,
        "source_high":high,
        "candidate_only":True,
        "model":p.MODEL,
        "trend_gate":trend,
        "candidate_entry_gate":gate,
        "atr14":atr,
        "source_sha256":"s",
        "strategy_source_sha256":"c",
    }


class PaperEngineTests(unittest.TestCase):
    def test_initial_no_action_no_fake_pnl(self):
        now=sample_at()
        state,audit=p.process(p.initial_state(),observation(now),quote(now),now)
        self.assertEqual(audit["events"][0]["type"],"no_action")
        self.assertEqual(state["qty_btc"],0)
        self.assertEqual(audit["paper_equity_usd"],100000)

    def test_intent_only_and_next_day_ask_fill(self):
        now=sample_at()
        s,a=p.process(p.initial_state(),observation(now,gate=True),quote(now),now)
        self.assertEqual(a["events"][0]["type"],"virtual_buy_intent_queued")
        self.assertIsNotNone(s["pending"])
        self.assertEqual(s["qty_btc"],0)
        next_day=now+dt.timedelta(days=1)
        s,a=p.process(s,observation(next_day,gate=False,trend=True),
                      quote(next_day,bid=64000,ask=64020),next_day)
        self.assertEqual(a["events"][0]["type"],"virtual_buy")
        self.assertEqual(s["entry_usd"],64020)
        self.assertGreater(s["qty_btc"],0)
        self.assertLessEqual(a["events"][0]["initial_risk_frac"],.005000001)
        self.assertLess(s["cash_usd"],100000)

    def test_price_below_stop_exit_at_sampled_bid(self):
        now=sample_at()
        s,_=p.process(p.initial_state(),observation(now,gate=True),quote(now),now)
        day2=now+dt.timedelta(days=1)
        s,_=p.process(s,observation(day2,trend=True),quote(day2,60000,60010),day2)
        stop=s["stop_usd"]
        day3=day2+dt.timedelta(days=1)
        exit_bid=stop-1000
        s,a=p.process(s,observation(day3,trend=True),
                      quote(day3,bid=exit_bid,ask=exit_bid+10),day3)
        self.assertEqual(a["events"][0]["type"],"virtual_sell")
        self.assertEqual(a["events"][0]["reason"],"observed_bid_below_stop")
        self.assertEqual(s["qty_btc"],0)
        self.assertLess(s["realized_pnl_usd"],0)

    def test_trend_exit_without_overnight_retroactive_fill(self):
        now=sample_at()
        s,_=p.process(p.initial_state(),observation(now,gate=True),quote(now),now)
        next_day=now+dt.timedelta(days=1)
        s,_=p.process(s,observation(next_day,trend=True),quote(next_day),next_day)
        day3=next_day+dt.timedelta(days=1)
        s,a=p.process(s,observation(day3,trend=False),quote(day3,bid=58000,ask=58010),day3)
        self.assertEqual(a["events"][0]["type"],"virtual_sell")
        self.assertEqual(a["events"][0]["reason"],"published_trend_gate_off")
        self.assertEqual(a["events"][0]["bid_usd"],58000)

    def test_stale_source_cancels_pending(self):
        now=sample_at()
        s,_=p.process(p.initial_state(),observation(now,gate=True),quote(now),now)
        next_day=now+dt.timedelta(days=1)
        o=observation(next_day,gate=True)
        o["source_last_completed_day"]=(next_day.date()-dt.timedelta(days=2)).isoformat()
        s,a=p.process(s,o,quote(next_day),next_day)
        self.assertEqual(a["events"][0]["type"],"intent_cancelled")
        self.assertEqual(a["events"][0]["reason"],"daily_source_not_fresh")
        self.assertIsNone(s["pending"])

    def test_reject_quote_and_duplicate_day(self):
        now=sample_at()
        s,_=p.process(p.initial_state(),observation(now),quote(now),now)
        with self.assertRaises(ValueError):
            p.process(s,observation(now),quote(now),now)
        q=quote(now)
        q["exchange_timestamp_utc"]=(now-dt.timedelta(minutes=5)).isoformat()
        with self.assertRaises(ValueError):
            p.process(p.initial_state(),observation(now),q,now)

    def test_fetch_quote_requires_fresh_bid_ask(self):
        now=sample_at()
        raw=json.dumps({"bid":"61000.00","ask":"61005.00",
                        "timestamp":str(int(now.timestamp()))}).encode()
        q=p.fetch_quote(now=now,raw=raw)
        self.assertEqual(q["bid_usd"],61000)
        self.assertEqual(q["ask_usd"],61005)
        bad=json.dumps({"bid":"62000","ask":"61000",
                        "timestamp":str(int(now.timestamp()))}).encode()
        with self.assertRaises(ValueError):
            p.fetch_quote(now=now,raw=bad)

    def test_trailing_stop_never_uses_future_or_entry_day_high(self):
        now=sample_at()
        s,_=p.process(p.initial_state(),observation(now,gate=True),quote(now),now)
        tomorrow=now+dt.timedelta(days=1)
        s,_=p.process(s,observation(tomorrow,gate=False,trend=True,high=999999),
                      quote(tomorrow),tomorrow)
        self.assertIsNone(s["highest_completed_daily_high"])
        following=tomorrow+dt.timedelta(days=1)
        s,a=p.process(s,observation(following,trend=True,high=61000,atr=100),
                      quote(following,bid=60010,ask=60020),following)
        self.assertEqual(s["highest_completed_daily_high"],61000)
        self.assertTrue(any(e["type"]=="virtual_stop_update" for e in a["events"]))


if __name__=="__main__":
    unittest.main()
