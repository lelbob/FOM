from test_app import IntegrationHarness, Client, app
import time

PNG='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='
class ReceiptMVP(IntegrationHarness):
    def create_mvp(self,kind='escrow'):
        status,d=self.seller.call('/api/mvp/create',dict(kind=kind,title='Headphones',amount=10000,description='With original case',delivery='Handover tomorrow',window='24 hours after receipt',receiving_method='KPay',phone='demo-4821',receiving_name='Aye Demo',shop_id='SHOP-001',contact='demo contact',command_id=app.uid('create')))
        self.assertEqual(status,200,d);return d['record']
    def act(self,c,r,action,**data):return c.call('/api/mvp/'+r['id']+'/'+action,dict(command_id=app.uid('cmd'),**data))
    def test_escrow_receipt_delivery_and_receive_without_money_movement(self):
        r=self.create_mvp();self.assertTrue(r['code'].startswith('ES-'))
        public=self.public.call('/api/mvp/record/'+r['id'])[1]['record']
        self.assertFalse(public['is_buyer']);self.assertFalse(public['private']);self.assertNotIn('phone',public)
        self.assertEqual(self.act(self.buyer,r,'join',agree=True)[0],200)
        self.assertEqual(self.act(self.buyer,r,'sent',payer_method='WavePay',receipt=PNG)[1]['record']['state'],'sent')
        self.assertEqual(self.act(self.seller,r,'dispatch',delivery_photo=PNG,delivery_note='Handed to courier')[1]['record']['state'],'delivering')
        self.assertEqual(self.act(self.buyer,r,'receive',agree=True)[0],409)
        self.assertEqual(self.act(self.seller,r,'arrive',agree=True)[1]['record']['state'],'arrived')
        self.assertEqual(self.act(self.buyer,r,'receive',agree=True)[1]['record']['state'],'completed')
        with app.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],0)
    def test_receipts_private_and_role_transitions_enforced(self):
        r=self.create_mvp();self.act(self.buyer,r,'join',agree=True);self.act(self.buyer,r,'sent',payer_method='KPay',receipt=PNG)
        public=self.public.call('/api/mvp/record/'+r['id'])[1]['record']
        for key in ['receipt','phone','receiving_name']:self.assertNotIn(key,public)
        self.assertEqual(self.act(self.buyer,r,'dispatch',delivery_photo=PNG,delivery_note='Wrong actor')[0],403)
        self.assertEqual(self.act(self.seller,r,'receive',agree=True)[0],403)
        third=Client(self.base);third.customer();self.assertEqual(self.act(third,r,'join',agree=True)[0],409)
    def test_single_use_receipt_operation_replay_is_idempotent(self):
        r=self.create_mvp('payment');self.assertTrue(r['code'].startswith('PY-'));self.act(self.buyer,r,'join',agree=True)
        b=dict(command_id=app.uid('sent'),receipt=PNG,payer_method='KPay')
        first=self.buyer.call('/api/mvp/'+r['id']+'/sent',b);again=self.buyer.call('/api/mvp/'+r['id']+'/sent',b)
        self.assertEqual(first,again);self.assertEqual(first[1]['record']['state'],'sent')
        self.assertEqual(self.act(self.buyer,r,'sent',receipt=PNG,payer_method='KPay')[0],409)
    def test_expiry_disables_new_join_but_preserves_history(self):
        import json
        r=self.create_mvp('payment')
        with app.connection(True) as db:
            d=json.loads(db.execute('SELECT data FROM mvp_records WHERE id=?',(r['id'],)).fetchone()[0]);d['expires']=int(time.time())-1
            db.execute('UPDATE mvp_records SET data=? WHERE id=?',(json.dumps(d),r['id']))
        self.assertEqual(self.act(self.buyer,r,'join',agree=True)[0],409)
        self.assertEqual(self.seller.call('/api/mvp/list')[1]['records'][0]['state'],'expired')
    def test_shop_application_saved_without_activation_or_contact(self):
        r=self.create_mvp('shop');self.assertTrue(r['code'].startswith('SP-'));self.assertEqual(r['state'],'contact_team')
        self.assertEqual(self.seller.call('/api/mvp/list')[1]['records'][0]['shop_id'],'SHOP-001')
        self.assertEqual(self.act(self.buyer,r,'join',agree=True)[0],409)
    def test_staff_can_inspect_but_not_submit_receipts(self):
        r=self.create_mvp();self.act(self.buyer,r,'join',agree=True);self.act(self.buyer,r,'sent',payer_method='KPay',receipt=PNG)
        staff=self.staff('support');self.assertEqual(staff.call('/api/mvp/staff')[1]['records'][0]['receipt'],PNG)
        self.assertEqual(self.seller.call('/api/mvp/staff')[0],403)
        self.assertEqual(self.act(staff,r,'receive',agree=True)[0],403)
    def test_delivery_requires_photo_and_receipt_is_not_optional(self):
        r=self.create_mvp();self.act(self.buyer,r,'join',agree=True)
        self.assertEqual(self.act(self.buyer,r,'sent',payer_method='KPay')[0],422)
        self.act(self.buyer,r,'sent',payer_method='KPay',receipt=PNG)
        self.assertEqual(self.act(self.seller,r,'dispatch',delivery_note='Handed over')[0],422)

    def test_payment_code_can_start_payer_flow_in_creator_browser(self):
        r=self.create_mvp('payment')
        status,joined=self.act(self.seller,r,'join',agree=True)
        self.assertEqual(status,200,joined)
        self.assertTrue(joined['record']['is_owner'])
        self.assertTrue(joined['record']['is_buyer'])
        self.assertEqual(self.act(self.seller,r,'sent',payer_method='WavePay')[0],422)
        status,sent=self.act(self.seller,r,'sent',payer_method='WavePay',receipt=PNG)
        self.assertEqual(status,200,sent)
        self.assertEqual(sent['record']['state'],'sent')
        self.assertEqual(sent['record']['payer_method'],'WavePay')
        self.assertEqual(sent['record']['receipt'],PNG)

    def test_escrow_owner_cannot_be_its_buyer(self):
        r=self.create_mvp('escrow')
        self.assertEqual(self.act(self.seller,r,'join',agree=True)[0],403)
        self.assertEqual(self.act(self.seller,r,'sent',payer_method='KPay',receipt=PNG)[0],403)

    def test_local_buyer_entry_preserves_seller_in_same_cookie_jar(self):
        r=self.create_mvp('escrow')
        seller_base=self.seller.base
        self.seller.base=seller_base.replace('127.0.0.1','localhost')
        self.seller.customer()
        status,joined=self.act(self.seller,r,'join',agree=True)
        self.assertEqual(status,200,joined)
        self.assertTrue(joined['record']['is_buyer'])
        self.assertFalse(joined['record']['is_owner'])
        self.seller.base=seller_base
        own=self.seller.call('/api/mvp/record/'+r['id'])[1]['record']
        self.assertTrue(own['is_owner'])
        self.assertFalse(own['is_buyer'])

    def test_payment_owner_cannot_replace_an_existing_payer(self):
        r=self.create_mvp('payment')
        self.assertEqual(self.act(self.buyer,r,'join',agree=True)[0],200)
        self.assertEqual(self.act(self.seller,r,'join',agree=True)[0],409)
        self.assertEqual(self.act(self.seller,r,'sent',payer_method='KPay',receipt=PNG)[0],403)

    def test_joined_payment_cannot_submit_receipt_after_expiry(self):
        import json
        r=self.create_mvp('payment')
        self.assertEqual(self.act(self.buyer,r,'join',agree=True)[0],200)
        with app.connection(True) as db:
            d=json.loads(db.execute('SELECT data FROM mvp_records WHERE id=?',(r['id'],)).fetchone()[0])
            d['expires']=int(time.time())-1
            db.execute('UPDATE mvp_records SET data=? WHERE id=?',(json.dumps(d),r['id']))
        self.assertEqual(self.act(self.buyer,r,'sent',payer_method='KPay',receipt=PNG)[0],409)

    def delivering_deal(self):
        r=self.create_mvp()
        self.act(self.buyer,r,'join',agree=True)
        self.act(self.buyer,r,'sent',payer_method='KPay',receipt=PNG)
        self.act(self.seller,r,'dispatch',delivery_photo=PNG,delivery_note='Courier ABC123')
        return r

    def test_arrival_is_a_second_seller_confirmation_before_buyer_receive(self):
        r=self.delivering_deal()
        self.assertEqual(self.act(self.buyer,r,'arrive',agree=True)[0],403)
        self.assertEqual(self.act(self.buyer,r,'receive',agree=True)[0],409)
        self.assertEqual(self.act(self.seller,r,'arrive')[0],409)
        body=dict(command_id=app.uid('arrive'),agree=True)
        first=self.seller.call('/api/mvp/'+r['id']+'/arrive',body)
        self.assertEqual(first[0],200)
        self.assertEqual(first[1]['record']['state'],'arrived')
        self.assertEqual(self.seller.call('/api/mvp/'+r['id']+'/arrive',body),first)
        self.assertEqual(self.act(self.seller,r,'receive',agree=True)[0],403)
        self.assertEqual(self.act(self.buyer,r,'receive',agree=True)[1]['record']['state'],'completed')

    def test_report_saves_private_evidence_and_pauses_until_author_withdraws(self):
        r=self.delivering_deal()
        third=Client(self.base);third.customer()
        self.assertEqual(self.act(third,r,'report',reason='Not a participant')[0],403)
        self.assertEqual(self.act(self.buyer,r,'report')[0],422)
        status,result=self.act(self.buyer,r,'report',reason='Package has not arrived',photo=PNG)
        self.assertEqual(status,200,result)
        self.assertTrue(result['record']['report_open'])
        self.assertEqual(result['record']['reports'][0]['photo'],PNG)
        self.assertEqual(self.act(self.seller,r,'arrive',agree=True)[0],409)
        self.assertEqual(self.act(self.buyer,r,'receive',agree=True)[0],409)
        public=self.public.call('/api/mvp/record/'+r['id'])[1]['record']
        self.assertNotIn('reports',public)
        private=self.seller.call('/api/mvp/record/'+r['id'])[1]['record']
        self.assertEqual(private['reports'][0]['reason'],'Package has not arrived')
        staff=self.staff('support')
        self.assertTrue(staff.call('/api/mvp/staff')[1]['records'][0]['report_open'])
        self.assertEqual(self.act(self.seller,r,'withdraw-report')[0],409)
        self.assertFalse(self.act(self.buyer,r,'withdraw-report')[1]['record']['report_open'])
        self.assertEqual(self.act(self.seller,r,'arrive',agree=True)[0],200)

    def test_withdrawing_one_report_does_not_clear_the_other_party_report(self):
        r=self.delivering_deal()
        self.act(self.buyer,r,'report',reason='Buyer issue')
        self.act(self.seller,r,'report',reason='Seller issue')
        self.assertEqual(self.act(self.buyer,r,'report',reason='Duplicate issue')[0],409)
        self.assertTrue(self.act(self.buyer,r,'withdraw-report')[1]['record']['report_open'])
        self.assertEqual(self.act(self.seller,r,'arrive',agree=True)[0],409)
        self.assertFalse(self.act(self.seller,r,'withdraw-report')[1]['record']['report_open'])

    def test_concurrent_code_claims_have_one_winner_and_stay_bound(self):
        from concurrent.futures import ThreadPoolExecutor
        for kind in ['payment','escrow']:
            r=self.create_mvp(kind)
            other=Client(self.base);other.customer()
            with ThreadPoolExecutor(max_workers=2) as pool:
                attempts=list(pool.map(lambda c:self.act(c,r,'join',agree=True),[self.buyer,other]))
            self.assertEqual(sorted(x[0] for x in attempts),[200,409])
            winner,loser=(self.buyer,other) if attempts[0][0]==200 else (other,self.buyer)
            self.assertEqual(self.act(winner,r,'join',agree=True)[0],200)
            self.assertEqual(self.act(loser,r,'join',agree=True)[0],409)
            self.assertFalse(loser.call('/api/mvp/record/'+r['id'])[1]['record']['is_buyer'])
            self.assertEqual(self.act(loser,r,'sent',payer_method='KPay',receipt=PNG)[0],403)
            self.assertTrue(winner.call('/api/mvp/record/'+r['id'])[1]['record']['is_buyer'])
            self.assertEqual(self.act(winner,r,'sent',payer_method='KPay',receipt=PNG)[0],200)
            self.assertEqual(self.act(loser,r,'join',agree=True)[0],409)

    def shop_inquiry(self,client=None,**changes):
        body=dict(kind='shop',title='Another shop',shop_id='SHOP-002',contact='Demo contact',command_id=app.uid('shop'))
        body.update(changes)
        return (client or self.seller).call('/api/mvp/create',body)

    def test_one_pending_shop_per_account_and_idempotent_submission(self):
        key=app.uid('shop')
        first=self.shop_inquiry(command_id=key)
        self.assertEqual(first[0],200)
        self.assertEqual(self.shop_inquiry(command_id=key),first)
        self.assertEqual(self.shop_inquiry()[0],409)
        self.assertEqual(self.shop_inquiry(self.buyer)[0],200)
        record=first[1]['record']
        self.assertTrue(record['inquiry_pending'])
        self.assertEqual(self.act(self.seller,record,'review-shop',decision='approved',reason='Self review')[0],403)
        support=self.staff('support')
        self.assertEqual(self.act(support,record,'review-shop',decision='approved',reason='Support review')[0],403)
        ops=self.staff('operations')
        approved=self.act(ops,record,'review-shop',decision='approved',reason='Registration reviewed')
        self.assertEqual(approved[0],200,approved)
        self.assertFalse(approved[1]['record']['inquiry_pending'])
        self.assertEqual(approved[1]['record']['state'],'registered')
        self.assertEqual(self.act(ops,record,'review-shop',decision='declined',reason='Second review')[0],409)
        self.assertEqual(self.shop_inquiry()[0],200)
        self.assertEqual(len(self.seller.call('/api/mvp/list')[1]['records']),2)

    def test_concurrent_shop_submissions_create_only_one_pending_inquiry(self):
        from concurrent.futures import ThreadPoolExecutor
        # Separate HTTP clients recover the same account, like two tabs/devices.
        c1=Client(self.base);account=c1.customer()
        c2=Client(self.base);c2.call('/api/session/recover',{'recovery':account['recovery']})
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda c:self.shop_inquiry(c),[c1,c2]))
        self.assertEqual(sorted(x[0] for x in results),[200,409])
        self.assertEqual(len(c1.call('/api/mvp/list')[1]['records']),1)

    def test_legacy_pending_shop_and_declined_inquiry_rules(self):
        import json
        r=self.create_mvp('shop')
        with app.connection(True) as db:
            data=json.loads(db.execute('SELECT data FROM mvp_records WHERE id=?',(r['id'],)).fetchone()[0])
            data.pop('inquiry_status',None)
            db.execute('UPDATE mvp_records SET data=? WHERE id=?',(json.dumps(data),r['id']))
        self.assertEqual(self.shop_inquiry()[0],409)
        ops=self.staff('operations')
        self.assertEqual(self.act(ops,r,'review-shop',decision='declined',reason='Details incomplete')[0],200)
        self.assertEqual(self.shop_inquiry()[0],200)
