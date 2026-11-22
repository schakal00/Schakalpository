#!/usr/bin/env python3
"""CECS 2.7 descriptive uncertainty on historical net-equity differences.

Independent-calendar-month BLOCK bootstrap (not a multiple-testing correction,
not valid as a formal inferential confidence interval for selected strategies).
All results are in % annualized daily LOG-return differential, not CAGR or alpha.
"""
import argparse
import csv
import math
import random
from collections import defaultdict
from pathlib import Path

PAIRS=(
    ("TrendVol30Vector","TrendVol30"),
    ("TrendVol30Vector","Trend50"),
    ("Trend25","BuyHold25"),
)
SEED=20261122
REPLICATIONS=4000
START="2022-01-01"
END="2026-11-21"


def estimate(rows,model_a,model_b,n=REPLICATIONS,seed=SEED):
    bydate=defaultdict(dict)
    for r in rows:
        day=r["date"]
        if START<=day<=END and r["model"] in (model_a,model_b):
            bydate[day][r["model"]]=float(r["equity_usd"])
    monthly=defaultdict(list)
    p1=p2=None
    for day in sorted(bydate):
        v=bydate[day]
        if model_a not in v or model_b not in v:
            raise ValueError("Missing paired model date "+day)
        a,b=v[model_a],v[model_b]
        if a<=0 or b<=0:
            raise ValueError("Invalid nonpositive equity")
        if p1 is not None and p2 is not None:
            monthly[day[:7]].append(math.log(a/p1)-math.log(b/p2))
        p1,p2=a,b
    blocks=list(monthly.values())
    if len(blocks)<24:
        raise ValueError("Fewer than 24 months")
    rng=random.Random(seed)
    observed=365*sum(sum(b) for b in blocks)/sum(map(len,blocks))
    boot=[]
    for _ in range(n):
        chosen=[blocks[rng.randrange(len(blocks))] for _ in blocks]
        boot.append(365*sum(map(sum,chosen))/sum(map(len,chosen)))
    boot.sort()
    return dict(model=model_a,comparison=model_b,
        months=len(blocks),observed_log_excess_ann_pct=round(100*observed,4),
        bootstrap_025_pct=round(100*boot[int(n*.025)],4),
        bootstrap_975_pct=round(100*boot[int(n*.975)-1],4),
        blocks_positive=sum(sum(x)>0 for x in blocks),
        replications=n,seed=seed,
        is_formal_statistical_significance_test=False,
        selection_bias_corrected=False)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="results_slow/daily_equity.csv")
    p.add_argument("--out",default="results_slow/exploratory_bootstrap.csv")
    a=p.parse_args()
    with open(a.input,encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    results=[estimate(rows,*pair) for pair in PAIRS]
    dest=Path(a.out)
    dest.parent.mkdir(exist_ok=True,parents=True)
    with dest.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    for r in results:
        print(r)


if __name__=="__main__":
    main()
