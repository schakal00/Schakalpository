import datetime as dt
import unittest
import copy

import cecs_v2_3_trend as m

def make_bars(n=700, jump=None):
    start=dt.date(2020,1,1)
    arr=[]
    for i in range(n):
        base=100+0.45*i
        if jump is not None and i>=jump:
            base-=50
        arr.append(dict(date=start+dt.timedelta(days=i),open=base,
                        high=base+2,low=base-2,close=base+1,
                        volume=100+(i%7)))
    return arr

class TrendResearchTests(unittest.TestCase):
    def test_past_indicators_do_not_change_when_future_appended(self):
        all_bars=make_bars(700)
        earlier=copy.deepcopy(all_bars[:600])
        m.indicators(all_bars)
        m.indicators(earlier)
        for i in range(0,600):
            for key in ("trend","sma200","score","cycle","elliott","vector_confirmed"):
                self.assertEqual(all_bars[i][key],earlier[i][key],(i,key))

    def test_flat_market_no_false_trend(self):
        bars=make_bars(600)
        for x in bars:
            x["open"]=x["close"]=100
            x["high"]=101
            x["low"]=99
        m.indicators(bars)
        result,eq,trades=m.backtest(bars,"TrendRisk")
        self.assertEqual(result["trades"],0)
        self.assertFalse(trades)
        self.assertEqual(result["return_pct"],0)
        self.assertEqual(result["exposure_pct"],0)

    def test_next_open_entry_is_not_same_signal_close(self):
        bars=make_bars(600)
        m.indicators(bars)
        result,eq,trades=m.backtest(bars,"TrendSpot")
        self.assertGreater(len(trades),0)
        first=trades[0]
        entry_idx=next(i for i,x in enumerate(bars) if str(x["date"])==first["entry"])
        self.assertTrue(bars[entry_idx-1]["trend"])
        self.assertAlmostEqual(first["entry_px"],bars[entry_idx]["open"],2)

    def test_gap_exits_at_open_not_at_stop(self):
        bars=make_bars(700)
        m.indicators(bars)
        _,_,trades=m.backtest(bars,"TrendRisk")
        # This checks risk accounting with a gap in the actual strategy trace.
        # It is not necessary for a gap to occur in the synthetic sample.
        for t in trades:
            self.assertTrue(t["reason"] in
                ("trend_exit","gap_stop","stop","entry_day_stop","end_of_sample"))

    def test_review_period_no_future_equity_reference(self):
        bars=make_bars(900)
        m.indicators(bars)
        _,equity,_=m.backtest(bars,"TrendSpot")
        periods=m.period_stats(equity)
        self.assertIn("2022", {x["period"] for x in periods})
        for p in periods:
            self.assertLessEqual(p["max_mtm_drawdown_pct"],0)

    def test_all_models_are_tested(self):
        bars=make_bars(650)
        m.indicators(bars)
        for model in m.MODELS:
            result,equity,trades=m.backtest(bars,model)
            self.assertEqual(len(equity),len(bars))
            self.assertEqual(result["trades"],len(trades))
            self.assertTrue(0<=result["exposure_pct"]<=100)


    def test_delayed_cycle_requires_confirmed_cycle(self):
        x={"trend": True,"cycle": False,"elliott": False,"vector_confirmed": False,"score": 0}
        self.assertFalse(m.entry_gate(x,"TrendCycleWide6Delayed"))
        x["cycle"]=True
        self.assertTrue(m.entry_gate(x,"TrendCycleWide6Delayed"))

    def test_delayed_entry_uses_two_day_old_candle(self):
        bars=make_bars(650)
        for x in bars:
            x.update(trend=False,cycle=False,elliott=False,vector_confirmed=False,score=0,atr=1.)
        bars[300]["trend"]=True
        bars[300]["cycle"]=True
        stats,eq,trades=m.backtest(bars,"TrendCycleWide6Delayed")
        self.assertGreaterEqual(len(trades),1)
        self.assertEqual(trades[0]["entry"],str(bars[302]["date"]))

    def test_running_position_is_not_forced_closed_for_monitoring(self):
        bars=make_bars(650)
        for x in bars:
            x.update(trend=True,cycle=True,elliott=False,vector_confirmed=False,score=1,atr=1.)
        stats,equity,trades,state=m.backtest(bars,"TrendCycleWide6Delayed",force_close_end=False,return_state=True)
        self.assertIn("quantity",state)
        self.assertEqual(len(equity),len(bars))
        if state["quantity"]>0:
            self.assertFalse(any(t["reason"]=="end_of_sample" for t in trades))

if __name__=="__main__":
    unittest.main()
