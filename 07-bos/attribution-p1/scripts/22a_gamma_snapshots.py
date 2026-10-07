"""Gamma: по каждому снимку — unsigned концентрации по страйкам. Только |gamma_exposure_per_1pct_move| (знак дилеров НЕ выводится).
G_up/G_dn: сумма по страйкам (spot,1.05*spot] / [0.95*spot,spot); A=(G_up-G_dn)/(G_up+G_dn). Описательно: страйк максимума в ±15% выше/ниже."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
P="/Users/arefevoleg/bot_project_v2"; Q=P+"/LAB_attrib_p1/out/phase2a"
parts=[]; neg=0; tot=0
for ch in pd.read_csv(P+"/gamma_snapshot_raw.csv",usecols=["snapshot_ts_utc","spot_price","strike","gamma_exposure_per_1pct_move"],chunksize=400000):
    neg+=int((ch.gamma_exposure_per_1pct_move<0).sum()); tot+=len(ch)
    parts.append(ch.groupby(["snapshot_ts_utc","strike"],as_index=False).agg(g=("gamma_exposure_per_1pct_move","sum"),spot=("spot_price","first")))
print("строк raw:",tot,"| отрицательных gamma_exposure_per_1pct_move:",neg)
D=pd.concat(parts).groupby(["snapshot_ts_utc","strike"],as_index=False).agg(g=("g","sum"),spot=("spot","first"))
D["ts"]=pd.to_datetime(D.snapshot_ts_utc,utc=True,format="ISO8601").dt.tz_localize(None); assert (D.ts.dt.year==2026).all()
out=[]
for ts,x in D.groupby("ts"):
    sp=x.spot.iloc[0]; s=x.set_index("strike").g
    up=s[(s.index>sp)&(s.index<=sp*1.05)].sum(); dn=s[(s.index<sp)&(s.index>=sp*0.95)].sum()
    u15=s[(s.index>sp)&(s.index<=sp*1.15)]; d15=s[(s.index<sp)&(s.index>=sp*0.85)]; tot15=u15.sum()+d15.sum()
    out.append({"ts":ts,"spot":sp,"G_up":up,"G_dn":dn,"A":(up-dn)/(up+dn) if up+dn>0 else np.nan,
      "top_up_strike":u15.idxmax() if len(u15) else np.nan,"top_up_dist_pct":(u15.idxmax()/sp-1)*100 if len(u15) else np.nan,"top_up_share":u15.max()/tot15 if len(u15) and tot15>0 else np.nan,
      "top_dn_strike":d15.idxmax() if len(d15) else np.nan,"top_dn_dist_pct":(d15.idxmax()/sp-1)*100 if len(d15) else np.nan,"top_dn_share":d15.max()/tot15 if len(d15) and tot15>0 else np.nan,"n_strikes":len(s)})
S=pd.DataFrame(out).sort_values("ts"); S["slot"]=S.ts.dt.round("10min"); S=S.drop_duplicates("slot",keep="first").drop(columns="slot")
S.to_csv(Q+"/gamma_snapshot_features.csv",index=False); print("снимков:",len(S),"| период",S.ts.min(),"→",S.ts.max()); print(S[["A","top_up_dist_pct","top_dn_dist_pct","top_up_share"]].describe().round(3).to_string())
