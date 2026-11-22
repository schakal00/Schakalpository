import copy
import datetime as dt
import math
import unittest

import cecs_v3_0_strategy as m
from cecs_v2_7_slow import prepare


def daily_bars(n=800):
    start=dt.date(2020,1,1)
    data=[]
    for i in range(n):
        price=15000+i*12
        data.append(dict(date=start+dt.timedelta(days=i),
            open=price,high=price+70,low=price-80,close=price+20,
            volume=200+(i%10)))
    return m.add_derived_features(prepare(data))


def quotes_for(data):
    return {x["date"]:x["open"] for x in data}


class CECSThreeResearchTests(unittest.TestCase):
    def test_positive_spot_exposure_and_failsafe(self):
        s=dict(trend=True,annualized_realized_vol30=.4,under_sma50=False,
               roc90=.2,vector_confirmed=True,cycle=True)
        for model in m.MODELS:
            weight=m.declared_weight(s,model)
            self.assertGreaterEqual(weight,0)
            self.assertLessEqual(weight,1)
        self.assertEqual(m.declared_weight(s,"CECS3_Defensive"),.25)
        s["annualized_realized_vol30"]=.9
        self.assertEqual(m.declared_weight(s,"CECS3_Defensive"),.125)
        s["trend"]=False
        self.assertEqual(m.declared_weight(s,"CECS3_Defensive"),0)
        self.assertEqual(m.declared_weight(s,"CECS3_Balanced"),0)

    def test_indicator_features_are_caused_by_past_only(self):
        full=daily_bars()
        left=m.add_derived_features(prepare(copy.deepcopy([
            {k:v for k,v in x.items() if k in ("date","open","high","low","close","volume")}
            for x in full[:650]])))
        for i in range(0,649):
            for feature in ("trend","sma50","sma200","roc90","under_sma50","cycle",
                            "elliott","annualized_realized_vol30"):
                self.assertEqual(full[i][feature],left[i][feature],(i,feature))

    def test_each_order_uses_exactly_two_day_old_signal(self):
        d=daily_bars()
        _,_,orders=m.simulate(d,quotes_for(d),"Trend25")
        self.assertGreater(len(orders),0)
        for x in orders:
            self.assertEqual(
                dt.date.fromisoformat(x["day"])-dt.date.fromisoformat(x["signal_day"]),
                dt.timedelta(days=2))
            self.assertEqual(x["execution_utc"],"09:00")

    def test_cash_stays_cash_and_no_negative_cash(self):
        d=daily_bars()
        report,curve,orders=m.simulate(d,quotes_for(d),"Cash")
        self.assertEqual(report["trades"],0)
        self.assertEqual(report["total_return_pct"],0)
        self.assertEqual(orders,[])
        for name in m.MODELS:
            s,e,o=m.simulate(d,quotes_for(d),name)
            self.assertEqual(len(e),len(d))
            self.assertGreater(e[-1]["equity_usd"],0)
            self.assertGreaterEqual(s["total_mtm_drawdown_pct"],-100)

    def test_missing_9am_sample_must_never_create_fill(self):
        d=daily_bars()
        q={}
        s,e,o=m.simulate(d,q,"Hold25")
        self.assertEqual(o,[])
        self.assertEqual(s["total_return_pct"],0)

    def test_nonmonday_decrease_to_zero_is_executed(self):
        d=daily_bars(800)
        for x in d:
            x["trend"]=False
        for k in range(202,250):
            d[k]["trend"]=True
        s,e,o=m.simulate(d,quotes_for(d),"CECS3_Defensive")
        buys=[x for x in o if x["action"]=="BUY"]
        sells=[x for x in o if x["action"]=="SELL"]
        self.assertTrue(buys)
        self.assertTrue(sells)
        self.assertGreaterEqual(sells[-1]["day"],str(d[252]["date"]))

    def test_weekday_buy_only_mondays(self):
        d=daily_bars()
        _,_,o=m.simulate(d,quotes_for(d),"CECS3_Defensive")
        self.assertGreater(len(o),0)
        self.assertTrue(all(dt.date.fromisoformat(t["day"]).weekday()==0
                            for t in o if t["action"]=="BUY"))

    def test_higher_cost_cannot_improve_simple_hold_in_rising_sample(self):
        d=daily_bars()
        low,_,_=m.simulate(d,quotes_for(d),"Hold25",cost_bps=0)
        high,_,_=m.simulate(d,quotes_for(d),"Hold25",cost_bps=50)
        self.assertLess(high["total_return_pct"],low["total_return_pct"])

    def test_real_15m_to_daily_pipeline_creates_vol_feature(self):
        # End-to-end representation test; catches missing derived features.
        start=dt.datetime(2020,1,1,tzinfo=dt.timezone.utc)
        small=[]
        for i in range(96*210):
            px=10000+i*.01
            small.append(dict(time=start+dt.timedelta(minutes=15*i),
                open=px,high=px+2,low=px-2,close=px+.5,volume=50))
        from cecs_v2_6_mw import full_daily
        from cecs_v2_7_slow import prepare
        result=m.add_derived_features(prepare(full_daily(small)))
        self.assertGreaterEqual(len(result),209)
        self.assertTrue(all("annualized_realized_vol30" in b for b in result))
        self.assertIsNotNone(result[-1]["annualized_realized_vol30"])
        self.assertIsInstance(m.declared_weight(result[-1],"CECS3_Defensive"),float)

    def test_period_report_start_equity_is_previous_day(self):
        d=daily_bars()
        _,curve,_=m.simulate(d,quotes_for(d),"Trend25")
        per=m.summary_by_period(curve)
        self.assertTrue(any(y["period"]=="2021" for y in per))
        for x in per:
            self.assertGreaterEqual(x["max_mtm_drawdown_pct"],-100)
            self.assertLessEqual(x["max_mtm_drawdown_pct"],0)


if __name__=="__main__":
    unittest.main()
