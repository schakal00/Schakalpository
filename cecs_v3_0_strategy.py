#!/usr/bin/env python3
"""CECS 3.0 research: BTC/USD LONG/CASH risk-budgeted daily trend strategies.

Design before evaluation:
  Primary candidate CECS3_Defensive: at most 25% BTC if the complete
  daily close is above SMA200 and SMA50>SMA200; halve to 12.5% if
  closed price is below SMA50 OR annualized realized vol30 > 80%.
  Otherwise cash. No leverage, no shorts, no borrowed capital.
  Rebalance weekly Mondays if deviation exceeds 3 percentage points;
  risk reductions are permitted immediately at the daily execution slot.

Signal t-2 UTC close -> historic simulated execution D at 09:00 UTC on
Bitstamp 15m open, NOT midnight open. Current 15m bar used only after entry
for same-day closing-equity mark; no trading using its future high/low.
Real fills cannot be proven from OHLC: simulated prices include additional
half-spread and fee/slippage. Do not import this result into frozen CECS2.8.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import statistics
from pathlib import Path

from cecs_v2_1_runner import URL as DAILY_SOURCE
from cecs_v2_2_intraday import download_year, aggregate_15m
from cecs_v2_6_mw import full_daily
from cecs_v2_7_slow import target_weight as existing_target, prepare

UTC=dt.timezone.utc
START_CASH=100000.
DEFAULT_COST_BPS_PER_SIDE=15
ASSUMED_HALF_SPREAD_BPS_PER_SIDE=2
REBALANCE_MIN_WEIGHT=.03
MODELS=("Cash","Hold25","Trend25","Trend50","CECS3_Defensive",
        "CECS3_Balanced","CECS3_Volatility","CECS3_Momentum",
        "TrendVol30Vector")
PERIODS=(
    ("development_2019_2021","2019-01-01","2021-12-31"),
    ("earlier_review_2022_2023","2022-01-01","2023-12-31"),
    ("seen_review_2024_2026","2024-01-01","2026-12-31"),
    ("full_2022_onward","2022-01-01","2026-12-31")
)


def add_derived_features(daily):
    for i,day in enumerate(daily):
        day["roc90"]=(day["close"]/daily[i-90]["close"]-1.) if i>=90 else None
        day["under_sma50"]=day["sma50"] is not None and day["close"]<day["sma50"]
    return daily


def declared_weight(features,name):
    """All weights deterministic on CURRENTLY KNOWN, fully closed bars only."""
    if name=="Cash":
        return 0.
    if name=="Hold25":
        return .25
    if name=="Trend25":
        return .25 if features["trend"] else 0.
    if name=="Trend50":
        return .50 if features["trend"] else 0.
    if name=="TrendVol30Vector":
        return existing_target(features,name)
    if name not in ("CECS3_Defensive","CECS3_Balanced",
                    "CECS3_Volatility","CECS3_Momentum"):
        raise ValueError(name)
    if not features["trend"]:
        return 0.
    vol=features["annualized_realized_vol30"]
    if vol is None or not math.isfinite(vol) or vol<=0:
        return 0.
    below=bool(features["under_sma50"])
    if name=="CECS3_Defensive":
        return .125 if (below or vol>.8) else .25
    if name=="CECS3_Balanced":
        return .15 if (below or vol>.8) else .30
    if name=="CECS3_Volatility":
        v=min(.35,.2/max(vol,.10))
        return v*.5 if below else v
    if name=="CECS3_Momentum":
        return .30 if (features["roc90"] is not None
                       and features["roc90"]>0 and not below) else .10
    raise ValueError(name)


def quote_points(bars15):
    """A Bitstamp 09:00 UTC 15m Open, not a contemporaneous bid/ask recording.
    Must exist in same day. Only a pricing proxy for a fresh morning ticker.
    """
    points={}
    for x in bars15:
        moment=x["time"]
        if moment.hour==9 and moment.minute==0:
            day=moment.date()
            if day in points:
                raise ValueError("Duplicate 09:00 Bitstamp quote")
            points[day]=x["open"]
    return points


def simulate(daily, quotes, model, cost_bps=DEFAULT_COST_BPS_PER_SIDE):
    if cost_bps<0 or not math.isfinite(cost_bps):
        raise ValueError("Cost must be nonnegative")
    friction=(cost_bps+ASSUMED_HALF_SPREAD_BPS_PER_SIDE)/10000
    cash=START_CASH
    qty=0.
    orders=[]
    curve=[]
    for i,bar in enumerate(daily):
        day=bar["date"]
        # Daily signal D-2 is safely completed before historical execution D at 09UTC.
        signal=daily[i-2] if i>=2 else None
        ready=i>=202 and signal is not None and signal["date"]==day-dt.timedelta(days=2)
        target=declared_weight(signal,model) if ready else 0.
        px=quotes.get(day)
        # Without a complete 09:00 15m bar, refuse a hypothetical execution.
        # Mark position at completed end-of-day price but do not trade.
        if ready and px is not None:
            gross=cash+qty*px
            current=qty*px/gross if gross>0 else 0.
            cut=target<current-REBALANCE_MIN_WEIGHT
            trade_now=(day.weekday()==0 and abs(current-target)>=REBALANCE_MIN_WEIGHT) or (
                model not in ("Cash","Hold25") and cut)
            # Never execute on a non-Monday when increasing risk.
            if trade_now:
                delta=target*gross-qty*px
                if delta>0:
                    buy=min(cash/(px*(1+friction)),
                            max(0,delta)/(px*(1+friction)))
                    if buy>1e-12:
                        cash-=buy*px*(1+friction)
                        qty+=buy
                        orders.append(dict(model=model,action="BUY",day=str(day),
                            signal_day=str(signal["date"]),execution_utc="09:00",
                            price_mid_open=round(px,4),
                            fill_assumption_usd=round(px*(1+friction),4),
                            btc=round(buy,9),
                            friction_paid_usd=round(buy*px*friction,4),
                            target_weight=round(target,6)))
                elif delta<0:
                    sell=min(qty,-delta/px)
                    if sell>1e-12:
                        cash+=sell*px*(1-friction)
                        qty-=sell
                        orders.append(dict(model=model,action="SELL",day=str(day),
                            signal_day=str(signal["date"]),execution_utc="09:00",
                            price_mid_open=round(px,4),
                            fill_assumption_usd=round(px*(1-friction),4),
                            btc=round(sell,9),
                            friction_paid_usd=round(sell*px*friction,4),
                            target_weight=round(target,6)))
        if cash < -1e-6:
            raise ValueError("Impossible negative cash / implicit leverage")
        close=bar["close"]
        gross_close=cash+qty*close
        equity=cash+qty*close*(1-friction)
        if equity<=0:
            raise ValueError("Insolvent paper portfolio")
        curve.append(dict(model=model,day=str(day),equity_usd=equity,
            target_weight=target,
            actual_weight=(qty*close/gross_close if gross_close else 0.),
            signal_day=str(signal["date"]) if signal else None))
    if not curve:
        raise ValueError("Empty series")
    peak=START_CASH
    dd=0.
    for row in curve:
        peak=max(peak,row["equity_usd"])
        dd=min(dd,row["equity_usd"]/peak-1.)
    total=dict(model=model,total_return_pct=round(100*(curve[-1]["equity_usd"]/START_CASH-1.),4),
        total_mtm_drawdown_pct=round(100*dd,4),
        avg_exposure_pct=round(100*statistics.mean(x["actual_weight"] for x in curve),3),
        trades=len(orders),fees_slippage_spread_usd=round(sum(x["friction_paid_usd"] for x in orders),2),
        current_position_pct=round(100*curve[-1]["actual_weight"],3),
        final_capital_usd=round(curve[-1]["equity_usd"],2))
    return total,curve,orders


def summary_by_period(curve):
    outcome=[]
    for label,start,end in PERIODS:
        sub=[x for x in curve if start<=x["day"]<=end]
        if len(sub)<2:
            continue
        prior=next((row for row in reversed(curve) if row["day"]<start),None)
        begin=prior["equity_usd"] if prior else START_CASH
        peak=begin
        drawdown=0.
        for x in sub:
            peak=max(peak,x["equity_usd"])
            drawdown=min(drawdown,x["equity_usd"]/peak-1)
        outcome.append(dict(model=sub[0]["model"],period=label,
            first_day=sub[0]["day"],last_day=sub[-1]["day"],
            return_pct=round(100*(sub[-1]["equity_usd"]/begin-1),4),
            max_mtm_drawdown_pct=round(100*drawdown,4),
            avg_exposure_pct=round(100*statistics.mean(x["actual_weight"] for x in sub),3)))
    for yr in range(2019,2027):
        start=f"{yr}-01-01"
        end=f"{yr}-12-31"
        sub=[x for x in curve if start<=x["day"]<=end]
        if not sub:
            continue
        prior=next((row for row in reversed(curve) if row["day"]<start),None)
        base=prior["equity_usd"] if prior else START_CASH
        pk=base
        dd=0.
        for x in sub:
            pk=max(pk,x["equity_usd"])
            dd=min(dd,x["equity_usd"]/pk-1)
        outcome.append(dict(model=sub[0]["model"],period=str(yr),
            first_day=sub[0]["day"],last_day=sub[-1]["day"],
            return_pct=round(100*(sub[-1]["equity_usd"]/base-1),4),
            max_mtm_drawdown_pct=round(100*dd,4),
            avg_exposure_pct=round(100*statistics.mean(x["actual_weight"] for x in sub),3)))
    return outcome


def save_csv(path,records):
    rows=list(records)
    if not rows:
        path.write_text("NO OBSERVATIONS\n",encoding="utf-8")
        return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def load(years):
    if not years or years!=list(range(years[0],years[-1]+1)):
        raise ValueError("Years must be contiguous")
    combined=[]
    sources=[]
    for year in years:
        compressed,url=download_year(year)
        this,coverage=aggregate_15m(compressed,year)
        if combined and this[0]["time"]!=combined[-1]["time"]+dt.timedelta(minutes=15):
            raise ValueError("Missing year boundary: don't fabricate price history")
        combined.extend(this)
        sources.append(dict(year=year,source=url,
            sha256=hashlib.sha256(compressed).hexdigest(),
            first=str(this[0]["time"]),last=str(this[-1]["time"]),
            coverage=coverage))
    return combined,sources


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--years",type=int,nargs="+",default=list(range(2019,2027)))
    p.add_argument("--out",default="results_cecs3")
    args=p.parse_args()
    raw,sources=load(args.years)
    quotes=quote_points(raw)
    daily=add_derived_features(prepare(full_daily(raw)))
    folder=Path(args.out)
    folder.mkdir(exist_ok=True,parents=True)
    overall,periods,orders,curves,cost_test=[],[],[],[],[]
    for name in MODELS:
        s,curve,executions=simulate(daily,quotes,name)
        overall.append(s)
        periods+=summary_by_period(curve)
        orders+=executions
        curves+=curve
        for c in (0,15,30,50):
            s2,e,_=simulate(daily,quotes,name,cost_bps=c)
            review=next((x for x in summary_by_period(e)
                         if x["period"]=="full_2022_onward"),None)
            cost_test.append(dict(model=name,cost_bps_each_side=c,
                total_return_pct=s2["total_return_pct"],
                total_dd_pct=s2["total_mtm_drawdown_pct"],
                review_return_pct=review["return_pct"] if review else None,
                review_dd_pct=review["max_mtm_drawdown_pct"] if review else None,
                trades=s2["trades"]))
    for label,records in [
        ("summary.csv",overall),("periods.csv",periods),("order_log.csv",orders),
        ("equity_daily.csv",curves),("cost_stress.csv",cost_test)]:
        save_csv(folder/label,records)
    manifest=dict(version="CECS3.0-research-2026-11-22",
        market="Bitstamp BTC/USD",sources=sources,
        first_day=str(daily[0]["date"]),last_day=str(daily[-1]["date"]),
        completed_daily=len(daily),valid_15m=len(raw),
        execution_price_proxy="15m opening price at 09:00 UTC on day D",
        signal_day="D-2",
        reported_bps_cost_each_leg=DEFAULT_COST_BPS_PER_SIDE,
        assumed_extra_half_spread_bps_each_leg=ASSUMED_HALF_SPREAD_BPS_PER_SIDE,
        models=list(MODELS),rebalance_threshold=REBALANCE_MIN_WEIGHT,
        declaration="Primary CECS3_Defensive defined before current study. All periods are historically seen, not prospectively untouched.",
        no_leverage=True,not_a_live_fill=True)
    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(dict(summary=overall,
         periods=[x for x in periods if x["period"] in ("earlier_review_2022_2023",
                      "seen_review_2024_2026","full_2022_onward")],manifest=manifest),
                      indent=2,default=str))


if __name__=="__main__":
    main()
