"""Диаграммы рассеяния двух кандидатов (все точки, подписи — дата события)."""
import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
Q="/Users/arefevoleg/bot_project_v2/LAB_attrib_p1/out/phase2a"; X=pd.read_csv(Q+"/events_full.csv",parse_dates=["T"])
col={"1D#2026-08-19 BULL":"tab:blue","1D#2026-09-18 BULL":"tab:orange","1D-gap":"tab:green"}; nm={"1D#2026-08-19 BULL":"1D-режим №1 (до 15.09)","1D#2026-09-18 BULL":"1D-режим №2 (с 18.09)","1D-gap":"пауза 1D"}
fig,ax=plt.subplots(1,2,figsize=(14,5.6))
def sc(a,d,f,xl,title,mark_dir):
    for c,g in d.groupby("cluster"):
        for dirn,mk in ((1,"o"),(-1,"s")):
            z=g[g.s==dirn]; a.scatter(z[f],z.MAE24*100,c=col[c],marker=mk,s=55,label=f"{nm[c]}, {'BULL' if dirn>0 else 'BEAR'}" if len(z) else None,edgecolor="k",lw=.4)
    for _,r in d.iterrows(): a.annotate(r["T"].strftime("%d.%m"),(r[f],r.MAE24*100),fontsize=6.5,xytext=(3,3),textcoords="offset points")
    a.set_xlabel(xl); a.set_ylabel("MAE за 24 ч, % (направленно; ближе к 0 — мягче)"); a.set_title(title,fontsize=9); a.axhline(0,color="k",lw=.4); a.legend(fontsize=6.5)
d1=X[X.family=="1H_start"].dropna(subset=["tp_fa_12h","MAE24"]); sc(ax[0],d1,"tp_fa_12h","Fa_12h = s·(колы_нетто − путы_нетто)/Σ|нотионал|, tape за 12 ч до T",f"Кандидат 1 (первичное семейство): старты 1H, n={len(d1)}, ρ=+0,62, p_перест=0,020, Holm 0,196",True)
d3=X[X.family=="TRANSITION"].dropna(subset=["gm_Aa","MAE24"]); sc(ax[1],d3,"gm_Aa","Aa = s·(G_вверх − G_вниз)/(G_вверх + G_вниз), unsigned gamma в ±5% от spot",f"Кандидат 2 (вторичный, post-hoc): мульти-ТФ переходы, n={len(d3)}, ρ=−0,58, p_сдвиг<0,001",False)
fig.suptitle("Два кандидата в одинаковом формате: все точки, без отбора. EXPLORATORY / INSUFFICIENT FOR CONFIRMATION",fontsize=10); fig.tight_layout(rect=[0,0,1,.95]); fig.savefig(Q+"/candidates_scatter.png",dpi=100); print("ok")
