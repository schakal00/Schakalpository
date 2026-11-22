#!/usr/bin/env python3
"""Prospective indicator OBSERVATION journal, no orders and no asserted fills.

Evaluates available public daily Bitstamp close data AFTER its publication.
Its labels are not executable next-open signals. Designed to preserve an
unmodified, dated evidence record for later analysis.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

from cecs_v2_1_runner import URL, fetch_data, parse_data
from cecs_v2_3_trend import indicators, backtest, entry_gate

MODEL="TrendCycleWide6Delayed"
FROZEN_VERSION="CECS-2.4-observation-2026-11-22"
FEE_SLIPPAGE_BPS_EACH_LEG=15


def snapshot(data, today, source_sha, code_sha):
    # Supply only completed bars as-of collection time.
    complete=[x for x in data if x["date"]<today]
    if len(complete)<600:
        raise ValueError("Not enough completed historical bars")
    latest=complete[-1]
    delay=(today-latest["date"]).days
    if delay>2 or delay<1:
        raise ValueError("Stale or future-dated source (last closed day=%s, today=%s)"%(latest["date"],today))
    indicators(complete)
    feature=complete[-1]
    history, equity, trades, state=backtest(complete,MODEL,force_close_end=False,return_state=True)
    already_in_position=state["quantity"]>0
    # This is a *screen*, not an order: there is still a trading day between
    # data publication and delayed execution, and its future bar is unknown.
    qualifies=entry_gate(feature,MODEL)
    return {
        "version":FROZEN_VERSION,
        "recorded_utc_date":today.isoformat(),
        "source_last_completed_day":str(feature["date"]),
        "execution_date_if_gate_persists":str(feature["date"]+dt.timedelta(days=2)),
        "candidate_only":True,
        "not_a_trade_or_fill":True,
        "no_actual_paper_fills_recorded":True,
        "source_url":URL,
        "source_sha256":source_sha,
        "strategy_source_sha256":code_sha,
        "model":MODEL,
        "assumed_cost_bps_each_leg":FEE_SLIPPAGE_BPS_EACH_LEG,
        "source_close":round(feature["close"],4),
        "source_high":round(feature["high"],4),
        "atr14":round(feature["atr"],4) if feature["atr"] is not None else None,
        "sma50":round(feature["sma50"],4) if feature["sma50"] is not None else None,
        "sma200":round(feature["sma200"],4) if feature["sma200"] is not None else None,
        "trend_gate":bool(feature["trend"]),
        "confirmed_cycle_proxy":bool(feature["cycle"]),
        "elliott_wave2_proxy":bool(feature["elliott"]),
        "vector_proxy_confirmed":bool(feature["vector_confirmed"]),
        "confluence_score":feature["score"],
        "candidate_entry_gate":bool(qualifies),
        "historically_reconstructed_open_position":bool(already_in_position),
        "historically_reconstructed_position_quantity":round(state["quantity"],8),
        "historically_reconstructed_stop":round(state["stop"],4) if state["stop"] is not None else None,
        "historically_reconstructed_cash_usd":round(state["cash"],4),
        "interpretation":"A historical-model STATE snapshot + prospectively timestamped gate; NOT an actual order, fill or paper P&L. Reconstructing future performance from this alone is invalid.",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="paper_watch")
    p.add_argument("--date",default=None,help="UTC recording date, for offline tests")
    p.add_argument("--csv",default=None)
    p.add_argument("--allow-stale",action="store_true",help="Only for LOCAL debugging; does not bypass snapshot guard")
    args=p.parse_args()
    today=dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(dt.timezone.utc).date()
    target=Path(args.out)/(today.isoformat()+".json")
    if target.exists():
        print(json.dumps({"status":"already_recorded","path":str(target)}))
        return
    payload=fetch_data(args.csv)
    data=parse_data(payload)
    code_sha=hashlib.sha256(Path(__file__).with_name("cecs_v2_3_trend.py").read_bytes()).hexdigest()
    item=snapshot(data,today,hashlib.sha256(payload).hexdigest(),code_sha)
    output=Path(args.out)
    output.mkdir(parents=True,exist_ok=True)
    target=output/(today.isoformat()+".json")
    if target.exists():
        raise FileExistsError("Concurrent duplicate observation: "+str(target))
    target.write_text(json.dumps(item,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"saved":str(target),"observation":item},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
