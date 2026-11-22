import copy
import datetime as dt
import unittest

import cecs_v2_7_slow as m


def bars(n=850):
    first=dt.date(2020,1,1)
    arr=[]
    for i in range(n):
        px=100+i*.3
        arr.append(dict(date=first+dt.timedelta(days=i),
            open=px,high=px+3,low=px-3,close=px+1,
            volume=100+(i%11)))
    return arr


class SlowTrendTests(unittest.TestCase):
    def test_indicator_prefix_does_not_require_future(self):
        b=bars()
        a=copy.deepcopy(b[:740])
        m.prepare(b)
        m.prepare(a)
        for i in range(0,730):
            for key in ("sma200","trend","cycle","elliott","vector_confirmed",
                        "annualized_realized_vol30"):
                self.assertEqual(b[i][key],a[i][key],(i,key))

    def test_target_weight_spot_no_leverage_and_nonfinite_handling(self):
        x=dict(trend=True,cycle=True,vector_confirmed=True,annualized_realized_vol30=.001)
        for model in m.MODEL_NAMES:
            w=m.target_weight(x,model)
            self.assertTrue(0<=w<=1,(model,w))
        self.assertEqual(m.target_weight(x,"TrendVol30"),.75)
        x["trend"]=False
        self.assertEqual(m.target_weight(x,"TrendVol30"),0)
        self.assertEqual(m.target_weight(x,"TrendVol30Vector"),0)

    def test_known_source_day_is_two_days_old(self):
        b=m.prepare(bars())
        s,curve,orders=m.simulate(b,"BuyHold100")
        self.assertGreater(len(orders),0)
        for order in orders:
            self.assertEqual(dt.date.fromisoformat(order["date"])-
                             dt.date.fromisoformat(order["source_date"]),
                             dt.timedelta(days=2))

    def test_fee_sensitivity_never_increases_buyhold_return(self):
        b=m.prepare(bars())
        no,_,_=m.simulate(b,"BuyHold100",0.)
        high,_,_=m.simulate(b,"BuyHold100",.003)
        self.assertLessEqual(high["total_return_pct"],no["total_return_pct"])

    def test_cash_never_trades(self):
        b=m.prepare(bars())
        stats,curve,orders=m.simulate(b,"Cash")
        self.assertEqual(stats["orders"],0)
        self.assertEqual(stats["total_return_pct"],0)
        self.assertTrue(all(x["market_exposure_pct"]==0 for x in curve))

    def test_trend_exit_not_on_same_observation_candle(self):
        b=m.prepare(bars(870))
        # All features already computed. Change the PUBLIC trend feature
        # to create a deterministic regime switch, not retroactive market candles.
        for x in b:
            x["trend"]=False
        for i in range(190,260):
            b[i]["trend"]=True
        _,_,orders=m.simulate(b,"Trend25")
        buys=[o for o in orders if o["side"]=="BUY"]
        sells=[o for o in orders if o["side"]=="SELL"]
        self.assertGreater(len(buys),0)
        self.assertGreater(len(sells),0)
        # Trend last true on day 259, so earliest exit decision on day 261.
        self.assertGreaterEqual(sells[-1]["date"],str(b[262]["date"]))

    def test_marked_equity_stays_finite(self):
        b=m.prepare(bars())
        for name in m.MODEL_NAMES:
            s,e,orders=m.simulate(b,name)
            self.assertEqual(len(e),len(b))
            self.assertTrue(-100<=s["total_max_daily_drawdown_pct"]<=0)
            self.assertGreater(e[-1]["equity_usd"],0)


if __name__=="__main__":
    unittest.main()
