"""Уточнения аудита: (1) маска ликвидаций с объединением интервалов и началом валидности 2026-08-29 11:28 UTC (смена endpoint),
(2) граница ненадёжности tape по правилу «день недели × час», (3) таблица общих окон простоя по всем потокам."""
import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings("ignore")
OUT="/Users/arefevoleg/bot_project_v2/LAB_attrib_p1/out"; P="/Users/arefevoleg/bot_project_v2"
def union(iv):
    iv=sorted(iv); m=[]
    for a,b in iv:
        if m and a<=m[-1][1]: m[-1][1]=max(m[-1][1],b)
        else: m.append([a,b])
    return m
R={}
# (1) ликвидации
w=pd.read_csv(OUT+"/liq_invalid_windows.csv",parse_dates=["from","to"])
START=pd.Timestamp("2026-08-29 11:28:12"); END=pd.Timestamp("2026-10-07 09:35:34")
iv=[[max(a,START),min(b,END)] for a,b in zip(w["from"],w["to"]) if b>START and a<END]
U=union(iv); tot=sum((b-a).total_seconds() for a,b in U)/3600; span=(END-START).total_seconds()/3600
big=sorted(U,key=lambda x:(x[0]-x[1]))[:0]
R["liq_mask"]={"valid_from_utc":str(START),"reason":"до этого endpoint /ws/ молчал (events=0); с 14:28 МСК — /market/ws/","span_h":round(span,1),
  "invalid_union_h":round(tot,1),"valid_pct":round(100-tot/span*100,2),"merged_windows":len(U),
  "windows_ge30min":sum(1 for a,b in U if (b-a).total_seconds()>=1800)}
pd.DataFrame(U,columns=["from","to"]).assign(min=lambda d:(d.to-d["from"]).dt.total_seconds()/60).to_csv(OUT+"/liq_invalid_union.csv",index=False)
# (2) tape: день недели × час
h=pd.read_csv(OUT+"/tape_hourly.csv",index_col=0,parse_dates=True)
h["wd"]=h.index.dayofweek; h["hr"]=h.index.hour
clean=h.loc["2026-08-29":"2026-10-01"]
cell_min=clean.groupby(["wd","hr"]).n.min().rename("cell_min"); cell_med=clean.groupby(["wd","hr"]).n.median().rename("cell_med")
x=h.loc["2026-10-01":"2026-10-07"].join(cell_min,on=["wd","hr"]).join(cell_med,on=["wd","hr"])
x["below_all_clean"]=x.n<x.cell_min
s=x[x.below_all_clean]
R["tape_boundary"]={"rule":"час ниже минимума всех чистых недель (29.08–01.10) для той же ячейки день_недели×час","n_flagged":int(len(s)),
  "flagged_hours":[str(i) for i in s.index], "weekday_of_oct3":"суббота","weekend_levels_clean":{str(k):int(v) for k,v in
    pd.read_csv(P+"/deribit_option_trades_raw.csv",usecols=["timestamp_ms"]).assign(d=lambda d:pd.to_datetime(d.timestamp_ms,unit="ms").dt.date).groupby("d").size().loc[
    [pd.Timestamp(i).date() for i in ("2026-08-29","2026-08-30","2026-09-05","2026-09-06","2026-09-12","2026-09-13","2026-09-19","2026-09-20","2026-09-26","2026-09-27")]].items()}}
json.dump(R,open(OUT+"/audit_fix.json","w"),ensure_ascii=False,indent=1,default=str)
print(json.dumps(R,ensure_ascii=False,indent=0,default=str)[:3500])
