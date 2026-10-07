"""Аудит регулярных потоков по реальным timestamp (не по логам): OI (5м), gamma_agg (10м), funding/markprice (~1с),
лог бота (~30м), свечи. Все времена в UTC."""
import pandas as pd, numpy as np, json, glob, warnings; warnings.filterwarnings("ignore")
P="/Users/arefevoleg/bot_project_v2"; OUT=P+"/LAB_attrib_p1/out"; R={}
NOW=pd.Timestamp.utcnow().tz_localize(None) if pd.Timestamp.utcnow().tzinfo else pd.Timestamp.utcnow()
def ts(s):
    r=pd.to_datetime(s, utc=True, format="ISO8601").dt.tz_localize(None)
    assert r.notna().all() and r.dt.year.between(2026,2026).all(), "NaT или год не 2026"
    return r
def gaps(t, thr_min, top=5):
    t=t.sort_values().drop_duplicates(); d=(t.diff().dt.total_seconds()/60)
    g=pd.DataFrame({"gap_min":d.round(1),"from":t.shift(),"to":t}).dropna()
    big=g[g.gap_min>thr_min].sort_values("gap_min",ascending=False)
    return len(big), big.head(top), g
def grid(name, t, step_min, thr_min, bin_round=True):
    t=t.sort_values().reset_index(drop=True)
    slot=t.dt.round(f"{step_min}min") if bin_round else t
    n=len(t); u=slot.nunique(); span=(t.iloc[-1]-t.iloc[0]).total_seconds()/60/step_min+1
    dup=n-u; nb,big,_=gaps(t,thr_min)
    r={"first":str(t.iloc[0]),"last":str(t.iloc[-1]),"N":n,"unique_slots":int(u),"expected_slots":round(span,1),"coverage_pct":round(u/span*100,2),
       "duplicate_rows_same_slot":int(dup),"gaps_gt_thr":int(nb),"thr_min":thr_min,
       "largest_gaps":[{"min":float(x.gap_min),"from":str(x["from"]),"to":str(x.to)} for _,x in big.head(5).iterrows()]}
    R[name]=r; return t,big
# --- OI
oi=pd.read_csv(P+"/oi_raw.csv"); oi["t"]=ts(oi["recv_ts_utc"])
t,_=grid("oi_raw",oi["t"],5,15)
R["oi_raw"]["symbols"]=oi.symbol.unique().tolist(); R["oi_raw"]["dup_exact_rows"]=int(oi.duplicated(["recv_ts_utc"]).sum())
# --- gamma agg
ga=pd.read_csv(P+"/gamma_snapshot_agg.csv"); ga["t"]=ts(ga["snapshot_ts_utc"])
t,_=grid("gamma_agg",ga["t"],10,15)
a=pd.Timestamp("2026-10-02 10:10"); b=pd.Timestamp("2026-10-06 23:10")
pre=ga[ga.t<=a]; post=ga[ga.t>=b]
R["gamma_agg"]["segment_pre"]={"first":str(pre.t.min()),"last":str(pre.t.max()),"N":len(pre)}
R["gamma_agg"]["segment_post"]={"first":str(post.t.min()),"last":str(post.t.max()),"N":len(post)}
R["gamma_agg"]["n_instruments_pre"]=pre.n_instruments.describe()[["min","50%","max"]].to_dict()
# дубли из-за двух экземпляров: две строки в одном 10-мин слоте
slot=ga.t.dt.round("10min"); R["gamma_agg"]["slots_with_2plus_rows"]=int((slot.value_counts()>1).sum())
# --- funding/markprice (~1/с)
fm=pd.read_csv(P+"/funding_markprice_raw.csv",usecols=["recv_ts_utc","event_time_ms","mark_price","funding_rate"])
fm["t"]=ts(fm["recv_ts_utc"]); fm=fm.sort_values("t")
span=(fm.t.iloc[-1]-fm.t.iloc[0]).total_seconds(); sec=fm.t.dt.floor("s").nunique()
d=fm.t.diff().dt.total_seconds().dropna()
big=fm.assign(gap_s=fm.t.diff().dt.total_seconds()).dropna().sort_values("gap_s",ascending=False).head(6)
R["funding_markprice"]={"first":str(fm.t.iloc[0]),"last":str(fm.t.iloc[-1]),"N":len(fm),"span_s":round(span),"unique_seconds":int(sec),
  "coverage_pct_of_seconds":round(sec/span*100,2),"dup_event_time_ms":int(fm.event_time_ms.duplicated().sum()),
  "gaps_gt_5s":int((d>5).sum()),"gaps_gt_60s":int((d>60).sum()),"gaps_gt_600s":int((d>600).sum()),
  "largest_gaps":[{"s":round(float(x.gap_s)),"to":str(x.t)} for _,x in big.iterrows()],
  "funding_rate_unique_values":int(fm.funding_rate.nunique())}
# залипание mark_price: самый длинный непрерывный отрезок одинаковых значений
same=(fm.mark_price!=fm.mark_price.shift()).cumsum(); run=fm.groupby(same).agg(a=("t","first"),b=("t","last"),n=("t","size"))
run["min"]=(run.b-run.a).dt.total_seconds()/60; r=run.sort_values("min",ascending=False).iloc[0]
R["funding_markprice"]["longest_same_mark_price_min"]=round(float(r["min"]),1)
# --- лог бота
fs=sorted(glob.glob(P+"/btc_signals_log(*)_v4.csv")); L=pd.concat([pd.read_csv(f) for f in fs]); L["t"]=pd.to_datetime(L["Time"])
t,big=grid("bot_log_ticks",L["t"].drop_duplicates(),30,75,bin_round=False)
R["bot_log_ticks"]["note"]="ожидаемо ~48 тиков/сутки; бот спит 1800с + время расчёта, поэтому expected_slots приблизителен"
# --- свечи
for tf,m in (("1d",1440),("4h",240),("1h",60)):
    k=pd.read_csv(f"{P}/LAB_attrib_p1/raw/BTCUSDT_{tf}_binance_raw.csv"); R[f"klines_{tf}"]={"first":str(k.open_time_utc.iloc[0]),"last":str(k.open_time_utc.iloc[-1]),"N":len(k),
      "dups":int(k.open_time_ms.duplicated().sum()),"irregular_steps":int((k.open_time_ms.diff().dropna()!=m*60000).sum())}
# --- backfill-файлы
for f in ("oi_history_backfill_30d.csv","funding_rate_history_backfill.csv"):
    x=pd.read_csv(P+"/"+f); R[f]={"cols":x.columns.tolist(),"N":len(x),"first":str(x.iloc[0,0]),"last":str(x.iloc[-1,0])}
json.dump(R,open(OUT+"/audit_grid.json","w"),ensure_ascii=False,indent=1,default=str)
for k,v in R.items():
    print("==",k); print(json.dumps(v,ensure_ascii=False,default=str)[:900])
