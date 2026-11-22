#!/usr/bin/env python3
"""CECS 2.2 Bitstamp BTC/USD intraday research PILOT.
15m/1h aggregated from exchange's 1-minute candles; NO live orders.
Vector/Cycle/Elliott are explicit research proxies, not proprietors' signals.
All signal calculations use CLOSED bars. Entry occurs at NEXT 15m open.
"""
import argparse
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
import statistics
import urllib.request
from collections import Counter
from pathlib import Path

from cecs_v2_1_runner import confirmed_pivots, wave_candidate, enrich

UTC = dt.timezone.utc
SOURCE = "https://raw.githubusercontent.com/alessiostomeo/btc-cycle-data/main/bitstamp/1min/BTCUSD_bitstamp_1min_{}.csv.gz"
COST = 0.0015  # cost on each leg, includes slippage assumption
MODES = ("Breakout", "BreakoutVector", "CycleVector", "ElliottVector", "AllConfluence")


def parse_time(s):
    t = dt.datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    return t.replace(tzinfo=UTC) if t.tzinfo is None else t.astimezone(UTC)


def download_year(year):
    url = SOURCE.format(year)
    req = urllib.request.Request(url, headers={"User-Agent": "CECS-open-research/2.2"})
    with urllib.request.urlopen(req, timeout=120) as response:
        payload = response.read()
    return payload, url


def aggregate_15m(compressed, year, minimum_coverage=0.95):
    # No missing candles are fabricated. Incomplete 15-minute windows are excluded.
    bars, total, bad, rejected = [], 0, 0, 0
    current = None
    last_t = None
    raw = gzip.GzipFile(fileobj=io.BytesIO(compressed))
    stream = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
    reader = csv.DictReader(stream)
    required = {"datetime_utc", "open", "high", "low", "close", "volume"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise ValueError("Unexpected 1-minute schema: " + str(reader.fieldnames))
    for row in reader:
        total += 1
        try:
            t = parse_time(row["datetime_utc"])
            o, h, l, c, v = (float(row[k]) for k in ("open", "high", "low", "close", "volume"))
            valid = t.year == year and t.second == 0 and t.microsecond == 0 and all(map(math.isfinite, (o,h,l,c,v))) and l > 0 and v >= 0 and h >= max(o,c,l) and l <= min(o,c)
        except (ValueError, TypeError, KeyError, OverflowError):
            valid = False
        if not valid:
            bad += 1
            continue
        bucket = t.replace(minute=t.minute // 15 * 15)
        if current is not None and current["time"] != bucket:
            if current["count"] == 15 and current["contiguous"]:
                current.pop("count")
                current.pop("contiguous")
                bars.append(current)
            else:
                rejected += 1
            current = None
        if current is None:
            current = dict(time=bucket, open=o, high=h, low=l, close=c, volume=v, count=0, contiguous=True)
        if last_t is not None and current["count"] > 0 and (t - last_t).total_seconds() != 60:
            current["contiguous"] = False
        current["count"] += 1
        current["high"] = max(current["high"], h)
        current["low"] = min(current["low"], l)
        current["close"] = c
        current["volume"] += v if current["count"] > 1 else 0
        last_t = t
    if current is not None:
        if current["count"] == 15 and current["contiguous"]:
            current.pop("count")
            current.pop("contiguous")
            bars.append(current)
        else:
            rejected += 1
    if not bars:
        raise ValueError("No complete 15m bars for " + str(year))
    expected = 96 * (366 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 365)
    # Current calendar year may be partial. Measure coverage only between observed min/max.
    observed_span = round((bars[-1]["time"] - bars[0]["time"]).total_seconds() / 900) + 1
    coverage = len(bars) / observed_span
    if coverage < minimum_coverage:
        raise ValueError("Coverage below threshold: " + str(year) + " " + str(round(coverage, 4)))
    return bars, dict(year=year, source_rows=total, invalid_rows=bad, incomplete_15m=rejected,
                      valid_15m=len(bars), observed_15m_span=observed_span,
                      coverage_pct=round(100*coverage, 3), full_calendar_year=observed_span >= expected - 96)


def enrich_vector(bars):
    for i, x in enumerate(bars):
        prev = bars[i-1]["close"] if i else x["close"]
        x["tr"] = max(x["high"]-x["low"], abs(x["high"]-prev), abs(x["low"]-prev))
        x["atr"] = statistics.mean(z["tr"] for z in bars[i-13:i+1]) if i >= 13 else None
        if i < 10:
            x["vector"] = "ordinary"
            continue
        sample = bars[i-10:i]
        avg_v = statistics.mean(y["volume"] for y in sample)
        top = max(y["volume"]*(y["high"]-y["low"]) for y in sample)
        climax = avg_v > 0 and x["volume"] > 0 and (x["volume"] >= 2*avg_v or x["volume"]*(x["high"]-x["low"]) >= top)
        elevated = avg_v > 0 and x["volume"] > 0 and not climax and x["volume"] >= 1.5*avg_v
        up = x["close"] > x["open"]
        x["vector"] = ("green" if up else "red") if climax else ("blue" if up else "violet") if elevated else "ordinary"


def completed_hourly(bars):
    hourly, group = [], []
    for x in bars:
        start = x["time"].replace(minute=0)
        if group and group[0]["time"].replace(minute=0) != start:
            if len(group) == 4 and [a["time"].minute for a in group] == [0,15,30,45]:
                hourly.append(dict(end=start, open=group[0]["open"],
                                   high=max(z["high"] for z in group), low=min(z["low"] for z in group),
                                   close=group[-1]["close"], volume=sum(z["volume"] for z in group)))
            group = []
        group.append(x)
    # Last incomplete hourly period is never used.
    ema50, ema200 = None, None
    for i, h in enumerate(hourly):
        ema50 = h["close"] if ema50 is None else (2/51)*h["close"]+(49/51)*ema50
        ema200 = h["close"] if ema200 is None else (2/201)*h["close"]+(199/201)*ema200
        h["ema50"] = ema50 if i >= 49 else None
        h["ema200"] = ema200 if i >= 199 else None
    return hourly


def completed_daily(bars):
    days, group = [], []
    for x in bars:
        date = x["time"].date()
        if group and group[0]["time"].date() != date:
            if len(group) == 96:
                d = dict(date=group[0]["time"].date(), open=group[0]["open"],
                         high=max(z["high"] for z in group), low=min(z["low"] for z in group),
                         close=group[-1]["close"], volume=sum(z["volume"] for z in group))
                days.append(d)
            group=[]
        group.append(x)
    # Only days with all 96 15m candles; may lose some edge days.
    enrich(days)
    events=confirmed_pivots(days, 7, 3)
    swings, anchor, result=[],None,[]
    for known, arr in enumerate(events):
        for kind, i, price in arr:
            if swings and swings[-1][0]==kind:
                if (kind=="L" and price<swings[-1][2]) or (kind=="H" and price>swings[-1][2]):
                    swings[-1]=(kind,i,price)
            else:
                swings.append((kind,i,price))
            swings=swings[-24:]
            if kind!="L":
                continue
            gap=i-anchor if anchor is not None else None
            cycle=False
            if gap is None or gap>=45:
                cycle=gap is not None and gap<=85
                anchor=i
            wave=wave_candidate(swings, days) is not None
            # Known ONLY after close of confirming daily candle, at next UTC midnight.
            known_at=dt.datetime.combine(days[known]["date"]+dt.timedelta(days=1),dt.time.min,tzinfo=UTC)
            result.append(dict(known_at=known_at, cycle=cycle, elliott=wave))
    return result, days


def vector_condition(bars, i):
    recent = bars[max(0,i-3):i+1]   # includes current CLOSED 15m candle
    bullish=any(z["vector"] in ("green","blue") for z in recent)
    if bullish:
        return True, "bull_vector"
    prev = next((z for z in reversed(bars[max(0,i-96):i]) if z["vector"] in ("red","violet")),None)
    if prev is not None and i > 0:
        mid=(prev["high"]+prev["low"])/2
        if bars[i-1]["close"] < mid <= bars[i]["close"]:
            return True, "bear_vector_mid_reclaim"
    return False, "none"


def signals_from_bars(bars):
    enrich_vector(bars)
    hourly=completed_hourly(bars)
    cycle_events,days=completed_daily(bars)
    signals=[]
    hidx=eidx=0
    hour=last_cycle=last_elliott=None
    by_model=Counter()
    for i in range(210,len(bars)-1):
        at=bars[i]["time"]+dt.timedelta(minutes=15)
        while hidx<len(hourly) and hourly[hidx]["end"]<=at:
            hour=hourly[hidx]
            hidx+=1
        while eidx<len(cycle_events) and cycle_events[eidx]["known_at"]<=at:
            event=cycle_events[eidx]
            if event["cycle"]:
                last_cycle=event["known_at"]
            if event["elliott"]:
                last_elliott=event["known_at"]
            eidx+=1
        if hour is None or hour["ema50"] is None or hour["ema200"] is None:
            continue
        # Hourly context may not be stale due to missing bars.
        if (at-hour["end"]).total_seconds()>5400:
            continue
        if not hour["ema50"]>hour["ema200"]:
            continue
        if bars[i]["close"]<=max(z["high"] for z in bars[i-8:i]):
            continue
        if bars[i+1]["time"]!=at:
            continue
        if not bars[i]["atr"]:
            continue
        vec,reason=vector_condition(bars,i)
        cycle=last_cycle is not None and (at-last_cycle).days<=30
        elliott=last_elliott is not None and (at-last_elliott).days<=30
        models=["Breakout"]
        if vec:
            models.append("BreakoutVector")
            if cycle:
                models.append("CycleVector")
            if elliott:
                models.append("ElliottVector")
            if cycle and elliott:
                models.append("AllConfluence")
        for model in models:
            by_model[model]+=1
            signals.append(dict(model=model, index=i+1, signal_at=at, vector_reason=reason,
                                cycle=int(cycle), elliott=int(elliott)))
    return signals,{"candles_15m": len(bars), "complete_1h": len(hourly), "complete_1d": len(days),
                    "events": len(cycle_events), "by_model": dict(by_model),
                    "vectors": dict(Counter(z["vector"] for z in bars))}


def simulate(bars, candidate, model, year, cost=COST):
    entries={x["index"]:x for x in candidate if x["model"]==model}
    cash=100000.0
    position=None
    daily_equity=[]
    peak=100000.0
    maxdd=0.0
    trades=[]
    for i,x in enumerate(bars):
        # New entries use the previous, already closed 15m signal.
        if position is None and i in entries:
            if i < len(bars)-1 and x["time"].year==year and bars[i-1]["time"]+dt.timedelta(minutes=15)==x["time"]:
                atr=bars[i-1]["atr"]
                if atr and atr>0:
                    opening=x["open"]
                    stop=opening-1.5*atr
                    entry_net=opening*(1+cost)
                    stop_net=stop*(1-cost)
                    risk=entry_net-stop_net
                    if stop>0 and risk>0:
                        qty=min(cash*.0025/risk,cash/entry_net)
                        if qty>0:
                            target=(entry_net+2*risk)/(1-cost)
                            position=dict(opened=i, signal=entries[i], entry=opening,
                                          net_entry=entry_net,stop=stop,target=target,
                                          qty=qty,risk=risk,elapsed=0)
        if position is not None:
            p=position
            # No speculative best-case ordering when both hit. Stop always first.
            if x["open"]<=p["stop"]:
                ex,why=x["open"],"gap_stop"
            elif x["open"]>=p["target"]:
                ex,why=x["open"],"gap_target"
            elif x["low"]<=p["stop"]:
                ex,why=p["stop"],"stop"
            elif x["high"]>=p["target"]:
                ex,why=p["target"],"target"
            elif p["elapsed"]>=95:
                ex,why=x["close"],"time_96_bars"
            elif i==len(bars)-1:
                ex,why=x["close"],"period_end"
            else:
                ex,why=None,None
            if ex is not None:
                pnl=p["qty"]*(ex*(1-cost)-p["net_entry"])
                cash+=pnl
                trades.append(dict(year=year,model=model,entry_time=bars[p["opened"]]["time"].isoformat(),
                                   exit_time=x["time"].isoformat(),entry_px=p["entry"],exit_px=ex,
                                   realized_r=round(pnl/(p["qty"]*p["risk"]),6),
                                   pnl_usd=round(pnl,2),outcome=why,
                                   vector_reason=p["signal"]["vector_reason"],
                                   cycle=p["signal"]["cycle"],elliott=p["signal"]["elliott"]))
                position=None
            else:
                p["elapsed"]+=1
        equity=cash if position is None else cash+position["qty"]*(x["close"]*(1-cost)-position["net_entry"])
        peak=max(peak,equity)
        maxdd=min(maxdd,equity/peak-1)
        daily_equity.append((x["time"],equity))
    winners=[z for z in trades if z["pnl_usd"]>0]
    gains=sum(max(z["pnl_usd"],0) for z in trades)
    losses=-sum(min(z["pnl_usd"],0) for z in trades)
    return dict(year=year,model=model,trades=len(trades),
                win_pct=round(100*len(winners)/len(trades),2) if trades else None,
                mean_r=round(statistics.mean(z["realized_r"] for z in trades),4) if trades else None,
                return_pct=round(100*(cash/100000-1),4) if trades else None,
                mtm_max_dd_pct=round(100*maxdd,4),
                profit_factor=round(gains/losses,4) if losses else None),trades


def write_csv(path, records):
    if not records:
        path.write_text("EMPTY\n",encoding="utf-8")
        return
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--years",type=int,nargs="+",default=[2024,2025,2026])
    ap.add_argument("--out",default="results_intraday")
    ap.add_argument("--local-dir",default=None)
    a=ap.parse_args()
    out=Path(a.out)
    out.mkdir(exist_ok=True,parents=True)
    manifest=dict(source_pattern=SOURCE,exchange="Bitstamp",pair="BTC/USD",
                  rules="15m vector+1h trend; cycle/Elliott optional annotations, no optimizer",
                  fee_slippage_per_leg=COST,
                  years=[],notes=["Full 15m bar closed before signal","Next 15m open entry",
                                   "Incomplete/missing minute bars discarded","Only historical, no forward performance claim"])
    summaries,trades,diagnostics,sensitivity=[],[],[],[]
    for year in a.years:
        if a.local_dir:
            p=Path(a.local_dir)/("BTCUSD_bitstamp_1min_%s.csv.gz"%year)
            compressed=p.read_bytes()
            url=str(p)
        else:
            compressed,url=download_year(year)
        bars,diagnostic=aggregate_15m(compressed,year)
        candidates,detail=signals_from_bars(bars)
        diagnostic.update(detail)
        diagnostics.append(diagnostic)
        manifest["years"].append(dict(year=year,url=url,gzip_sha256=hashlib.sha256(compressed).hexdigest(),
                                       earliest=str(bars[0]["time"]),latest=str(bars[-1]["time"])))
        for model in MODES:
            summary,records=simulate(bars,candidates,model,year)
            summaries.append(summary)
            trades.extend(records)
            sensitivity.append({"cost_bps_each_leg": 15, **summary})
            for basis_points in (0, 5):
                scenario,_=simulate(bars,candidates,model,year,cost=basis_points/10000)
                sensitivity.append({"cost_bps_each_leg": basis_points, **scenario})
    write_csv(out/"intraday_summary.csv",summaries)
    write_csv(out/"intraday_sensitivity.csv",sensitivity)
    write_csv(out/"intraday_trades.csv",trades)
    write_csv(out/"intraday_coverage.csv",diagnostics)
    (out/"intraday_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(dict(summary=summaries,coverage=diagnostics),indent=2,default=str))


if __name__=="__main__":
    main()
