"""Research-only closed-bar entry point. No network, credentials, notifications or production edits."""
import pandas as pd
from candidate_core import add_indicators,compute_impulse

def analyze_closed_frame(df, tf, as_of):
    if tf not in ('1h','4h','1d'):raise ValueError('unsupported timeframe')
    try:
        if df is None or df.empty:return {'state':'DATA_UNAVAILABLE','reason':'empty response'}
        d=df.copy();t=pd.to_datetime(d['Open time'],utc=True);now=pd.Timestamp(as_of)
        if now.tzinfo is None:raise ValueError('as_of must include timezone')
        step=pd.Timedelta(tf);d=d[(t+step)<=now].copy()
        if len(d)<50:return {'state':'DATA_UNAVAILABLE','reason':'insufficient closed bars'}
        t=pd.to_datetime(d['Open time'],utc=True)
        if not t.is_monotonic_increasing or t.duplicated().any() or (t.diff().dropna()!=step).any():return {'state':'DATA_UNAVAILABLE','reason':'non-contiguous candle history'}
        if d[['Open','High','Low','Close','Volume']].isna().any().any():return {'state':'DATA_UNAVAILABLE','reason':'missing OHLCV'}
        d['Open time']=t.dt.tz_localize(None)
        out=compute_impulse(add_indicators(d.tail(499).reset_index(drop=True)),closed_only=False,tf=tf)
        out['data_as_of_utc']=str(t.iloc[-1]+step)
        return out
    except (KeyError,TypeError,ValueError) as e:return {'state':'DATA_UNAVAILABLE','reason':type(e).__name__}

def active_direction(imp):
    return imp.get('direction') if imp and imp.get('state')=='ACTIVE' else None

def summarize_layers(d1,h4,h1):
    layers={'1D':d1,'4H':h4,'1H':h1}
    parts=[]
    for name,r in layers.items():
        state=r.get('state','DATA_UNAVAILABLE')
        if state=='DATA_UNAVAILABLE':parts.append(name+' DATA_UNAVAILABLE')
        elif state=='ACTIVE':parts.append(name+' '+r['direction']+' ACTIVE')
        elif state=='ENDED':parts.append(name+' inactive (last '+str(r.get('direction'))+')')
        else:parts.append(name+' inactive')
    return ' | '.join(parts)
