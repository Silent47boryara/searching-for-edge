"""Фаза 2A, шаг 1: таблица событий (замороженные эпизоды/переходы Фазы 1). Только структура, без цен и признаков."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
O="/Users/arefevoleg/bot_project_v2/LAB_attrib_p1/out"; Q=O+"/phase2a"; WIN0=pd.Timestamp("2026-08-29 11:28:12")
rep={tf:pd.read_csv(f"{O}/replay_{tf}.csv",parse_dates=["bar_close_utc"]).rename(columns={"bar_close_utc":"t"}) for tf in ("1d","4h","1h")}
for tf,r in rep.items(): r["act"]=np.where(r.state=="ACTIVE",r.direction,"NONE")
G=rep["1h"][["t","act","start_time"]].rename(columns={"act":"h1","start_time":"h1_key"}).sort_values("t")
for tf in ("4h","1d"):
    S=rep[tf][["t","act","start_time"]].rename(columns={"act":tf,"start_time":tf+"_key"}).sort_values("t"); G=pd.merge_asof(G,S,on="t",direction="backward")
G["state3"]="1D "+G["1d"]+" / 4H "+G["4h"]+" / 1H "+G["h1"]; G.to_csv(Q+"/full_grid_1h.csv",index=False)
def state_at(T): 
    r=G[G.t<=T].iloc[-1]; return r
def cluster(T):
    r=state_at(T); return ("1D#"+str(r["1d_key"])+" "+r["1d"]) if r["1d"]!="NONE" else "1D-gap"
EP=pd.read_csv(O+"/episodes.csv",parse_dates=["first_seen_close","last_active_close"]); EP=EP[EP.in_win]
rows=[]
def add(fam,T,s,**kw): rows.append({"family":fam,"T":T,"s":s,"cluster":cluster(T),**kw})
for e in EP.itertuples():
    s=1 if e.direction=="BULL" else -1
    if e.tf in ("1h","4h"):
        fam=e.tf.upper()+"_start"; r=state_at(e.first_seen_close)
        add(fam,e.first_seen_close,s,ep=f"{e.tf}|{e.direction}|{e.start_label}",dir=e.direction,d1=r["1d"],against_1d=bool(r["1d"]!="NONE" and r["1d"]!=e.direction))
        if e.ended_observed:
            nxt=rep[e.tf][rep[e.tf].t>e.last_active_close].t.iloc[0]
            add(e.tf.upper()+"_end",nxt,s,ep=f"{e.tf}|{e.direction}|{e.start_label}",dir=e.direction,end_reason=e.end_reason,d1=state_at(nxt)["1d"],against_1d=False)
# F3 переходы (заморожены из Фазы 1)
H=pd.read_csv(O+"/multi_tf_state_1h_grid.csv",parse_dates=["t"]); H["chg"]=H.state3!=H.state3.shift()
tr=H[H.chg].iloc[1:].copy(); tr["prev"]=H.state3.shift()[H.chg].iloc[1:].values
def sdir(st):
    for part in st.split(" / "):
        d=part.split(" ")[1]
        if d!="NONE": return 1 if d=="BULL" else -1
    return 0
for r in tr.itertuples(): add("TRANSITION",r.t,sdir(r.state3),state_after=r.state3,state_before=r.prev)
# выравнивание
G["full"]=(G["1d"]==G["4h"])&(G["4h"]==G["h1"])&(G["1d"]!="NONE"); G["fchg"]=G.full!=G.full.shift()
for r in G[(G.fchg)&(G.t>=WIN0)&(G.t>G.t.iloc[0])].itertuples():
    d=1 if r.h1=="BULL" or r._4==("BULL") else -1
    dirn=1 if (r._6=="BULL" or r.h1=="BULL") else -1
    add("ALIGN_RESTORED" if r.full else "ALIGN_LOST",r.t,1 if G.loc[G.t==r.t,"1d"].iloc[0]=="BULL" else -1,state_after=r.state3)
E=pd.DataFrame(rows).sort_values(["family","T"]).reset_index(drop=True); E.insert(0,"ev_id",range(len(E))); E.to_csv(Q+"/events.csv",index=False)
print(E.groupby("family").agg(N=("T","size"),кластеров_1D=("cluster","nunique"),BULL=("s",lambda x:int((x>0).sum())),BEAR=("s",lambda x:int((x<0).sum()))).to_string())
print("\nпротив 1D среди 1H_start:",int(E[(E.family=="1H_start")].against_1d.sum()),"из",int((E.family=="1H_start").sum()))
print("\nкластеры по семействам:"); print(E.groupby(["family","cluster"]).size().unstack(fill_value=0).to_string())
