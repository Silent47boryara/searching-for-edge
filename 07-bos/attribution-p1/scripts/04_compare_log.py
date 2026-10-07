"""Сверка replay с боевым логом btc_signals_log*_v4.csv. Время в логе — UTC (проверено по mtime файла)."""
import glob, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
P="/Users/arefevoleg/bot_project_v2"; OUT=P+"/LAB_attrib_p1/out"
fs=sorted(glob.glob(P+"/btc_signals_log(*)_v4.csv"))
L=pd.concat([pd.read_csv(f).assign(src=f.split("/")[-1]) for f in fs], ignore_index=True)
L["T"]=pd.to_datetime(L["Time"]); L=L.drop_duplicates("T").sort_values("T").reset_index(drop=True)
print("лог: файлов",len(fs),"строк",len(L),"|",L["T"].min(),"→",L["T"].max())
pref={"1d":"IMP_","4h":"H4_IMP_","1h":"H1_IMP_"}
res=[]
for tf in ("1d","4h","1h"):
    R=pd.read_csv(f"{OUT}/replay_{tf}.csv"); R["close_utc"]=pd.to_datetime(R["bar_close_utc"])
    R=R.sort_values("close_utc")
    M=pd.merge_asof(L[["T","src"]+[pref[tf]+c for c in ("State","Direction","Start_Time")]].sort_values("T"),
                    R[["close_utc","state","direction","start_time"]].rename(columns={"state":"r_state","direction":"r_dir","start_time":"r_start"}),
                    left_on="T", right_on="close_utc", direction="backward")
    M=M[M["close_utc"].notna()]
    M["state_ok"]=M[pref[tf]+"State"]==M["r_state"]
    M["dir_ok"]=M[pref[tf]+"Direction"]==M["r_dir"]
    M["start_ok"]=M[pref[tf]+"Start_Time"].astype(str)==M["r_start"].astype(str)
    M["all_ok"]=M.state_ok&M.dir_ok&M.start_ok
    M["tf"]=tf; res.append(M)
    print(f"{tf}: сопоставлено тиков {len(M)} | полное совпадение {M.all_ok.mean()*100:.1f}% | state {M.state_ok.mean()*100:.1f}% dir {M.dir_ok.mean()*100:.1f}% start {M.start_ok.mean()*100:.1f}%")
A=pd.concat(res); A.to_csv(OUT+"/replay_vs_log.csv",index=False)
bad=A[~A.all_ok]
print("расхождений всего:",len(bad)); print(bad.groupby("tf").size().to_dict())
print(bad[["tf","T"]+[c for c in bad.columns if c in ("r_state","r_dir","r_start")]].head(12).to_string(index=False))
