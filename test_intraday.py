import csv
import datetime as dt
import gzip
import io
import unittest

import cecs_v2_2_intraday as m

UTC=dt.timezone.utc


def bar(time, price=100, volume=10):
    return dict(time=time, open=price, high=price+2, low=price-2,
                close=price+1, volume=volume, atr=1.0, vector="ordinary")


class IntradayResearchTests(unittest.TestCase):
    def test_minute_aggregation_and_incomplete_windows(self):
        out=io.StringIO()
        w=csv.writer(out)
        w.writerow(["datetime_utc","open","high","low","close","volume"])
        start=dt.datetime(2024,1,1,tzinfo=UTC)
        for n in range(45):
            if n==32:
                continue  # missing minute: third 15m candle must be discarded
            t=start+dt.timedelta(minutes=n)
            w.writerow([t.isoformat(),100,102,99,101,2])
        compressed=gzip.compress(out.getvalue().encode())
        bars,stat=m.aggregate_15m(compressed,2024,minimum_coverage=0.0)
        self.assertEqual(len(bars),2)
        self.assertEqual([z["volume"] for z in bars],[30,30])
        self.assertEqual(stat["incomplete_15m"],1)

    def test_hourly_context_only_after_completed_hour(self):
        start=dt.datetime(2024,1,1,tzinfo=UTC)
        bars=[bar(start+dt.timedelta(minutes=15*n)) for n in range(5)]
        hours=m.completed_hourly(bars)
        self.assertEqual(len(hours),1)
        self.assertEqual(hours[0]["end"],start+dt.timedelta(hours=1))
        self.assertEqual(hours[0]["close"],bars[3]["close"])

    def test_vector_calculation_does_not_use_future(self):
        start=dt.datetime(2024,1,1,tzinfo=UTC)
        bars=[bar(start+dt.timedelta(minutes=15*i),100+i*0.1) for i in range(35)]
        m.enrich_vector(bars)
        initial=[z["vector"] for z in bars[:-1]]
        bars[-1]["volume"]=999999
        m.enrich_vector(bars)
        self.assertEqual(initial,[z["vector"] for z in bars[:-1]])
        self.assertIn(bars[-1]["vector"],("green","red"))

    def test_mid_reclaim_includes_only_past_bearish_vector(self):
        start=dt.datetime(2025,1,1,tzinfo=UTC)
        b=[bar(start+dt.timedelta(minutes=15*i)) for i in range(12)]
        b[1]["vector"]="red"
        b[1]["high"]=110
        b[1]["low"]=90
        b[9]["close"]=98
        b[10]["close"]=102
        valid,why=m.vector_condition(b,10)
        self.assertEqual((valid,why),(True,"bear_vector_mid_reclaim"))
        b[1]["vector"]="ordinary"
        valid,_=m.vector_condition(b,10)
        self.assertFalse(valid)

    def test_same_bar_hits_stop_and_target_uses_stop(self):
        start=dt.datetime(2025,1,1,tzinfo=UTC)
        b=[bar(start+dt.timedelta(minutes=15*i)) for i in range(5)]
        b[1]["open"]=100
        b[1]["high"]=120
        b[1]["low"]=80
        signals=[dict(model="Breakout",index=1,signal_at=start+dt.timedelta(minutes=15),
                      vector_reason="none",cycle=0,elliott=0)]
        out,rows=m.simulate(b,signals,"Breakout",2025)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["outcome"],"stop")
        self.assertLess(rows[0]["realized_r"],0)

    def test_no_trade_is_not_zero_return(self):
        b=[bar(dt.datetime(2025,1,1,tzinfo=UTC)+dt.timedelta(minutes=15*i)) for i in range(2)]
        summary,_=m.simulate(b,[],"AllConfluence",2025)
        self.assertIsNone(summary["return_pct"])
        self.assertIsNone(summary["win_pct"])


if __name__=="__main__":
    unittest.main()
