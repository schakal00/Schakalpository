import copy
import datetime as dt
import unittest

import daily_watch as w


class ForwardJournalTests(unittest.TestCase):
    def bars(self,n=620):
        start=dt.date(2024,1,1)
        arr=[]
        for i in range(n):
            price=30000+12*i
            arr.append(dict(date=start+dt.timedelta(days=i),open=price,
                            high=price+80,low=price-70,close=price+35,
                            volume=50+(i%20)))
        return arr

    def test_snapshot_uses_only_complete_bars(self):
        a=self.bars()
        # Day after last complete bar, any same-day unfinished candle must be ignored
        today=a[-1]["date"]+dt.timedelta(days=1)
        future=dict(a[-1])
        future["date"]=today
        future["open"]=future["high"]=future["low"]=future["close"]=999999
        x=w.snapshot(copy.deepcopy(a),today,"sha","code")
        y=w.snapshot(copy.deepcopy(a+[future]),today,"sha","code")
        for key in ("source_last_completed_day","trend_gate","confirmed_cycle_proxy",
                    "elliott_wave2_proxy","source_close","candidate_entry_gate",
                    "historically_reconstructed_open_position"):
            self.assertEqual(x[key],y[key],key)
        self.assertTrue(x["not_a_trade_or_fill"])

    def test_stale_data_fails_closed(self):
        a=self.bars()
        today=a[-1]["date"]+dt.timedelta(days=4)
        with self.assertRaises(ValueError):
            w.snapshot(a,today,"sha","code")

    def test_frozen_label_and_execution_window(self):
        a=self.bars()
        today=a[-1]["date"]+dt.timedelta(days=1)
        x=w.snapshot(a,today,"sha","code")
        self.assertEqual(x["model"],"TrendCycleWide6Delayed")
        self.assertEqual(x["execution_date_if_gate_persists"],
                         str(a[-1]["date"]+dt.timedelta(days=2)))
        self.assertIsInstance(x["candidate_entry_gate"],bool)


if __name__=="__main__":
    unittest.main()
