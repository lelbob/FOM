"""One-time source update for the PRD 2.2 local simulation."""
from pathlib import Path
root=Path(__file__).resolve().parent
p=root/'server.py'
s=p.read_text(encoding='utf-8')
def replace(old,new):
    global s
    assert old in s, old[:100]
    s=s.replace(old,new)
replace("fields = ['id'", "fields = ['merchant','environment','settlement_model','provider_profile','id'")
replace("    return out\n\ndef journal", """    out['environment']='simulation'
    if r.get('settlement_model')=='merchant_direct':
        out['settlement_status']=r.get('payout','not_started')
        if r['kind']=='request' and r.get('payment_id'): out['settlement_status']=payment['payout']
    if private and (out['is_payer'] or out['is_buyer']) and r.get('collection_ref'):
        out['payment_action']={'kind':'qr' if r.get('provider_profile')=='qr' else 'hosted_checkout',
            'checkout_url':'/authorization.html#'+r['id'], 'reference':r['collection_ref'],
            'expires_at':r.get('quote_expires'),'environment':'simulation'}
    return out

def journal""")
replace("    fields=['net','fee'", "    fields=['merchant','provider_profile','settlement_model','net','fee'")
replace("    kind=job['type']; n=", "    if job['type']=='settlement': return\n    kind=job['type']; n=")
replace("    require(kind=='refund' or available_float", "    if kind=='payout' and r.get('settlement_model')=='merchant_direct': kind='settlement'\n    require(kind in ['refund','settlement'] or available_float")
replace("else 'payout_pending')", "else 'settlement_pending' if kind=='settlement' else 'payout_pending')")
replace("    journal(db,r,'collection:'+rid", "    if r.get('settlement_model')=='merchant_direct':\n        postings=[('merchant_provider_clearing',r['total']),('merchant_settlement_due',-r['net']),('merchant_fee_due',-r['fee'])]\n    journal(db,r,'collection:'+rid")
replace("if available_float(db)<r['net'] or r.get('scenario')=='insufficient_float':", "if r.get('settlement_model')!='merchant_direct' and (available_float(db)<r['net'] or r.get('scenario')=='insufficient_float'):")
replace("        journal(db,r,job['id']", "        if job['type']=='settlement':\n            postings=[('merchant_provider_clearing',-r['total']),('merchant_settlement_due',r['net']),('merchant_fee_due',r['fee'])]\n        journal(db,r,job['id']")
replace("state='refunded' if job['type']=='refund' else 'completed'", "state='refunded' if job['type']=='refund' else 'settled' if job['type']=='settlement' else 'completed'")
replace("        name=text(b.get('name')", """        merchant=None
        if b.get('merchant_setup') is True and kind!='escrow':
            row=db.execute('SELECT data FROM merchants WHERE actor=?',(actor,)).fetchone()
            require(row is not None,'Set up your demo merchant first.',409)
            merchant=json.loads(row['data'])
            require(merchant['status']=='approved','Demo merchant verification is pending.',409)
            b=dict(b,name=merchant['display_name'],rail=merchant['rail'],destination=merchant['account'],demo_verified=True)
        name=text(b.get('name')""")
replace("        if kind!='shop':", "        if merchant: data.update(merchant={k:v for k,v in merchant.items() if k!='account'},settlement_model='merchant_direct',provider_profile=merchant['profile'],environment='simulation')\n        if kind!='shop':")
replace("        require(available_float(db)>=net", "        require(r.get('settlement_model')=='merchant_direct' or available_float(db)>=net")
replace("        if r['kind']=='request': r['payment_id']", "        for field in ['merchant','settlement_model','provider_profile','environment']:\n            if field in r: p[field]=r[field]\n        save(db,p)\n        if r['kind']=='request': r['payment_id']")
replace("        require(available_float(db)>=r['net']", "        require(r.get('settlement_model')=='merchant_direct' or available_float(db)>=r['net']")
replace("            if path=='/api/session':", """            if path=='/api/merchant':
                with connection() as db:
                    s=self.session(db)
                    require(s and s['role']=='customer','Private customer access required.',401)
                    row=db.execute('SELECT data FROM merchants WHERE actor=?',(s['actor'],)).fetchone()
                    self.respond({'merchant':json.loads(row['data']) if row else None})
                return
            if path=='/api/session':""")
replace("                if path=='/api/drafts':", """                if path=='/api/merchant':
                    require(s['role']=='customer','Private customer access required.',403)
                    require(b.get('demo_verified') is True,'Confirm fictional merchant details.')
                    profile=b.get('profile','hosted');require(profile in ['hosted','qr'],'Choose hosted or QR demo checkout.')
                    rail=b.get('rail','KPay');require(rail in METHODS,'Unsupported demo account.')
                    previous=db.execute('SELECT data FROM merchants WHERE actor=?',(s['actor'],)).fetchone()
                    version=json.loads(previous['data'])['version']+1 if previous else 1
                    account=text(b.get('account'),'Fictional account',5,30)
                    m=dict(id='demo-merchant:'+s['actor'],display_name=text(b.get('display_name'),'Merchant name',1,60),payment_name=text(b.get('display_name'),'Merchant name',1,60),rail=rail,account=account,account_mask='•• '+account[-4:],profile=profile,status='approved',environment='simulation',version=version,settlement_timing='Automatic demo settlement after collection; no live schedule agreed')
                    db.execute('INSERT INTO merchants VALUES (?,?) ON CONFLICT(actor) DO UPDATE SET data=excluded.data',(s['actor'],encode(m)))
                    event(db,m['id'],s['actor'],'merchant.demo_approved','Fictional profile; verification is simulated')
                    self.respond({'merchant':m});return
                if path=='/api/drafts':""")
# Reconciliation includes provider-held merchant funds without recording platform cash.
replace("l.account=\\'provider_cash\\'", "l.account IN (\\'provider_cash\\',\\'merchant_provider_clearing\\')")
p.write_text(s,encoding='utf-8')
p=root/'providers.py';s=p.read_text()
s=s.replace("        submit=SimulatedProvider.submit_refund", "        if job['type']=='settlement': return SimulatedProvider._record_instruction(db,job,scenario,created)\n        submit=SimulatedProvider.submit_refund")
p.write_text(s)
p=root/'check_database.py';s=p.read_text();s=s.replace("l.account='provider_cash'", "l.account IN ('provider_cash','merchant_provider_clearing')");p.write_text(s)
