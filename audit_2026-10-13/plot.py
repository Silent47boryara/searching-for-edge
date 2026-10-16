import os
os.environ['MPLCONFIGDIR']='/private/tmp/bos_mpl'
import pandas as pd,numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path('/Users/arefevoleg/bot_project_v2');O=Path(__file__).parent
L=pd.concat([pd.read_csv(f) for f in P.glob('btc_signals_log(*)_v4.csv')],ignore_index=True);L['T']=pd.to_datetime(L.Time,utc=True);L=L.sort_values('T').drop_duplicates('T')
for name,a,b in [('peak_bos','2026-09-15','2026-09-27'),('oct2_bos','2026-09-30','2026-10-04')]:
    q=L[(L['T']>=pd.Timestamp(a,tz='UTC'))&(L['T']<pd.Timestamp(b,tz='UTC'))].copy();g=q['T'].diff()>pd.Timedelta(minutes=75);q['group']=g.cumsum()
    fig,axs=plt.subplots(4,1,figsize=(12,7.5),sharex=True,gridspec_kw={'height_ratios':[3,1,1,1]})
    for _,z in q.groupby('group'):
        axs[0].plot(z['T'],z.Price,color='black',lw=1.3)
        for ax,pref in zip(axs[1:],['IMP_','H4_IMP_','H1_IMP_']):
            v=np.where(z[pref+'State']=='ACTIVE',np.where(z[pref+'Direction']=='BULL',1,-1),0);ax.step(z['T'],v,where='post',lw=1.4)
    for i in np.where(g.values)[0]:
        for ax in axs:ax.axvspan(q.iloc[i-1]['T'],q.iloc[i]['T'],color='grey',alpha=.15)
    for ax,label in zip(axs[1:],['1D','4H','1H']):
        ax.set_yticks([-1,0,1]);ax.set_yticklabels(['BEAR','inactive','BULL']);ax.set_ylabel(label);ax.grid(alpha=.2)
    peak=q.loc[q.Price.idxmax(),'T'];axs[0].axvline(peak,color='red',ls='--');axs[0].set_ylabel('BTC spot, USD');axs[0].set_title('Logged price and ACTIVE BOS states (UTC); grey = missing log >75 min')
    fig.autofmt_xdate();fig.tight_layout();fig.savefig(O/(name+'.png'),dpi=140);plt.close(fig)
