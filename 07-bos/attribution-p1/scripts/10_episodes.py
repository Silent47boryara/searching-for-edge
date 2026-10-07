"""Эпизоды BOS (IMPULSE) и структурные переходы по replay. Единица эпизода: (tf, direction, start_time) из состояния ACTIVE.
Окно анализа: с 2026-08-29 11:28 UTC (общее начало потоков). Левоцензурированные эпизоды (начались раньше) помечены."""
import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings("ignore")
O="/Users/arefevoleg/bot_project_v2/LAB_attrib_p1/out"; WIN0=pd.Timestamp("2026-08-29 11:28:12"); R={}
def year_ok(s): return pd.to_datetime(s).dt.year.eq(2026).all()
EP=[]; ST={}
for tf in ("1d","4h","1h"):
    r=pd.read_csv(f"{O}/replay_{tf}.csv"); r["close"]=pd.to_datetime(r.bar_close_utc); r["bo"]=pd.to_datetime(r.bar_open_utc)
    assert year_ok(r.close)
    r["act"]=np.where(r.state=="ACTIVE",r.direction,"NONE"); ST[tf]=r[["close","act","start_time","state","direction"]].rename(columns={"close":"t"})
    # эпизоды: смена (act,start_time) при ACTIVE
    a=r[r.state=="ACTIVE"].copy(); a["key"]=a.direction+"|"+a.start_time.astype(str)
    for key,g in a.groupby("key",sort=False):
        first=g.iloc[0]; last=g.iloc[-1]
        # конец: ближайший следующий тик, где ключ изменился
        nxt=r[r.close>last.close].head(1)
        ended=(len(nxt)>0) and not (nxt.state.iloc[0]=="ACTIVE" and (nxt.direction.iloc[0]+"|"+str(nxt.start_time.iloc[0]))==key)
        reason=None
        if ended:
            # причина берётся из первого ENDED/нового ACTIVE тика
            reason=("opposite_bos" if nxt.state.iloc[0]=="ACTIVE" else (nxt.end_reason.iloc[0]))
        EP.append({"tf":tf,"direction":first.direction,"start_label":first.start_time,"first_seen_close":first.close,"last_active_close":last.close,
                   "n_ticks_active":len(g),"ended_observed":bool(ended),"end_reason":reason,"max_age_bars":int(g.age_bars.max()),
                   "confirmations_max":int(g.confirmations.max()),"left_censored":bool(first.close<=r.close.iloc[0]+pd.Timedelta(minutes=1) and True)})
E=pd.DataFrame(EP)
E["in_win"]=E.last_active_close>=WIN0
E.to_csv(f"{O}/episodes.csv",index=False)
print("== эпизоды по ТФ (всего в replay / пересекают окно с 29.08 11:28 UTC / завершены наблюдаемо / ещё активны)")
for tf in ("1d","4h","1h"):
    x=E[E.tf==tf]; w=x[x.in_win]
    print(f"{tf}: всего {len(x)} | в окне {len(w)} (BULL {int((w.direction=='BULL').sum())}/BEAR {int((w.direction=='BEAR').sum())}) | завершены {int(w.ended_observed.sum())} | активны сейчас {int((~w.ended_observed).sum())} | лево-цензурированных {int(w.left_censored.sum())}")
    print("   причины завершения:",w[w.ended_observed].end_reason.value_counts().to_dict())
print("\nЭпизоды 1D (все):"); print(E[E.tf=="1d"][["direction","start_label","first_seen_close","last_active_close","ended_observed","end_reason","max_age_bars","confirmations_max","left_censored"]].to_string(index=False))
# ---- переходы состояния по каждому ТФ на тиках (на закрытии бара)
TR=[]
for tf,s in ST.items():
    s=s.sort_values("t").reset_index(drop=True); s["prev"]=s.act.shift(); s["pkey"]=s.start_time.shift()
    ch=s[(s.prev.notna())&((s.act!=s.prev)|((s.act!="NONE")&(s.start_time!=s.pkey)))]
    for _,x in ch.iterrows():
        # NONE в замысле = «нет ACTIVE» (ENDED/NONE объединены)
        TR.append({"tf":tf,"t":x.t,"from":x.prev,"to":x.act,"same_dir_new_start":bool(x.act==x.prev and x.act!="NONE")})
T=pd.DataFrame(TR); T=T[T.t>=WIN0]; T["type"]=T["from"]+"→"+T["to"]; T.to_csv(f"{O}/transitions_single_tf.csv",index=False)
print("\n== одиночные ТФ-переходы в окне (по типам)"); print(T.groupby(["tf","type"]).size().unstack(0).fillna(0).astype(int).to_string())
# ---- мульти-ТФ состояние на сетке 1H-закрытий
H=ST["1h"].rename(columns={"act":"h1"}).drop(columns=["start_time","state","direction"])
for tf in ("4h","1d"):
    S=ST[tf].rename(columns={"act":tf}).drop(columns=["start_time","state","direction"]).sort_values("t")
    H=pd.merge_asof(H.sort_values("t"),S,on="t",direction="backward")
H=H[H.t>=WIN0].reset_index(drop=True); H["state3"]="1D "+H["1d"]+" / 4H "+H["4h"]+" / 1H "+H["h1"]
H.to_csv(f"{O}/multi_tf_state_1h_grid.csv",index=False)
vc=H.state3.value_counts(); print("\n== мульти-ТФ состояния (часов в окне):"); print(vc.to_string())
H["chg"]=H.state3!=H.state3.shift(); runs=H[H.chg].copy()
H["run"]=H.chg.cumsum(); rr=H.groupby("run").agg(state=("state3","first"),t0=("t","first"),t1=("t","last"),hours=("t","size"))
print("\nсегментов постоянного мульти-ТФ состояния:",len(rr),"| медианная длительность, ч:",float(rr.hours.median()),"| сегментов длиной 1 ч:",int((rr.hours==1).sum()))
print("\nкол-во сегментов по состоянию (число отдельных заходов):"); print(rr.groupby("state").agg(заходов=("hours","size"),медиана_ч=("hours","median"),макс_ч=("hours","max")).sort_values("заходов",ascending=False).to_string())
rr.to_csv(f"{O}/multi_tf_segments.csv")
