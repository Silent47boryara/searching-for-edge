"""Маска валидности ликвидаций v2. Порог пропуска heartbeat выбран по данным (распределение интервалов), а не подгонкой под результат;
приёмочный тест: число событий CSV внутри невалидных окон должно быть ~0 (поток в простое событий не пишет)."""
import pandas as pd, numpy as np, re, json, warnings; warnings.filterwarnings("ignore")
P="/Users/arefevoleg/bot_project_v2"; O=P+"/LAB_attrib_p1/out"
LINE=re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ (\w+) (.*)$")
rows=[(pd.Timestamp(m.group(1))-pd.Timedelta(hours=3),m.group(2),m.group(3)) for ln in open(P+"/liq_collector.log",encoding="utf-8") if (m:=LINE.match(ln))] if False else []
for ln in open(P+"/liq_collector.log",encoding="utf-8",errors="replace"):
    m=LINE.match(ln)
    if m: rows.append((pd.Timestamp(m.group(1))-pd.Timedelta(hours=3),m.group(2),m.group(3)))
L=pd.DataFrame(rows,columns=["t","lvl","msg"]).sort_values("t")
START=pd.Timestamp("2026-08-29 11:28:12")
hb=L[L.msg.str.contains("heartbeat")&(L.t>=START)].t.reset_index(drop=True)
d=hb.diff().dt.total_seconds().dropna()/60
print("интервалы heartbeat, мин: квантили",d.quantile([.5,.9,.99,.995]).round(1).to_dict(),"| max",round(d.max(),1))
print("число интервалов в диапазонах: <=10м",int((d<=10).sum()),"| 10–15м",int(((d>10)&(d<=15)).sum()),"| 15–30м",int(((d>15)&(d<=30)).sum()),"| >30м",int((d>30).sum()))
def build(thr):
    ev=pd.concat([pd.DataFrame({"t":L[L.msg.str.startswith("Подключено")].t,"k":"C"}),pd.DataFrame({"t":L[L.lvl=="ERROR"].t,"k":"E"}),pd.DataFrame({"t":hb,"k":"H"})]).sort_values("t")
    bad=[];state=None;bf=None;lh=None
    for t,k in zip(ev.t,ev.k):
        if k=="E" and state!="down": state="down"; bf=t
        elif k=="C" and state=="down": bad.append([bf,t]); state="up"
        elif k=="C": state="up"
        if k=="H":
            if lh is not None and (t-lh).total_seconds()/60>thr: bad.append([lh,t])
            lh=t
    bad=sorted(bad); m=[]
    for a,b in bad:
        if m and a<=m[-1][1]: m[-1][1]=max(m[-1][1],b)
        else: m.append([a,b])
    return [[max(a,START),b] for a,b in m if b>START]
lq=pd.read_csv(P+"/liquidations_raw.csv",usecols=["recv_ts_utc"]); lq["t"]=pd.to_datetime(lq.recv_ts_utc,utc=True,format="ISO8601").dt.tz_localize(None)
END=lq.t.max(); span=(END-START).total_seconds()
for thr in (10,15,20,30):
    U=build(thr); a=np.array([x[0] for x in U],dtype="datetime64[ns]"); b=np.array([x[1] for x in U],dtype="datetime64[ns]")
    idx=np.searchsorted(a,lq.t.values.astype("datetime64[ns]"),side="right")-1
    ins=(idx>=0)&(lq.t.values.astype("datetime64[ns]")<=b[np.clip(idx,0,None)])
    tot=sum((y-x).total_seconds() for x,y in U)
    print(f"порог {thr:>2} мин: окон {len(U):>4} | невалидно {tot/3600:6.1f} ч ({tot/span*100:5.1f}% времени) | событий внутри: {int(ins.sum()):>5} ({ins.mean()*100:.2f}%)")
# ---- итоговая маска (порог 15 мин; обоснование: чуть выше 99.5-го перцентиля интервалов heartbeat = 12.4 мин; результат устойчив при 10–30)
U=build(15); pd.DataFrame(U,columns=["from","to"]).assign(min=lambda x:(x.to-x["from"]).dt.total_seconds()/60).to_csv(O+"/liq_invalid_union_v2.csv",index=False)
print("сохранено окон:",len(U))
