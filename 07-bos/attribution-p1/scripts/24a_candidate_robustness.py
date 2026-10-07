"""Диагностика (НЕ подбор) кандидата: tp_fa_12h -> MAE24 на F1 (старты 1H-эпизодов). Ничего не оптимизируется."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
from scipy.stats import rankdata, spearmanr
Q="/Users/arefevoleg/bot_project_v2/LAB_attrib_p1/out/phase2a"; X=pd.read_csv(Q+"/events_full.csv",parse_dates=["T"])
F1=X[X.family=="1H_start"].copy(); z=F1.dropna(subset=["tp_fa_12h","MAE24"]).sort_values("T")
print("14 событий:"); print(z[["T","dir","s","cluster","tp_fa_12h","tp_n_12h","tp_abs_12h","R24","MAE24","abs_ret_24h_before"]].assign(abs_M=lambda d:d.tp_abs_12h/1e6).drop(columns="tp_abs_12h").round(4).to_string(index=False))
rho=spearmanr(z.tp_fa_12h,z.MAE24)[0]; print("\nρ =",round(rho,3))
loo=[spearmanr(z.drop(i).tp_fa_12h,z.drop(i).MAE24)[0] for i in z.index]; print("leave-one-out ρ: min",round(min(loo),3),"max",round(max(loo),3))
for c in z.cluster.unique():
    zc=z[z.cluster==c]; print("кластер",c,"n",len(zc),"ρ",round(spearmanr(zc.tp_fa_12h,zc.MAE24)[0],3) if len(zc)>=4 else "n<4")
for d,m in (("BULL",z.s>0),("BEAR",z.s<0)):
    zz=z[m]; print(d,"n",len(zz),"ρ",round(spearmanr(zz.tp_fa_12h,zz.MAE24)[0],3) if len(zz)>=4 else "n<4")
# частичный ρ при контроле |доходности за 24ч| и размера потока
def resid(y,xs):
    A=np.column_stack([rankdata(x) for x in xs]+[np.ones(len(y))]); b=np.linalg.lstsq(A,rankdata(y),rcond=None)[0]; return rankdata(y)-A@b
zz=z.dropna(subset=["abs_ret_24h_before","tp_abs_12h"])
for lab,ctl in (("|ret24h до T|",["abs_ret_24h_before"]),("размер потока Σ|notional|",["tp_abs_12h"]),("оба",["abs_ret_24h_before","tp_abs_12h"])):
    r=spearmanr(resid(zz.tp_fa_12h,[zz[c] for c in ctl]),resid(zz.MAE24,[zz[c] for c in ctl]))[0]; print(f"частичный ρ при контроле {lab}: {r:.3f} (n={len(zz)})")
# пересечение окон 24ч между событиями
t=z["T"].sort_values().values; gap=np.diff(t).astype("timedelta64[h]").astype(int); print("\nинтервалы между соседними событиями (ч):",gap.tolist(),"| событий с соседом <24ч:",int(((np.r_[gap,999]<24)|(np.r_[999,gap]<24)).sum()))
# тот же признак/исход в других семействах и окнах (описательно)
print("\nρ(tp_fa_12h, MAE24) по семействам:")
for fam in ["1H_start","1H_end","4H_start","4H_end","TRANSITION","ALIGN_LOST","ALIGN_RESTORED"]:
    d=X[X.family==fam].dropna(subset=["tp_fa_12h","MAE24"]); print(f"  {fam:<15} n={len(d):>2}", f"ρ={spearmanr(d.tp_fa_12h,d.MAE24)[0]:+.3f}" if len(d)>=5 else "n<5")
print("ρ(tp_fa_4h, MAE24) F1:", round(spearmanr(*F1.dropna(subset=['tp_fa_4h','MAE24'])[['tp_fa_4h','MAE24']].T.values)[0],3))
# 1H_end и 1H_start — одни и те же эпизоды? (зависимость)
print("\nпересечение эпизодов 1H_start/1H_end:", len(set(X[X.family=='1H_start'].ep)&set(X[X.family=='1H_end'].ep)),"общих эпизодов")
