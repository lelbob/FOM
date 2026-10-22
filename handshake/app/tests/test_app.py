"""Integration checks against real HTTP sessions and a temporary SQLite database."""
import concurrent.futures
import hashlib
import hmac
import http.cookiejar
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server as app

class Client:
    def __init__(self, base):
        self.base=base
        self.http=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def call(self,path,body=None,headers=None):
        request=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers or ({'Content-Type':'application/json','X-Handshake':'1'} if body is not None else {}))
        try:
            with self.http.open(request,timeout=15) as response:return response.status,json.loads(response.read())
        except urllib.error.HTTPError as error:return error.code,json.loads(error.read())
    def customer(self):return self.call('/api/session/create',{})[1]
    def staff(self,name):return self.call('/api/session/staff',{'username':name,'password':app.STAFF_PASSWORD})
    def command(self,r,action,**data):
        data.setdefault('command_id',app.uid('cmd'))
        return self.call('/api/records/'+r['id']+'/'+action,data)

class IntegrationHarness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db=app.DB
        cls.http=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        cls.http.lookups={};cls.http.logins={}
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.http.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();app.DB=cls.original_db
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();app.DB=Path(self.temp.name)/'test.sqlite3';app.initialize()
        self.http.logins={};self.http.lookups={}
        self.seller=Client(self.base);self.seller.customer()
        self.buyer=Client(self.base);self.buyer.customer()
        self.public=Client(self.base)
    def tearDown(self):self.temp.cleanup()
    def create(self,kind='escrow',net=10000):
        status,result=self.seller.call('/api/create',dict(kind=kind,name='Aye',net=net,rail='KPay',destination='demo-4821',demo_verified=True,item='Headphones',description='Agreed headphones',delivery='Direct handover tomorrow',window='24 hours after confirmed receipt',command_id=app.uid('create')))
        self.assertEqual(status,200,result)
        return result['record']
    def join(self,r):
        status,data=self.buyer.command(r,'join',agree=True,invitation=r['invitation']);self.assertEqual(status,200,data);return data['record']
    def intent(self,r,net=10000,client=None):
        status,data=(client or self.buyer).command(r,'pay-intent',net=net);self.assertEqual(status,200,data);return data['record']
    def pay(self,r):
        status,data=self.buyer.command(r,'authorize',agree=True,method='UAB Pay');self.assertEqual(status,200,data)
        status,data=self.buyer.call('/api/simulate/'+r['id'],{'outcome':'confirmed'});self.assertEqual(status,200,data);return data['record']
    def settle(self):
        with app.connection(True) as db:db.execute('UPDATE jobs SET due=0')
        app.process_jobs()
    def get(self,r,client=None):
        status,data=(client or self.buyer).call('/api/records/'+r['id']);self.assertEqual(status,200,data);return data['record']
    def staff(self,name):
        c=Client(self.base);self.assertEqual(c.staff(name)[0],200);return c
    def scenario(self,r,value):
        c=self.staff('finance-a');self.assertEqual(c.command(r,'scenario',scenario=value,reason='Deterministic integration scenario')[0],200)
    def balances(self):
        with app.connection() as db:
            return [tuple(r) for r in db.execute('SELECT journal,SUM(amount) FROM ledger GROUP BY journal')]

class Integration(IntegrationHarness):
    def test_escrow_happy_path_and_persistent_shared_state(self):
        r=self.create();r=self.join(r);r=self.pay(r);self.assertEqual(r['state'],'held')
        self.assertEqual(self.get(r,self.seller)['state'],'held')
        self.assertEqual(self.seller.command(r,'deliver')[0],200)
        self.assertEqual(self.get(r)['state'],'delivered')
        self.assertEqual(self.buyer.command(r,'release',agree=True)[0],200)
        self.assertEqual(self.get(r,self.seller)['state'],'release_pending')
        self.settle();self.assertEqual(self.get(r)['state'],'completed')
        app.initialize();self.assertEqual(self.get(r,self.seller)['state'],'completed')
        self.assertTrue(all(total==0 for _,total in self.balances()))
    def test_public_links_cannot_join_without_private_invitation_or_release(self):
        r=self.create();public=self.get(r,self.public)
        self.assertNotIn('invitation',public);self.assertNotIn('destination',public);self.assertNotIn('events',public)
        self.assertEqual(self.public.command(r,'release',agree=True)[0],401)
        self.assertEqual(self.buyer.command(r,'join',agree=True,invitation=r['code'])[0],403)
        r=self.join(r);r=self.pay(r)
        outsider=Client(self.base);outsider.customer()
        self.assertEqual(outsider.command(r,'release',agree=True)[0],403)
        self.assertEqual(self.seller.command(r,'release',agree=True)[0],403)
    def test_request_success_collection_not_payout(self):
        source=self.create('request');r=self.intent(source);r=self.pay(r)
        self.assertEqual(r['collection'],'confirmed');self.assertEqual(r['state'],'payout_pending');self.assertNotEqual(r['payout'],'confirmed')
        self.settle();self.assertEqual(self.get(r)['state'],'completed')
    def test_three_independent_shop_payments_and_pause(self):
        shop=self.create('shop');ids=[]
        for net in [3000,5000,10000]:
            p=self.intent(shop,net);ids.append(p['id']);self.pay(p)
        self.assertEqual(len(set(ids)),3);self.settle()
        self.assertEqual(self.seller.command(shop,'pause')[0],200)
        self.assertEqual(self.buyer.command(shop,'pay-intent',net=10000)[0],409)
        self.assertEqual(self.get({'id':ids[0]})['state'],'completed')
    def test_single_use_request_concurrency(self):
        r=self.create('request');other=Client(self.base);other.customer()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results=list(pool.map(lambda c:c.command(r,'pay-intent',net=10000),[self.buyer,other]))
        self.assertEqual(sorted(x[0] for x in results),[200,409])
        with app.connection() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM records WHERE kind='payment'").fetchone()[0],1)
    def test_same_payer_resumes_request(self):
        r=self.create('request');a=self.intent(r);b=self.intent(r)
        self.assertEqual(a['id'],b['id'])
    def test_duplicate_callbacks_deduplicate_receipts_and_balances(self):
        r=self.intent(self.create('request'));self.buyer.command(r,'authorize',agree=True,method='KPay')
        authorized=self.get(r)
        payload={'record_id':r['id'],'event_id':'event-one','receipt_id':'receipt-one','amount':r['total'],'currency':'MMK','reference':authorized['collection_reference'],'method':'KPay','final':True}
        def callback(p):
            raw=json.dumps(p).encode()
            with app.connection() as db:secret=app.settings(db,'callback_secret')
            headers={'Content-Type':'application/json','X-Provider-Signature':hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()}
            return self.public.call('/api/provider/callback',p,headers)
        self.assertEqual(callback(payload)[0],200);self.assertEqual(callback(payload)[0],200)
        self.assertEqual(callback(dict(payload,event_id='event-two'))[0],200)
        self.assertEqual(callback(dict(payload,event_id='event-three',receipt_id='receipt-two'))[0],202)
        self.assertEqual(callback(dict(payload,amount=r['total']+1))[0],409)
        self.assertEqual(callback(dict(payload,currency='USD'))[0],409)
        self.assertEqual(callback(dict(payload,reference='wrong-reference'))[0],409)
        self.assertEqual(callback(dict(payload,final=False))[0],409)
        self.settle();self.settle()
        with app.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM callbacks').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],1)
            self.assertEqual(db.execute("SELECT SUM(amount) FROM ledger WHERE account='receipt_suspense'").fetchone()[0],-r['total'])
        self.assertTrue(all(total==0 for _,total in self.balances()))
    def test_unsigned_and_out_of_order_callback_denied(self):
        r=self.intent(self.create('request'))
        self.assertEqual(self.public.call('/api/provider/callback',{'record_id':r['id']})[0],403)
        self.assertEqual(self.buyer.call('/api/simulate/'+r['id'],{'outcome':'confirmed'})[0],409)
    def test_dispute_blocks_queued_release_atomically(self):
        r=self.pay(self.join(self.create()));self.seller.command(r,'deliver')
        self.assertEqual(self.buyer.command(r,'release',agree=True)[0],200)
        self.assertEqual(self.seller.command(r,'dispute',reason='The delivery needs a human review')[0],200)
        self.settle();r=self.get(r);self.assertEqual(r['state'],'disputed');self.assertEqual(r['payout'],'blocked')
        self.assertEqual(self.buyer.command(r,'release',agree=True)[0],409)
        with app.connection() as db:
            self.assertEqual(db.execute("SELECT SUM(amount) FROM ledger WHERE account='payout_reserved'").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT SUM(amount) FROM ledger WHERE account='escrow_liability'").fetchone()[0],-r['net'])
    def test_support_cannot_make_finance_decisions(self):
        r=self.pay(self.join(self.create()));self.buyer.command(r,'dispute',reason='Item does not match agreed terms')
        support=self.staff('support')
        self.assertEqual(support.command(r,'note',reason='Requested clarification from both parties')[0],200)
        self.assertEqual(support.command(r,'review',reason='I reviewed all provided evidence')[0],403)
        self.assertEqual(support.command(r,'propose',decision='refund',reason='Refund the customer after review')[0],403)
    def test_independent_approval_and_refund(self):
        r=self.pay(self.join(self.create()));self.buyer.command(r,'dispute',reason='Item does not match agreed terms')
        a=self.staff('finance-a');b=self.staff('finance-b')
        self.assertEqual(a.command(r,'review',reason='Reviewed both parties and agreement')[0],200)
        self.assertEqual(a.command(r,'propose',decision='refund',reason='Full refund to original payer source')[0],200)
        proposal=self.get(r,a)['proposals'][0]
        self.assertEqual(a.command(r,'approve',proposal=proposal['id'],reason='Attempt to approve my own instruction')[0],403)
        self.assertEqual(a.command(r,'submit',proposal=proposal['id'],reason='Attempt submit before approval')[0],409)
        self.assertEqual(b.command(r,'approve',proposal=proposal['id'],reason='Independent review of refund instruction')[0],200)
        self.assertEqual(a.command(r,'submit',proposal=proposal['id'],reason='Dispatch approved original source refund')[0],200)
        self.settle();self.assertEqual(self.get(r)['state'],'refunded')
        self.assertTrue(all(total==0 for _,total in self.balances()))
    def test_unknown_is_queried_before_retry(self):
        source=self.create('request');self.scenario(source,'payout_unknown');r=self.intent(source);self.pay(r);self.settle()
        self.assertEqual(self.get(r)['state'],'payout_unknown')
        a=self.staff('finance-a')
        self.assertEqual(a.command(r,'propose',decision='retry',reason='Cannot retry an uncertain payout')[0],409)
        self.assertEqual(a.command(r,'query',reason='Query original provider reference')[0],409)
        self.assertEqual(a.command(r,'scenario',scenario='success',reason='Provider now has a confirmed result')[0],200)
        self.assertEqual(a.command(r,'query',reason='Query original provider reference again')[0],200)
        self.assertEqual(self.get(r)['state'],'completed');self.assertTrue(all(total==0 for _,total in self.balances()))
    def test_failed_payout_recovery(self):
        source=self.create('request');self.scenario(source,'payout_failed');r=self.intent(source);self.pay(r);self.settle()
        self.assertEqual(self.get(r)['state'],'payout_failed')
        a=self.staff('finance-a');b=self.staff('finance-b')
        a.command(r,'scenario',scenario='success',reason='Payout service has recovered now')
        self.assertEqual(a.command(r,'propose',decision='retry',reason='Original payout authoritatively failed')[0],200)
        pid=self.get(r,a)['proposals'][0]['id']
        self.assertEqual(b.command(r,'approve',proposal=pid,reason='Confirm safe retry with original quote')[0],200)
        self.assertEqual(a.command(r,'submit',proposal=pid,reason='Submit independently approved retry')[0],200)
        self.settle();self.assertEqual(self.get(r)['state'],'completed')
        with app.connection() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM jobs WHERE state='confirmed'").fetchone()[0],1)
    def test_private_recovery_across_sessions(self):
        original=Client(self.base);result=original.customer()
        old=self.seller;self.seller=original;r=self.create('shop');self.seller=old
        restored=Client(self.base);self.assertEqual(restored.call('/api/session/recover',{'recovery':result['recovery']})[0],200)
        self.assertTrue(self.get(r,restored)['is_owner'])
        self.assertEqual(restored.call('/api/session/recover',{'recovery':r['code']})[0],401)
    def test_idempotency_and_stale_versions(self):
        r=self.create();cmd=app.uid('join')
        data=dict(agree=True,invitation=r['invitation'],command_id=cmd,expected_version=r['version'])
        a=self.buyer.command(r,'join',**data);b=self.buyer.command(r,'join',**data)
        self.assertEqual(a,b);self.assertEqual(a[0],200)
        self.assertEqual(self.buyer.command(r,'join',**dict(data,agree=False))[0],409)
        self.assertEqual(self.buyer.command(r,'authorize',method='KPay',agree=True,expected_version=r['version'])[0],409)
    def test_expiry_and_late_confirmed_receipt(self):
        source=self.create('request');r=self.intent(source);self.buyer.command(r,'authorize',method='KPay',agree=True)
        with app.connection(True) as db:
            x=app.get_record(db,source['id']);x['expires']=0;app.save(db,x)
        self.assertEqual(self.buyer.call('/api/simulate/'+r['id'],{'outcome':'confirmed'})[0],200)
        self.settle();self.assertEqual(self.get(r)['state'],'completed')
        another=self.create('request')
        with app.connection(True) as db:
            x=app.get_record(db,another['id']);x['expires']=0;app.save(db,x)
        self.assertEqual(self.buyer.command(another,'pay-intent',net=10000)[0],409)
    def test_insufficient_float_prevents_collection_and_preserves_received_funds(self):
        source=self.create('request');self.scenario(source,'insufficient_float');r=self.intent(source);self.pay(r)
        self.assertEqual(self.get(r)['state'],'payout_failed');self.assertEqual(self.get(r)['collection'],'confirmed')
        with app.connection(True) as db:db.execute("UPDATE settings SET value='0' WHERE key='float'")
        shop=self.create('shop');self.assertEqual(self.buyer.command(shop,'pay-intent',net=10000)[0],409)
    def test_evidence_privacy_and_append_only_history(self):
        r=self.pay(self.join(self.create()));self.buyer.command(r,'dispute',reason='Item does not match agreed terms')
        self.assertEqual(self.buyer.command(r,'evidence',name='details.txt',mime='text/plain',content='aGVsbG8=')[0],200)
        file=self.get(r)['evidence'][0]
        self.assertEqual(self.public.call('/api/evidence/'+file['id'])[0],403)
        self.assertEqual(len(self.get(r,self.seller)['evidence']),1)
        with app.connection(True) as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute('DELETE FROM events')
            with self.assertRaises(sqlite3.IntegrityError):db.execute('UPDATE ledger SET amount=0')
    def test_validation_csrf_and_staff_access(self):
        self.assertEqual(self.public.call('/api/admin')[0],401)
        self.assertEqual(self.seller.call('/api/admin')[0],403)
        self.assertEqual(self.seller.call('/api/create',{'kind':'shop'},headers={'Content-Type':'application/json'})[0],403)
        body=dict(kind='request',name='Aye',rail='KPay',destination='demo-4821',demo_verified=True,net=1.5,command_id=app.uid('cmd'))
        self.assertEqual(self.seller.call('/api/create',body)[0],422)
        body['net']=True;self.assertEqual(self.seller.call('/api/create',body)[0],422)
    def test_reconciliation_and_route_pause(self):
        r=self.pay(self.intent(self.create('request')));self.settle()
        ops=self.staff('operations');status,result=ops.call('/api/admin')
        self.assertEqual(status,200);self.assertEqual(result['differences'],[])
        self.assertEqual(ops.call('/api/admin/route',{'open':False,'reason':'Planned provider maintenance window'})[0],200)
        shop=self.create('shop');self.assertEqual(self.buyer.command(shop,'pay-intent',net=10000)[0],409)
        self.assertEqual(self.get(r)['state'],'completed')
    def test_assignment_and_evidence_request_share_only_with_participants(self):
        r=self.pay(self.join(self.create()));self.buyer.command(r,'dispute',reason='The supplied item needs review')
        support=self.staff('support')
        self.assertEqual(support.command(r,'assign',assignee='finance-a',reason='Assign for financial case review')[0],200)
        self.assertEqual(support.command(r,'request-evidence',reason='Please upload a photo of the item')[0],200)
        self.assertEqual(self.get(r)['assignee'],'finance-a')
        self.assertIn('photo',self.get(r)['evidence_request'])
        self.assertNotIn('evidence_request',self.get(r,self.public))
    def test_stale_proposal_can_be_canceled_and_replaced(self):
        r=self.pay(self.join(self.create()));self.buyer.command(r,'dispute',reason='Item does not match the agreement')
        a=self.staff('finance-a');b=self.staff('finance-b')
        a.command(r,'review',reason='Reviewed terms and participant evidence')
        a.command(r,'propose',decision='refund',reason='Full original source refund after review')
        pid=self.get(r,a)['proposals'][0]['id']
        a.command(r,'note',reason='New evidence arrived after proposal')
        self.assertEqual(b.command(r,'approve',proposal=pid,reason='Attempt approval after record change')[0],409)
        self.assertEqual(a.command(r,'cancel',reason='Reconsider after new evidence arrived')[0],200)
        self.assertEqual(a.command(r,'propose',decision='refund',reason='Reviewed new evidence and retained refund')[0],200)
    def test_failed_refund_retry_preserves_original_source_instruction(self):
        r=self.pay(self.join(self.create()));self.buyer.command(r,'dispute',reason='Refund required for incorrect delivery')
        a=self.staff('finance-a');b=self.staff('finance-b')
        a.command(r,'review',reason='Reviewed the original source refund')
        a.command(r,'scenario',scenario='payout_failed',reason='Simulate initial refund transport failure')
        for action in ['refund','retry']:
            if action=='retry':a.command(r,'scenario',scenario='success',reason='Original source provider recovered')
            self.assertEqual(a.command(r,'propose',decision=action,reason='Use original payer source for refund')[0],200)
            p=self.get(r,a)['proposals'][0];self.assertEqual(p['amount'],r['total'])
            self.assertEqual(b.command(r,'approve',proposal=p['id'],reason='Independent approval of original source')[0],200)
            self.assertEqual(a.command(r,'submit',proposal=p['id'],reason='Submit original source refund instruction')[0],200)
            self.settle()
        self.assertEqual(self.get(r)['state'],'refunded')
        with app.connection() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM jobs WHERE type='payout'").fetchone()[0],0)

if __name__=='__main__':unittest.main(verbosity=2)
