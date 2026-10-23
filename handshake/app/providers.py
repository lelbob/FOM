"""Server-only provider boundary. Only the deterministic simulator is configured."""
import hashlib
import hmac

class SimulatedProvider:
    capabilities={'collection':True,'status':True,'payout':True,'refund':True,'settlement':True,'settlement_reporting':True,'escrow_hold':True,'escrow_release':True,'escrow_freeze':True,'hosted_checkout':True,'bank_payment_qr':False,'live':False}
    @staticmethod
    def verify_callback(secret, raw, signature):
        expected=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature,expected)
    @staticmethod
    def collection_result(record):
        return {'record_id':record['id'],'event_id':'sim-event:'+record['id'],
                'receipt_id':'sim-receipt:'+record['id'],'amount':record['total'],
                'currency':'MMK','reference':record['collection_ref'],
                'method':record['method'],'final':True}
    @staticmethod
    def payout_status(scenario):
        return 'unknown' if scenario=='payout_unknown' else 'failed' if scenario in ['payout_failed','insufficient_float'] else 'confirmed'
    @staticmethod
    def refund_status(scenario):
        return SimulatedProvider.payout_status(scenario)

    @staticmethod
    def submit_payout(db, job, scenario, created):
        if job['type']!='payout': raise ValueError('Payout capability requires a payout instruction')
        return SimulatedProvider._record_instruction(db,job,scenario,created)

    @staticmethod
    def submit_refund(db, job, scenario, created):
        if job['type']!='refund': raise ValueError('Refund capability requires a refund instruction')
        return SimulatedProvider._record_instruction(db,job,scenario,created)

    @staticmethod
    def query_instruction(db, job, scenario, created):
        if not db.execute('SELECT 1 FROM provider_instructions WHERE reference=?',(job['reference'],)).fetchone():
            raise ValueError('Status cannot dispatch a missing instruction')
        return SimulatedProvider._record_instruction(db,job,scenario,created)

    @staticmethod
    def instruction_status(db, job, scenario, created):
        """Worker boundary: initial dispatch and later status use separate capabilities."""
        prior=db.execute('SELECT 1 FROM provider_instructions WHERE reference=?',(job['reference'],)).fetchone()
        if prior: return SimulatedProvider.query_instruction(db,job,scenario,created)
        if job['type']=='settlement': return SimulatedProvider._record_instruction(db,job,scenario,created)
        submit=SimulatedProvider.submit_refund if job['type']=='refund' else SimulatedProvider.submit_payout
        return submit(db,job,scenario,created)

    @staticmethod
    def _record_instruction(db, job, scenario, created):
        """Durable simulated provider outcome at the original idempotency reference."""
        instruction_hash=hashlib.sha256((job['instruction'] or job['id']).encode()).hexdigest()
        prior=db.execute('SELECT * FROM provider_instructions WHERE reference=?',(job['reference'],)).fetchone()
        if prior:
            if prior['instruction_hash']!=instruction_hash: raise ValueError('Provider instruction identity conflict')
            if prior['outcome']!='unknown': return prior['outcome']
        outcome=SimulatedProvider.refund_status(scenario) if job['type']=='refund' else SimulatedProvider.payout_status(scenario)
        if prior:
            db.execute('UPDATE provider_instructions SET outcome=? WHERE reference=?',(outcome,job['reference']))
        else:
            db.execute('INSERT INTO provider_instructions VALUES (?,?,?,?,?)',(job['reference'],job['id'],instruction_hash,outcome,created))
        return outcome

provider=SimulatedProvider()
