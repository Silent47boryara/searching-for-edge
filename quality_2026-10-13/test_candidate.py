import pandas as pd,numpy as np
import candidate_helpers as H
from candidate_core import _detect_swings,find_all_bos
assert H.active_direction({'state':'ENDED','direction':'BULL'}) is None
assert H.active_direction({'state':'ACTIVE','direction':'BULL'})=='BULL'
assert 'ACTIVE' not in H.summarize_layers(*[{'state':'ENDED','direction':'BULL'}]*3)
assert H.analyze_closed_frame(None,'1h','2026-10-13T12:00Z')['state']=='DATA_UNAVAILABLE'
from pathlib import Path
P=Path('/Users/arefevoleg/bot_project_v2');d=pd.read_csv(P/'LAB_attrib_p1/raw/BTCUSDT_1h_binance_raw.csv');d['Open time']=pd.to_datetime(d.open_time_ms,unit='ms',utc=True)
a=H.analyze_closed_frame(d,'1h','2026-09-23T04:30Z');b=H.analyze_closed_frame(d[d['Open time']<pd.Timestamp('2026-09-23T04:00Z')],'1h','2026-09-23T04:30Z')
assert a==b and a['data_as_of_utc']=='2026-09-23 04:00:00+00:00'
x=d[(d['Open time']>pd.Timestamp('2026-09-01',tz='UTC'))&(d['Open time']<pd.Timestamp('2026-09-10',tz='UTC'))].iloc[::2]
assert H.analyze_closed_frame(x,'1h','2026-10-13T12:00Z')['state']=='DATA_UNAVAILABLE'
print('7 candidate contract checks PASS')
