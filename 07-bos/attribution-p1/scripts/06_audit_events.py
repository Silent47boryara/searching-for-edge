"""Аудит событийных потоков (ликвидации, tape) + маска валидности по heartbeat/ошибкам + общие окна простоя.
Логи коллекторов в МСК (UTC+3, без DST) -> переводим в UTC (проверено: mtime/последние строки)."""
import pandas as pd, numpy as np, re, json, glob, warnings; warnings.filterwarnings("ignore")
P="/Users/arefevoleg/bot_project_v2"; OUT=P+"/LAB_attrib_p1/out"; R={}
def ts(s):
    r=pd.to_datetime(s,utc=True,format="ISO8601").dt.tz_localize(None); assert r.notna().all() and (r.dt.year==2026).all(); return r
LINE=re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ (\w+) (.*)$")
def parse(files):
    rows=[]
    for f in files:
        for ln in open(f,encoding="utf-8",errors="replace"):
            m=LINE.match(ln)
            if m: rows.append((pd.Timestamp(m.group(1))-pd.Timedelta(hours=3),m.group(2),m.group(3)))
    return pd.DataFrame(rows,columns=["t","lvl","msg"]).sort_values("t").reset_index(drop=True)
# ===== ЛИКВИДАЦИИ
lq=pd.read_csv(P+"/liquidations_raw.csv"); lq["t"]=ts(lq["recv_ts_utc"])
key=["event_time_ms","symbol","raw_side","orig_qty","price","trade_time_ms"]
R["liquidations"]={"first":str(lq.t.min()),"last":str(lq.t.max()),"N":len(lq),"dup_full_key":int(lq.duplicated(key).sum()),"symbols":lq.symbol.unique().tolist(),
  "per_day_median":float(lq.groupby(lq.t.dt.date).size().median()),"days_with_zero":int(((pd.date_range(lq.t.min().normalize(),lq.t.max().normalize()).difference(pd.to_datetime(lq.t.dt.date.unique())))).size),
  "side_counts":lq.liquidation_side.value_counts().to_dict(),"notional_total_usd":round(float(lq.notional_usd.sum()))}
L=parse([P+"/liq_collector.log"])
hb=L[L.msg.str.contains("heartbeat")].t.reset_index(drop=True)
err=L[L.lvl=="ERROR"].t; con=L[L.msg.str.startswith("Подключено")].t
# маска: СОЕДИНЕНИЕ ЖИВО = от «Подключено.» до ближайшей ошибки/пропуска heartbeat>7 мин
ev=pd.concat([pd.DataFrame({"t":con,"k":"C"}),pd.DataFrame({"t":err,"k":"E"}),pd.DataFrame({"t":hb,"k":"H"})]).sort_values("t").reset_index(drop=True)
bad=[];state=None;last_h=None;bad_from=None
for _,r in ev.iterrows():
    if r.k=="E" and state!="down": state="down"; bad_from=r.t
    elif r.k=="C" and state=="down": bad.append((bad_from,r.t)); state="up"
    elif r.k=="C": state="up"
    if r.k=="H":
        if last_h is not None and (r.t-last_h).total_seconds()>7*60 and state!="down": bad.append((last_h,r.t))  # пропуск heartbeat без ошибки
        last_h=r.t
B=pd.DataFrame(bad,columns=["from","to"]); B["min"]=(B.to-B["from"]).dt.total_seconds()/60
w=B[(B.to>=lq.t.min())&(B["from"]<=lq.t.max())]
R["liquidations"]["heartbeat_log_first"]=str(hb.iloc[0]); R["liquidations"]["heartbeat_n"]=len(hb)
R["liquidations"]["invalid_windows_n"]=len(w); R["liquidations"]["invalid_total_h"]=round(float(w["min"].sum()/60),1)
R["liquidations"]["invalid_windows_ge30min"]=int((w["min"]>=30).sum())
R["liquidations"]["largest_invalid"]=[{"min":round(float(x["min"])),"from":str(x["from"]),"to":str(x["to"])} for _,x in w.sort_values("min",ascending=False).head(6).iterrows()]
span=(lq.t.max()-lq.t.min()).total_seconds()/60; R["liquidations"]["valid_pct_of_span"]=round(100-w["min"].sum()/span*100,2)
w.to_csv(OUT+"/liq_invalid_windows.csv",index=False)
# ===== TAPE
tp=pd.read_csv(P+"/deribit_option_trades_raw.csv",usecols=["recv_ts_utc","trade_id","timestamp_ms","instrument_name","direction","amount","price","iv","block_trade_id","combo_id"])
tp["recv"]=ts(tp.recv_ts_utc); tp["t"]=pd.to_datetime(tp.timestamp_ms,unit="ms"); tp["lag_h"]=(tp.recv-tp.t).dt.total_seconds()/3600
R["tape"]={"first_trade":str(tp.t.min()),"last_trade":str(tp.t.max()),"N":len(tp),"dup_trade_id":int(tp.trade_id.duplicated().sum()),
  "is_trade_id_monotonic_in_time":bool(tp.sort_values("trade_id").t.is_monotonic_increasing)}
h=tp.groupby(tp.t.dt.floor("h")).agg(n=("trade_id","size"),lag_med=("lag_h","median"),lag_max=("lag_h","max"))
h=h.reindex(pd.date_range(h.index.min(),h.index.max(),freq="h")); h["n"]=h.n.fillna(0)
clean=h.loc["2026-08-29":"2026-10-01"]
q05=clean.n.quantile(0.05); med=clean.n.median()
R["tape"]["baseline_hourly_n_clean_Aug29_Oct1"]={"median":float(med),"p05":float(q05),"p25":float(clean.n.quantile(.25))}
d=tp.groupby(tp.t.dt.date).size(); R["tape"]["per_day"]={str(k):int(v) for k,v in d.items() if str(k)>="2026-09-25"}
R["tape"]["per_day_median_Aug29_Oct1"]=float(d.loc[pd.Timestamp("2026-08-29").date():pd.Timestamp("2026-10-01").date()].median())
# правило (объявлено заранее): час «подозрительный», если n < p05 чистого периода ИЛИ медианный лаг записи > 1 ч
h["susp"]=(h.n<q05)|(h.lag_med>1)
x=h.loc["2026-10-01":"2026-10-07"]; s=x[x.susp]
R["tape"]["suspicious_hours_Oct1_Oct7"]={"n":int(len(s)),"first":str(s.index.min()),"last":str(s.index.max())}
# непрерывные трёхчасовые провалы по времени сделок
tt=tp.sort_values("t"); g=tt.t.diff().dt.total_seconds()/60; gg=pd.DataFrame({"gap_min":g.round(1),"to":tt.t}).sort_values("gap_min",ascending=False).head(6)
R["tape"]["largest_trade_time_gaps"]=[{"min":float(a),"to":str(b)} for a,b in zip(gg.gap_min,gg.to)]
R["tape"]["max_lag_h_by_trade_day"]={str(k):round(float(v),1) for k,v in tp.groupby(tp.t.dt.date).lag_h.max().items() if str(k)>="2026-09-28"}
# лог tape: первые ошибки (все ротированные файлы)
T=parse(sorted(glob.glob(P+"/deribit_trade_tape_collector.log*")))
e=T[(T.lvl.isin(["WARNING","ERROR"]))]; R["tape"]["log_range"]=[str(T.t.min()),str(T.t.max())]
R["tape"]["first_log_warning_utc"]=str(e.t.min()); R["tape"]["log_warn_err_per_day"]={str(k):int(v) for k,v in e.groupby(e.t.dt.date).size().items()}
R["tape"]["ok_pages_per_day"]={str(k):int(v) for k,v in T[T.msg.str.startswith("trade tape: +")].groupby(T.t.dt.date).size().items()}
tp.to_pickle(OUT+"/_tape_cache.pkl") if False else None
h.to_csv(OUT+"/tape_hourly.csv")
json.dump(R,open(OUT+"/audit_events.json","w"),ensure_ascii=False,indent=1,default=str)
for k,v in R.items(): print("==",k); print(json.dumps(v,ensure_ascii=False,default=str,indent=0)[:2600])
