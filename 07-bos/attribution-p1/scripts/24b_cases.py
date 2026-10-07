"""Фаза 2A, п.4: семь входов в «1D BULL / 4H NONE / 1H BEAR» поштучно + сравнение с двумя соседними состояниями."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
Q="/Users/arefevoleg/bot_project_v2/LAB_attrib_p1/out/phase2a"; O=Q+"/.."
X=pd.read_csv(Q+"/events_full.csv",parse_dates=["T"]); G=pd.read_csv(Q+"/full_grid_1h.csv",parse_dates=["t"])
EP=pd.read_csv(O+"/episodes.csv",parse_dates=["first_seen_close","last_active_close"])
rep1h=pd.read_csv(O+"/replay_1h.csv",parse_dates=["bar_close_utc"]); ticks1h=rep1h.bar_close_utc.values
KEY="1D BULL / 4H NONE / 1H BEAR"; S2="1D BULL / 4H BULL / 1H BEAR"; S3="1D BULL / 4H NONE / 1H NONE"
T=X[(X.family=="TRANSITION")&(X.state_after==KEY)].sort_values("T")
def after(T0,hours): return G[(G.t>T0)&(G.t<=T0+pd.Timedelta(hours=hours))]
def case_row(r,wide=True):
    d={"T_UTC":r["T"],"цена":round(r.P_T),"из":r.state_before.replace("1D BULL / ","")}
    # 1H BEAR эпизод, содержащий T
    e=EP[(EP.tf=="1h")&(EP.direction=="BEAR")&(EP.first_seen_close<=r["T"])&(EP.last_active_close>=r["T"])]
    if len(e):
        e=e.iloc[0]; d["1H_BEAR_старт"]=e.start_label
        if e.ended_observed:
            nxt=pd.Timestamp(ticks1h[ticks1h>np.datetime64(e.last_active_close)][0]); d["1H_BEAR_конец"]=nxt.strftime("%d.%m %H:%M"); d["длит_с_T_ч"]=(nxt-r["T"]).total_seconds()/3600; d["причина"]=e.end_reason
        else: d["1H_BEAR_конец"]="ещё активен"; d["длит_с_T_ч"]=np.nan; d["причина"]=None
    a72=after(r["T"],72); d["4H_BULL_вернулся_72ч"]=bool((a72["4h"]=="BULL").any()); d["4H_BEAR_появился_72ч"]=bool((a72["4h"]=="BEAR").any())
    for h in (24,72):
        a=G[G.t==r["T"]+pd.Timedelta(hours=h)]; d[f"1D_через_{h}ч"]=a["1d"].iloc[0] if len(a) else "нет данных"
    n1=G[(G.t>r["T"])&(G["1d"]!="BULL")]; d["1D_BULL_потерян_в"]=n1.t.iloc[0].strftime("%d.%m %H:%M") if len(n1) else "нет"
    for h in (1,4,12,24): d[f"R{h}_%"]=round(r[f"R{h}"]*100,2) if r[f"R{h}"]==r[f"R{h}"] else np.nan
    d["MFE24_%"]=round(r.MFE24*100,2) if r.MFE24==r.MFE24 else np.nan; d["MAE24_%"]=round(r.MAE24*100,2) if r.MAE24==r.MAE24 else np.nan
    for c,n in (("dOI_4h","ΔOI4ч_%"),("dOI_24h","ΔOI24ч_%")): d[n]=round(r[c]*100,2) if r[c]==r[c] else np.nan
    d["funding_%"]=round(r.f_T*100,4) if r.f_T==r.f_T else np.nan
    d["liq_imb_4h"]=round(r.liq_imb_4h,2) if r.liq_imb_4h==r.liq_imb_4h else np.nan; d["liq_imb_12h"]=round(r.liq_imb_12h,2) if r.liq_imb_12h==r.liq_imb_12h else np.nan
    d["liq_total_12h_млн"]=round(r.liq_total_12h/1e6,2) if r.liq_total_12h==r.liq_total_12h else np.nan
    d["gamma_A"]=round(r.gm_A,2) if "gm_A" in r and r.gm_A==r.gm_A else np.nan
    d["tape_flow_12h"]=round(r.tp_flow_12h,3) if r.tp_flow_12h==r.tp_flow_12h else np.nan; d["tape_IV_12h"]=round(r.tp_iv_12h,1) if r.tp_iv_12h==r.tp_iv_12h else np.nan
    return d
C=pd.DataFrame([case_row(r) for r in T.itertuples()]) if False else pd.DataFrame([case_row(r) for _,r in T.iterrows()])
C.to_csv(Q+"/C_seven_cases.csv",index=False)
pd.set_option("display.width",250); pd.set_option("display.max_columns",40)
print("== 7 входов: структура ==\n",C[["T_UTC","цена","из","1H_BEAR_старт","1H_BEAR_конец","длит_с_T_ч","причина","4H_BULL_вернулся_72ч","4H_BEAR_появился_72ч","1D_через_24ч","1D_через_72ч","1D_BULL_потерян_в"]].to_string(index=False))
print("\n== 7 входов: исходы (s=+1) ==\n",C[["T_UTC","R1_%","R4_%","R12_%","R24_%","MFE24_%","MAE24_%"]].to_string(index=False))
print("\n== 7 входов: деривативы до T ==\n",C[["T_UTC","ΔOI4ч_%","ΔOI24ч_%","funding_%","liq_imb_4h","liq_imb_12h","liq_total_12h_млн","gamma_A","tape_flow_12h","tape_IV_12h"]].to_string(index=False))
# сравнение состояний
rows=[]
for lab,st in (("A: "+KEY,KEY),("B: "+S2,S2),("C: "+S3,S3)):
    d=X[(X.family=="TRANSITION")&(X.state_after==st)]
    rows.append({"состояние":lab,"входов":len(d),"кластеров":d.cluster.nunique(),"R4_мед%":d.R4.median()*100,"R12_мед%":d.R12.median()*100,"R24_мед%":d.R24.median()*100,"R24_ост>0 %":(d.R24.dropna()>0).mean()*100,"MAE24_мед%":d.MAE24.median()*100,"MFE24_мед%":d.MFE24.median()*100,
      "ΔOI24ч_мед%":d.dOI_24h.median()*100,"funding_мед%":d.f_T.median()*100,"liq_imb12_мед":d.liq_imb_12h.median(),"gamma_A_мед":d.gm_A.median(),"tape_flow12_мед":d.tp_flow_12h.median()})
CMP=pd.DataFrame(rows); CMP.to_csv(Q+"/C_state_comparison.csv",index=False); print("\n== сравнение ==\n",CMP.round(3).T.to_string(header=False))
print("\n== состояние B (4H BULL / 1H BEAR) поштучно =="); print(pd.DataFrame([case_row(r) for _,r in X[(X.family=='TRANSITION')&(X.state_after==S2)].sort_values('T').iterrows()])[["T_UTC","цена","из","R4_%","R12_%","R24_%","MAE24_%","4H_BULL_вернулся_72ч","1D_BULL_потерян_в"]].to_string(index=False))
# ранг «серьёзного ухудшения» (1D BULL потерян в течение 72ч) среди 7
C["det72"]=[ (pd.to_datetime(v,format="%d.%m %H:%M",errors="coerce").replace(year=2026)-t).total_seconds()/3600<=72 if v!="нет" else False for v,t in zip(C["1D_BULL_потерян_в"],C["T_UTC"])]
print("\nвходов с потерей 1D BULL ≤72ч:",int(C.det72.sum()),"из",len(C)); print(C[C.det72][["T_UTC","1D_BULL_потерян_в"]].to_string(index=False))
feat=["ΔOI4ч_%","ΔOI24ч_%","funding_%","liq_imb_4h","liq_imb_12h","liq_total_12h_млн","gamma_A","tape_flow_12h","tape_IV_12h"]
print("\nранг (1=наименьшее) случая(ев) с потерей 1D среди 7 по признаку:")
for i in C[C.det72].index:
    print(" ",C.loc[i,"T_UTC"],{f:(int(C[f].rank().loc[i]) if C[f].notna().sum()>=5 and not np.isnan(C.loc[i,f]) else "н/д") for f in feat})
