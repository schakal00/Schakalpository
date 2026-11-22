#!/usr/bin/env python3
"""CECS 2.6: explicit Traders-Reality-inspired W/M & Vector proxy study.
Long/flat BTC/USD spot only; M is an optional LONG EXIT, not a short.
Does NOT claim to replicate Tino's discretionary strategy.
Causal signals from completed 15m, 1h and daily candles; next 15m open fill.
Years are contiguous; year boundaries DO NOT reset averages or positions.
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

from cecs_v2_1_runner import confirmed_pivots
from cecs_v2_2_intraday import download_year, aggregate_15m, enrich_vector, completed_hourly
from cecs_v2_3_trend import indicators

UTC=dt.timezone.utc
COST=0.0015
MAX_LOSS_FRACTION=.005
STOP_ATR_MULT=5.
TARGET_R=2.5
MAX_HOLD=288
MIN_SEPARATION=8
MAX_SEPARATION=96
MATCH_ATR=0.8
MIN_NECKLINE_ATR=1.3
CONFIRM_RIGHT=2
WINDOW_EXPIRY=96
MODES=("WOnly","WVector","W1h","WDaily","WCycle","WFusion","WFusionMExit","W1hMExit")
PERIODS=(("development","2019-01-01","2021-12-31"),
         ("historical_comparison","2022-01-01","2023-12-31"),
         ("previously_inspected_review","2024-01-01","2026-12-31"))


def full_daily(bars):
    groups=[]
    current=[]
    for b in bars:
        if current and b["time"].date()!=current[0]["time"].date():
            if len(current)==96 and all(current[j]["time"]==current[0]["time"]+dt.timedelta(minutes=15*j) for j in range(96)):
                groups.append(dict(date=current[0]["time"].date(),
                    open=current[0]["open"],high=max(x["high"] for x in current),
                    low=min(x["low"] for x in current),close=current[-1]["close"],
                    volume=sum(x["volume"] for x in current)))
            current=[]
        current.append(b)
    # Last unfinished day excluded, even if complete: no inference until next midnight.
    indicators(groups)
    for d in groups:
        d["available"]=dt.datetime.combine(d["date"]+dt.timedelta(days=1),
                                            dt.time.min,tzinfo=UTC)
    return groups


def pivot_motifs(bars):
    """Emit W and M formations only upon a confirmed breakout beyond neckline.
    Pivots need four bars left and two FUTURE bars, so known at p+2.
    The pre-breakout motif is never treated as known at its pivot time.
    """
    p=confirmed_pivots(bars,4,CONFIRM_RIGHT)
    lows,highs=[],[]
    candidate_w=[]
    candidate_m=[]
    patterns=[]
    for t in range(20,len(bars)-1):
        for kind,pidx,price in p[t]:
            if kind=="L":
                prev=next((q for q in reversed(lows)
                           if MIN_SEPARATION<=pidx-q[0]<=MAX_SEPARATION),None)
                if prev is not None and bars[t]["atr"] is not None:
                    p1=prev[0]
                    tol=MATCH_ATR*bars[t]["atr"]
                    neckline=max(x["high"] for x in bars[p1:pidx+1])
                    if abs(price-prev[1])<=tol and neckline-max(price,prev[1])>=MIN_NECKLINE_ATR*bars[t]["atr"]:
                        zone=next((x for x in reversed(bars[max(0,pidx-3):pidx+3])
                                   if x["vector"] in ("red","violet")),None)
                        candidate_w.append(dict(confirmed=t,expires=t+WINDOW_EXPIRY,
                            neckline=neckline,first=p1,second=pidx,
                            vector_zone_mid=(zone["high"]+zone["low"])/2 if zone else None))
                lows.append((pidx,price))
                lows=[q for q in lows if pidx-q[0]<=MAX_SEPARATION]
            else:
                prev=next((q for q in reversed(highs)
                           if MIN_SEPARATION<=pidx-q[0]<=MAX_SEPARATION),None)
                if prev is not None and bars[t]["atr"] is not None:
                    p1=prev[0]
                    tol=MATCH_ATR*bars[t]["atr"]
                    neckline=min(x["low"] for x in bars[p1:pidx+1])
                    if abs(price-prev[1])<=tol and min(price,prev[1])-neckline>=MIN_NECKLINE_ATR*bars[t]["atr"]:
                        candidate_m.append(dict(confirmed=t,expires=t+WINDOW_EXPIRY,
                            neckline=neckline,first=p1,second=pidx))
                highs.append((pidx,price))
                highs=[q for q in highs if pidx-q[0]<=MAX_SEPARATION]
        candidate_w=[w for w in candidate_w if w["expires"]>=t]
        candidate_m=[m for m in candidate_m if m["expires"]>=t]
        for w in list(candidate_w):
            if t>w["confirmed"] and bars[t-1]["close"]<=w["neckline"]<bars[t]["close"]:
                # A bearish-vector-zone midpoint may be reclaimed on/before breakout.
                # No future candle is needed to assert this by time t.
                vector_zone=w["vector_zone_mid"]
                bullish_vector=any(x["vector"] in ("green","blue")
                    for x in bars[max(0,t-8):t+1])
                vector_ok=(vector_zone is not None and bars[t]["close"]>=vector_zone) or bullish_vector
                patterns.append(dict(kind="W",time=t,known_at=bars[t]["time"]+dt.timedelta(minutes=15),
                                     first=w["first"],second=w["second"],neckline=w["neckline"],
                                     vector_ok=bool(vector_ok),has_bear_zone=vector_zone is not None))
                candidate_w.remove(w) # one signal per motif
        for m in list(candidate_m):
            if t>m["confirmed"] and bars[t-1]["close"]>=m["neckline"]>bars[t]["close"]:
                patterns.append(dict(kind="M",time=t,known_at=bars[t]["time"]+dt.timedelta(minutes=15),
                                     first=m["first"],second=m["second"],neckline=m["neckline"]))
                candidate_m.remove(m)
    return patterns


def candidates(bars):
    enrich_vector(bars)
    hours=completed_hourly(bars)
    days=full_daily(bars)
    motifs=pivot_motifs(bars)
    latest_hour=latest_day=None
    hidx=didx=0
    by_time={p["time"]:[] for p in motifs}
    for p in motifs:
        by_time[p["time"]].append(p)
    signals=[]
    m_exits=set()
    diagnostic=Counter()
    for t in sorted(by_time):
        at=bars[t]["time"]+dt.timedelta(minutes=15)
        if t+1>=len(bars) or bars[t+1]["time"]!=at:
            continue
        while hidx<len(hours) and hours[hidx]["end"]<=at:
            latest_hour=hours[hidx]
            hidx+=1
        while didx<len(days) and days[didx]["available"]<=at:
            latest_day=days[didx]
            didx+=1
        if latest_hour is None or latest_day is None:
            continue
        if (at-latest_hour["end"]).total_seconds()>5400:
            continue
        hour_trend=(latest_hour["ema50"] is not None and latest_hour["ema200"] is not None
                    and latest_hour["ema50"]>latest_hour["ema200"])
        day_trend=bool(latest_day["trend"])
        cycle=bool(latest_day["cycle"])
        elliott=bool(latest_day["elliott"])
        for p in by_time[t]:
            if p["kind"]=="M":
                m_exits.add(t+1)
                diagnostic["M_breakdowns"]+=1
                continue
            diagnostic["W_breakouts"]+=1
            vec=bool(p["vector_ok"])
            models=["WOnly"]
            if vec:
                models.append("WVector")
            if hour_trend:
                models.extend(["W1h","W1hMExit"])
            if day_trend:
                models.append("WDaily")
            if day_trend and cycle:
                models.append("WCycle")
            if day_trend and hour_trend and vec and (cycle or elliott):
                models.extend(["WFusion","WFusionMExit"])
            for name in models:
                diagnostic["signals_"+name]+=1
                signals.append(dict(model=name,index=t+1,signal_time=at.isoformat(),
                    motif_first=bars[p["first"]]["time"].isoformat(),
                    motif_second=bars[p["second"]]["time"].isoformat(),
                    vector=vec,hourly_trend=hour_trend,daily_trend=day_trend,
                    daily_cycle=cycle,daily_elliott=elliott))
    return signals,m_exits,dict(diagnostic),dict(days=len(days),hours=len(hours),
                             patterns=len(motifs),bars15m=len(bars))


def simulate(bars,signals,m_exits,model,cost=COST):
    # Same position sizing, fill rules, exit conditions and fees for all model arms.
    entry_indices={s["index"]:s for s in signals if s["model"]==model}
    cash=100000.
    qty=0.
    p=None
    trades=[]
    marks=[]
    max_dd=0.
    peak=100000.
    mexit=model.endswith("MExit")
    for i,x in enumerate(bars):
        exited_this_bar=False
        if p is not None:
            why=px=None
            if i in m_exits and mexit:
                why="confirmed_M_breakdown"
                px=x["open"]
            elif x["open"]<=p["stop"]:
                why="gap_stop"
                px=x["open"]
            elif x["open"]>=p["target"]:
                why="gap_target"
                px=x["open"]
            elif x["low"]<=p["stop"]:
                why="stop_first"
                px=p["stop"]
            elif x["high"]>=p["target"]:
                why="target"
                px=p["target"]
            elif i>=p["open_idx"]+MAX_HOLD:
                why="time_stop"
                px=x["close"]
            elif i==len(bars)-1:
                why="end_of_sample"
                px=x["close"]
            if why:
                proceeds=qty*px*(1-cost)
                pnl=proceeds-p["spent"]
                cash+=proceeds
                trades.append(dict(model=model,entry=str(bars[p["open_idx"]]["time"]),
                    exit=str(x["time"]),reason=why,pnl_usd=round(pnl,4),
                    r=round(pnl/(qty*p["risk_one"]),5),
                    initial_cost_usd=round(p["fee_entry"],4),
                    closing_cost_usd=round(qty*px*cost,4),
                    entry_usd=p["price"],exit_usd=px,
                    daily_cycle=p["signal"]["daily_cycle"],
                    daily_elliott=p["signal"]["daily_elliott"],
                    vector=p["signal"]["vector"]))
                qty=0
                p=None
                exited_this_bar=True
        if not exited_this_bar and qty==0 and p is None and i in entry_indices and i>0 and i<len(bars)-1:
            if bars[i]["time"]==bars[i-1]["time"]+dt.timedelta(minutes=15):
                signal=entry_indices[i]
                atr=bars[i-1]["atr"]
                if atr and atr>0:
                    open_px=x["open"]
                    stop=open_px-STOP_ATR_MULT*atr
                    risk_one=open_px*(1+cost)-stop*(1-cost)
                    if stop>0 and risk_one>0:
                        qty=min(cash/(open_px*(1+cost)),
                                MAX_LOSS_FRACTION*cash/risk_one)
                        if qty>0:
                            spent=qty*open_px*(1+cost)
                            cash-=spent
                            target=(open_px*(1+cost)+TARGET_R*risk_one)/(1-cost)
                            p=dict(open_idx=i,price=open_px,stop=stop,target=target,
                                spent=spent,fee_entry=qty*open_px*cost,
                                risk_one=risk_one,signal=signal)
                            # Entry bar is a valid intraday trade interval. Both
                            # levels touched => choose the stop first (pessimistic).
                            hit_stop=x["low"]<=stop
                            hit_target=x["high"]>=target
                            if hit_stop or hit_target:
                                fill=stop if hit_stop else target
                                reason="entry_bar_stop" if hit_stop else "entry_bar_target"
                                proceeds=qty*fill*(1-cost)
                                pnl=proceeds-p["spent"]
                                cash+=proceeds
                                trades.append(dict(model=model,entry=str(x["time"]),
                                    exit=str(x["time"]),reason=reason,
                                    pnl_usd=round(pnl,4),r=round(pnl/(qty*risk_one),5),
                                    initial_cost_usd=round(p["fee_entry"],4),
                                    closing_cost_usd=round(qty*fill*cost,4),
                                    entry_usd=open_px,exit_usd=fill,
                                    daily_cycle=signal["daily_cycle"],
                                    daily_elliott=signal["daily_elliott"],
                                    vector=signal["vector"]))
                                qty=0
                                p=None
        equity=cash+(qty*x["close"]*(1-cost) if qty>0 else 0.)
        peak=max(peak,equity)
        max_dd=min(max_dd,equity/peak-1)
        marks.append(dict(date=x["time"].date().isoformat(),
                          equity=equity,invested=int(qty>0)))
    winners=[t for t in trades if t["pnl_usd"]>0]
    losers=[t for t in trades if t["pnl_usd"]<0]
    overall=dict(model=model,cost_bps_each_leg=round(cost*10000),
            trades=len(trades),wins=len(winners),
            win_pct=round(100*len(winners)/len(trades),2) if trades else None,
            gross_profit=round(sum(t["pnl_usd"] for t in winners),2),
            gross_loss=round(-sum(t["pnl_usd"] for t in losers),2),
            profit_factor=round(sum(t["pnl_usd"] for t in winners)/
                -sum(t["pnl_usd"] for t in losers),3) if losers else None,
            mean_r=round(statistics.mean(t["r"] for t in trades),4) if trades else None,
            return_pct=round(100*(marks[-1]["equity"]/100000-1),3),
            max_mark_to_market_drawdown_pct=round(100*max_dd,3),
            exposure_pct=round(100*sum(x["invested"] for x in marks)/len(marks),2))
    yearly=[]
    # Calendar returns are calculated from end-of-period equity, without resets.
    for label,start,end in PERIODS:
        subset=[x for x in marks if start<=x["date"]<=end]
        if not subset: continue
        prev=next((x for x in reversed(marks) if x["date"]<start),None)
        equity_start=prev["equity"] if prev else 100000.
        pk=equity_start; dd=0.
        for row in subset:
            pk=max(pk,row["equity"])
            dd=min(dd,row["equity"]/pk-1)
        yearly.append(dict(model=model,cost_bps_each_leg=round(cost*10000),
            period=label,first=subset[0]["date"],last=subset[-1]["date"],
            return_pct=round(100*(subset[-1]["equity"]/equity_start-1),3),
            max_mark_to_market_drawdown_pct=round(100*dd,3),
            exposure_pct=round(100*sum(x["invested"] for x in subset)/len(subset),2),
            entries=sum(start<=t["entry"][:10]<=end for t in trades)))
    return overall,yearly,trades


def csv_out(path,rows):
    if not rows:
        path.write_text("NO OBSERVATIONS\n",encoding="utf-8")
        return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--years",type=int,nargs="+",default=list(range(2019,2027)))
    p.add_argument("--out",default="results_mw")
    args=p.parse_args()
    if any(y<2012 or y>2026 for y in args.years) or args.years!=list(range(args.years[0],args.years[-1]+1)):
        raise ValueError("Use contiguous published Bitstamp years only")
    out=Path(args.out)
    out.mkdir(exist_ok=True,parents=True)
    bars=[]
    sources=[]
    for year in args.years:
        raw,url=download_year(year)
        segment,coverage=aggregate_15m(raw,year)
        if bars and segment[0]["time"]!=bars[-1]["time"]+dt.timedelta(minutes=15):
            raise ValueError("Year boundary gap, cannot silently fabricate candles")
        bars+=segment
        sources.append(dict(year=year,url=url,compressed_sha256=hashlib.sha256(raw).hexdigest(),
                            first=str(segment[0]["time"]),last=str(segment[-1]["time"]),
                            coverage=coverage))
    signals,mexit,diag,shape=candidates(bars)
    summaries,periods,trades,stress=[],[],[],[]
    for name in MODES:
        s,y,t=simulate(bars,signals,mexit,name,cost=COST)
        summaries.append(s)
        periods+=y
        trades+=t
        for bp in (0,5,15,30):
            a,b,_=simulate(bars,signals,mexit,name,cost=bp/10000)
            stress.append(dict(model=name,cost_bps_each_leg=bp,
                               total_return_pct=a["return_pct"],
                               total_max_drawdown_pct=a["max_mark_to_market_drawdown_pct"],
                               total_trades=a["trades"],
                               **{"return_"+x["period"]+"_pct":x["return_pct"] for x in b}))
    csv_out(out/"summary.csv",summaries)
    csv_out(out/"chronological_periods.csv",periods)
    csv_out(out/"cost_sensitivity.csv",stress)
    csv_out(out/"trade_log.csv",trades)
    (out/"manifest.json").write_text(json.dumps(dict(
        model_version="CECS2.6-pre-registered-proxy-2026-11-22",
        source="Bitstamp BTC/USD minute archives, community mirrored",
        created_at_utc=dt.datetime.now(UTC).isoformat(),sources=sources,
        pattern=dict(pivot_left=4,pivot_right=CONFIRM_RIGHT,
                     separation_bars=[MIN_SEPARATION,MAX_SEPARATION],
                     tolerance_ATR=MATCH_ATR,min_neckline_ATR=MIN_NECKLINE_ATR,
                     expiry_bars=WINDOW_EXPIRY),
        trading=dict(initial_usd=100000,cost_bps_each_leg=15,
                     initial_risk_fraction=MAX_LOSS_FRACTION,
                     stop_atr=STOP_ATR_MULT,target_net_R=TARGET_R,
                     max_hold_15m_bars=MAX_HOLD),
        diagnostics=diag,shape=shape,
        disclaimer="Mechanically defined research, no true untouched holdout; prior 2024-2026 prices already studied, no live-trading approval"),indent=2),encoding="utf-8")
    print(json.dumps(dict(summary=summaries,periods=periods,diagnostics=diag,shape=shape),indent=2))


if __name__=="__main__":
    main()
