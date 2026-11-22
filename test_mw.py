import copy
import datetime as dt
import unittest

import cecs_v2_6_mw as m

UTC=dt.timezone.utc


def minutes(n=220, price=100):
    start=dt.datetime(2023,1,1,tzinfo=UTC)
    arr=[]
    for k in range(n):
        arr.append(dict(time=start+dt.timedelta(minutes=15*k),
                        open=price,high=price+1,low=price-1,close=price,
                        volume=50,atr=2.,vector="ordinary"))
    return arr


class MWWalkForwardTests(unittest.TestCase):
    def make_w(self):
        b=minutes(220)
        b[50]["low"]=93.
        for i in range(51,75):
            b[i]["high"]=106.
        b[75]["low"]=93.2
        b[80]["close"]=107.
        b[80]["high"]=108.
        b[75]["vector"]="red"
        return b

    def test_w_neckline_only_confirmed_after_second_pivot(self):
        b=self.make_w()
        events=m.pivot_motifs(b)
        matches=[x for x in events if x["kind"]=="W" and x["second"]==75]
        self.assertTrue(matches,events)
        self.assertEqual(matches[0]["time"],80)
        self.assertGreaterEqual(matches[0]["time"],75+m.CONFIRM_RIGHT)
        self.assertTrue(matches[0]["vector_ok"])

    def test_w_signal_prefix_invariant(self):
        b=self.make_w()
        shortened=copy.deepcopy(b[:190])
        original=m.pivot_motifs(b)
        prefix=m.pivot_motifs(shortened)
        self.assertEqual([x for x in original if x["time"]<170],
                         [x for x in prefix if x["time"]<170])

    def test_m_double_top_requires_neckline_breakdown(self):
        b=minutes(220)
        b[50]["high"]=110
        for i in range(51,75):
            b[i]["low"]=95
        b[75]["high"]=109.8
        b[80]["close"]=94
        b[80]["low"]=93
        events=m.pivot_motifs(b)
        matches=[x for x in events if x["kind"]=="M" and x["second"]==75]
        self.assertTrue(matches,events)
        self.assertEqual(matches[0]["time"],80)

    def test_next_bar_entry_and_m_exit(self):
        b=minutes(15)
        signal=dict(model="W1hMExit",index=1,signal_time=b[1]["time"].isoformat(),
                    daily_cycle=False,daily_elliott=False,vector=False)
        b[1]["open"]=100
        b[3]["open"]=102
        stats,_,trades=m.simulate(b,[signal],{3},"W1hMExit")
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0]["reason"],"confirmed_M_breakdown")
        self.assertEqual(trades[0]["exit_usd"],102.)
        self.assertEqual(trades[0]["entry_usd"],100.)

    def test_stop_first_same_entry_bar(self):
        b=minutes(12)
        signal=dict(model="WOnly",index=1,signal_time=b[1]["time"].isoformat(),
                    daily_cycle=False,daily_elliott=False,vector=False)
        b[1]["low"]=80
        b[1]["high"]=125
        stats,_,trades=m.simulate(b,[signal],set(),"WOnly")
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0]["reason"],"entry_bar_stop")
        self.assertLess(trades[0]["pnl_usd"],0)

    def test_completed_daily_is_next_midnight_only(self):
        b=minutes(96*3+7)
        d=m.full_daily(b)
        self.assertEqual(len(d),3)
        self.assertEqual(d[0]["available"],
            dt.datetime(2023,1,2,tzinfo=UTC))
        self.assertTrue(all(x["available"].date()>x["date"] for x in d))

    def test_spot_risk_and_costs(self):
        b=minutes(30)
        signal=dict(model="WOnly",index=1,signal_time=b[1]["time"].isoformat(),
                    daily_cycle=False,daily_elliott=False,vector=False)
        s,y,t=m.simulate(b,[signal],set(),"WOnly",cost=.0015)
        self.assertEqual(s["trades"],1)
        self.assertLessEqual(s["max_mark_to_market_drawdown_pct"],0)
        self.assertAlmostEqual(t[0]["pnl_usd"],-30,delta=150)
        self.assertEqual(s["cost_bps_each_leg"],15)

    def test_no_silent_trade_when_no_signal(self):
        b=minutes(12)
        s,periods,t=m.simulate(b,[],set(),"WOnly")
        self.assertEqual(len(t),0)
        self.assertIsNone(s["win_pct"])
        self.assertEqual(s["return_pct"],0)


if __name__=="__main__":
    unittest.main()
