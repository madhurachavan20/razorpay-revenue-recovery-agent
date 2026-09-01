from pathlib import Path
from typing import Optional
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
RECOMMENDATIONS_FILE = DATA_DIR / 'recovery_recommendations.csv'
PAYMENTS_FILE = DATA_DIR / 'payments.csv'

app = FastAPI(title='RevenueOS - Revenue Recovery Agent', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

def load_csv(path: Path, label: str):
    if not path.exists(): raise HTTPException(404, f'{label} not found: {path}')
    try: return pd.read_csv(path)
    except Exception as e: raise HTTPException(500, f'Could not read {label}: {e}')

def recs():
    df=load_csv(RECOMMENDATIONS_FILE,'Recovery recommendations')
    for c in ['amount','expected_recovery_value','recovery_probability']:
        if c in df: df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0)
    for c in ['transaction_id','customer_id','payment_method','failure_reason','failure_category','priority','recommended_action']:
        if c in df: df[c]=df[c].fillna('UNKNOWN').astype(str).str.strip()
    for c in ['payment_method','failure_reason','failure_category','priority']:
        if c in df: df[c]=df[c].str.upper()
    return df

def pays():
    df=load_csv(PAYMENTS_FILE,'Payments')
    if 'amount' in df: df['amount']=pd.to_numeric(df['amount'],errors='coerce').fillna(0)
    for c in ['status','payment_method','failure_reason']:
        if c in df: df[c]=df[c].fillna('').astype(str).str.strip().str.upper()
    return df

def safe_records(df): return df.where(pd.notna(df),'').to_dict(orient='records')

def priorities(df):
    out={'HIGH':0,'MEDIUM':0,'LOW':0}
    if 'priority' in df:
        vc=df['priority'].astype(str).str.upper().value_counts()
        for k in out: out[k]=int(vc.get(k,0))
    return out

def breakdown(df, group, money):
    if group not in df: return []
    cols={'failed_payments':('transaction_id','count'),'revenue_at_risk':('amount','sum'),'expected_recovery':('expected_recovery_value','sum')}
    g=df.groupby(group,dropna=False).agg(**cols).reset_index().sort_values('failed_payments',ascending=False)
    return safe_records(g.round(2))

@app.get('/')
def root(): return {'service':'RevenueOS','status':'online','dashboard':'/dashboard/summary','docs':'/docs'}
@app.get('/health')
def health(): return {'status':'healthy','service':'RevenueOS'}

@app.get('/dashboard/summary')
def dashboard_summary():
    p=pays(); r=recs(); total=len(p)
    success=int((p['status']=='SUCCESS').sum()) if 'status' in p else 0
    failed=int((p['status']=='FAILED').sum()) if 'status' in p else len(r)
    risk=float(r['amount'].sum()) if 'amount' in r else 0
    expected=float(r['expected_recovery_value'].sum()) if 'expected_recovery_value' in r else 0
    top=r.sort_values('expected_recovery_value',ascending=False).head(10) if 'expected_recovery_value' in r else r.head(10)
    methods=breakdown(r,'payment_method','amount')
    failures=breakdown(r,'failure_category','amount')
    reasons=[]
    if 'failure_reason' in r:
        x=r.groupby('failure_reason').agg(failed_payments=('transaction_id','count')).reset_index().sort_values('failed_payments',ascending=False)
        reasons=safe_records(x)
    return {'status':'success','payment_metrics':{'total_transactions':total,'successful_payments':success,'failed_payments':failed,'success_rate':success/total if total else 0,'failure_rate':failed/total if total else 0,'total_transaction_value':float(p['amount'].sum()) if 'amount' in p else 0},'recovery_metrics':{'total_failed_payments':len(r),'revenue_at_risk':risk,'expected_recovery':expected,'recovery_rate':expected/risk if risk else 0,'average_recovery_probability':float(r['recovery_probability'].mean()) if 'recovery_probability' in r else 0},'priority_distribution':priorities(r),'payment_method_breakdown':methods,'failure_category_breakdown':failures,'failure_reason_breakdown':reasons,'top_opportunities':safe_records(top)}

@app.get('/metrics')
def metrics():
    d=dashboard_summary(); return {'total_failed_payments':d['recovery_metrics']['total_failed_payments'],'total_expected_recovery':d['recovery_metrics']['expected_recovery'],'priority_distribution':d['priority_distribution']}

@app.get('/recovery-opportunities')
def recovery_opportunities(priority: Optional[str]=Query(None), limit:int=Query(50,ge=1,le=500)):
    df=recs(); selected=None
    if priority:
        selected=priority.strip().upper()
        if selected not in {'HIGH','MEDIUM','LOW'}: raise HTTPException(400,'Priority must be HIGH, MEDIUM, or LOW.')
        df=df[df['priority']==selected]
    if 'expected_recovery_value' in df: df=df.sort_values('expected_recovery_value',ascending=False)
    df=df.head(limit)
    return {'status':'success','count':len(df),'priority':selected,'data':safe_records(df)}

@app.get('/recovery-opportunities/{transaction_id}')
def recovery_one(transaction_id:str):
    df=recs(); m=df[df['transaction_id'].astype(str).str.strip()==transaction_id.strip()]
    if m.empty: raise HTTPException(404,'Transaction not found.')
    return safe_records(m.head(1))[0]

@app.get('/payments/summary')
def payment_summary():
    p=pays(); total=len(p); s=int((p['status']=='SUCCESS').sum()); f=int((p['status']=='FAILED').sum())
    return {'total_transactions':total,'successful_payments':s,'failed_payments':f,'success_rate':s/total if total else 0,'failure_rate':f/total if total else 0,'total_transaction_value':float(p['amount'].sum()) if 'amount' in p else 0}

@app.get('/payments')
def payments(status:Optional[str]=Query(None), limit:int=Query(100,ge=1,le=1000)):
    df=pays()
    if status:
        st=status.strip().upper()
        if st not in {'SUCCESS','FAILED'}: raise HTTPException(400,'Status must be SUCCESS or FAILED.')
        df=df[df['status']==st]
    return {'status':'success','count':min(len(df),limit),'data':safe_records(df.head(limit))}

@app.get('/customers')
def customers(limit:int=Query(100,ge=1,le=1000)):
    df=recs()
    if 'customer_id' not in df: return {'status':'success','count':0,'data':[]}
    g=df.groupby('customer_id').agg(failed_payments=('transaction_id','count'),revenue_at_risk=('amount','sum'),expected_recovery=('expected_recovery_value','sum'),average_recovery_probability=('recovery_probability','mean')).reset_index().sort_values('expected_recovery',ascending=False).head(limit)
    return {'status':'success','count':len(g),'data':safe_records(g.round(4))}

@app.get('/analytics/overview')
def analytics_overview():
    d=dashboard_summary(); return {**d['payment_metrics'], 'revenue_at_risk':d['recovery_metrics']['revenue_at_risk'],'expected_recovery':d['recovery_metrics']['expected_recovery'],'recovery_rate':d['recovery_metrics']['recovery_rate']}
@app.get('/analytics/payment-methods')
def analytics_methods(): return dashboard_summary()['payment_method_breakdown']
@app.get('/analytics/failure-categories')
def analytics_failures(): return dashboard_summary()['failure_category_breakdown']
@app.get('/analytics/recovery-priorities')
def analytics_priorities():
    d=dashboard_summary(); return [{'priority':k,'opportunities':v} for k,v in d['priority_distribution'].items()]
