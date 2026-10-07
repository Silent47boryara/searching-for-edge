"""Детерминированный replay состояний импульса (BOS-state machine) 1D/4H/1H.
Для каждого закрытого бара k воспроизводим то, что видел бы бот в тик после закрытия бара k:
окно из 500 баров = 499 закрытых (до k включительно) + 1 «формирующийся» бар (отбрасывается в compute_impulse).
Без правок логики: используется дословная копия функций (scripts/bot_v2_extracted.py)."""
import sys, json, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/arefevoleg/bot_project_v2/LAB_attrib_p1/scripts")
import pandas as pd, numpy as np
import bot_v2_extracted as B
RAW="/Users/arefevoleg/bot_project_v2/LAB_attrib_p1/raw"; OUT="/Users/arefevoleg/bot_project_v2/LAB_attrib_p1/out"
FROM = pd.Timestamp("2026-08-20 00:00")   # начало сравнения с логом (v4-логи с 21.08)
KEYS = ["state","direction","start_time","start_price","age_bars","confirmations","confirm_dates","price","move_pct","mfe_pct","mae_pct",
        "break_level","dist_to_break_pct","end_time","end_price","broken_level","end_reason"]
for tf, mins in (("1d",1440),("4h",240),("1h",60)):
    raw = pd.read_csv(f"{RAW}/BTCUSDT_{tf}_binance_raw.csv")
    raw["Open time"] = pd.to_datetime(raw["open_time_ms"], unit="ms")          # naive UTC, как в bot_v2.fetch_data
    base = raw[["Open time","Open","High","Low","Close","Volume","open_time_ms","close_time_ms"]].reset_index(drop=True)
    rows=[]
    ks = [k for k in range(len(base)) if base.loc[k,"Open time"] >= FROM and k >= 498]
    for k in ks:
        w = base.iloc[k-498:k+1].copy()
        forming = base.iloc[k+1:k+2].copy() if k+1 < len(base) else base.iloc[k:k+1].copy()   # отбрасывается closed_only
        df = pd.concat([w, forming], ignore_index=True)
        df = B.add_indicators(df)
        imp = B.compute_impulse(df, closed_only=True, tf=tf)
        r = {"tf":tf, "bar_open_utc": str(base.loc[k,"Open time"]), "bar_close_ms": int(base.loc[k,"close_time_ms"]),
             "bar_close_utc": str(pd.to_datetime(int(base.loc[k,"close_time_ms"])+1, unit="ms")), "close": float(base.loc[k,"Close"])}
        for key in KEYS: r[key] = imp.get(key)
        rows.append(r)
    o = pd.DataFrame(rows); o.to_csv(f"{OUT}/replay_{tf}.csv", index=False)
    print(tf, "тиков replay:", len(o), "| состояния:", o["state"].value_counts().to_dict())
