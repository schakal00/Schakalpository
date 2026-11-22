import datetime as dt
import unittest

import cecs3_data_audit as m


class CrossSourceOHLCVTests(unittest.TestCase):
    def sample(self):
        a=[];b=[]
        start=dt.date(2024,1,1)
        for i in range(12):
            day=start+dt.timedelta(days=i)
            x=dict(date=day,open=100+i,high=110+i,low=90+i,close=102+i)
            a.append(x)
            b.append(dict(x))
        return a,b

    def test_identical_ohlc_matches_zero_error(self):
        a,b=self.sample()
        summary,worst=m.compare(a,b)
        self.assertEqual(len(summary),4)
        self.assertTrue(all(x["max_abs_pct"]==0 for x in summary))

    def test_alerts_to_single_bad_close(self):
        a,b=self.sample()
        b[4]["close"]*=1.025
        summary,worst=m.compare(a,b)
        close=next(x for x in summary if x["field"]=="close")
        self.assertEqual(close["greater_1pct"],1)
        self.assertEqual(worst[0]["date"],str(b[4]["date"]))
        self.assertEqual(worst[0]["field"],"close")

    def test_nonmatching_days_fail_closed(self):
        a,b=self.sample()
        for row in b:
            row["date"]+=dt.timedelta(days=365)
        with self.assertRaises(ValueError):
            m.compare(a,b)

    def test_negative_prices_rejected(self):
        a,b=self.sample()
        b[0]["open"]=-5
        with self.assertRaises(ValueError):
            m.compare(a,b)


if __name__=="__main__":
    unittest.main()
