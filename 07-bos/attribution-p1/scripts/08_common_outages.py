"""Общие окна простоя: сопоставление дыр разных потоков (по реальным timestamp). Цель — отделить сбои машины/сети
от сбоев отдельных сборщиков и сформировать итоговую маску валидности для join."""
import pandas as pd, numpy as np, json, glob, warnings; warnings.filterwarnings("ignore")
P="/Users/arefevoleg/bot_project_v2"; OUT=P+"/LAB_attrib_p1/out"
def ts(s): r=pd.to_datetime(s,utc=True,format="ISO8601").dt.tz_localize(None); assert r.notna().all(); return r
def gaps(t,thr_min):
    t=t.sort_values().drop_duplicates().reset_index(drop=True); d=t.diff().dt.total_seconds()/60
    return [(a,b) for a,b,x in zip(t.shift(),t,d) if x>thr_min]
S={}
S["funding"]=gaps(ts(pd.read_csv(P+"/funding_markprice_raw.csv",usecols=["recv_ts_utc"]).recv_ts_utc),1.0)
S["oi"]=gaps(ts(pd.read_csv(P+"/oi_raw.csv").recv_ts_utc),15)
S["gamma"]=gaps(ts(pd.read_csv(P+"/gamma_snapshot_agg.csv").snapshot_ts_utc),15)
L=pd.concat([pd.read_csv(f,usecols=["Time"]) for f in glob.glob(P+"/btc_signals_log(*)_v4.csv")]); S["bot_log"]=gaps(pd.to_datetime(L.Time),75)
tp=pd.read_csv(P+"/deribit_option_trades_raw.csv",usecols=["timestamp_ms"]); S["tape(время сделок,>60м)"]=gaps(pd.to_datetime(tp.timestamp_ms,unit="ms"),60)
U=pd.read_csv(OUT+"/liq_invalid_union_v2.csv",parse_dates=["from","to"]); S["liq(маска)"]=[(a,b) for a,b in zip(U["from"],U["to"]) if (b-a).total_seconds()>=600]
def dur(iv): return sum((b-a).total_seconds() for a,b in iv)/3600
def overlap(A,B):
    tot=0; j=0
    for a,b in A:
        for c,d in B:
            lo,hi=max(a,c),min(b,d)
            if hi>lo: tot+=(hi-lo).total_seconds()
    return tot/3600
print("поток | окон | суммарно часов")
for k,v in S.items(): print(f"{k} | {len(v)} | {dur(v):.1f}")
f=S["funding"]; l=S["liq(маска)"]
print(f"\nликв.маска ∩ funding-дыры(>1м): {overlap(l,f):.1f} ч из {dur(l):.1f} ч маски (≥10м окна)")
# общие события: окна funding >=30 мин, считаем сколько других потоков пересекается
ev=[(a,b) for a,b in S["funding"] if (b-a).total_seconds()>=1800]
rows=[]
for a,b in sorted(ev,key=lambda x:x[0]-x[1])[:25]:
    hit=[k for k,v in S.items() if k!="funding" and any(min(b,d)>max(a,c) for c,d in v)]
    rows.append({"from_utc":str(a),"to_utc":str(b),"часов":round((b-a).total_seconds()/3600,1),"пересекают":", ".join(hit)})
T=pd.DataFrame(rows); T.to_csv(OUT+"/common_outages.csv",index=False)
print("\nтоп-25 окон funding ≥30 мин и какие потоки тоже падали:"); print(T.to_string(index=False))
json.dump({k:[(str(a),str(b)) for a,b in v] for k,v in S.items()},open(OUT+"/outage_windows_by_stream.json","w"))
