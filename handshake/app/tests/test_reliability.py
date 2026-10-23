"""Regression tests for privacy, durable exceptions, instruction recovery and concurrency."""
import concurrent.futures
import hashlib
import hmac
import json
import sqlite3
import threading
from contextlib import closing
from unittest.mock import patch
from test_app import IntegrationHarness, Client, app


class Reliability(IntegrationHarness):
    def signed(self,payload):
        raw=json.dumps(payload).encode()
        with app.connection() as db:secret=app.settings(db,'callback_secret')
        return self.public.call('/api/provider/callback',payload,{'Content-Type':'application/json','X-Provider-Signature':hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()})

    def receipt(self,r,**overrides):
        r=self.get(r)
        return dict(dict(record_id=r['id'],event_id=app.uid('evt'),receipt_id=app.uid('receipt'),amount=r['total'],currency='MMK',reference=r['collection_reference'],method=r['method'],final=True),**overrides)

    def refund(self,r):
        a=self.staff('finance-a');b=self.staff('finance-b')
        self.assertEqual(a.command(r,'propose',decision='refund',reason='Refund confirmed unmatched original receipt')[0],200)
        proposal=self.get(r,a)['proposals'][0]
        self.assertEqual(b.command(r,'approve',proposal=proposal['id'],reason='Independent original source verification')[0],200)
        self.assertEqual(a.command(r,'submit',proposal=proposal['id'],reason='Submit approved original source refund')[0],200)
        self.settle()

    def test_payment_privacy_and_staff_notes_never_enter_participant_history(self):
        payment=self.intent(self.create('shop'))
        outsider=Client(self.base);outsider.customer()
        self.assertEqual(self.public.call('/api/records/'+payment['id'])[0],403)
        self.assertEqual(outsider.call('/api/records/'+payment['id'])[0],403)
        support=self.staff('support');support.command(payment,'note',reason='Internal confidential investigation note')
        self.assertNotIn('confidential',json.dumps(self.get(payment)))
        self.assertIn('confidential',json.dumps(self.get(payment,support)))

    def test_mismatched_and_extra_receipts_keep_separate_balanced_refund_liabilities(self):
        r=self.intent(self.create('request'))
        self.buyer.command(r,'authorize',method='UAB Pay',agree=True)
        payload=self.receipt(r,amount=r['total']-100)
        status,result=self.signed(payload);self.assertEqual(status,202,result)
        recovery=self.get({'id':result['recovery_id']})
        self.assertEqual(self.get(r)['collection'],'pending')
        self.assertEqual(recovery['total'],r['total']-100)
        self.assertEqual(self.signed(payload)[1]['recovery_id'],recovery['id'])
        a=self.staff('finance-a')
        self.assertEqual(a.command(recovery,'propose',decision='release',reason='Must not divert exceptional receipt')[0],409)
        self.refund(recovery)
        self.assertEqual(self.get(recovery)['state'],'refunded')
        self.assertEqual(self.signed(self.receipt(r))[0],200)
        extra=self.signed(self.receipt(r));self.assertEqual(extra[0],202)
        self.refund(self.get({'id':extra[1]['recovery_id']}))
        self.assertEqual(self.get(r)['state'],'completed')
        self.assertTrue(all(total==0 for _,total in self.balances()))
        with app.connection() as db:
            self.assertEqual(db.execute("SELECT SUM(amount) FROM ledger WHERE account='receipt_suspense'").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM provider_instructions WHERE outcome='confirmed'").fetchone()[0],3)

    def test_rejected_and_unmatched_authenticated_events_are_durable(self):
        r=self.intent(self.create('request'));self.buyer.command(r,'authorize',method='KPay',agree=True)
        bad=self.receipt(r,reference='wrong-authorization')
        self.assertEqual(self.signed(bad)[0],409)
        self.assertEqual(self.signed(bad)[0],409)
        unknown=self.receipt(r,record_id='pay-does-not-exist')
        self.assertEqual(self.signed(unknown)[0],404)
        self.assertEqual(self.signed(unknown)[0],404)
        result=self.staff('operations').call('/api/admin')[1]
        self.assertEqual(len(result['inbox']),2)
        self.assertEqual(len(result['differences']),2)
        self.assertEqual(self.get(r)['collection'],'pending')
        with app.connection(True) as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute('DELETE FROM provider_inbox')

    def test_late_old_attempt_is_refunded_without_fulfilling_twice(self):
        r=self.intent(self.create('request'));self.buyer.command(r,'authorize',method='KPay',agree=True)
        old=self.receipt(r)
        self.buyer.call('/api/simulate/'+r['id'],{'outcome':'failed'})
        self.buyer.command(r,'authorize',method='UAB Pay',agree=True)
        status,result=self.signed(old);self.assertEqual(status,202,result)
        self.refund(self.get({'id':result['recovery_id']}))
        self.assertEqual(self.get(r)['collection'],'pending')
        self.assertEqual(self.signed(self.receipt(r))[0],200);self.settle()
        self.assertEqual(self.get(r)['state'],'completed')

    def test_failed_job_does_not_starve_others_and_reuses_immutable_reference(self):
        first=self.pay(self.intent(self.create('request')))
        second=self.pay(self.intent(self.create('request')))
        with app.connection(True) as db:db.execute('UPDATE jobs SET due=0')
        original=app.provider.instruction_status
        def faulty(db,job,scenario,created):
            if job['record_id']==first['id']:raise TimeoutError('Deterministic transport interruption')
            return original(db,job,scenario,created)
        with patch.object(app.provider,'instruction_status',side_effect=faulty):app.process_jobs()
        self.assertEqual(self.get(first)['state'],'payout_pending')
        self.assertEqual(self.get(second)['state'],'completed')
        with app.connection() as db:
            job=dict(db.execute('SELECT * FROM jobs WHERE record_id=?',(first['id'],)).fetchone())
            self.assertIn('interruption',job['last_error'])
        app.initialize();self.settle();self.settle()
        with app.connection(True) as db:
            updated=db.execute('SELECT * FROM jobs WHERE id=?',(job['id'],)).fetchone()
            self.assertEqual(updated['reference'],job['reference'])
            self.assertEqual(updated['instruction'],job['instruction'])
            with self.assertRaises(sqlite3.IntegrityError):db.execute("UPDATE jobs SET instruction='changed' WHERE id=?",(job['id'],))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM provider_instructions').fetchone()[0],2)
        self.assertTrue(all(total==0 for _,total in self.balances()))

    def test_concurrent_release_dispute_never_dispatches_after_timely_dispute(self):
        r=self.pay(self.join(self.create()));self.seller.command(r,'deliver')
        barrier=threading.Barrier(2)
        def release():barrier.wait();return self.buyer.command(r,'release',agree=True)
        def dispute():barrier.wait();return self.seller.command(r,'dispute',reason='Timely dispute while both actions compete')
        with concurrent.futures.ThreadPoolExecutor() as pool:
            a=pool.submit(release);b=pool.submit(dispute);outcomes=[a.result()[0],b.result()[0]]
        self.assertIn(outcomes[0],[200,409]);self.assertEqual(outcomes[1],200)
        self.settle()
        self.assertEqual(self.get(r)['state'],'disputed')
        with app.connection() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM provider_instructions').fetchone()[0],0)

    def test_drafts_recover_privately_and_clear_only_after_creation(self):
        c=Client(self.base);access=c.customer()
        self.assertEqual(c.call('/api/drafts',dict(kind='escrow',name='Saved private draft',destination='demo-1234',item='Draft headphones'))[0],200)
        restored=Client(self.base);restored.call('/api/session/recover',{'recovery':access['recovery']})
        self.assertEqual(restored.call('/api/drafts')[1]['drafts']['escrow']['item'],'Draft headphones')
        self.assertEqual(self.seller.call('/api/drafts')[1]['drafts'],{})
        self.assertEqual(self.public.call('/api/drafts')[0],401)
        old=self.seller;self.seller=restored;self.create();self.seller=old
        self.assertEqual(restored.call('/api/drafts')[1]['drafts'],{})

    def test_migrations_preserve_legacy_data_and_are_repeatable(self):
        from pathlib import Path
        r=self.create();previous=app.DB;app.DB=Path(self.temp.name)/'legacy.sqlite3'
        try:
            with closing(sqlite3.connect(app.DB)) as db:
                db.executescript((app.ROOT/'migrations/001_initial.sql').read_text())
                db.execute('INSERT INTO records VALUES (?,?,?,?,?,?)',(r['id'],'escrow','legacy-owner',r['code'],1,json.dumps(dict(r,owner='legacy-owner'))))
                db.commit()
            app.initialize();app.initialize()
            self.assertEqual(self.get(r)['state'],'awaiting_buyer')
            with app.connection() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0],len(list((app.ROOT/'migrations').glob('*.sql'))))
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        finally:app.DB=previous

    def test_status_capability_cannot_dispatch_an_unsubmitted_instruction(self):
        r=self.pay(self.intent(self.create('request')))
        with app.connection(True) as db:
            job=db.execute('SELECT * FROM jobs WHERE record_id=?',(r['id'],)).fetchone()
            with self.assertRaises(ValueError):app.provider.query_instruction(db,job,'success',app.now())
            self.assertEqual(db.execute('SELECT COUNT(*) FROM provider_instructions').fetchone()[0],0)

    def test_new_shop_destination_does_not_mutate_existing_quote(self):
        shop=self.create('shop');old=self.intent(shop)
        self.assertEqual(self.seller.command(shop,'destination',rail='WavePay',destination='new-demo-7755',demo_verified=True)[0],200)
        new=self.intent(shop)
        self.assertEqual(old['beneficiary_version'],1);self.assertEqual(new['beneficiary_version'],2)
        self.assertEqual(self.get(old)['rail'],'KPay')
        self.pay(old);self.pay(new);self.settle()
        with app.connection() as db:
            instructions=[json.loads(x['instruction']) for x in db.execute('SELECT instruction FROM jobs ORDER BY rowid')]
        self.assertEqual([x['destination'] for x in instructions],['demo-4821','new-demo-7755'])

    def test_admin_cannot_bypass_independent_approval_or_impersonate_customer(self):
        r=self.pay(self.join(self.create()));self.buyer.command(r,'dispute',reason='Human review and refund are needed')
        admin=self.staff('admin');admin.command(r,'review',reason='Administrator reviewed both parties')
        admin.command(r,'propose',decision='refund',reason='Administrator proposes original source refund')
        proposal=self.get(r,admin)['proposals'][0]
        self.assertEqual(admin.command(r,'approve',proposal=proposal['id'],reason='Cannot approve my own proposal')[0],403)
        self.assertEqual(admin.command(self.create('shop'),'pay-intent',net=10000)[0],403)

    def test_float_reserved_unknown_and_final_ledger_liabilities_reconcile(self):
        source=self.create('request');self.scenario(source,'payout_unknown');r=self.pay(self.intent(source));self.settle()
        a=self.staff('finance-a');snapshot=a.call('/api/admin')[1]
        self.assertEqual(snapshot['liquidity']['reserved'],r['net'])
        self.assertEqual(snapshot['differences'],[])
        a.command(r,'scenario',scenario='success',reason='Provider now confirms the original payment')
        a.command(r,'query',reason='Query original unknown provider reference');self.settle()
        result=a.call('/api/admin')[1]
        self.assertEqual(result['liquidity']['reserved'],0)
        balances={x['account']:x['balance'] for x in result['balances']}
        self.assertEqual(balances['merchant_payable'],0)
        self.assertEqual(balances['payout_reserved'],0)
        self.assertEqual(balances['deferred_fee'],0)
        self.assertEqual(balances['fee_income'],-r['fee'])

    def split(self,scenario='success'):
        r=self.pay(self.join(self.create()));self.buyer.command(r,'dispute',reason='Both participants request an agreed partial settlement')
        a=self.staff('finance-a');b=self.staff('finance-b')
        a.command(r,'review',reason='Human review of proposed partial allocations')
        if scenario!='success':a.command(r,'scenario',scenario=scenario,reason='Test independently recoverable settlement legs')
        status,result=a.command(r,'offer-split',seller_net=6000,reason='Offer exact agreed allocation and original service fee')
        self.assertEqual(status,200,result);r=result['record'];h=r['split_terms']['hash']
        self.assertEqual(a.command(r,'propose',decision='split',reason='Cannot dispatch without both participant agreements')[0],409)
        outsider=Client(self.base);outsider.customer()
        self.assertEqual(outsider.command(r,'consent-split',agree=True,split_hash=h)[0],403)
        self.assertEqual(self.buyer.command(r,'consent-split',agree=True,split_hash='stale-hash')[0],409)
        self.assertEqual(self.buyer.command(r,'consent-split',agree=True,split_hash=h)[0],200)
        self.assertEqual(self.seller.command(r,'consent-split',agree=True,split_hash=h)[0],200)
        self.assertEqual(a.command(r,'propose',decision='split',reason='Both parties consented to these exact amounts')[0],200)
        proposal=self.get(r,a)['proposals'][0]
        b.command(r,'approve',proposal=proposal['id'],reason='Independent check of consent and conservation')
        status,result=a.command(r,'submit',proposal=proposal['id'],reason='Submit both independently tracked settlement legs')
        self.assertEqual(status,200,result)
        self.assertEqual(a.command(r,'submit',proposal=proposal['id'],reason='Do not dispatch the original hold again')[0],409)
        return result['record'],a,b

    def test_agreed_partial_settlement_conserves_money_and_requires_both_consents(self):
        r,a,b=self.split();self.settle();self.settle()
        settled=self.get(r)
        self.assertEqual(settled['state'],'settled')
        self.assertEqual(len(settled['settlement_legs']),2)
        self.assertEqual(sorted(x['net'] for x in settled['settlement_legs']),[4000,6000])
        self.assertEqual(a.command(r,'propose',decision='refund',reason='Cannot reuse the allocated original collection')[0],409)
        result=a.call('/api/admin')[1];balances={x['account']:x['balance'] for x in result['balances']}
        for account in ['escrow_liability','merchant_payable','receipt_suspense','settlement_clearing','payout_reserved','refund_reserved','deferred_fee']:
            self.assertEqual(balances[account],0,account)
        self.assertEqual(balances['provider_cash'],r['fee']);self.assertEqual(balances['fee_income'],-r['fee'])
        self.assertEqual(result['differences'],[])
        with app.connection() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM callbacks').fetchone()[0],1)

    def test_partial_settlement_failure_recovers_only_the_failed_leg(self):
        r,a,b=self.split('payout_failed');self.settle()
        self.assertEqual(self.get(r)['state'],'settlement_attention')
        legs=self.get(r)['settlement_legs'];failed=next(x for x in legs if x['payout']=='failed')
        self.assertEqual(next(x for x in legs if x['instruction_type']=='refund')['state'],'refunded')
        a.command(failed,'scenario',scenario='success',reason='Seller payout route recovered after final failure')
        self.assertEqual(a.command(failed,'propose',decision='retry',reason='Retry only the failed seller settlement leg')[0],200)
        proposal=self.get(failed,a)['proposals'][0]
        b.command(failed,'approve',proposal=proposal['id'],reason='Independent approval of only the unpaid leg')
        a.command(failed,'submit',proposal=proposal['id'],reason='Preserve the already confirmed buyer refund')
        self.settle();self.assertEqual(self.get(r)['state'],'settled')
        with app.connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM provider_instructions p JOIN jobs j ON j.id=p.job_id WHERE j.type='refund'").fetchone()[0],1)
        self.assertTrue(all(total==0 for _,total in self.balances()))
