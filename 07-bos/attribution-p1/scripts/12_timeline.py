"""Синхронный пример. Правило выбора (задано ДО просмотра): самое раннее событие входа в «1D BULL / 4H NONE / 1H BEAR»,
у которого доступны все 5 слоёв (OI, funding, liq, gamma, tape) по event_availability.csv. Окно ±36 ч. Gamma-панель — иллюстрация, не признак."""
import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates, warnings; warnings.filterwarnings("ignore")
P="/Users/arefevoleg/bot_project_v2"; O=P+"/LAB_attrib_p1/out"
def ts(s): return pd.to_datetime(s,utc=True,format="ISO8601").dt.tz_localize(None)
V=pd.read_csv(O+"/event_availability.csv",parse_dates=["T"])
c=V[(V.kind=="multi_tf_transition")&(V.label=="1D BULL / 4H NONE / 1H BEAR")&V.all_ok].sort_values("T"); T0=c["T"].iloc[0]
a,b=T0-pd.Timedelta(hours=36),T0+pd.Timedelta(hours=36); print("T0 =",T0)
k=pd.read_csv(P+"/LAB_attrib_p1/raw/BTCUSDT_1h_binance_raw.csv"); k["t"]=pd.to_datetime(k.open_time_ms,unit="ms")+pd.Timedelta(hours=1); k=k[(k.t>=a)&(k.t<=b)]
G=pd.read_csv(O+"/multi_tf_state_1h_grid.csv",parse_dates=["t"]); G=G[(G.t>=a)&(G.t<=b)]
E=pd.read_csv(O+"/episodes.csv",parse_dates=["first_seen_close"]); E=E[(E.first_seen_close>=a)&(E.first_seen_close<=b)]
oi=pd.read_csv(P+"/oi_raw.csv"); oi["t"]=ts(oi.recv_ts_utc); oi=oi[(oi.t>=a)&(oi.t<=b)]
fu=pd.read_csv(P+"/funding_markprice_raw.csv",usecols=["recv_ts_utc","funding_rate"]); fu["t"]=ts(fu.recv_ts_utc); fu=fu[(fu.t>=a)&(fu.t<=b)].set_index("t").funding_rate.resample("5min").last()
lq=pd.read_csv(P+"/liquidations_raw.csv",usecols=["recv_ts_utc","liquidation_side","notional_usd"]); lq["t"]=ts(lq.recv_ts_utc); lq=lq[(lq.t>=a)&(lq.t<=b)]
U=pd.read_csv(O+"/liq_invalid_union_v2.csv",parse_dates=["from","to"])
# gamma raw (чанками, фильтр по строке времени)
rows=[]; s0,s1=str(a)[:16].replace(" ","T"),str(b)[:16].replace(" ","T")
for ch in pd.read_csv(P+"/gamma_snapshot_raw.csv",usecols=["snapshot_ts_utc","spot_price","strike","gamma_exposure_per_1pct_move"],chunksize=300000):
    m=ch[(ch.snapshot_ts_utc.str[:16]>=s0)&(ch.snapshot_ts_utc.str[:16]<=s1)]
    if len(m): rows.append(m)
g=pd.concat(rows); g["t"]=ts(g.snapshot_ts_utc).dt.round("10min")
out=[]
for t,x in g.groupby("t"):
    sp=x.spot_price.iloc[0]; s=x.groupby("strike").gamma_exposure_per_1pct_move.sum()
    up=s[(s.index>sp)&(s.index<=sp*1.15)]; dn=s[(s.index<sp)&(s.index>=sp*0.85)]
    out.append((t,sp,up.idxmax() if len(up) else np.nan,dn.idxmax() if len(dn) else np.nan))
Gm=pd.DataFrame(out,columns=["t","spot","up","dn"]).drop_duplicates("t")
tp=pd.read_csv(P+"/deribit_option_trades_raw.csv",usecols=["timestamp_ms","instrument_name","direction","amount","index_price"]); tp["t"]=pd.to_datetime(tp.timestamp_ms,unit="ms")
tp=tp[(tp.t>=a)&(tp.t<=b)].copy(); tp["cp"]=tp.instrument_name.str[-1]; tp["usd"]=tp.amount*tp.index_price*np.where(tp.direction=="buy",1,-1)
fl=tp.groupby([tp.t.dt.floor("h"),"cp"]).usd.sum().unstack().reindex(pd.date_range(a.floor("h"),b,freq="h")).fillna(0)
fig,ax=plt.subplots(5,1,figsize=(14,15),sharex=True,gridspec_kw={"height_ratios":[3.2,1.6,1.6,2,1.8]})
col={"BULL":"#2e8b57","BEAR":"#c0392b","NONE":"#d0d0d0"}
ax[0].plot(k.t,k.Close,color="k",lw=1.2,label="BTCUSDT, закрытие 1ч")
lo=k.Close.min(); rng=k.Close.max()-lo
for i,(tf,name) in enumerate((("1d","1D"),("4h","4H"),("h1","1H"))):
    y0=lo-rng*(0.07+0.07*i)
    for j in range(len(G)-1):
        ax[0].fill_between([G.t.iloc[j],G.t.iloc[j+1]],y0,y0-rng*0.05,color=col[G[tf].iloc[j]])
    ax[0].text(a,y0-rng*0.025,f" {name}",va="center",fontsize=8)
for r in E.itertuples():
    y=k.loc[(k.t-r.first_seen_close).abs().idxmin(),"Close"]
    ax[0].annotate(f"{r.tf.upper()} {r.direction}\nстарт",(r.first_seen_close,y),xytext=(0,16 if r.direction=="BULL" else -26),textcoords="offset points",ha="center",fontsize=7,arrowprops=dict(arrowstyle="-",lw=.5))
ax[0].axvline(T0,color="purple",ls="--",lw=1); ax[0].set_title(f"Панель 1. Цена BTC и состояния BOS (зелёный BULL, красный BEAR, серый — нет). Пунктир: {T0:%d.%m %H:%M} UTC, вход в «1D BULL/4H NONE/1H BEAR»",fontsize=10)
ax[1].plot(oi.t,oi.open_interest,color="tab:blue",label="OI, BTC"); ax[1].set_ylabel("OI, BTC")
a2=ax[1].twinx(); a2.plot(fu.index,fu.values*100,color="tab:orange",lw=1,label="funding, %"); a2.set_ylabel("funding, %")
ax[1].set_title("Панель 2. Open interest (Binance, шаг 5 мин) и funding rate"); ax[1].axvline(T0,color="purple",ls="--",lw=1)
hh=lq.groupby([lq.t.dt.floor("h"),"liquidation_side"]).notional_usd.sum().unstack().reindex(pd.date_range(a.floor("h"),b,freq="h")).fillna(0)
w=pd.Timedelta(minutes=40)
ax[2].bar(hh.index+pd.Timedelta(minutes=30),hh.get("LONG_LIQUIDATION",0)/1e6,width=w,color="#c0392b",label="ликвидации лонгов")
ax[2].bar(hh.index+pd.Timedelta(minutes=30),-hh.get("SHORT_LIQUIDATION",0)/1e6,width=w,color="#2e8b57",label="ликвидации шортов")
for s,e in zip(U["from"],U["to"]):
    if e>a and s<b: ax[2].axvspan(max(s,a),min(e,b),color="grey",alpha=.35)
ax[2].set_ylabel("млн USD"); ax[2].set_title("Панель 3. Ликвидации Binance (выборка forceOrder, не весь рынок); серым — окна простоя сборщика"); ax[2].axvline(T0,color="purple",ls="--",lw=1)
ax[3].plot(Gm.t,Gm.spot,color="k",lw=1,label="spot (Deribit)"); ax[3].plot(Gm.t,Gm.up,color="#8e44ad",marker=".",ms=3,lw=0,label="страйк макс. концентрации выше spot (≤+15%)")
ax[3].plot(Gm.t,Gm.dn,color="#16a085",marker=".",ms=3,lw=0,label="страйк макс. концентрации ниже spot (≤−15%)")
ax[3].set_title("Панель 4. Gamma Deribit: концентрация |gamma_exposure_per_1pct_move| по страйкам (без знака, иллюстрация, не признак)"); ax[3].legend(fontsize=7,loc="upper left"); ax[3].axvline(T0,color="purple",ls="--",lw=1)
x=np.arange(len(fl)); wd=pd.Timedelta(minutes=22)
ax[4].bar(fl.index+pd.Timedelta(minutes=15),fl.get("C",0)/1e6,width=wd,color="#2980b9",label="колы: покупки − продажи агрессора")
ax[4].bar(fl.index+pd.Timedelta(minutes=45),fl.get("P",0)/1e6,width=wd,color="#e67e22",label="путы: покупки − продажи агрессора")
ax[4].axhline(0,color="k",lw=.5); ax[4].set_ylabel("млн USD (amount×index)"); ax[4].legend(fontsize=7,loc="upper left"); ax[4].axvline(T0,color="purple",ls="--",lw=1)
ax[4].set_title("Панель 5. Опционный поток Deribit (tape): чистый агрессивный нотионал по часам; direction = сторона тейкера")
ax[4].xaxis.set_major_formatter(mdates.DateFormatter("%d.%m %H:%M")); ax[4].set_xlim(a,b)
fig.suptitle(f"Синхронный пример (выбран по правилу: самое раннее событие этого типа со всеми 5 слоями данных). Время — UTC",fontsize=12,y=0.995)
fig.tight_layout(); fig.savefig(O+"/timeline_example.png",dpi=105); print("сохранено timeline_example.png")
