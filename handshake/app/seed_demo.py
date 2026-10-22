"""Optional: add clearly named local walkthrough records without clearing existing data."""
import argparse
import http.cookiejar
import json
import secrets
import os
import time
import urllib.request

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url',default='http://127.0.0.1:8800')
parser.add_argument('--scenario', choices=['success','payout_failed','payout_unknown','insufficient_float','duplicate_events'], default='success')
args=parser.parse_args()

class Client:
    def __init__(self):
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def post(self,path,body):
        request=urllib.request.Request(args.url+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-Handshake':'1'})
        with self.opener.open(request) as response:return json.loads(response.read())
    def command(self,r,action,**values):
        return self.post('/api/records/'+r['id']+'/'+action,dict(values,command_id=secrets.token_hex(16)))['record']

seller,buyer,finance=Client(),Client(),Client()
finance.post('/api/session/staff',{'username':'finance-a','password':os.environ.get('HANDSHAKE_STAFF_PASSWORD','handshake-demo-2026')})
seller_access=seller.post('/api/session/create',{})
buyer_access=buyer.post('/api/session/create',{})
records=[]
for kind,title in [('request','Demo payment request'),('shop','Demo neighbourhood shop'),('escrow','Demo headphones — review case')]:
    r=seller.post('/api/create',dict(kind=kind,name=title,item=title,description='Clearly labeled local demonstration record.',delivery='Direct handover by agreement',window='24 hours after confirmed receipt',net=10000,rail='KPay',destination='demo-4821',demo_verified=True,command_id=secrets.token_hex(16)))['record']
    records.append(r)
    if kind=='request':
        if args.scenario not in ['success','duplicate_events']:
            r=finance.command(r,'scenario',scenario=args.scenario,reason='Deterministic local seed scenario')
        payment=buyer.command(r,'pay-intent')
        buyer.command(payment,'authorize',agree=True,method='UAB Pay')
        buyer.post('/api/simulate/'+payment['id'],{'outcome':'confirmed'})
        if args.scenario=='duplicate_events':
            buyer.post('/api/simulate/'+payment['id'],{'outcome':'confirmed'})
            buyer.post('/api/simulate/'+payment['id'],{'outcome':'pending'})
        records.append(payment)
    if kind=='escrow':
        r=buyer.command(r,'join',agree=True,invitation=r['invitation'])
        buyer.command(r,'authorize',agree=True,method='KPay')
        buyer.post('/api/simulate/'+r['id'],{'outcome':'confirmed'})
        buyer.command(r,'dispute',reason='Demo case: the delivered item does not match the agreement.')
print('Added labeled local '+args.scenario+' acceptance payment, permanent shop and funded disputed escrow. Existing records were preserved.')
for r in records:print(r['kind']+': '+args.url+'/#record/'+r['id'])
print('Demo seller recovery key (private): '+seller_access['recovery'])
print('Demo buyer recovery key (private): '+buyer_access['recovery'])
print('Staff can inspect the case in the workspace using the documented local demo credentials.')
