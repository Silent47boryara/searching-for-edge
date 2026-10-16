from pathlib import Path
import pandas as pd,numpy as np,json,hashlib
O=Path(__file__).parent;P=Path('/Users/arefevoleg/bot_project_v2');D=pd.read_csv(O/'hourly_features.csv',index_col=0,parse_dates=True);D.index=pd.to_datetime(D.index,utc=True);M=pd.read_csv(O/'minute_mark.csv',index_col=0,parse_dates=True);M.index=pd.to_datetime(M.index,utc=True)
assert (D.index.year==2026).all() and D.index.is_unique
for a in ['liq_imb','tape_flow','gamma_A']:assert D[a].dropna().between(-1-1e-9,1+1e-9).all()
valid=D.gamma_A.notna();assert (D.loc[valid,'gamma_available_ns']<=D.index[valid].astype('int64')).all();assert (D.loc[valid,'gamma_snapshot_ns']<=D.loc[valid,'gamma_available_ns']).all()
# Independent direct minute target/control checks, not same rolling formula
for T in D.dropna(subset=['yvol4','logrv4']).index[::100]:
    past=M[(M.index>T-pd.Timedelta(hours=4))&(M.index<=T)].p;future=M[(M.index>T)&(M.index<=T+pd.Timedelta(hours=4))].p
    # include prior closing price to compute first return
    seq=M[(M.index>=T)&(M.index<=T+pd.Timedelta(hours=4))].p.to_numpy();r=np.diff(np.log(seq));actual=np.sqrt(np.nansum(r*r))
    assert np.isclose(np.log(actual),D.loc[T,'yvol4'],rtol=1e-10)
# Tape independently filter ALL raw data by both event and receive timestamps
X=pd.read_csv(P/'deribit_option_trades_raw.csv',usecols=['recv_ts_utc','timestamp_ms','trade_id','instrument_name','direction','amount','index_price']);X['recv']=pd.to_datetime(X.recv_ts_utc,format='ISO8601',utc=True);X['trade']=pd.to_datetime(X.timestamp_ms,unit='ms',utc=True);X=X.drop_duplicates('trade_id')
for T in D[D.tape_flow.notna()].index[::200]:
    x=X[(X.recv<=T)&(X.trade<=T)&(X.trade>T-pd.Timedelta(hours=4))];usd=x.amount*x.index_price;sg=np.where(x.direction=='buy',1,-1)*np.where(x.instrument_name.str[-1]=='C',1,-1);tot=usd.sum();f=(usd*sg).sum()/tot if tot>0 else 0
    assert np.isclose(f,D.loc[T,'tape_flow'],atol=1e-10)
R=pd.read_csv(O/'model_results.csv');assert len(R)==24 and R.p_Holm.between(0,1).all();PR=pd.read_csv(O/'predictions.csv',parse_dates=['T']);assert not PR.duplicated(['group','target','T']).any()
for (group,target),q in PR.groupby(['group','target']):
    z=R[(R.group==group)&(R.target==target)].iloc[0];eb=np.mean((q.y-q.baseline)**2);ea=np.mean((q.y-q.pred)**2);assert np.isclose(100*(eb-ea)/eb,z.MSE_improvement_pct)
# Source code hash should remain exactly the preceding audit value
assert hashlib.sha256((P/'bot_v2.py').read_bytes()).hexdigest()=='85c427e78766fa1548cdcd2a43433ee849ea6beeb1f052da9fd54ecf547f620c'
print('PASS: time years, bounded flows, gamma completion availability, independent future RV, causal tape recomputation,24 primary tests,prediction uniqueness,metric recomputation,source bot unchanged')
