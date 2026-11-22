import datetime as dt
import unittest

import cecs_uncertainty as u


class UncertaintyTests(unittest.TestCase):
    def data(self,n=900):
        first=dt.date(2022,1,1)
        data=[]
        for i in range(n):
            date=first+dt.timedelta(days=i)
            price=100000*(1+0.0003*i)
            data.append(dict(model="TrendVol30Vector",date=date.isoformat(),
                             equity_usd=str(price*(1+0.00002*i))))
            data.append(dict(model="TrendVol30",date=date.isoformat(),
                             equity_usd=str(price)))
        return data

    def test_fixed_seed_reproducibility(self):
        a=u.estimate(self.data(),"TrendVol30Vector","TrendVol30",n=100,seed=12)
        b=u.estimate(self.data(),"TrendVol30Vector","TrendVol30",n=100,seed=12)
        self.assertEqual(a,b)
        self.assertGreaterEqual(a["months"],24)
        self.assertFalse(a["selection_bias_corrected"])

    def test_missing_paired_dates_fails(self):
        d=self.data()
        d.pop()
        with self.assertRaises(ValueError):
            u.estimate(d,"TrendVol30Vector","TrendVol30",n=20)

    def test_only_descriptive_confidence(self):
        row=u.estimate(self.data(),"TrendVol30Vector","TrendVol30",n=100,seed=24)
        self.assertLessEqual(row["bootstrap_025_pct"],row["bootstrap_975_pct"])
        self.assertFalse(row["is_formal_statistical_significance_test"])


if __name__=="__main__":
    unittest.main()
