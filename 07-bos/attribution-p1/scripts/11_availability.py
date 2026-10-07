"""Доступность производных данных на моменты событий (причинно: только timestamp <= T) и границы tape.
Правила свежести (утверждены): OI<=15м, gamma<=20м, funding<=60с. Для событийных потоков — маска валидности (liq) / исключение (tape)."""
import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings("ignore")
P="/Users/arefevoleg/bot_project_v2"; O=P+"/LAB_attrib_p1/out"
def ts(s): r=pd.to_datetime(s,utc=True,format="ISO8601").dt.tz_localize(None); assert r.notna().all() and (r.dt.year==2026).all(); return r
WIN0=pd.Timestamp("2026-08-29 11:28:12")
# --- tape: границы (по данным)
h=pd.read_csv(O+"/tape_hourly.csv",index_col=0,parse_dates=True)
late=h[h.lag_med>1]; print("tape: часы со ср.лагом записи >1ч: первый",late.index.min(),"последний",late.index.max(),"| всего",len(late))
lm=h.loc["2026-10-01":"2026-10-07"]; print("tape: медианный лаг по дням (ч):",lm.groupby(lm.index.date).lag_med.median().round(1).to_dict())
TAPE_BAD=(pd.Timestamp("2026-10-02 00:00"),pd.Timestamp("2026-10-06 23:05"))   # консервативно; подтверждённые дыры: 05.10 03:22–10:17 и 14:44–22:37
# --- события
E=pd.read_csv(O+"/episodes.csv",parse_dates=["first_seen_close","last_active_close"]); E=E[E.in_win]
Hg=pd.read_csv(O+"/multi_tf_state_1h_grid.csv",parse_dates=["t"]); Hg["chg"]=Hg.state3!=Hg.state3.shift()
tr=Hg[Hg.chg].iloc[1:].copy(); tr["prev"]=Hg.state3.shift()[Hg.chg].iloc[1:].values
ev=[("episode_start",r.tf,r.first_seen_close) for r in E.itertuples()]+[("multi_tf_transition",r.state3,r.t) for r in tr.itertuples()]
V=pd.DataFrame(ev,columns=["kind","label","T"])
# --- ряды
oi=pd.DataFrame({"t":ts(pd.read_csv(P+"/oi_raw.csv").recv_ts_utc)}).sort_values("t")
ga=pd.DataFrame({"t":ts(pd.read_csv(P+"/gamma_snapshot_agg.csv").snapshot_ts_utc)}).sort_values("t")
fu=pd.DataFrame({"t":ts(pd.read_csv(P+"/funding_markprice_raw.csv",usecols=["recv_ts_utc"]).recv_ts_utc)}).sort_values("t")
V=V.sort_values("T")
def fresh(ser,limit):
    m=pd.merge_asof(V[["T"]],ser.assign(s=ser.t),left_on="T",right_on="t",direction="backward")
    return ((m["T"].values-m["s"].values)/np.timedelta64(1,"s")<=limit).astype(bool)&m["s"].notna().values
V["oi_ok"]=fresh(oi,15*60); V["gamma_ok"]=fresh(ga,20*60); V["funding_ok"]=fresh(fu,60)
V["gamma_ok"]=V.gamma_ok&(V["T"]<=pd.Timestamp("2026-10-02 10:10"))     # только непрерывный сегмент до дыры
U=pd.read_csv(O+"/liq_invalid_union_v2.csv",parse_dates=["from","to"])
def liq_cov(T,hours=24):
    a=T-pd.Timedelta(hours=hours); bad=0.0
    for s,e in zip(U["from"],U["to"]):
        lo,hi=max(a,s),min(T,e)
        if hi>lo: bad+=(hi-lo).total_seconds()
    return 1-bad/(hours*3600)
V["liq_cov24h"]=[liq_cov(t) for t in V["T"]]
V["liq_valid_at_T"]=[not any(s<=t<=e for s,e in zip(U["from"],U["to"])) for t in V["T"]]
V["liq_ok"]=(V.liq_valid_at_T)&(V["T"]>=WIN0+pd.Timedelta(hours=24))&(V.liq_cov24h>=0.9)
V["tape_ok"]=~((V["T"]>=TAPE_BAD[0]-pd.Timedelta(hours=24))&(V["T"]<=TAPE_BAD[1]+pd.Timedelta(hours=24)))&(V["T"]>=pd.Timestamp("2026-08-29 21:27")+pd.Timedelta(hours=24))
V["all_ok"]=V.oi_ok&V.funding_ok&V.gamma_ok&V.liq_ok&V.tape_ok
V.to_csv(O+"/event_availability.csv",index=False)
for kind in ("episode_start","multi_tf_transition"):
    x=V[V.kind==kind]; print(f"\n{kind}: N={len(x)} | OI {int(x.oi_ok.sum())} | funding {int(x.funding_ok.sum())} | liq(24ч, покрытие>=90%) {int(x.liq_ok.sum())} | gamma(до 02.10) {int(x.gamma_ok.sum())} | tape(вне исключения±24ч) {int(x.tape_ok.sum())} | ВСЕ пять {int(x.all_ok.sum())}")
x=V[V.kind=="episode_start"]; print(x.groupby("label")[["oi_ok","funding_ok","liq_ok","gamma_ok","tape_ok","all_ok"]].sum().assign(N=x.groupby("label").size()).to_string())
# цепочка из задания: как входили в «1D BULL / 4H NONE / 1H BEAR»
key="1D BULL / 4H NONE / 1H BEAR"; c=tr[tr.state3==key]
print(f"\nвходов в «{key}»: {len(c)}; предыдущие состояния:"); print(c.prev.value_counts().to_string())
c2=V[(V.kind=="multi_tf_transition")&(V.label==key)]; print("доступность на этих входах:\n",c2[["T","oi_ok","funding_ok","liq_ok","gamma_ok","tape_ok","all_ok"]].to_string(index=False))
# зазор между временем закрытия бара-старта и первым тиком ACTIVE у эпизодов
EE=pd.read_csv(O+"/episodes.csv",parse_dates=["first_seen_close"]); print("\nпервый ACTIVE-тик эпизодов (UTC):"); print(EE[EE.in_win][["tf","direction","start_label","first_seen_close"]].head(30).to_string(index=False))
