#!/usr/bin/env python3
"""CECS 2.5: forward-only VIRTUAL BTC/USD paper ledger.

No broker connection, no real trading, no historical next-open backfills.
Runs once per UTC day AFTER daily_watch.py has saved the observation.
A prospective BUY intent is not fillable until at least the NEXT UTC DATE,
and is then priced at a fresh, timestamped Bitstamp bid/ask snapshot.
A "fill" is an assumption with stated costs, not an exchange execution.
Stops are checked ONLY at daily quote observations; overnight/intraday
stop touches are not fully captured. Not a brokerage-realistic backtest.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import urllib.request
from pathlib import Path

VERSION="CECS-2.5-FORWARD-PAPER-2026-11-22"
MODEL="TrendCycleWide6Delayed"
TICKER_URL="https://www.bitstamp.net/api/v2/ticker/btcusd/"
START_CASH_USD=100000.0
COST_LEG=0.0015  # 15 bps including assumed trading friction
RISK_FRACTION=0.005
ATR_STOP=6.0
COOLDOWN_DAYS=10
MAX_QUOTE_AGE_SEC=180


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


def initial_state():
    return {
        "version":VERSION,"model":MODEL,"started_utc_date":"2026-11-22",
        "initial_cash_usd":START_CASH_USD,"cash_usd":START_CASH_USD,
        "qty_btc":0.0,"entry_usd":None,"entry_at":None,"entry_cost_usd":None,
        "stop_usd":None,"highest_completed_daily_high":None,
        "last_trailing_source_day":None,"pending":None,"last_exit_date":None,
        "processed_dates":[],"realized_pnl_usd":0.0,"closed_trades":0,
    }


def fetch_quote(now=None, raw=None):
    now=now or utcnow()
    if raw is None:
        request=urllib.request.Request(TICKER_URL,headers={
            "User-Agent":"CECS-2.5-forward-paper-no-orders/1.0",
            "Accept":"application/json"})
        with urllib.request.urlopen(request,timeout=25) as resp:
            raw=resp.read()
    obj=json.loads(raw)
    if not isinstance(obj,dict):
        raise ValueError("Invalid ticker response")
    ask=float(obj["ask"])
    bid=float(obj["bid"])
    epoch=float(obj["timestamp"])
    if not all(math.isfinite(x) for x in (ask,bid,epoch)) or ask<=0 or bid<=0 or bid>ask:
        raise ValueError("Invalid quote")
    if (ask-bid)/bid>0.02:
        raise ValueError("Suspiciously wide bid-ask spread")
    quote_time=dt.datetime.fromtimestamp(epoch,dt.timezone.utc)
    age=(now-quote_time).total_seconds()
    if age < -15 or age>MAX_QUOTE_AGE_SEC:
        raise ValueError("Stale or future exchange quote: age %.1fs" % age)
    return dict(
        source=TICKER_URL,exchange="Bitstamp",symbol="BTC/USD",
        exchange_timestamp_utc=quote_time.isoformat(),
        captured_at_utc=now.isoformat(),age_seconds=round(age,2),
        bid_usd=bid,ask_usd=ask,
        quote_sha256=hashlib.sha256(raw if isinstance(raw,bytes) else raw.encode()).hexdigest()
    )


def iso_day(x):
    return dt.date.fromisoformat(x)


def process(state,observation,quote,now):
    """Pure, deterministic daily transition. No network/files.
    All decisions use today's timestamped observation and quote only.
    """
    current=now.date()
    day=current.isoformat()
    if observation.get("recorded_utc_date")!=day:
        raise ValueError("Observation date does not match capture date")
    if observation.get("model")!=MODEL or not observation.get("candidate_only"):
        raise ValueError("Observation uses unexpected research model")
    if iso_day(observation["source_last_completed_day"])>=current:
        raise ValueError("Incomplete or future daily bar in observation")
    source_age=(current-iso_day(observation["source_last_completed_day"])).days
    if source_age>2:
        raise ValueError("Source too stale for paper monitor")
    if quote["exchange"]!="Bitstamp" or quote["symbol"]!="BTC/USD":
        raise ValueError("Wrong exchange or market")
    quote_time=dt.datetime.fromisoformat(quote["exchange_timestamp_utc"])
    if quote_time>now or (now-quote_time).total_seconds()>MAX_QUOTE_AGE_SEC:
        raise ValueError("Exchange quote outdated at state transition")
    if day in state["processed_dates"]:
        raise ValueError("Duplicate day; never double-apply a quote")
    if state["processed_dates"] and day<=state["processed_dates"][-1]:
        raise ValueError("Out-of-order day; cannot rewrite history")
    if state["version"]!=VERSION or state["model"]!=MODEL:
        raise ValueError("Frozen model mismatch")
    result=copy.deepcopy(state)
    events=[]
    bid=quote["bid_usd"]
    ask=quote["ask_usd"]
    fresh_features=source_age==1
    exited=False
    if result["qty_btc"]>0:
        trigger=None
        if bid<=result["stop_usd"]:
            trigger="observed_bid_below_stop"
        elif fresh_features and not observation["trend_gate"]:
            trigger="published_trend_gate_off"
        if trigger:
            qty=result["qty_btc"]
            net_proceeds=qty*bid*(1-COST_LEG)
            result["cash_usd"]+=net_proceeds
            pnl=net_proceeds-result["entry_cost_usd"]
            result["realized_pnl_usd"]+=pnl
            result["closed_trades"]+=1
            events.append(dict(type="virtual_sell",reason=trigger,
                bid_usd=bid,qty_btc=qty,cost_usd=qty*bid*COST_LEG,
                pnl_usd=round(pnl,4),original_entry_at=result["entry_at"]))
            for k in ("qty_btc","entry_usd","entry_at","entry_cost_usd","stop_usd",
                      "highest_completed_daily_high","last_trailing_source_day"):
                result[k]=0.0 if k=="qty_btc" else None
            result["last_exit_date"]=day
            exited=True
        elif fresh_features and (result["last_trailing_source_day"] is None or
                                 observation["source_last_completed_day"]>result["last_trailing_source_day"]):
            # Use a daily HIGH only from a date starting on/after the entry date.
            # On the first observation after entry, the previous FULL day is known.
            entry_day=result["entry_at"][:10]
            if observation["source_last_completed_day"]>=entry_day:
                high=float(observation["source_high"])
                atr=float(observation["atr14"])
                result["highest_completed_daily_high"]=max(
                    result["highest_completed_daily_high"] or high,high)
                proposed=result["highest_completed_daily_high"]-ATR_STOP*atr
                if math.isfinite(proposed) and proposed>result["stop_usd"]:
                    prior=result["stop_usd"]
                    result["stop_usd"]=proposed
                    events.append(dict(type="virtual_stop_update",
                        former_stop_usd=round(prior,4),
                        new_stop_usd=round(proposed,4),
                        effective_at_next_observation=True))
                result["last_trailing_source_day"]=observation["source_last_completed_day"]

    if result["qty_btc"]==0 and result["pending"] is not None:
        p=result["pending"]
        execute_date=iso_day(p["not_before_utc_date"])
        if current>=execute_date:
            why=None
            if current!=execute_date:
                why="intent_expired"
            elif not fresh_features:
                why="daily_source_not_fresh"
            elif exited:
                why="same_day_exit"
            elif not observation["trend_gate"]:
                why="trend_off_before_entry"
            elif result["last_exit_date"] is not None and (current-iso_day(result["last_exit_date"])).days<=COOLDOWN_DAYS:
                why="cooldown"
            if why:
                events.append(dict(type="intent_cancelled",reason=why,origin=p))
            else:
                # Assume marketable paper BUY at current ASK; additionally charge cost.
                at_ask=ask*(1+COST_LEG)
                atr=float(p["atr14_at_signal"])
                stop=ask-ATR_STOP*atr
                effective_stop=stop*(1-COST_LEG)
                net_risk_one=at_ask-effective_stop
                equity=result["cash_usd"]
                if stop<=0 or net_risk_one<=0:
                    events.append(dict(type="intent_cancelled",reason="invalid_stop",origin=p))
                else:
                    qty=min(result["cash_usd"]/at_ask,
                            equity*RISK_FRACTION/net_risk_one)
                    if qty<=0 or not math.isfinite(qty):
                        events.append(dict(type="intent_cancelled",reason="invalid_size",origin=p))
                    else:
                        total=qty*at_ask
                        result["cash_usd"]-=total
                        result["qty_btc"]=qty
                        result["entry_usd"]=ask
                        result["entry_at"]=now.isoformat()
                        result["entry_cost_usd"]=total
                        result["stop_usd"]=stop
                        result["highest_completed_daily_high"]=None
                        result["last_trailing_source_day"]=None
                        events.append(dict(type="virtual_buy",reason="prior_day_intent",
                            ask_usd=ask,qty_btc=qty,stop_usd=stop,
                            cost_usd=qty*ask*COST_LEG,
                            initial_nominal_risk_usd=qty*net_risk_one,
                            initial_risk_frac=round(qty*net_risk_one/equity,8),
                            origin=p))
            result["pending"]=None
    # A new entry may be QUEUED, but never traded today, and not after exit.
    if result["qty_btc"]==0 and result["pending"] is None and not exited:
        cooldown=(result["last_exit_date"] is None or
                  (current-iso_day(result["last_exit_date"])).days>COOLDOWN_DAYS)
        if fresh_features and cooldown and observation.get("candidate_entry_gate"):
            pending=dict(
                signal_recorded_utc_day=day,
                source_day=observation["source_last_completed_day"],
                not_before_utc_date=(current+dt.timedelta(days=1)).isoformat(),
                atr14_at_signal=float(observation["atr14"]),
                evidence_source_sha256=observation["source_sha256"],
                strategy_source_sha256=observation["strategy_source_sha256"])
            if pending["atr14_at_signal"]>0:
                result["pending"]=pending
                events.append(dict(type="virtual_buy_intent_queued",
                                   reason="trend_and_confirmed_cycle",intent=pending))
    result["processed_dates"].append(day)
    equity=result["cash_usd"]+result["qty_btc"]*bid*(1-COST_LEG)
    audit=dict(
        recorded_utc=now.isoformat(),utc_date=day,
        closed_day=observation["source_last_completed_day"],
        feature_age_days=source_age,
        exchange_quote=quote,
        strategy_version=VERSION,model=MODEL,
        observed_gate=bool(observation["candidate_entry_gate"]),
        events=events or [dict(type="no_action")],
        paper_cash_usd=round(result["cash_usd"],4),
        paper_qty_btc=round(result["qty_btc"],10),
        paper_equity_usd=round(equity,4),
        paper_stop_usd=round(result["stop_usd"],4) if result["stop_usd"] is not None else None,
        realized_pnl_usd=round(result["realized_pnl_usd"],4),
        pending_intent=result["pending"],
        warning="Virtual trade assumptions at sampled ticker quotes. NOT real fills. Daily monitoring misses intra-day stops; simulated risk can exceed nominal 0.5%."
    )
    return result,audit


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--watch",default="paper_watch")
    p.add_argument("--out",default="paper_execution")
    args=p.parse_args()
    now=utcnow()
    day=now.date().isoformat()
    dest=Path(args.out)
    audit_path=dest/"observations"/(day+".json")
    if audit_path.exists():
        print(json.dumps({"status":"already_recorded","path":str(audit_path)}))
        return
    obs=json.loads((Path(args.watch)/(day+".json")).read_text())
    state_path=dest/"state.json"
    state=json.loads(state_path.read_text()) if state_path.exists() else initial_state()
    quote=fetch_quote(now=now)
    new_state,audit=process(state,obs,quote,now)
    audit_path.parent.mkdir(parents=True,exist_ok=True)
    # Write audit first, then derived current state; commit both atomically in Git.
    audit_path.write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n")
    state_path.write_text(json.dumps(new_state,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":"observation_written","path":str(audit_path),
                      "paper_equity_usd":audit["paper_equity_usd"],
                      "events":audit["events"]},indent=2))


if __name__=="__main__":
    main()
