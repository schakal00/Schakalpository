#!/usr/bin/env python3
"""CECS 2.8: independent FORWARD shadow paper portfolios.

Parallel models: (1) 25% BTC weekly-rebalanced benchmark, (2) conservative
Trend25, (3) high-risk TrendVol30Vector. Simulated BTC/USD spot only.

Only uses completed daily Bitstamp BTC/USD bars from a public community CSV,
at most through yesterday, with a deliberate TWO-DAY signal lag.
Rebalances at a fresh timestamped Bitstamp quote (ask to buy, bid to sell).
No actual exchange fills, no short-selling, no leverage, no broker keys.
NOT a real-time stop-risk engine; Trend/vol is NOT a hard loss guarantee.
"""
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path

from cecs_v2_1_runner import fetch_data,parse_data,URL
from cecs_v2_7_slow import prepare,target_weight
from paper_engine import fetch_quote,utcnow,TICKER_URL

VERSION="CECS-2.8-forward-shadow-2026-11-22"
COST=.0015
CAPITAL=100000.0
MODELS=("BuyHold25","Trend25","TrendVol30Vector")
REBALANCE_STEP=.05


def new_state(source_code_sha):
    return dict(version=VERSION,source_code_sha256=source_code_sha,
                started_utc_date="2026-11-22",
                models={model:dict(cash_usd=CAPITAL,qty_btc=0.0,trade_count=0)
                        for model in MODELS},
                processed_dates=[])


def new_observation(payload,today):
    records=[x for x in parse_data(payload) if x["date"]<today]
    if len(records)<600:
        raise ValueError("Insufficient historical data")
    if records[-1]["date"]!=today-dt.timedelta(days=1):
        raise ValueError("Daily source not yet updated for prior UTC day")
    prepare(records)
    known=records[-2]
    if known["date"]!=today-dt.timedelta(days=2):
        raise ValueError("Unexpected source calendar gap or latency")
    return dict(observation_day=today.isoformat(),
                source_last_completed_day=str(records[-1]["date"]),
                source_signal_day=str(known["date"]),
                source_sha256=hashlib.sha256(payload).hexdigest(),
                source_url=URL,
                known_features=dict(close_usd=known["close"],
                                    sma50_usd=known["sma50"],sma200_usd=known["sma200"],
                                    realized_vol30=known["annualized_realized_vol30"],
                                    uptrend=bool(known["trend"]),
                                    cycle_proxy=bool(known["cycle"]),
                                    vector_proxy=bool(known["vector_confirmed"])),
                weights={name:target_weight(known,name) for name in MODELS})


def advance(state,snapshot,quote,now,source_code_sha):
    today=now.date().isoformat()
    if state["version"]!=VERSION:
        raise ValueError("Unexpected shadow account version")
    if state["source_code_sha256"]!=source_code_sha:
        raise ValueError("Frozen benchmark strategy source changed: fail closed")
    if snapshot["observation_day"]!=today or snapshot["source_signal_day"]!=(now.date()-dt.timedelta(days=2)).isoformat():
        raise ValueError("Incorrect historical publication lag")
    if today in state["processed_dates"]:
        raise ValueError("Duplicate daily record")
    if state["processed_dates"] and today<state["processed_dates"][-1]:
        raise ValueError("Backdated observation forbidden")
    bid=float(quote["bid_usd"])
    ask=float(quote["ask_usd"])
    if bid<=0 or ask<bid or quote["symbol"]!="BTC/USD" or quote["exchange"]!="Bitstamp":
        raise ValueError("Invalid market quote")
    time=dt.datetime.fromisoformat(quote["exchange_timestamp_utc"])
    if (now-time).total_seconds() > 180 or (time-now).total_seconds()>15:
        raise ValueError("Stale market quote")
    result=copy.deepcopy(state)
    evidence={}
    for model in MODELS:
        account=result["models"][model]
        cash=account["cash_usd"]
        qty=account["qty_btc"]
        gross_value=cash+qty*bid
        current_weight=qty*bid/gross_value if gross_value>0 else 0.
        desired=float(snapshot["weights"][model])
        if not 0<=desired<=1:
            raise ValueError("Target is not a spot position weight")
        trade=None
        # On Mondays, rebalance by >5 percentage points. On ALL days,
        # a defeated trend must get to zero target exposure promptly.
        rebalance=(now.date().weekday()==0 and abs(current_weight-desired)>=REBALANCE_STEP) or (
                    desired==0 and qty>0)
        if rebalance:
            difference=desired*gross_value-qty*bid
            if difference>0:
                # The latest quote is not a completed order, only assumed.
                buy=min(difference/(ask*(1+COST)),cash/(ask*(1+COST)))
                if buy>0:
                    cash-=buy*ask*(1+COST)
                    qty+=buy
                    trade=dict(side="VIRTUAL_BUY",ask_usd=ask,
                        qty_btc=round(buy,9),fee_usd=round(buy*ask*COST,4),
                        assumed_fill_time_utc=now.isoformat())
            elif difference<0:
                sell=min(qty,-difference/bid)
                if sell>0:
                    cash+=sell*bid*(1-COST)
                    qty-=sell
                    trade=dict(side="VIRTUAL_SELL",bid_usd=bid,
                        qty_btc=round(sell,9),fee_usd=round(sell*bid*COST,4),
                        assumed_fill_time_utc=now.isoformat())
        if trade:
            account["trade_count"]+=1
        account["cash_usd"]=cash
        account["qty_btc"]=qty
        estimate_equity=cash+qty*bid*(1-COST)
        evidence[model]=dict(target_weight_pct=round(100*desired,4),
            observed_weight_pct=round(100*qty*bid/(cash+qty*bid),4) if cash+qty*bid else 0,
            paper_cash_usd=round(cash,4),paper_qty_btc=round(qty,10),
            paper_liquidation_equity_usd=round(estimate_equity,4),
            paper_return_since_start_pct=round(100*(estimate_equity/CAPITAL-1),6),
            total_virtual_orders=account["trade_count"],
            event=trade or dict(side="NO_ACTION"))
    result["processed_dates"].append(today)
    audit=dict(version=VERSION,date=today,
        captured_at_utc=now.isoformat(),source=snapshot,exchange_quote=quote,
        portfolios=evidence,
        caveats=[
            "These are new prospective VIRTUAL observations; no historical returns imported",
            "No live orders, no broker integration, no actual fills",
            "One quote per day cannot detect all intraday losses; no risk guarantee",
            "The 09:00 UTC quote is not the historical midnight open used in backtests",
            "Models were selected after earlier retrospective comparisons, so historical performance is contaminated by selection",
        ])
    return result,audit


def main():
    today=utcnow()
    day=today.date().isoformat()
    out=Path("slow_shadow")
    datefile=out/"observations"/(day+".json")
    if datefile.exists():
        print(json.dumps(dict(status="already_recorded",date=day)))
        return
    source=Path(__file__).with_name("cecs_v2_7_slow.py").read_bytes()
    sha=hashlib.sha256(source).hexdigest()
    payload=fetch_data(None)
    features=new_observation(payload,today.date())
    quote=fetch_quote(now=today)
    state_path=out/"state.json"
    old=json.loads(state_path.read_text()) if state_path.exists() else new_state(sha)
    next_state,audit=advance(old,features,quote,today,sha)
    datefile.parent.mkdir(parents=True,exist_ok=True)
    datefile.write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n")
    state_path.write_text(json.dumps(next_state,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(dict(status="saved",date=day,
        portfolio_summary={m:{k:v for k,v in audit["portfolios"][m].items()
             if k in ("paper_liquidation_equity_usd","paper_return_since_start_pct","event")}
             for m in MODELS}),indent=2))


if __name__=="__main__":
    main()
