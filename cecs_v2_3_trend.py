#!/usr/bin/env python3
"""CECS 2.3 - slow BTC/USD trend-first research, not a live signal service.

Core principle: do NOT optimize against a known future return. Compare registered
long/cash strategy variants and a buy-and-hold baseline with chronological
market data and conservative fills. Camel/Elliott/TradersReality are EXPLICIT
mechanical proxies; not official implementations or verified predictive tools.

At decision on closed date t:
  all features use bars <= t; earliest trade open is t+1.
Position risk: <= 0.50% at the INITIAL STOP in a non-gap fill; no leverage.
No same-day trailing stop updates; stop priority on conflicting fills.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from cecs_v2_1_runner import URL, fetch_data, parse_data, confirmed_pivots, enrich, wave_candidate

COST=0.0015  # entry/exit as a fraction of gross notional, including assumed slippage
RISK=.005
STOP_ATR=3.
COOLDOWN=10
WINDOW_VECTOR=7
WINDOW_CYCLE=45
WINDOW_WAVE=60
START=200
MODELS=("BuyHoldSpot","TrendSpot","TrendSpotQuarter","TrendRisk",
        "TrendWide6","TrendWide10","TrendCycleWide6Delayed","TrendVectorWide6","TrendCycleWide6",
        "TrendVector","TrendCycle","TrendElliott","TrendScore1","TrendScore2")


def indicators(bars):
    enrich(bars)
    close=[x["close"] for x in bars]
    s50=s200=0.
    for i,x in enumerate(bars):
        s50+=close[i]
        s200+=close[i]
        if i>=50:
            s50-=close[i-50]
        if i>=200:
            s200-=close[i-200]
        x["sma50"]=s50/50 if i>=49 else None
        x["sma200"]=s200/200 if i>=199 else None
        x["trend"]=bool(i>=199 and x["close"]>x["sma200"] and x["sma50"]>x["sma200"])
    piv=confirmed_pivots(bars,7,3)
    swings=[]
    dcl_anchor=None
    last_cycle=last_wave=last_bull_vector=None
    events=Counter()
    for i,x in enumerate(bars):
        if x["vector"] in ("green","blue"):
            last_bull_vector=i
        for kind,p,price in piv[i]:
            if swings and swings[-1][0]==kind:
                if (kind=="L" and price<swings[-1][2]) or (kind=="H" and price>swings[-1][2]):
                    swings[-1]=(kind,p,price)
            else:
                swings.append((kind,p,price))
            swings=swings[-24:]
            if kind!="L":
                continue
            events["confirmed_daily_lows"]+=1
            interval=p-dcl_anchor if dcl_anchor is not None else None
            if interval is None or interval>=45:
                if interval is not None and interval<=85:
                    last_cycle=i
                    events["confirmed_DCL_45_85"]+=1
                dcl_anchor=p
            if wave_candidate(swings,bars) is not None:
                last_wave=i
                events["elliott_wave2_proxies"]+=1
        cycle=last_cycle is not None and i-last_cycle<=WINDOW_CYCLE
        elliott=last_wave is not None and i-last_wave<=WINDOW_WAVE
        vector=last_bull_vector is not None and i-last_bull_vector<=WINDOW_VECTOR
        x["cycle"]=bool(cycle)
        x["elliott"]=bool(elliott)
        x["vector_confirmed"]=bool(vector)
        x["score"]=int(cycle)+int(elliott)+int(vector)
    return events


def entry_gate(b,model):
    if model=="BuyHoldSpot":
        return True
    if not b["trend"]:
        return False
    if model in ("TrendSpot","TrendSpotQuarter","TrendRisk","TrendWide6","TrendWide10"):
        return True
    if model in ("TrendVector","TrendVectorWide6"):
        return b["vector_confirmed"]
    if model in ("TrendCycle","TrendCycleWide6","TrendCycleWide6Delayed"):
        return b["cycle"]
    if model=="TrendElliott":
        return b["elliott"]
    if model=="TrendScore1":
        return b["score"]>=1
    if model=="TrendScore2":
        return b["score"]>=2
    raise ValueError(model)


def gross_equity(cash,quantity,mark,cost=COST):
    return cash+quantity*mark*(1-cost)


def backtest(bars,model,cost=COST,force_close_end=True,return_state=False):
    cash=100000.
    qty=0.
    stop=None
    highest=None
    entry=None
    entry_idx=None
    entry_qty=None
    entry_cost=None
    entry_risk=None
    entry_score=None
    last_exit=-COOLDOWN-9999
    trades=[]
    equity=[]
    exposure_bars=0
    peak=100000.
    drawdown=0.
    def close_trade(i,price,reason):
        nonlocal cash,qty,stop,highest,entry,entry_idx,last_exit,entry_qty,entry_cost,entry_risk,entry_score
        cash+=qty*price*(1-cost)
        pnl=qty*(price*(1-cost)-entry*(1+cost))
        trades.append(dict(model=model,entry=str(bars[entry_idx]["date"]),exit=str(bars[i]["date"]),
                           entry_px=round(entry,2),exit_px=round(price,2),reason=reason,
                           pnl_usd=round(pnl,2),r=round(pnl/(entry_qty*entry_risk),5) if entry_risk else None,
                           score_at_entry=entry_score))
        last_exit=i
        qty=0.
        stop=highest=entry=entry_idx=entry_qty=entry_cost=entry_risk=entry_score=None

    for i,x in enumerate(bars):
        lag = 2 if model=="TrendCycleWide6Delayed" else 1
        yesterday=bars[i-lag] if i>=lag else None
        # A regime exit was known at the previous day's CLOSE. Fill at today's OPEN.
        if qty>0 and model!="BuyHoldSpot" and yesterday is not None and not yesterday["trend"]:
            close_trade(i,x["open"],"trend_exit")
        # Stop order carried from prior day. On a gap, fill at opening price, not optimistic stop.
        if qty>0 and stop is not None:
            if x["open"]<=stop:
                close_trade(i,x["open"],"gap_stop")
            elif x["low"]<=stop:
                close_trade(i,stop,"stop")
        # Enter based only on previous completed daily candle; no same-day reentry.
        if i>=START and qty==0 and yesterday is not None and last_exit!=i and entry_gate(yesterday,model):
            if model=="BuyHoldSpot":
                if not trades:    # after initial buy, never reenter
                    allocation=cash/(x["open"]*(1+cost))
                else:
                    allocation=0.
                init_stop=None
                unit_risk=None
            elif model in ("TrendSpot","TrendSpotQuarter"):
                fraction=.25 if model=="TrendSpotQuarter" else 1.0
                allocation=fraction*cash/(x["open"]*(1+cost))
                init_stop=None
                unit_risk=None
            elif i-last_exit>COOLDOWN:
                atr_factor=(10. if model=="TrendWide10" else 6. if model in ("TrendWide6","TrendVectorWide6","TrendCycleWide6","TrendCycleWide6Delayed") else STOP_ATR)
                init_stop=yesterday["close"]-atr_factor*yesterday["atr"] if yesterday["atr"] else None
                unit_risk=x["open"]*(1+cost)-init_stop*(1-cost) if init_stop else None
                allocation=min(RISK*cash/unit_risk,cash/(x["open"]*(1+cost))) if unit_risk and unit_risk>0 and init_stop<x["open"] else 0.
            else:
                allocation=0.
                init_stop=None
                unit_risk=None
            if allocation>0:
                qty=allocation
                cash-=allocation*x["open"]*(1+cost)
                entry=x["open"]
                entry_idx=i
                entry_qty=allocation
                entry_cost=cost
                entry_risk=unit_risk
                entry_score=yesterday["score"]
                stop=init_stop
                highest=x["high"]
                # Initial stop must also be honored on entry day.
                if stop is not None and x["low"]<=stop:
                    close_trade(i,stop,"entry_day_stop")
        if qty>0:
            exposure_bars+=1
            # End-of-day update, never applied to the earlier part of this candle.
            if stop is not None and x["atr"]:
                highest=max(highest,x["high"])
                atr_factor=(10. if model=="TrendWide10" else 6. if model in ("TrendWide6","TrendVectorWide6","TrendCycleWide6","TrendCycleWide6Delayed") else STOP_ATR)
                stop=max(stop,highest-atr_factor*x["atr"])
            if force_close_end and i==len(bars)-1:
                close_trade(i,x["close"],"end_of_sample")
        net=gross_equity(cash,qty,x["close"],cost) if qty>0 else cash
        peak=max(peak,net)
        drawdown=min(drawdown,net/peak-1.)
        equity.append(dict(model=model,date=str(x["date"]),equity=round(net,6),
                           invested=int(qty>0),score=x["score"]))
    wins=[t for t in trades if t["pnl_usd"]>0]
    losses=[t for t in trades if t["pnl_usd"]<0]
    stats=dict(model=model,trades=len(trades),
               win_rate_pct=round(100*len(wins)/len(trades),2) if trades else None,
               profit_factor=round(sum(t["pnl_usd"] for t in wins)/(-sum(t["pnl_usd"] for t in losses)),3) if losses else None,
               avg_r=round(statistics.mean(t["r"] for t in trades if t["r"] is not None),4) if any(t["r"] is not None for t in trades) else None,
               return_pct=round(100*(equity[-1]["equity"]/100000-1),3),
               max_mtm_drawdown_pct=round(100*drawdown,3),
               exposure_pct=round(100*exposure_bars/len(bars),2))
    state=dict(quantity=qty, stop=stop, entry=entry, entry_index=entry_idx,
               highest=highest, cash=cash, last_exit_index=last_exit)
    return (stats,equity,trades,state) if return_state else (stats,equity,trades)


def period_stats(equity):
    # Retrospective period comparisons. No selection/training on review data.
    periods=[("development_2017_2021","2017-01-01","2021-12-31"),
             ("historical_review_2022_2026","2022-01-01","2026-12-31")]
    for year in range(2017,2027):
        periods.append((str(year),f"{year}-01-01",f"{year}-12-31"))
    arr=[]
    for label,start,finish in periods:
        subset=[r for r in equity if start<=r["date"]<=finish]
        if len(subset)<2:
            continue
        # Use equity close from the day just BEFORE period start as the base.
        previous=next((r for r in reversed(equity) if r["date"]<start),None)
        base=previous["equity"] if previous is not None else 100000.
        peak=base
        dd=0.
        for r in subset:
            peak=max(peak,r["equity"])
            dd=min(dd,r["equity"]/peak-1.)
        arr.append(dict(model=subset[0]["model"],period=label,
                        start=subset[0]["date"],end=subset[-1]["date"],
                        return_pct=round(100*(subset[-1]["equity"]/base-1.),4),
                        max_mtm_drawdown_pct=round(100*dd,4),
                        exposure_pct=round(100*sum(z["invested"] for z in subset)/len(subset),2)))
    return arr


def write_csv(path,records):
    rows=list(records)
    if not rows:
        path.write_text("NO OBSERVATIONS\n",encoding="utf-8")
        return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",default=None)
    p.add_argument("--out",default="results_trend")
    args=p.parse_args()
    source=fetch_data(args.csv)
    bars=parse_data(source)
    event_counts=indicators(bars)
    output=Path(args.out)
    output.mkdir(parents=True,exist_ok=True)
    summaries,periods,trades,equity,sensitivity=[],[],[],[],[]
    for model in MODELS:
        s,e,t=backtest(bars,model)
        summaries.append(s)
        periods+=period_stats(e)
        trades+=t
        equity+=e
        if model in ("TrendWide6","TrendWide10","TrendCycleWide6","TrendCycleWide6Delayed","TrendVectorWide6","TrendSpotQuarter"):
            for bp in (0,5,15,30):
                alt_stats,alt_eq,alt_trades=backtest(bars,model,cost=bp/10000)
                review=next(x for x in period_stats(alt_eq) if x["period"]=="historical_review_2022_2026")
                sensitivity.append(dict(model=model,fee_slippage_bps_per_leg=bp,
                                        review_return_pct=review["return_pct"],
                                        review_max_dd_pct=review["max_mtm_drawdown_pct"],
                                        review_exposure_pct=review["exposure_pct"],
                                        overall_trades=len(alt_trades),
                                        historical_review_trades=sum(t["entry"]>="2022-01-01" for t in alt_trades)))
    write_csv(output/"fee_sensitivity.csv",sensitivity)
    write_csv(output/"summary.csv",summaries)
    write_csv(output/"periods.csv",periods)
    write_csv(output/"trades.csv",trades)
    write_csv(output/"equity_daily.csv",equity)
    manifest=dict(source=URL if args.csv is None else str(args.csv),sha256=hashlib.sha256(source).hexdigest(),
                  first=str(bars[0]["date"]),last=str(bars[-1]["date"]),rows=len(bars),
                  fee_slippage_per_leg=COST,initial_stop_atr=STOP_ATR,
                  nominal_stop_risk=RISK,models=MODELS,events=dict(event_counts),
                  disclaimer="Retrospective proxy research, do not optimize on historical review or equate profit with validated edge")
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(dict(summary=summaries,periods=[x for x in periods if x["period"]=="historical_review_2022_2026"],manifest=manifest),indent=2))


if __name__=="__main__":
    main()
