#!/usr/bin/env python3
"""CECS 2.1 minimal, independently auditable BTC/USD research runner.

Uses causal confirmed pivots and a Traders-Reality-inspired Vector Candle proxy.
Not an official Camel Finance/Elliott/Traders Reality implementation.
Not financial advice or a live execution system.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import statistics
import urllib.request
from collections import Counter
from pathlib import Path

URL = "https://raw.githubusercontent.com/daniegitx1/btc-price-history/main/data/btc_usd_daily.csv"
FEE_SLIPPAGE = 0.0015
MODELS = ("Breakout", "Cycle", "Elliott", "CECS", "Vector", "CycleVector", "ElliottVector", "CECSVector")


def fetch_data(path):
    if path:
        return Path(path).read_bytes()
    with urllib.request.urlopen(URL, timeout=90) as r:
        return r.read()


def parse_data(payload):
    import io
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    needed = {"date_utc", "open", "high", "low", "close", "volume"}
    if not needed.issubset(set(reader.fieldnames or [])):
        raise ValueError("Missing OHLCV columns")
    data = []
    for row in reader:
        day = dt.date.fromisoformat(row["date_utc"])
        if day < dt.date(2017, 1, 1):
            continue
        x = {key: float(row[key]) for key in ("open", "high", "low", "close", "volume")}
        if any(not math.isfinite(v) for v in x.values()):
            raise ValueError("Invalid nonfinite OHLCV")
        if not (x["low"] > 0 and x["volume"] >= 0 and x["high"] >= max(x["open"], x["close"]) and x["low"] <= min(x["open"], x["close"])):
            raise ValueError("Invalid OHLCV candle")
        x["date"] = day
        if data and (day - data[-1]["date"]).days != 1:
            raise ValueError("Gap or duplicate day: " + str(day))
        data.append(x)
    if len(data) < 600:
        raise ValueError("Not enough data")
    return data


def confirmed_pivots(bars, left, right):
    events = [[] for _ in bars]
    for i in range(left, len(bars) - right):
        lo, hi = bars[i]["low"], bars[i]["high"]
        is_low = all(lo < bars[k]["low"] for k in range(i - left, i)) and all(lo <= bars[k]["low"] for k in range(i + 1, i + right + 1))
        is_high = all(hi > bars[k]["high"] for k in range(i - left, i)) and all(hi >= bars[k]["high"] for k in range(i + 1, i + right + 1))
        if is_low:
            events[i + right].append(("L", i, lo))
        if is_high:
            events[i + right].append(("H", i, hi))
    return events


def enrich(data):
    for i, x in enumerate(data):
        prev_close = data[i - 1]["close"] if i else x["close"]
        x["tr"] = max(x["high"] - x["low"], abs(x["high"] - prev_close), abs(x["low"] - prev_close))
        x["atr"] = statistics.mean(v["tr"] for v in data[i - 13:i + 1]) if i >= 13 else None
        if i < 10:
            x["vector"] = "ordinary"
            continue
        prev = data[i - 10:i]
        m = statistics.mean(y["volume"] for y in prev)
        max_spread = max(y["volume"] * (y["high"] - y["low"]) for y in prev)
        climax = m > 0 and x["volume"] > 0 and (x["volume"] >= 2 * m or x["volume"] * (x["high"] - x["low"]) >= max_spread)
        rising = m > 0 and x["volume"] > 0 and not climax and x["volume"] >= 1.5 * m
        up = x["close"] > x["open"]
        x["vector"] = ("green" if up else "red") if climax else ("blue" if up else "violet") if rising else "ordinary"


def weekly_events(data):
    # Fully closed Monday-Sunday weekly bars, never available before next Monday.
    weeks = []
    for i, x in enumerate(data):
        monday = x["date"] - dt.timedelta(days=x["date"].weekday())
        if not weeks or weeks[-1]["monday"] != monday:
            weeks.append({"monday": monday, "first": i, "last": i, "high": x["high"], "low": x["low"], "close": x["close"], "count": 0})
        w = weeks[-1]
        w["last"] = i
        w["high"] = max(w["high"], x["high"])
        w["low"] = min(w["low"], x["low"])
        w["close"] = x["close"]
        w["count"] += 1
    weeks = [x for x in weeks if x["count"] == 7]
    alpha, ema = 2 / 27, None
    for i, w in enumerate(weeks):
        ema = w["close"] if ema is None else alpha * w["close"] + (1 - alpha) * ema
        w["ema"] = ema if i >= 25 else None
        w["ema_lag4"] = weeks[i - 4]["ema"] if i >= 29 else None
        w["available"] = w["monday"] + dt.timedelta(days=7)
    piv = confirmed_pivots(weeks, 3, 2)
    wcl, anchor = [], None
    for known_i, events in enumerate(piv):
        for kind, idx, price in events:
            if kind != "L":
                continue
            gap = idx - anchor if anchor is not None else None
            if gap is None or gap >= 12:
                wcl.append({"available": weeks[known_i]["available"], "low": price, "valid": gap is not None and 12 <= gap <= 40, "pivot": idx})
                anchor = idx
    return weeks, wcl


def wave_candidate(swings, data):
    if len(swings) < 3:
        return None
    (a, ai, ap), (b, bi, bp), (c, ci, cp) = swings[-3:]
    if (a, b, c) != ("L", "H", "L"):
        return None
    amp = bp - ap
    atr = data[bi]["atr"]
    if not (7 <= bi - ai <= 120 and 3 <= ci - bi <= 180 and atr and amp >= 3 * atr and cp > ap):
        return None
    retrace = (bp - cp) / amp
    if not (0.5 <= retrace <= 0.786):
        return None
    return {"target": cp + 1.618 * amp, "retrace": retrace}


def vector_confirmation(data, t):
    if data[t]["vector"] in ("green", "blue"):
        return True
    if any(x["vector"] in ("green", "blue") for x in data[max(0, t - 3):t]):
        return True
    bearish = [x for x in data[max(0, t - 21):t] if x["vector"] in ("red", "violet")]
    if bearish and t > 0:
        m = (bearish[-1]["high"] + bearish[-1]["low"]) / 2
        return data[t - 1]["close"] < m <= data[t]["close"]
    return False


def find_signals(data):
    enrich(data)
    weeks, wcls = weekly_events(data)
    piv = confirmed_pivots(data, 7, 3)
    swings, watches, signals = [], [], []
    widx = wcl_idx = 0
    active_week = active_wcl = None
    dcl_anchor = None
    counts = Counter()
    for t in range(200, len(data) - 1):
        today = data[t]["date"]
        while widx < len(weeks) and weeks[widx]["available"] <= today:
            active_week = weeks[widx]
            widx += 1
        while wcl_idx < len(wcls) and wcls[wcl_idx]["available"] <= today:
            active_wcl = wcls[wcl_idx]
            wcl_idx += 1
        for kind, i, price in piv[t]:
            if swings and swings[-1][0] == kind:
                if (kind == "L" and price < swings[-1][2]) or (kind == "H" and price > swings[-1][2]):
                    swings[-1] = (kind, i, price)
            else:
                swings.append((kind, i, price))
            swings = swings[-24:]
            if kind == "L":
                counts["confirmed_lows"] += 1
                gap = i - dcl_anchor if dcl_anchor is not None else None
                dcl_valid = False
                if gap is None or gap >= 45:
                    dcl_valid = gap is not None and gap <= 85
                    dcl_anchor = i
                w = wave_candidate(swings, data)
                watches.append({"known": t, "expire": t + 12, "low": price, "idx": i, "cycle": dcl_valid, "elliott": w})
                counts["cycle_candidates"] += int(dcl_valid)
                counts["elliott_candidates"] += int(w is not None)
                counts["joint_candidates"] += int(dcl_valid and w is not None)
        watches = [w for w in watches if t <= w["expire"]]
        if not active_wcl or not active_wcl["valid"] or not active_week or active_week["ema"] is None or active_week["ema_lag4"] is None:
            continue
        if (today - active_wcl["available"]).days >= 270:
            continue
        close = data[t]["close"]
        if not (close > active_week["ema"] > active_week["ema_lag4"] and close > active_wcl["low"]):
            continue
        if close <= max(data[j]["high"] for j in range(t - 10, t)):
            continue
        confirmed = vector_confirmation(data, t)
        seen = set()
        for watch in watches:
            variants = ["Breakout"]
            if watch["cycle"]:
                variants.append("Cycle")
            if watch["elliott"]:
                variants.append("Elliott")
            if watch["cycle"] and watch["elliott"]:
                variants.append("CECS")
            if confirmed:
                variants.append("Vector")
                if watch["cycle"]:
                    variants.append("CycleVector")
                if watch["elliott"]:
                    variants.append("ElliottVector")
                if watch["cycle"] and watch["elliott"]:
                    variants.append("CECSVector")
            for model in variants:
                if model in seen:
                    continue
                seen.add(model)
                opening = data[t + 1]["open"]
                stop = watch["low"] - 0.25 * data[t]["atr"]
                entry_net = opening * (1 + FEE_SLIPPAGE)
                stop_net = stop * (1 - FEE_SLIPPAGE)
                risk = entry_net - stop_net
                if risk <= 0 or opening <= stop or stop <= 0:
                    continue
                if model in ("CECS", "CECSVector"):
                    fib = watch["elliott"]["target"]
                    if fib * (1 - FEE_SLIPPAGE) < entry_net + 2 * risk:
                        continue
                target = (entry_net + 3 * risk) / (1 - FEE_SLIPPAGE)
                signals.append({"model": model, "day": t + 1, "stop": stop, "target": target, "risk": risk,
                                "signal": str(today), "entry": str(data[t + 1]["date"]), "vector": data[t]["vector"]})
        # Once a model has generated a signal, don't repeat that setup later.
        watches = [w for w in watches if w["known"] != t and w["expire"] > t] if seen else watches
    return signals, counts


def simulate(data, signals, model, begin, end):
    capital = 100000.0
    wins, gross_up, gross_down, rvalues, records = 0, 0.0, 0.0, [], []
    peak = capital
    max_dd = 0.0
    occupied_until = begin - 1
    for s in sorted((x for x in signals if x["model"] == model and begin <= x["day"] <= end), key=lambda v: v["day"]):
        i = s["day"]
        if i <= occupied_until:
            continue
        opening = data[i]["open"]
        risk = s["risk"]
        qty = min(0.005 * capital / risk, capital / (opening * (1 + FEE_SLIPPAGE)))
        if qty <= 0:
            continue
        stop = s["stop"]
        target = s["target"]
        last = min(end, i + 90)
        for j in range(i, last + 1):
            x = data[j]
            if x["open"] <= stop:
                exit_px, reason = x["open"], "stop_gap"
            elif x["open"] >= target:
                exit_px, reason = x["open"], "target_gap"
            elif x["low"] <= stop:
                exit_px, reason = stop, "stop"
            elif x["high"] >= target:
                exit_px, reason = target, "target"
            elif j == last:
                exit_px, reason = x["close"], "period_end" if j == end else "time"
            else:
                continue
            pnl = qty * (exit_px * (1 - FEE_SLIPPAGE) - opening * (1 + FEE_SLIPPAGE))
            r = pnl / (qty * risk)
            capital += pnl
            wins += int(pnl > 0)
            gross_up += max(0, pnl)
            gross_down += max(0, -pnl)
            rvalues.append(r)
            occupied_until = j
            peak = max(peak, capital)
            max_dd = min(max_dd, capital / peak - 1)
            records.append({"model": model, "period": "development" if end < len(data) - 365 else "review",
                            "entry": s["entry"], "exit": str(data[j]["date"]), "signal": s["signal"],
                            "pnl": round(pnl, 2), "r": round(r, 5), "reason": reason})
            break
    return {"model": model, "trades": len(records), "win_rate_pct": round(100 * wins / len(records), 2) if records else None,
            "mean_r": round(statistics.mean(rvalues), 4) if rvalues else None,
            "return_pct": round(100 * (capital / 100000 - 1), 4),
            "closed_trade_drawdown_pct": round(100 * max_dd, 4),
            "profit_factor": round(gross_up / gross_down, 4) if gross_down else None}, records


def study_vector_recovery(data, begin, end):
    groups = {}
    # Only count candles whose entire follow-up window lies in the period.
    for i in range(max(10, begin), end - 9):
        x = data[i]
        up = x["close"] > x["open"]
        direction = "up" if up else "down"
        label = x["vector"] if x["vector"] != "ordinary" else "ordinary_" + direction
        mid = (x["high"] + x["low"]) / 2
        following = data[i + 1:i + 11]
        half = any((y["low"] <= mid if up else y["high"] >= mid) for y in following)
        full = any((y["low"] <= x["low"] if up else y["high"] >= x["high"]) for y in following)
        rec = groups.setdefault(label, [0, 0, 0])
        rec[0] += 1
        rec[1] += half
        rec[2] += full
    return [{"label": k, "n": a, "mid_recovery_pct": round(100 * b / a, 2),
             "full_recovery_pct": round(100 * c / a, 2)} for k, (a, b, c) in sorted(groups.items())]


def save_csv(path, records):
    rows = list(records)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    source = fetch_data(args.csv)
    data = parse_data(source)
    signals, funnel = find_signals(data)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    split = next((i for i, x in enumerate(data) if x["date"] >= dt.date(2022, 1, 1)), len(data))
    summaries, trades = [], []
    for label, start, finish in (("development", 0, split - 1), ("review", split, len(data) - 1)):
        if start >= finish:
            continue
        for model in MODELS:
            stats, rows = simulate(data, signals, model, start, finish)
            stats["period"] = label
            summaries.append(stats)
            for row in rows:
                row["period"] = label
            trades.extend(rows)
    save_csv(out / "summary.csv", summaries)
    save_csv(out / "trades.csv", trades)
    save_csv(out / "vector_recovery_2017_2021.csv", study_vector_recovery(data, 0, split - 1))
    save_csv(out / "vector_recovery_2022_2026.csv", study_vector_recovery(data, split, len(data) - 1))
    manifest = {"sha256": hashlib.sha256(source).hexdigest(), "source": URL if not args.csv else str(args.csv),
                "first": str(data[0]["date"]), "last": str(data[-1]["date"]), "candles": len(data),
                "vector_counts": dict(Counter(x["vector"] for x in data)),
                "candidate_funnel": dict(funnel), "signals": len(signals),
                "disclaimer": "Experimental strategy proxies, retrospective research, no validated edge"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": manifest, "summary": summaries}, indent=2))


if __name__ == "__main__":
    main()
