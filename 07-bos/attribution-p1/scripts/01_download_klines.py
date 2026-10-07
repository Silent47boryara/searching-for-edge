"""Загрузка свечей BTCUSDT с Binance (spot, как в bot_v2.fetch_data) в НОВЫЕ неизменяемые файлы.
Источник: https://api.binance.com/api/v3/klines. Существующие файлы истории не трогаем."""
import requests, pandas as pd, json, time, os, sys, datetime as dt
OUT = "/Users/arefevoleg/bot_project_v2/LAB_attrib_p1/raw"
URL = "https://api.binance.com/api/v3/klines"
STEP = {"1h": 3600_000, "4h": 4*3600_000, "1d": 86400_000}
START = {"1d": "2025-01-01", "4h": "2026-04-01", "1h": "2026-06-15"}   # запас прогрева >= 500 баров до 2026-08-21
END_MS = int(dt.datetime(2026,10,7,23,59,59,tzinfo=dt.timezone.utc).timestamp()*1000)
COLS = ['open_time_ms','Open','High','Low','Close','Volume','close_time_ms','quote_vol','n_trades','taker_base','taker_quote','ignore']
now_ms = int(time.time()*1000)
for tf in ("1d","4h","1h"):
    fn = f"{OUT}/BTCUSDT_{tf}_binance_raw.csv"
    if os.path.exists(fn): print("ПРОПУСК, файл уже есть (неизменяемый):", fn); continue
    t = int(dt.datetime.fromisoformat(START[tf]).replace(tzinfo=dt.timezone.utc).timestamp()*1000)
    rows = []
    while t < min(END_MS, now_ms):
        r = requests.get(URL, params={"symbol":"BTCUSDT","interval":tf,"startTime":t,"limit":1000}, timeout=20)
        r.raise_for_status(); d = r.json()
        if not d: break
        rows += d; t = d[-1][0] + STEP[tf]; time.sleep(0.25)
    df = pd.DataFrame(rows, columns=COLS).drop_duplicates('open_time_ms')
    # оставляем ТОЛЬКО закрытые свечи на момент загрузки
    df = df[df['close_time_ms'] < now_ms].reset_index(drop=True)
    for c in ['Open','High','Low','Close','Volume']: df[c] = pd.to_numeric(df[c])
    df['open_time_utc'] = pd.to_datetime(df['open_time_ms'], unit='ms', utc=True)
    df.to_csv(fn, index=False); os.chmod(fn, 0o444)
    gaps = df['open_time_ms'].diff().dropna(); gaps = gaps[gaps != STEP[tf]]
    meta = {"file": os.path.basename(fn), "source": URL, "symbol": "BTCUSDT", "interval": tf,
            "downloaded_utc": dt.datetime.utcnow().isoformat()+"Z", "first_open_utc": str(df['open_time_utc'].iloc[0]),
            "last_open_utc": str(df['open_time_utc'].iloc[-1]), "rows": len(df), "gaps_n": int(len(gaps)),
            "closed_only": True}
    json.dump(meta, open(fn.replace(".csv",".meta.json"),"w"), ensure_ascii=False, indent=1)
    print(meta)
