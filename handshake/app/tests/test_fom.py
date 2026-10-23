from test_app import IntegrationHarness, Client, app

class FOM(IntegrationHarness):
    def merchant(self,account='demo-4821'):
        status,data=self.seller.call('/api/merchant',dict(display_name='Mya Demo Shop',account=account,rail='KPay',profile='hosted',demo_verified=True))
        self.assertEqual(status,200,data)
        return data['merchant']
    def source(self,kind='request'):
        self.merchant()
        status,data=self.seller.call('/api/create',dict(kind=kind,net=10000,merchant_setup=True,purpose='Tea order',command_id=app.uid('create')))
        self.assertEqual(status,200,data)
        return data['record']
    def test_merchant_collection_receipt_precedes_separate_settlement(self):
        source=self.source();r=self.pay(self.intent(source))
        self.assertEqual(r['state'],'settlement_pending')
        self.assertEqual(r['collection'],'confirmed');self.assertEqual(r['settlement_status'],'pending')
        self.assertEqual(r['purpose'],'Tea order')
        with app.connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM ledger WHERE account='provider_cash'").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT SUM(amount) FROM ledger WHERE account='merchant_provider_clearing'").fetchone()[0],10200)
        self.settle();self.assertEqual(self.get(r)['state'],'settled')
        self.assertTrue(all(total==0 for _,total in self.balances()))
    def test_counter_is_single_use_browser_checkout_without_owner_payer_authority(self):
        shop=self.source('shop');cmd=app.uid('counter')
        status,d=self.seller.command(shop,'counter-request',net=5000,purpose='Counter order',command_id=cmd)
        self.assertEqual(status,200,d);source=d['record']
        status,d=self.seller.command(shop,'counter-request',net=5000,purpose='Counter order',command_id=cmd)
        self.assertEqual(d['record']['id'],source['id'])
        self.assertEqual(self.buyer.command(shop,'counter-request',net=5000)[0],403)
        r=self.intent(source);self.assertEqual(r['shop_id'],shop['id'])
        self.assertEqual(self.seller.command(r,'authorize',agree=True,method='KPay')[0],403)
        self.pay(r)
        outsider=Client(self.base);outsider.customer()
        self.assertEqual(outsider.command(source,'pay-intent')[0],409)
        self.assertEqual(self.public.call('/api/records/'+r['id'])[0],403)
    def test_three_orders_including_equal_amounts_keep_receipts_private(self):
        shop=self.source('shop');ids=[]
        for net in [10000,5000,10000]:
            customer=Client(self.base);customer.customer();r=self.intent(shop,net,customer);ids.append(r['id'])
            self.assertEqual(customer.command(r,'authorize',method='KPay',agree=True)[0],200)
            self.assertEqual(customer.call('/api/simulate/'+r['id'],{'outcome':'confirmed'})[0],200)
            for previous in ids[:-1]:self.assertEqual(customer.call('/api/records/'+previous)[0],403)
        self.assertEqual(len(set(ids)),3);self.settle()
        self.assertTrue(all(total==0 for _,total in self.balances()))
    def test_account_change_preserves_authorized_snapshot(self):
        shop=self.source('shop');r=self.intent(shop)
        self.buyer.command(r,'authorize',method='KPay',agree=True)
        self.merchant('demo-9999')
        self.assertEqual(self.get(r)['destination_mask'],'•• 4821')
        self.assertEqual(self.get(r)['quote']['beneficiary']['destination_mask'],'•• 4821') if 'beneficiary' in self.get(r)['quote'] else None
    def test_unknown_settlement_keeps_original_instruction(self):
        source=self.source();self.scenario(source,'payout_unknown');r=self.pay(self.intent(source));self.settle()
        self.assertEqual(self.get(r)['payout'],'unknown')
        with app.connection() as db:before=dict(db.execute('SELECT * FROM jobs WHERE record_id=?',(r['id'],)).fetchone())
        self.assertEqual(self.buyer.command(r,'authorize',method='KPay',agree=True)[0],409)
        self.settle()
        with app.connection() as db:
            after=dict(db.execute('SELECT * FROM jobs WHERE record_id=?',(r['id'],)).fetchone())
            self.assertEqual(before['reference'],after['reference']);self.assertEqual(before['instruction'],after['instruction'])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM collection_attempts WHERE record_id=?',(r['id'],)).fetchone()[0],1)
    def test_stage_draft_retains_typed_approval_and_identity(self):
        d=dict(kind='escrow',item='Long item',net=5000,demo_verified=True,merchant_setup=False,command_id='stable-draft-command')
        self.assertEqual(self.seller.call('/api/drafts',d)[0],200)
        saved=self.seller.call('/api/drafts')[1]['drafts']['escrow']
        self.assertIs(saved['demo_verified'],True);self.assertIs(saved['merchant_setup'],False)
        self.assertEqual(saved['command_id'],'stable-draft-command')

    def test_merchant_refund_after_definitive_settlement_failure_uses_provider_clearing(self):
        source=self.source();self.scenario(source,'payout_failed');r=self.pay(self.intent(source));self.settle()
        self.assertEqual(self.get(r)['payout'],'failed')
        a=self.staff('finance-a');b=self.staff('finance-b')
        self.assertEqual(a.command(r,'scenario',scenario='success',reason='Refund route available in simulation')[0],200)
        self.assertEqual(a.command(r,'review',reason='Reviewed definitive failure and original payment')[0],200)
        self.assertEqual(a.command(r,'propose',decision='refund',reason='Refund original source before merchant settlement')[0],200)
        proposal=self.get(r,a)['proposals'][0]
        self.assertEqual(b.command(r,'approve',proposal=proposal['id'],reason='Independent original source refund approval')[0],200)
        self.assertEqual(a.command(r,'submit',proposal=proposal['id'],reason='Submit approved original source refund')[0],200)
        self.settle();self.assertEqual(self.get(r)['state'],'refunded')
        with app.connection() as db:
            for account in ['merchant_provider_clearing','merchant_settlement_due','merchant_fee_due','refund_reserved']:
                self.assertEqual(db.execute('SELECT COALESCE(SUM(amount),0) FROM ledger WHERE account=?',(account,)).fetchone()[0],0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM ledger WHERE account='provider_cash'").fetchone()[0],0)

    def test_public_request_does_not_expose_private_resume_or_receipt(self):
        source=self.source();r=self.pay(self.intent(source))
        self.assertEqual(self.get(source,self.buyer)['resume_payment_id'],r['id'])
        public=self.get(source,self.public)
        self.assertNotIn('resume_payment_id',public);self.assertNotIn('payment_id',public)
        self.assertEqual(self.public.call('/api/records/'+r['id'])[0],403)
    def test_optional_photo_rejects_active_content_and_accepts_png(self):
        import base64
        body=dict(kind='escrow',name='Aye',item='Item with photo',description='Description',delivery='Direct handover',window='After confirmed receipt',net=5000,rail='KPay',destination='demo-4821',demo_verified=True)
        bad=dict(body,photo='data:image/svg+xml;base64,PHN2Zz4=',command_id=app.uid('photo'))
        self.assertEqual(self.seller.call('/api/create',bad)[0],422)
        png='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='
        status,data=self.seller.call('/api/create',dict(body,photo=png,command_id=app.uid('photo')))
        self.assertEqual(status,200,data);self.assertEqual(self.get(data['record'],self.public)['photo'],png)
