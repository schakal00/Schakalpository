#!/usr/bin/env python3
"""Independent CECS3 cross-source OHLC audit.

Compare two PUBLIC Bitstamp-labeled archives:
(1) public daily BTC/USD dataset, (2) 1-minute candles aggregated to
complete UTC days. This is a data-consistency check, not alpha validation.
No strategy weights are changed and no trading decisions depend on this script.
"""
import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

from cecs_v2_1_runner import fetch_data,parse_data,URL
from cecs_v2_6_mw import full_daily
from cecs_v3_0_strategy import load


FIELDS=("open","high","low","close")


def compare(daily,from_minute,min_overlap=10):
    a={x["date"]:x for x in daily}
    b={x["date"]:x for x in from_minute}
    days=sorted(set(a)&set(b))
    if len(days)<min_overlap:
        raise ValueError("Overlapping days too few to audit")
    pairs=[]
    discrepancy={}
    for date in days:
        for key in FIELDS:
            reference=a[date][key]
            minute=b[date][key]
            if reference<=0 or minute<=0:
                raise ValueError("Nonpositive price in common date")
            rel=100*abs(minute-reference)/reference
            pairs.append(dict(date=str(date),field=key,daily=round(reference,5),
                minute_aggregated=round(minute,5),absolute_relative_error_pct=round(rel,8)))
            discrepancy[(date,key)]=rel
    summary=[]
    for name in FIELDS:
        vals=sorted(discrepancy[(day,name)] for day in days)
        summary.append(dict(field=name,compared_days=len(days),
            first=str(days[0]),last=str(days[-1]),
            median_abs_pct=round(statistics.median(vals),6),
            p95_abs_pct=round(vals[int((len(vals)-1)*.95)],6),
            max_abs_pct=round(max(vals),6),
            greater_0_1pct=sum(x>.1 for x in vals),
            greater_0_5pct=sum(x>.5 for x in vals),
            greater_1pct=sum(x>1 for x in vals)))
    worst=sorted(pairs,key=lambda x:x["absolute_relative_error_pct"],reverse=True)[:30]
    return summary,worst


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--years",type=int,nargs="+",default=list(range(2019,2027)))
    p.add_argument("--out",default="results_cross_source")
    args=p.parse_args()
    source=fetch_data(None)
    daily=parse_data(source)
    bars,sources=load(args.years)
    derived=full_daily(bars)
    rows,worst=compare(daily,derived,min_overlap=1000)
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    with (out/"source_comparison.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (out/"largest_differences.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(worst[0]))
        writer.writeheader()
        writer.writerows(worst)
    risk=any(x["field"]=="close" and x["greater_1pct"]>max(5,.01*x["compared_days"])
             for x in rows)
    meta=dict(
        daily_data=URL,source_daily_sha256=hashlib.sha256(source).hexdigest(),
        minute_archives=sources,comparisons=rows,
        serious_close_discrepancy_flag=risk,
        note="Disagreements need external investigation. Trading backtests are not proof of genuine fills."
    )
    (out/"manifest.json").write_text(json.dumps(meta,indent=2,default=str),encoding="utf-8")
    print(json.dumps({"comparison":rows,"worst_examples":worst[:8],
        "serious_close_discrepancy_flag":risk},indent=2))
    if risk:
        raise ValueError("Daily vs reconstructed 1m close discrepancy exceeds predeclared threshold")


if __name__=="__main__":
    main()
