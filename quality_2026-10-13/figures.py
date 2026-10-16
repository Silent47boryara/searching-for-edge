import os
os.environ['MPLCONFIGDIR']='/private/tmp/bos_mpl'
from pathlib import Path
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).parent;m=pd.read_csv(O/'metrics.csv')
fig,axs=plt.subplots(1,2,figsize=(12,4.5))
models=['original','lag_fixed','fallback_contract','ema20'];names=['BOS original','Lag corrected','Initial level exit*','EMA20 reference']
for k,tf in enumerate(['1h','4h','1d']):
    v=m[(m.scope=='all')&(m.tf==tf)].set_index('model');axs[0].bar(np.arange(4)+k*.25-.25,[100*v.loc[x,'BA'] for x in models],width=.24,label=tf)
axs[0].set_xticks(range(4));axs[0].set_xticklabels(names,rotation=15,ha='right');axs[0].set_ylabel('Balanced descriptive score, %');axs[0].set_ylim(0,100);axs[0].legend();axs[0].set_title('Historical local-direction agreement')
x=np.arange(3)
q=m[(m.scope=='gamma')&(m.model=='original')].set_index('tf').loc[['1h','4h','1d']]
a=q.active_same_pct.to_numpy();b=q.active_flat_pct.to_numpy();c=q.active_opposite_pct.to_numpy()
axs[1].bar(x,a,color='#3c9a65',label='same direction');axs[1].bar(x,b,bottom=a,color='#b8b8b8',label='neutral');axs[1].bar(x,c,bottom=a+b,color='#cf655d',label='opposite');axs[1].set_xticks(x);axs[1].set_xticklabels(['1H','4H','1D']);axs[1].set_ylim(0,100);axs[1].set_ylabel('% of ACTIVE BOS bars');axs[1].set_title('Gamma period: what ACTIVE accompanies');axs[1].legend(fontsize=8)
fig.suptitle('Descriptive diagnostics, NOT trading accuracy or P&L',fontsize=12);fig.text(.02,.01,'Reference: trailing 12-bar displacement vs 1 ATR. *Specification change. EMA switches more often.',fontsize=8);fig.tight_layout(rect=[0,.06,1,.94]);fig.savefig(O/'quality_summary.png',dpi=150)
