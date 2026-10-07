# АВТОГЕНЕРАЦИЯ. Дословная копия из bot_v2.py, sha256 исходника = b1f4eaa37187cb2917b92471c4dff9f71ecd88e6e3c4d0e539b8cf7abaa996c8
# Не редактировать вручную. Секретов здесь нет.
import bisect
import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import AverageTrueRange
SOURCE_SHA256 = "b1f4eaa37187cb2917b92471c4dff9f71ecd88e6e3c4d0e539b8cf7abaa996c8"

def add_indicators(df):
    if df.empty: return df
    df['RSI'] = RSIIndicator(df['Close'], window=10).rsi()
    macd = MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['EMA_50'] = EMAIndicator(df['Close'], window=50).ema_indicator()
    df['EMA_200'] = EMAIndicator(df['Close'], window=200).ema_indicator()
    df['ADX'] = ADXIndicator(df['High'], df['Low'], df['Close'], window=10).adx()
    df['ATR'] = AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range()
    df['Stoch'] = StochasticOscillator(df['High'], df['Low'], df['Close']).stoch()
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).cumsum()
    df['OBV_mean'] = df['OBV'].rolling(20).mean()
    return df

SWING_LAG = 2

def _detect_swings(df):
    """Те же условия, что в compute_market_structure. Возвращает
    (список (idx, high), список (idx, low)) по всему df."""
    if df is None or len(df) < 30:
        return [], []
    vol_ma = df['Volume'].rolling(20).mean()
    High = df['High'].values
    Low = df['Low'].values
    ATRv = df['ATR'].values
    EMAv = df['EMA_50'].values
    Volv = df['Volume'].values
    VMAv = vol_ma.values

    highs, lows = [], []
    for i in range(2, len(df) - SWING_LAG):
        atr = ATRv[i]; ema50 = EMAv[i]; vma = VMAv[i]
        if np.isnan(atr) or np.isnan(ema50) or np.isnan(vma):
            continue
        if High[i] >= High[i-2:i+3].max() and (High[i] - ema50) > 0.7*atr and Volv[i] > 1.05*vma:
            highs.append((i, float(High[i])))
        if Low[i] <= Low[i-2:i+3].min() and (ema50 - Low[i]) > 0.7*atr and Volv[i] > 1.05*vma:
            lows.append((i, float(Low[i])))
    return highs, lows

def find_all_bos(df):
    """Все дискретные BOS-события. Детектор НЕ меняется — те же swing
    (с фильтрами EMA/объём) и то же условие пробоя, что в compute_market_structure.
    Событие = первый бар непрерывной серии флага одного направления.
    Причинность: swing виден только с бара i + SWING_LAG.
    """
    if df is None or len(df) < 30:
        return []
    highs, lows = _detect_swings(df)
    if not highs or not lows:
        return []
    hi_idx=[x[0] for x in highs]; hi_val=[x[1] for x in highs]
    lo_idx=[x[0] for x in lows];  lo_val=[x[1] for x in lows]
    Close = df['Close'].values
    events=[]; prev_up=prev_dn=False
    for t in range(len(df)):
        cutoff = t - SWING_LAG
        h = bisect.bisect_left(hi_idx, cutoff)
        l = bisect.bisect_left(lo_idx, cutoff)
        bos_up=bos_dn=False; level=None
        if h > 0 and l > 0:
            if Close[t] > hi_val[h-1]*1.001: bos_up=True; level=hi_val[h-1]
            elif Close[t] < lo_val[l-1]*0.999: bos_dn=True; level=lo_val[l-1]
        if bos_up and not prev_up: events.append((t, 1, level))
        if bos_dn and not prev_dn: events.append((t, -1, level))
        prev_up, prev_dn = bos_up, bos_dn
    return events

def _local_pivots(df):
    """Локальные 5-барные экстремумы БЕЗ фильтров EMA/объёма.
    Отличие от _detect_swings: снят фильтр (ema50 - low) > 0.7*ATR, который
    в сильном тренде не давал новым минимумам формироваться вообще — из-за
    него уровень слома висел неподвижно сотни дней.
    Причинность: пивот на баре i требует баров i+1 и i+2, поэтому известен
    только начиная с бара i + SWING_LAG. Проверено: 1093 момента, 0 расхождений
    с пересчётом только по данным до t.
    """
    H = df['High'].values; L = df['Low'].values; m = len(df)
    hi=[i for i in range(2, m-SWING_LAG) if H[i] >= H[i-2:i+3].max()]
    lo=[i for i in range(2, m-SWING_LAG) if L[i] <= L[i-2:i+3].min()]
    return hi, lo

def compute_impulse(df, closed_only=True, tf="1d"):
    """IMPULSE STATE MACHINE.

    Машина полностью таймфрейм-независима: тот же детектор swing, тот же BOS,
    те же локальные пивоты, тот же SWING_LAG. Параметр tf влияет ТОЛЬКО на
    формат меток времени в выводе (дата для 1d, дата+час для 4h/1h).
    Окна доходности ret3/5/14 считаются в БАРАХ этого таймфрейма.

    ВАЖНО: работает только по ЗАКРЫТЫМ свечам. Binance отдаёт последним баром
    текущую формирующуюся свечу — она отбрасывается (closed_only=True), иначе
    BOS/слом могли бы сработать в середине дня и исчезнуть к закрытию.
    Текущая рыночная цена показывается отдельно и в модель не входит.

      BOS                       -> импульс стартует
      BOS того же направления   -> продлевает/подтверждает, якорь НЕ сбрасывается
      закрытие за последний подтверждённый локальный пивот против направления
                                -> импульс закончен
      противоположный BOS       -> импульс закончен, стартует новый

    Между импульсами состояния нет: NO ACTIVE IMPULSE.
    Персистентности нет — всё восстанавливается реплеем из OHLC.
    """
    out = {"state": "NONE"}
    if df is None or len(df) < 30:
        return out

    if closed_only and len(df) > 1:
        df = df.iloc[:-1]          # последний бар = незакрытая свеча
        if len(df) < 30:
            return out

    events = find_all_bos(df)
    if not events:
        return out
    piv_hi, piv_lo = _local_pivots(df)
    C = df['Close'].values; H = df['High'].values; L = df['Low'].values
    m = len(df); ev = {e[0]: e for e in events}

    cur=None; last_done=None
    for t in range(m):
        # --- проверка слома текущего импульса ---
        if cur is not None:
            s = cur['dir']
            pool = piv_lo if s == 1 else piv_hi
            vis = [i for i in pool if i <= t - SWING_LAG and i > cur['start']]
            if vis:
                lvl = L[vis[-1]] if s == 1 else H[vis[-1]]
                broke = (C[t] < lvl*0.999) if s == 1 else (C[t] > lvl*1.001)
                if broke:
                    cur['end']=t; cur['end_level']=float(lvl); cur['end_reason']='pivot'
                    last_done=cur; cur=None
        # --- события ---
        if t in ev:
            i, s, lv = ev[t]
            if cur is None:
                cur={'start':t,'dir':s,'level':lv,'conf':[]}
            elif s == cur['dir']:
                cur['conf'].append(t)
            else:
                cur['end']=t; cur['end_level']=None; cur['end_reason']='opposite_bos'
                last_done=cur
                cur={'start':t,'dir':s,'level':lv,'conf':[]}

    def _t(i):
        try:
            ts = pd.to_datetime(df['Open time'].iloc[i])
            return str(ts.date()) if tf == "1d" else ts.strftime('%d.%m %H:%M')
        except Exception:
            return str(i)

    def _geom(x, t_end, active):
        a=x['start']; s=x['dir']; p0=float(C[a]); pe=float(C[t_end])
        if t_end > a:
            sg=slice(a+1, t_end+1)
            fav=float(H[sg].max() if s==1 else L[sg].min())
            adv=float(L[sg].min() if s==1 else H[sg].max())
        else:
            fav=adv=p0
        r={"direction":"BULL" if s==1 else "BEAR",
           "start_time":_t(a),"start_price":p0,
           "age_bars":t_end-a,"confirmations":len(x['conf']),
           "confirm_dates":",".join(_t(c) for c in x['conf']),
           "price":pe,
           "move_pct":(pe/p0-1)*100*s,
           "mfe_pct":(fav/p0-1)*100*s,
           "mae_pct":(adv/p0-1)*100*s,
           "peak_price":fav}
        r["giveback_pct"]=r["mfe_pct"]-r["move_pct"]
        if active:
            pool = piv_lo if s==1 else piv_hi
            vis=[i for i in pool if i <= t_end - SWING_LAG and i > a]
            brk = float(L[vis[-1]] if s==1 else H[vis[-1]]) if vis else (float(x['level']) if x['level'] else None)
            r["break_level"]=brk
            r["break_pivot_time"]=_t(vis[-1]) if vis else None
            r["dist_to_break_pct"]=((pe/brk-1)*100*s) if brk else None
        else:
            r["end_time"]=_t(x['end']); r["end_price"]=float(C[x['end']])
            r["broken_level"]=x.get('end_level'); r["end_reason"]=x.get('end_reason')
        # доходности окон
        for N in (3,5,14):
            r[f"ret{N}d_pct"]=((pe/float(C[t_end-N])-1)*100*s) if t_end-N >= 0 else None
        return r

    if cur is not None:
        out={"state":"ACTIVE"}; out.update(_geom(cur, m-1, True))
    elif last_done is not None:
        out={"state":"ENDED"}; out.update(_geom(last_done, last_done['end'], False))
    return out
