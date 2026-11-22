#!/usr/bin/env python3
"""CECS 2.7 risk-aware slow trend / volatility target exploration.

BTC/USD spot long/cash, no leverage, no fitted ML, no broker connection.
All signals from COMPLETED daily candles. Execution at NEXT FEASIBLE open:
a signal on closed date t executes on day t+2 open, allowing morning
publication on day t+1. Historical midnight fills on day t+2 remain
hypothetical; forward paper uses fresh timestamped exchange bid/ask.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import statistics
from pathlib import Path

from cecs_v2_1_runner import URL, fetch_data, parse_data
from cecs_v2_3_trend import indicators

COST=.0015
MODEL_NAMES=("Cash","BuyHold25","BuyHold50","BuyHold100",
             "Trend25","Trend50","TrendVol20","TrendVol30",
             "TrendVol30Cycle","TrendVol30Vector")
INITIAL=100000.
VOL_DAYS=30
YEAR_DAYS=365
MAX_EXPOSURE=.75
START=201
REBALANCE_THRESHOLD=.05
PERIODS=(("development_2017_2021","2017-01-01","2021-12-31"),
         ("historically_seen_2022_2026","2022-01-01","2026-12-31"))


def prepare(bars):
    indicators(bars)
    for i,x in enumerate(bars):
        if i < VOL_DAYS:
            x["annualized_realized_vol30"]=None
        else:
            rets=[math.log(bars[j]["close"]/bars[j-1]["close"])
                  for j in range(i-VOL_DAYS+1,i+1)]
            st=statistics.stdev(rets)
            x["annualized_realized_vol30"]=st*math.sqrt(YEAR_DAYS)
    return bars


def target_weight(signal,model):
    if model=="Cash":
        return 0.
    if model.startswith("BuyHold"):
        return {"BuyHold25":.25,"BuyHold50":.50,"BuyHold100":1.0}[model]
    if not signal["trend"]:
        return 0.
    if model=="Trend25":
        return .25
    if model=="Trend50":
        return .5
    if model.startswith("TrendVol"):
        annual_vol=signal["annualized_realized_vol30"]
        if annual_vol is None or annual_vol<=0:
            return 0.
        target_vol=.20 if model=="TrendVol20" else .30
        base=min(MAX_EXPOSURE,target_vol/max(annual_vol,.10))
        if model=="TrendVol30Cycle":
            base*=1.2 if signal["cycle"] else .8
        if model=="TrendVol30Vector":
            base*=1.2 if signal["vector_confirmed"] else .8
        return min(MAX_EXPOSURE,base)
    raise ValueError(model)


def simulate(bars,model,cost=COST):
    cash=INITIAL
    qty=0.
    orders=[]
    equity=[]
    max_dd=0.
    peak=INITIAL
    for i,x in enumerate(bars):
        # Signal available only from day i-2 close, not yesterday's inaccessible midnight close.
        known=bars[i-2] if i>=2 else None
        eligible=known is not None and i>=START+2
        desired=target_weight(known,model) if eligible else 0.
        opening=x["open"]
        # Rebalance weekly on Monday, with prompt defensive exit on regime-off.
        gross_value=cash+qty*opening
        actual_weight=qty*opening/gross_value if gross_value>0 else 0.
        should_trade=eligible and (
            (x["date"].weekday()==0 and abs(desired-actual_weight)>=REBALANCE_THRESHOLD)
            or (desired==0 and qty>0)
            or (model.startswith("BuyHold") and qty==0))
        if should_trade and gross_value>0:
            desired_notional=desired*gross_value
            current_notional=qty*opening
            delta=desired_notional-current_notional
            if delta>0:
                additional=min(delta/(opening*(1+cost)),
                               max(0.,cash)/(opening*(1+cost)))
                if additional>0:
                    fee=additional*opening*cost
                    qty+=additional
                    cash-=additional*opening+fee
                    orders.append(dict(model=model,date=str(x["date"]),source_date=str(known["date"]),
                        side="BUY",units_btc=round(additional,9),price_usd=round(opening,4),
                        cost_usd=round(fee,4),target_weight=round(desired,5)))
            elif delta<0:
                sell=min(qty,-delta/opening)
                if sell>0:
                    fee=sell*opening*cost
                    qty-=sell
                    cash+=sell*opening-fee
                    orders.append(dict(model=model,date=str(x["date"]),source_date=str(known["date"]),
                        side="SELL",units_btc=round(sell,9),price_usd=round(opening,4),
                        cost_usd=round(fee,4),target_weight=round(desired,5)))
        liquidation=cash+qty*x["close"]*(1-cost)
        peak=max(peak,liquidation)
        max_dd=min(max_dd,liquidation/peak-1)
        equity.append(dict(model=model,date=str(x["date"]),equity_usd=round(liquidation,6),
                           market_exposure_pct=round(100*qty*x["close"]/(cash+qty*x["close"]),4)
                           if cash+qty*x["close"]>0 else 0.,source_day=str(known["date"]) if known else None))
    totals=dict(model=model,cost_bps_each_leg=round(10000*cost),
                total_return_pct=round(100*(equity[-1]["equity_usd"]/INITIAL-1),3),
                total_max_daily_drawdown_pct=round(100*max_dd,3),
                average_exposure_pct=round(statistics.mean(y["market_exposure_pct"] for y in equity),2),
                orders=len(orders),turnover_usd=round(sum(o["units_btc"]*o["price_usd"] for o in orders),2),
                transaction_costs_usd=round(sum(o["cost_usd"] for o in orders),2))
    return totals,equity,orders


def periods(equity):
    windows=list(PERIODS)
    windows.extend((str(y),f"{y}-01-01",f"{y}-12-31") for y in range(2017,2027))
    arr=[]
    for label,a,b in windows:
        sub=[x for x in equity if a<=x["date"]<=b]
        if not sub: continue
        prev=next((x for x in reversed(equity) if x["date"]<a),None)
        start_eq=prev["equity_usd"] if prev else INITIAL
        peak=start_eq
        dd=0.
        for x in sub:
            peak=max(peak,x["equity_usd"])
            dd=min(dd,x["equity_usd"]/peak-1)
        arr.append(dict(model=sub[0]["model"],period=label,from_date=sub[0]["date"],
            to_date=sub[-1]["date"],return_pct=round(100*(sub[-1]["equity_usd"]/start_eq-1),3),
            max_daily_drawdown_pct=round(100*dd,3),
            avg_market_exposure_pct=round(statistics.mean(x["market_exposure_pct"] for x in sub),2)))
    return arr


def csvout(path,items):
    if not items:
        path.write_text("NO RECORDS\n",encoding="utf-8")
        return
    with path.open("w",newline="",encoding="utf-8") as fh:
        writer=csv.DictWriter(fh,fieldnames=list(items[0]))
        writer.writeheader()
        writer.writerows(items)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv",default=None)
    ap.add_argument("--out",default="results_slow")
    args=ap.parse_args()
    payload=fetch_data(args.csv)
    bars=prepare(parse_data(payload))
    out=Path(args.out)
    out.mkdir(exist_ok=True,parents=True)
    allsummary,allperiods,allorders,allmarks,stress=[],[],[],[],[]
    for model in MODEL_NAMES:
        total,marks,orders=simulate(bars,model,COST)
        allsummary.append(total)
        allperiods+=periods(marks)
        allorders+=orders
        allmarks+=marks
        if model!="Cash":
            for bp in (0,5,15,30):
                summary,curve,orders2=simulate(bars,model,bp/10000)
                cut=next((x for x in periods(curve) if x["period"]=="historically_seen_2022_2026"),None)
                stress.append(dict(model=model,cost_bps_each_leg=bp,
                    total_return_pct=summary["total_return_pct"],
                    total_max_dd_pct=summary["total_max_daily_drawdown_pct"],
                    review_2022_2026_return_pct=cut["return_pct"] if cut else None,
                    review_2022_2026_max_dd_pct=cut["max_daily_drawdown_pct"] if cut else None,
                    orders=len(orders2)))
    csvout(out/"summary.csv",allsummary)
    csvout(out/"periods.csv",allperiods)
    csvout(out/"orders.csv",allorders)
    csvout(out/"daily_equity.csv",allmarks)
    csvout(out/"cost_sensitivity.csv",stress)
    (out/"manifest.json").write_text(json.dumps(dict(
        version="CECS-2.7-exploratory-2026-11-22",
        source=URL,sha256=hashlib.sha256(payload).hexdigest(),
        first_day=str(bars[0]["date"]),last_day=str(bars[-1]["date"]),
        bars=len(bars),model_count=len(MODEL_NAMES),
        full_model_list=MODEL_NAMES,
        rules=dict(last_available_bar_lag_days=2,vol_window_days=VOL_DAYS,
                   annualized_sqrt_days=YEAR_DAYS,max_exposure=MAX_EXPOSURE,
                   weekly_rebalance_day="Monday UTC",
                   minimum_rebalance_weight_change=REBALANCE_THRESHOLD,
                   total_cost_assumed_bps_per_leg=15),
        warning="Not true unseen holdout, optimistic historical open fills vs prospective quote executions; multiple candidate trials, no guaranteed edge."),indent=2),encoding="utf-8")
    print(json.dumps(dict(summary=allsummary,
                          history=[p for p in allperiods if p["period"]=="historically_seen_2022_2026"],
                          count_models=len(MODEL_NAMES)),indent=2))


if __name__=="__main__":
    main()
