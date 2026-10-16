import os
os.environ['MPLCONFIGDIR']='/private/tmp/bos_mpl'
from pathlib import Path
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).parent;r=pd.read_csv(O/'model_results.csv');groups=r.group.drop_duplicates().tolist();names={'OI':'OI','funding':'Funding','liquidations':'Liquidations','gamma':'Gamma','tape':'Option tape','OI+funding':'OI + funding','OI+liquidations':'OI + liquidations','OI+tape':'OI + tape','funding+liquidations':'Funding + liquidations','gamma+tape':'Gamma + tape','liquidations+tape':'Liquidations + tape','all5':'All five'}
fig,axs=plt.subplots(1,2,figsize=(12,6.5),sharey=True)
for ax,target,title in zip(axs,['yret4','yvol4'],['Next 4h return','Next 4h realized volatility']):
    z=r[r.target==target].set_index('group').loc[groups];v=z.MSE_improvement_pct.to_numpy();lo=z.CI_lo.to_numpy();hi=z.CI_hi.to_numpy();y=np.arange(len(groups));ax.errorbar(v,y,xerr=[v-lo,hi-v],fmt='o',color='#3573a3',capsize=3);ax.axvline(0,color='black',lw=1);ax.set_title(title);ax.set_xlabel('MSE improvement over price-only, %');ax.grid(axis='x',alpha=.2);ax.set_yticks(y);ax.set_yticklabels([names[x] for x in groups]);ax.invert_yaxis()
fig.suptitle('Forward chronological tests; 24h block bootstrap intervals',fontsize=13);fig.text(.02,.02,'Positive = better than price-only. Samples differ by data availability (51–119 cases). No primary test significant.',fontsize=9);fig.tight_layout(rect=[0,.07,1,.95]);fig.savefig(O/'forward_comparison.png',dpi=145)
# One illustrative observed unwind (selected after analysis, NOT validation)
d=pd.read_csv(O/'hourly_features.csv',index_col=0,parse_dates=True);q=d.loc['2026-10-07':'2026-10-09'];fig,axs=plt.subplots(3,1,figsize=(11,7),sharex=True)
axs[0].plot(q.index,q.price,color='black');axs[0].set_ylabel('Mark price, USD');axs[0].set_title('Illustration: Oct 8 sell-off with OI reduction and long liquidations (UTC)')
axs[1].plot(q.index,q.oi/1000,color='#3b7198');axs[1].set_ylabel('OI, thousand BTC')
axs[2].bar(q.index,q.liq_usd/1e6,width=.025,color=np.where(q.liq_imb<0,'#c36363','#579375'));axs[2].set_ylabel('Liquidations, USD mn\nrolling 4h');axs[2].set_xlabel('Red = long liquidations dominate; green = short. Overlapping windows, not incremental hourly totals.')
for ax in axs:ax.grid(alpha=.2)
fig.autofmt_xdate();fig.tight_layout();fig.savefig(O/'unwind_example.png',dpi=145)
