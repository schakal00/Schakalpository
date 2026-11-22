#!/usr/bin/env python3
"""CECS 3.0 DEFENSIVE: independent, frozen, PROSPECTIVE virtual paper account.

No real orders. No broker keys. NO historical profits imported.
Each UTC day at >=09:00, use daily OHLCV only through D-2 to produce
target BTC allocation and evaluate against fresh Bitstamp BTC/USD BID/ASK.

The backtest execution proxy is the 09:00 15m open, while these future
virtual executions use a later sampled BID/ASK. Different price models
are disclosed; quote-based journal is not an exchange order fill.

Long BTC/USD spot <=25% account equity, rest USD, no borrowing/shorting.
Costs: 15 bps virtual fees/slippage PER executed side in addition to
actual observed BID/ASK spread. No intraday stop / guaranteed drawdown cap.
"""
import copy
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

from cecs_v2_1_runner import fetch_data, parse_data, URL as OHLCV_URL
from cecs_v2_7_slow import prepare
from cecs_v3_0_strategy import add_derived_features, declared_weight
from paper_engine import fetch_quote, utcnow

VERSION="CECS-3.0-DEFENSIVE-FORWARD-2026-11-22"
STRATEGY="CECS3_Defensive"
INITIAL=100000.
FEE_FRACTION=.0015
MIN_WEIGHT_CHANGE=.03


def initial_state(strategy_sha):
    return dict(version=VERSION,strategy=STRATEGY,
                frozen_strategy_sha256=strategy_sha,
                started_utc_date="2026-11-22",cash_usd=INITIAL,
                btc_quantity=0.,all_virtual_orders=0,
                observed_peak_equity_usd=INITIAL,
                max_observed_drawdown_pct=0.,
                processed_dates=[])


def collect_snapshot(payload,today):
    rows=[x for x in parse_data(payload) if x["date"]<today]
    if len(rows)<600:
        raise ValueError("Not enough daily BTC/USD OHLCV")
    if rows[-1]["date"]!=today-dt.timedelta(days=1):
        raise ValueError("Daily data not updated for yesterday: fail closed")
    prepared=add_derived_features(prepare(rows))
    known=prepared[-2]
    if known["date"]!=today-dt.timedelta(days=2):
        raise ValueError("Unexpected history gap / source publication lag")
    allocation=declared_weight(known,STRATEGY)
    return dict(
        observed_on_utc_day=today.isoformat(),
        most_recent_complete_utc_day=str(prepared[-1]["date"]),
        last_actionable_signal_day=str(known["date"]),
        source_url=OHLCV_URL,
        source_sha256=hashlib.sha256(payload).hexdigest(),
        actionable_features=dict(close_usd=round(known["close"],4),
            sma50=round(known["sma50"],4),
            sma200=round(known["sma200"],4),
            realized_vol30=round(known["annualized_realized_vol30"],6),
            close_below_sma50=bool(known["under_sma50"]),
            trend_regime=bool(known["trend"]),
            cycle_proxy=bool(known["cycle"]),
            vector_proxy=bool(known["vector_confirmed"])),
        desired_btc_weight=allocation
    )


def advance(state,snapshot,quote,now,source_sha):
    current=now.date()
    day=current.isoformat()
    if now.tzinfo is None or now.utcoffset()!=dt.timedelta():
        raise ValueError("UTC now required")
    if state["version"]!=VERSION or state["strategy"]!=STRATEGY:
        raise ValueError("Paper model version mismatch")
    if state["frozen_strategy_sha256"]!=source_sha:
        raise ValueError("Strategy source was changed after paper account was frozen")
    if day in state["processed_dates"] or (state["processed_dates"] and day<=state["processed_dates"][-1]):
        raise ValueError("Duplicate / backdated observation")
    if snapshot["observed_on_utc_day"]!=day or snapshot["last_actionable_signal_day"]!=(current-dt.timedelta(days=2)).isoformat():
        raise ValueError("Improper 2-day signal lag")
    if snapshot["most_recent_complete_utc_day"]!=(current-dt.timedelta(days=1)).isoformat():
        raise ValueError("Stale daily source")
    if quote["exchange"]!="Bitstamp" or quote["symbol"]!="BTC/USD":
        raise ValueError("Wrong market")
    bid=float(quote["bid_usd"])
    ask=float(quote["ask_usd"])
    at=dt.datetime.fromisoformat(quote["exchange_timestamp_utc"])
    if at.tzinfo is None or bid<=0 or ask<bid or not all(map(math.isfinite,(bid,ask))):
        raise ValueError("Invalid exchange quote")
    if (now-at).total_seconds()>180 or (at-now).total_seconds()>15:
        raise ValueError("Stale / future quote")
    desired=float(snapshot["desired_btc_weight"])
    if not (0<=desired<=.25 and math.isfinite(desired)):
        raise ValueError("Overweight / invalid CECS3 allocation")
    revised=copy.deepcopy(state)
    cash=float(revised["cash_usd"])
    qty=float(revised["btc_quantity"])
    gross=cash+qty*bid
    current_weight=qty*bid/gross if gross>0 else 0.
    if gross<=0 or cash < -1e-6 or qty<0:
        raise ValueError("Invalid virtual balance")
    diff=desired-current_weight
    is_monday=current.weekday()==0
    # Strictly no ad-hoc buying before weekly Monday risk review.
    do_rebalance=(is_monday and abs(diff)>=MIN_WEIGHT_CHANGE) or (
        desired<current_weight-MIN_WEIGHT_CHANGE)
    event=dict(type="NO_ACTION")
    if do_rebalance:
        delta=desired*gross-qty*bid
        if delta>0 and is_monday:
            units=min(max(0.,cash)/(ask*(1+FEE_FRACTION)),
                      delta/(ask*(1+FEE_FRACTION)))
            if units>1e-12:
                fees=units*ask*FEE_FRACTION
                qty+=units
                cash-=units*ask+fees
                event=dict(type="SIMULATED_BUY",side="ask",price_usd=ask,
                    units_btc=round(units,10),estimated_cost_usd=round(fees,5),
                    assumed_execution_utc=now.isoformat())
        elif delta<0:
            units=min(qty,-delta/bid)
            if units>1e-12:
                fees=units*bid*FEE_FRACTION
                qty-=units
                cash+=units*bid-fees
                event=dict(type="SIMULATED_SELL",side="bid",price_usd=bid,
                    units_btc=round(units,10),estimated_cost_usd=round(fees,5),
                    assumed_execution_utc=now.isoformat())
    if cash<-1e-6 or qty<-1e-10:
        raise ValueError("No leverage / negative balances allowed")
    revised["cash_usd"]=cash
    revised["btc_quantity"]=qty
    if event["type"]!="NO_ACTION":
        revised["all_virtual_orders"]+=1
    equity=cash+qty*bid*(1-FEE_FRACTION)
    peak=max(revised["observed_peak_equity_usd"],equity)
    observed_dd=100*(equity/peak-1)
    revised["observed_peak_equity_usd"]=peak
    revised["max_observed_drawdown_pct"]=min(revised["max_observed_drawdown_pct"],observed_dd)
    revised["processed_dates"].append(day)
    now_weight=qty*bid/(cash+qty*bid) if cash+qty*bid>0 else 0.
    observation=dict(
        system_version=VERSION,utc_day=day,observed_at_utc=now.isoformat(),
        frozen_strategy_sha256=source_sha,
        signal=snapshot,exchange_quote=quote,
        allocation=dict(target_btc_pct=round(desired*100,4),
            actual_btc_pct=round(now_weight*100,4)),
        event=event,
        virtual_account=dict(cash_usd=round(cash,4),
            btc_quantity=round(qty,10),
            liquidation_equity_usd=round(equity,4),
            return_since_start_pct=round((equity/INITIAL-1)*100,6),
            max_observed_drawdown_pct=round(revised["max_observed_drawdown_pct"],6),
            trades_to_date=revised["all_virtual_orders"]),
        safeguards=[
            "No real orders, no broker connection, no actual fills.",
            "Only sampled daily quote snapshots. Intraday losses and overnight gaps are NOT covered by a stop.",
            "Historical +13.95% was observed on already examined dates; not a forecast.",
            "Model stays frozen; changes require new version and separate account."
        ])
    return revised,observation


def main():
    now=utcnow()
    today=now.date().isoformat()
    root=Path("cecs3_forward")
    journal=root/"observations"/(today+".json")
    if journal.exists():
        print(json.dumps(dict(status="already_recorded",date=today)))
        return
    strategy_code=Path(__file__).with_name("cecs_v3_0_strategy.py").read_bytes()
    sha=hashlib.sha256(strategy_code).hexdigest()
    data=fetch_data(None)
    snap=collect_snapshot(data,now.date())
    quote=fetch_quote(now=now)
    state_path=root/"state.json"
    state=json.loads(state_path.read_text()) if state_path.exists() else initial_state(sha)
    new_state,record=advance(state,snap,quote,now,sha)
    journal.parent.mkdir(parents=True,exist_ok=True)
    journal.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    state_path.write_text(json.dumps(new_state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(dict(status="saved",utc_day=today,
        event=record["event"],equity=record["virtual_account"],
        allocation=record["allocation"]),indent=2))


if __name__=="__main__":
    main()
