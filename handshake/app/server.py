"""Handshake local full-stack simulator. Python 3.11+, SQLite, no runtime install."""
import base64
import hashlib
import hmac
import io
import json
import mimetypes
import os
import secrets
import sqlite3
import sys
import threading
import time
from contextlib import contextmanager
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from providers import provider
import receipt_mvp

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
DB = Path(os.environ.get('HANDSHAKE_DB', str(ROOT / 'data/handshake.sqlite3')))
PORT = int(os.environ.get('HANDSHAKE_PORT', '8800'))
STAFF_PASSWORD = os.environ.get('HANDSHAKE_STAFF_PASSWORD', 'handshake-demo-2026')
STAFF = {'support': 'support', 'operations': 'operations', 'finance-a': 'finance', 'finance-b': 'finance', 'admin': 'admin'}
METHODS = ['KPay', 'WavePay', 'UAB Pay', 'AYA Pay']
SCENARIOS = ['success', 'payout_failed', 'payout_unknown', 'insufficient_float']

def now(): return int(time.time())
def uid(prefix): return prefix + '-' + secrets.token_hex(8)
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def encode(value): return json.dumps(value, separators=(',', ':'), ensure_ascii=False)

class DomainError(Exception):
    def __init__(self, message, status=422): self.message, self.status = message, status

def require(condition, message, status=422):
    if not condition: raise DomainError(message, status)

@contextmanager
def connection(write=False):
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        if write: db.execute('BEGIN IMMEDIATE')
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally: db.close()

def initialize():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with connection() as db:
        db.executescript((ROOT / 'migrations/001_initial.sql').read_text())
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY, applied INTEGER NOT NULL)')
        for migration in sorted((ROOT / 'migrations').glob('*.sql')):
            if db.execute('SELECT 1 FROM schema_migrations WHERE version=?',(migration.name,)).fetchone(): continue
            if migration.name!='001_initial.sql':
                db.executescript('BEGIN IMMEDIATE;\n'+migration.read_text()+'\nINSERT INTO schema_migrations VALUES (\''+migration.name+'\','+str(now())+');\nCOMMIT;')
            else:
                db.execute('INSERT INTO schema_migrations VALUES (?,?)',(migration.name,now()))
                db.commit()
        db.execute('INSERT OR IGNORE INTO settings VALUES (?,?)', ('callback_secret', os.environ.get('HANDSHAKE_CALLBACK_SECRET', secrets.token_hex(32))))
        db.execute('INSERT OR IGNORE INTO settings VALUES (?,?)', ('float', '10000000'))
        db.execute('INSERT OR IGNORE INTO settings VALUES (?,?)', ('route_open', 'true'))

def event(db, rid, actor, kind, reason=''):
    db.execute('INSERT INTO events(record_id,actor,type,reason,created) VALUES (?,?,?,?,?)', (rid, actor, kind, reason, now()))

def get_record(db, rid):
    row = db.execute('SELECT * FROM records WHERE id=?', (rid,)).fetchone()
    require(row is not None, 'This link is unavailable. Check the link or code.', 404)
    result = json.loads(row['data'])
    result.update(id=row['id'], kind=row['kind'], owner=row['owner'], code=row['code'], version=row['version'])
    return result

def save(db, r):
    before=db.execute('SELECT data FROM records WHERE id=?',(r['id'],)).fetchone()
    r['version'] += 1
    db.execute('UPDATE records SET data=?, version=? WHERE id=?', (encode(r), r['version'], r['id']))
    previous=json.loads(before['data'])
    keys=['state','collection','payout']
    if any(previous.get(k)!=r.get(k) for k in keys):
        event(db,r['id'],'system','financial.transition',encode(dict(before={k:previous.get(k) for k in keys},after={k:r.get(k) for k in keys},version=r['version'],net=r.get('net'),total=r.get('total'),currency='MMK',destination=r.get('destination_mask'))))

def insert(db, kind, actor, data):
    rid, code = uid({'escrow':'deal', 'request':'req', 'shop':'shop', 'payment':'pay'}[kind]), 'HS-' + secrets.token_hex(4).upper()
    r = dict(data, id=rid, kind=kind, owner=actor, code=code, version=1, created=now())
    db.execute('INSERT INTO records VALUES (?,?,?,?,?,?)', (rid, kind, actor, code, 1, encode(r)))
    event(db, rid, actor, kind + '.created')
    return r

def member(r, session): return session and (session['role'] != 'customer' or session['actor'] in [r['owner'], r.get('buyer'), r.get('payer')])
def owner(r, session): return session and session['actor'] == r['owner']
def finance(s): require(s['role'] in ['finance','admin'], 'A finance staff session is required.', 403)
def staff(s): require(s['role'] in ['support', 'operations', 'finance','admin'], 'A staff session is required.', 403)
def amount(value):
    require(type(value) is int and 500 <= value <= 1000000, 'Enter a whole MMK amount between 500 and 1,000,000.')
    return value
def text(value, label, minimum=1, maximum=300):
    require(isinstance(value, str) and minimum <= len(value.strip()) <= maximum, f'{label} must contain {minimum}–{maximum} characters.')
    return value.strip()
def fee(net): return max(100, (net * 2 + 99) // 100)
def settings(db, key): return db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()[0]

def project(db, r, s):
    private = bool(member(r, s))
    require(r['kind']!='payment' or private,'Private payer or recipient access required.',403)
    fields = ['photo','purpose','delivery_note','merchant','environment','settlement_model','provider_profile','id','kind','code','version','created','name','item','description','delivery','window','net','fee','total','rail','state','collection','payout','expires','shop_id','source_id','quote_expires','destination_mask','accepted','case_open','scenario','reviewed','method','instruction_type','recovery_only','beneficiary_version','fee_version']
    out = {k: r[k] for k in fields if k in r}
    if r['kind']=='request' and r.get('payment_id'):
        payment=get_record(db,r['payment_id'])
        out.update(state=payment['state'],collection=payment['collection'],payout=payment['payout'])
        if s and s['actor']==payment.get('payer'):out['resume_payment_id']=payment['id']
    if r['kind']=='request' and now() >= r['expires'] and not r.get('payment_id'): out['state']='expired'
    out['private'] = private
    out['is_owner'] = bool(owner(r, s))
    out['is_buyer'] = bool(s and s['actor'] == r.get('buyer'))
    out['is_payer'] = bool(s and s['actor'] == r.get('payer'))
    out['can_join'] = bool(r['kind']=='escrow' and not r.get('buyer') and not owner(r,s) and (not s or s['role']=='customer'))
    if r['kind']=='shop': out['paused'] = r.get('paused', False)
    if private:
        out['case_id'] = 'case:'+r['id'] if r.get('case_open') else None
        out['quote'] = r.get('quote')
        if r.get('split_terms'):
            out['split_terms']=r['split_terms']
            out['split_consents']=r.get('split_consents',[])
            out['has_split_consent']=s['actor'] in r.get('split_consents',[])
        if r.get('settlement_children'):
            out['settlement_legs']=[{k:leg.get(k) for k in ['id','net','total','fee','state','payout','instruction_type','destination_mask','rail']} for leg in [get_record(db,x) for x in r['settlement_children']]]
        if owner(r,s) and r['kind']=='escrow': out['invitation'] = r.get('invitation')
        out['payment_id'] = r.get('payment_id')
        out['case_reason'] = r.get('case_reason')
        out['assignee'] = r.get('assignee','support') if r.get('case_open') else r.get('assignee')
        out['case_status'] = 'awaiting_provider' if r.get('case_open') and r.get('payout') in ['pending','unknown'] else 'open' if r.get('case_open') else 'closed'
        out['evidence_request'] = r.get('evidence_request')
        out['collection_reference'] = r.get('collection_ref')
        out['events'] = [dict(x) for x in db.execute('SELECT * FROM events WHERE record_id=? ORDER BY id', (r['id'],)) if s['role']!='customer' or x['type'] not in ['case.note_added','case.human_review_recorded','instruction.proposed','instruction.proposal_canceled','instruction.independently_approved','simulator.scenario_changed','financial.transition','command.denied','command.committed']]
        if s['role']=='customer':
            for item in out['events']:
                if item['actor'] in STAFF: item['reason']=''
                if item['type']=='settlement.participant_consented':item['reason']='Agreement recorded for this exact allocation.'
                if item['type']=='settlement.allocated':item['reason']='Separate payout and refund instructions follow the allocation agreed by both participants.'
                if item['type']=='settlement.leg_created':item['reason']='This transfer is part of an agreed settlement and has its own reference.'
        out['evidence'] = [dict(x) for x in db.execute('SELECT id,name,mime FROM evidence WHERE record_id=?', (r['id'],))]
        if s['role'] != 'customer':
            out['proposals'] = [dict(x) for x in db.execute('SELECT * FROM proposals WHERE record_id=? ORDER BY rowid DESC', (r['id'],))]
            out['jobs'] = [dict(x) for x in db.execute('SELECT * FROM jobs WHERE record_id=?', (r['id'],))]
    else:
        out.pop('scenario', None)
        out.pop('case_open', None)
    out['environment']='simulation'
    if r.get('settlement_model')=='merchant_direct':
        out['settlement_status']=r.get('payout','not_started')
        if r['kind']=='request' and r.get('payment_id'): out['settlement_status']=payment['payout']
    if private and (out['is_payer'] or out['is_buyer']) and r.get('collection_ref'):
        out['payment_action']={'kind':'qr' if r.get('provider_profile')=='qr' else 'hosted_checkout',
            'checkout_url':'/simulator.html#'+r['id'], 'reference':r['collection_ref'],
            'expires_at':r.get('quote_expires'),'environment':'simulation'}
    return out

def journal(db, r, key, postings):
    require(sum(v for _,v in postings)==0, 'Unbalanced journal.', 500)
    existing = db.execute('SELECT 1 FROM ledger WHERE journal=?', (key,)).fetchone()
    if existing: return
    db.executemany('INSERT INTO ledger(journal,record_id,account,amount,created) VALUES (?,?,?,?,?)', [(key,r['id'],a,v,now()) for a,v in postings])

def liability(r):
    return 'receipt_suspense' if r.get('recovery_only') else 'escrow_liability' if r['kind']=='escrow' else 'merchant_payable'

def quote_snapshot(r, method=None):
    fields=['merchant','provider_profile','settlement_model','net','fee','total','rail','destination','beneficiary_version','fee_version','delivery','description','window','agreement_version','quote_expires']
    q={k:r[k] for k in fields if k in r}
    q.update(currency='MMK',collection_route=method,provider_collection_cost=0,provider_payout_cost=0,fee_policy='illustrative; full fee returned on full refund',beneficiary_verification='simulated')
    q['hash']=digest(encode(q))
    return q

def reserve_job(db, r, job, reverse=False):
    if not r.get('accounting_version'): return
    if job['type']=='settlement': return
    kind=job['type']; n=r['total'] if kind=='refund' else r['net']
    postings=[(liability(r),r['net']),('deferred_fee',r['fee']),('refund_reserved',-n)] if kind=='refund' else [(liability(r),n),('payout_reserved',-n)]
    if kind=='refund' and r.get('settlement_model')=='merchant_direct':
        postings=[('merchant_settlement_due',r['net']),('merchant_fee_due',r['fee']),('refund_reserved',-n)]
    journal(db,r,('unreserve:' if reverse else 'reserve:')+job['id'],[(a,-v if reverse else v) for a,v in postings if v])

def start_job(db, r, kind='payout'):
    require(r.get('collection')=='confirmed' and r.get('payout')!='confirmed','Confirmed, unsettled collection required.',409)
    require(not db.execute("SELECT 1 FROM jobs WHERE record_id=? AND state IN ('pending','unknown')",(r['id'],)).fetchone(),'An existing instruction must be resolved first.',409)
    if kind=='payout' and r.get('settlement_model')=='merchant_direct': kind='settlement'
    require(kind in ['refund','settlement'] or available_float(db)>=r['net'],'Payout float unavailable.',409)
    key = uid('job')
    instruction=dict(type=kind,amount=r['total'] if kind=='refund' else r['net'],currency='MMK',destination=('original-source:'+r['collection_ref']) if kind=='refund' else r['destination'],rail=r.get('method') if kind=='refund' else r['rail'],beneficiary_version=r.get('beneficiary_version'),quote_hash=r.get('quote',{}).get('hash'),allocation_hash=r.get('allocation_hash'))
    db.execute('INSERT INTO jobs(id,record_id,type,state,due,scenario,reference,instruction) VALUES (?,?,?,?,?,?,?,?)', (key,r['id'],kind,'pending',now()+2,r.get('scenario','success'),uid('SIM-OUT'),encode(instruction)))
    reserve_job(db,r,dict(id=key,type=kind))
    r['payout']='pending'
    r['instruction_type']=kind
    r['state']='release_pending' if r['kind']=='escrow' and kind=='payout' else ('refund_pending' if kind=='refund' else 'settlement_pending' if kind=='settlement' else 'payout_pending')
    event(db,r['id'],'system',kind+'.requested')

def available_float(db):
    reserved = db.execute("SELECT COALESCE(SUM(CAST(json_extract(r.data,'$.net') AS INTEGER)),0) FROM jobs j JOIN records r ON r.id=j.record_id WHERE j.state IN ('pending','unknown') AND j.type='payout'").fetchone()[0]
    return int(settings(db,'float'))-reserved

def receive(db, rid, event_id, receipt_id, paid_amount):
    r = get_record(db, rid)
    seen = db.execute('SELECT * FROM callbacks WHERE event_id=? OR receipt_id=?',(event_id,receipt_id)).fetchone()
    if seen:
        require(seen['record_id']==rid and seen['amount']==paid_amount, 'Conflicting duplicate receipt.', 409)
        return r
    require(r['kind'] in ['escrow','payment'], 'This record cannot collect a payment.')
    require(r.get('collection') in ['pending','confirmed'], 'No authorized collection is pending.',409)
    require(type(paid_amount) is int and paid_amount==r['total'], 'Receipt amount does not match the accepted quote.',409)
    require(r.get('accepted'), 'The payer has not accepted this quote.',409)
    require(not r.get('receipt_id'), 'A different successful receipt already exists.',409)
    db.execute('INSERT INTO callbacks VALUES (?,?,?,?)',(event_id,receipt_id,rid,paid_amount))
    r.update(collection='confirmed',receipt_id=receipt_id,state='held' if r['kind']=='escrow' else 'collected')
    postings=[('provider_cash',r['total']),(liability(r),-r['net']),('deferred_fee',-r['fee'])] if r.get('accounting_version') else [('provider_cash',r['total']),('customer_liability',-r['total'])]
    if r.get('settlement_model')=='merchant_direct':
        postings=[('merchant_provider_clearing',r['total']),('merchant_settlement_due',-r['net']),('merchant_fee_due',-r['fee'])]
    journal(db,r,'collection:'+rid,[(a,v) for a,v in postings if v])
    event(db,rid,'simulator','collection.confirmed',receipt_id)
    if r['kind']=='payment':
        if r.get('settlement_model')!='merchant_direct' and (available_float(db)<r['net'] or r.get('scenario')=='insufficient_float'):
            r.update(state='payout_failed',payout='failed',case_open=True,case_reason='Payment received; payout liquidity is unavailable.')
            event(db,rid,'system','case.opened',r['case_reason'])
        else: start_job(db,r)
    save(db,r)
    return r

def accept_callback(db, b):
    """Persist signed deliveries, including conflicts; retain genuine extra funds for refund."""
    require(isinstance(b,dict),'Callback object required.',400)
    for name in ['record_id','event_id','receipt_id','reference','method']:
        text(b.get(name),name,1,200)
    payload_hash=digest(encode(b))
    existing=db.execute('SELECT * FROM provider_inbox WHERE event_id=? AND payload_hash=?',(b['event_id'],payload_hash)).fetchone()
    if existing:
        status=202 if existing['recovery_id'] else 200 if existing['disposition'] in ['matched','duplicate'] else existing['http_status']
        return status,dict(accepted=status<400,disposition=existing['disposition'],recovery_id=existing['recovery_id'])
    disposition,reason,recovery_id,status='rejected','',None,409
    try:
        require(b.get('currency')=='MMK' and b.get('final') is True,'Final MMK collection confirmation required.',409)
        require(type(b.get('amount')) is int and 0<b['amount']<=10000000,'Invalid receipt amount.',409)
        original=get_record(db,b['record_id'])
        attempt=db.execute('SELECT * FROM collection_attempts WHERE reference=? AND record_id=?',(b['reference'],original['id'])).fetchone()
        require((attempt and attempt['method']==b['method']) or (b['reference']==original.get('collection_ref') and b['method']==original.get('method')),'Provider reference or route does not match authorization.',409)
        claim=db.execute('SELECT * FROM receipt_claims WHERE receipt_id=? OR event_id=?',(b['receipt_id'],b['event_id'])).fetchone()
        legacy=db.execute('SELECT * FROM callbacks WHERE receipt_id=? OR event_id=?',(b['receipt_id'],b['event_id'])).fetchone()
        if claim:
            require(claim['receipt_id']==b['receipt_id'] and claim['record_id']==b['record_id'] and claim['amount']==b['amount'],'Conflicting receipt identity.',409)
            first=db.execute('SELECT payload FROM provider_inbox WHERE event_id=? AND payload_hash=?',(claim['event_id'],claim['payload_hash'])).fetchone()
            if first:
                frozen=json.loads(first['payload'])
                require(all(frozen.get(k)==b.get(k) for k in ['reference','method','currency']),'Conflicting duplicate receipt route or reference.',409)
            recovery_id=claim['recovery_id'];status=202 if recovery_id else 200;disposition='duplicate'
        elif legacy:
            require(legacy['receipt_id']==b['receipt_id'] and legacy['record_id']==b['record_id'] and legacy['amount']==b['amount'],'Conflicting existing receipt.',409)
            disposition='duplicate';status=200
        elif original.get('accepted') and (original.get('receipt_id') or b['amount']!=original['total'] or b['reference']!=original.get('collection_ref') or original.get('collection')=='failed'):
            # The authenticated provider reported a real additional/mismatched MMK receipt.
            # Keep it separate from fulfillment and refund only to its original source.
            reason='Extra receipt after fulfillment' if original.get('receipt_id') else 'Late receipt from an earlier or failed attempt' if b['reference']!=original.get('collection_ref') or original.get('collection')=='failed' else 'Receipt amount differs from frozen quote'
            data=dict(name=original['name'],net=b['amount'],fee=0,total=b['amount'],rail=original['rail'],destination=original['destination'],destination_mask=original['destination_mask'],beneficiary_version=original['beneficiary_version'],payer=original.get('payer',original.get('buyer')),source_id=original['id'],collection='confirmed',payout='not_started',state='review_required',case_open=True,case_reason=reason,recovery_only=True,accounting_version=2,accepted=True,collection_ref=b['reference'],receipt_id=b['receipt_id'],method=b['method'],scenario='success')
            recovery=insert(db,'payment',original['owner'],data);recovery_id=recovery['id']
            db.execute('INSERT INTO callbacks VALUES (?,?,?,?)',(b['event_id'],b['receipt_id'],recovery_id,b['amount']))
            journal(db,recovery,'collection:'+recovery_id,[('provider_cash',b['amount']),('receipt_suspense',-b['amount'])])
            event(db,recovery_id,'provider','case.receipt_exception',reason)
            disposition='extra' if original.get('receipt_id') else 'amount_mismatch';status=202
        else:
            receive(db,b['record_id'],b['event_id'],b['receipt_id'],b['amount'])
            disposition='matched';status=200
        if not claim:
            db.execute('INSERT INTO receipt_claims VALUES (?,?,?,?,?,?)',(b['receipt_id'],b['event_id'],payload_hash,b['record_id'],b['amount'],recovery_id))
    except DomainError as error:
        reason=error.message;status=error.status
        if status==404: disposition='unmatched'
    db.execute('INSERT INTO provider_inbox(event_id,receipt_id,record_id,payload_hash,payload,disposition,reason,recovery_id,created,http_status) VALUES (?,?,?,?,?,?,?,?,?,?)',(b['event_id'],b['receipt_id'],b['record_id'],payload_hash,encode(b),disposition,reason,recovery_id,now(),status))
    if reason: event(db,b['record_id'],'provider','receipt.'+disposition,reason)
    result=dict(accepted=status<400,disposition=disposition,recovery_id=recovery_id)
    if status>=400:result['error']=reason
    return status,result

def finish_job(db, job, outcome=None):
    # Re-read under the write lock; repeat workers/status queries are harmless.
    job=db.execute('SELECT * FROM jobs WHERE id=?',(job['id'],)).fetchone()
    if not job or job['state'] not in ['pending','unknown']: return
    r = get_record(db,job['record_id'])
    if r.get('release_blocked') and r['kind']=='escrow' and job['type']=='payout':
        db.execute("UPDATE jobs SET state='blocked' WHERE id=?",(job['id'],))
        reserve_job(db,r,job,True)
        return
    scenario = outcome or job['scenario']
    outcome=provider.instruction_status(db,job,scenario,now())
    db.execute('UPDATE jobs SET attempts=attempts+1,last_error=NULL WHERE id=?',(job['id'],))
    if outcome!='confirmed':
        state=outcome
        db.execute('UPDATE jobs SET state=? WHERE id=?',(state,job['id']))
        if state=='failed': reserve_job(db,r,job,True)
        r.update(payout=state,state=('settlement_attention' if job['type']=='settlement' else 'payout_'+state),case_open=True,case_reason=('Merchant settlement outcome is unknown; query the original reference.' if state=='unknown' else 'Provider confirmed merchant settlement failure.') if job['type']=='settlement' else ('Provider outcome is unknown.' if state=='unknown' else 'Provider confirmed payout failure.'))
        event(db,r['id'],'simulator','payout.'+state,job['reference'])
    else:
        net = r['total'] if job['type']=='refund' else r['net']
        if job['type']=='payout':
            require(int(settings(db,'float'))>=net, 'Payout float unavailable.',409)
            db.execute("UPDATE settings SET value=CAST(value AS INTEGER)-? WHERE key='float'",(net,))
        postings=([('refund_reserved',net),('provider_cash',-net)] if job['type']=='refund' else [('payout_reserved',net),('deferred_fee',r['fee']),('provider_cash',-net),('fee_income',-r['fee'])]) if r.get('accounting_version') else [('customer_liability',r['total']),('provider_cash',-net)]+([] if job['type']=='refund' else [('fee_income',-r['fee'])])
        if job['type']=='refund' and r.get('settlement_model')=='merchant_direct':
            postings=[('refund_reserved',net),('merchant_provider_clearing',-net)]
        if job['type']=='settlement':
            postings=[('merchant_provider_clearing',-r['total']),('merchant_settlement_due',r['net']),('merchant_fee_due',r['fee'])]
        journal(db,r,job['id'],[(a,v) for a,v in postings if v])
        db.execute("UPDATE jobs SET state='confirmed' WHERE id=?",(job['id'],))
        r.update(payout='confirmed',state='refunded' if job['type']=='refund' else 'settled' if job['type']=='settlement' else 'completed',case_open=False)
        event(db,r['id'],'simulator',job['type']+'.confirmed',job['reference'])
    save(db,r)
    if r.get('settlement_parent'): sync_settlement(db,r['settlement_parent'])

def sync_settlement(db, rid):
    parent=get_record(db,rid)
    legs=[get_record(db,x) for x in parent['settlement_children']]
    complete=all(x['payout']=='confirmed' for x in legs)
    problem=any(x['payout'] in ['failed','unknown'] for x in legs)
    parent.update(state='settled' if complete else 'settlement_attention' if problem else 'settlement_pending',payout='confirmed' if complete else 'unknown' if any(x['payout']=='unknown' for x in legs) else 'failed' if problem else 'pending',case_open=not complete)
    save(db,parent)

def start_split(db, r, snapshot):
    terms=r['split_terms']
    require(snapshot.get('split_hash')==terms['hash'] and set(r.get('split_consents',[]))=={r['owner'],r['buyer']},'Both participants must agree to this exact allocation.',409)
    require(available_float(db)>=terms['seller_net'],'Payout float unavailable.',409)
    # Transfer the held gross into two separately recoverable obligations.
    parent_account='escrow_liability' if r.get('accounting_version') else 'customer_liability'
    postings=[(parent_account,r['net']),('deferred_fee',r['fee']),('settlement_clearing',-r['total'])] if r.get('accounting_version') else [(parent_account,r['total']),('settlement_clearing',-r['total'])]
    journal(db,r,'allocate:'+r['id'],[(a,v) for a,v in postings if v])
    children=[]
    for kind,net,charge in [('payout',terms['seller_net'],r['fee']),('refund',terms['buyer_refund'],0)]:
        data={k:r[k] for k in ['name','rail','destination','destination_mask','beneficiary_version','method','collection_ref']}
        data.update(net=net,fee=charge,total=net+charge,payer=r['buyer'],source_id=r['id'],settlement_parent=r['id'],allocation_hash=terms['hash'],accounting_version=2,collection='confirmed',payout='not_started',state='collected',accepted=True,recovery_only=kind=='refund',scenario=r.get('scenario','success') if kind=='payout' else 'success',quote=r.get('quote'))
        leg=insert(db,'payment',r['owner'],data)
        journal(db,leg,'allocation:'+leg['id'],[(a,v) for a,v in [('settlement_clearing',leg['total']),(liability(leg),-net),('deferred_fee',-charge)] if v])
        start_job(db,leg,kind);save(db,leg);children.append(leg['id'])
        event(db,leg['id'],'system','settlement.leg_created','From '+r['id']+'; exact consent '+terms['hash'])
    r.update(settlement_children=children,state='settlement_pending',payout='pending',case_open=True)
    event(db,r['id'],'system','settlement.allocated','Both parties consented; '+encode(terms))

def process_jobs():
    with connection() as db: jobs=db.execute("SELECT id FROM jobs WHERE state='pending' AND due<=?",(now(),)).fetchall()
    for item in jobs:
        try:
            with connection(True) as db: finish_job(db,item)
        except Exception as error:
            # One unavailable instruction cannot roll back or starve unrelated payments.
            with connection(True) as db:
                job=db.execute('SELECT * FROM jobs WHERE id=?',(item['id'],)).fetchone()
                db.execute('UPDATE jobs SET due=?,attempts=attempts+1,last_error=? WHERE id=?',(now()+30,str(error)[:300],item['id']))
                r=get_record(db,job['record_id']);r.update(case_open=True,case_reason='Financial job retained for investigation. No replacement instruction was created.');save(db,r)
                event(db,r['id'],'system','job.recovery_required',job['reference'])

def create_session(db, actor, role):
    token=secrets.token_urlsafe(32)
    db.execute('INSERT INTO sessions VALUES (?,?,?,?)',(digest(token),actor,role,now()+7*86400))
    return token

def mutate(db, path, b, s):
    actor=s['actor']
    if path=='/api/create':
        require(s['role']=='customer','Use a customer session to create a payment.',403)
        kind=b.get('kind')
        require(kind in ['escrow','request','shop'],'Choose escrow, payment request, or shop.')
        merchant=None
        if b.get('merchant_setup') is True and kind!='escrow':
            row=db.execute('SELECT data FROM merchants WHERE actor=?',(actor,)).fetchone()
            require(row is not None,'Set up your demo merchant first.',409)
            merchant=json.loads(row['data'])
            require(merchant['status']=='approved','Demo merchant verification is pending.',409)
            b=dict(b,name=merchant['display_name'],rail=merchant['rail'],destination=merchant['account'],demo_verified=True)
        name=text(b.get('shop_name') or b.get('name'),'Your name',1,60)
        rail=b.get('rail','KPay'); require(rail in METHODS,'Unsupported payout method.')
        destination=text(b.get('destination'),'Demo payout destination',5,30)
        require(b.get('demo_verified') is True,'Confirm the simulated beneficiary setup.')
        data=dict(name=name,rail=rail,destination_mask='•• '+destination[-4:],destination=destination,beneficiary_version=1,fee_version='demo-net-2pct-min100-v1',accounting_version=2,state='open',scenario='success',payout='not_started',collection='not_started')
        data['purpose']=text(b.get('purpose') or 'Merchant payment','Purpose',1,100)
        if merchant: data.update(merchant={k:v for k,v in merchant.items() if k!='account'},settlement_model='merchant_direct',provider_profile=merchant['profile'],environment='simulation')
        if kind!='shop':
            net=amount(b.get('net')); data.update(net=net,fee=fee(net),total=net+fee(net),expires=now()+1800)
        else: data['paused']=False
        if b.get('photo'):
            photo=b['photo'];require(isinstance(photo,str) and photo.startswith(('data:image/png;base64,','data:image/jpeg;base64,')) and len(photo)<700000,'Choose a PNG/JPEG up to 500 KB.')
            try: decoded=base64.b64decode(photo.split(',',1)[1],validate=True)
            except Exception: raise DomainError('Invalid item photo.')
            require(len(decoded)<=500*1024 and (decoded.startswith(b'\x89PNG\r\n\x1a\n') or decoded.startswith(b'\xff\xd8')),'Invalid PNG/JPEG image.')
            data['photo']=photo
        if kind=='escrow':
            data.update(item=text(b.get('item'),'Item',1,100),description=text(b.get('description','Agreed directly between buyer and seller'),'Description',1,600),delivery=text(b.get('delivery'),'Delivery agreement',3,300),window=text(b.get('window','24 hours after confirmed receipt'),'Check window',3,100),state='awaiting_buyer',agreement_version=1,invitation=secrets.token_urlsafe(18))
        db.execute('UPDATE accounts SET name=? WHERE id=?',(name,actor))
        r=insert(db,kind,actor,data)
        db.execute('DELETE FROM drafts WHERE actor=? AND kind=?',(actor,kind))
        return {'record':project(db,r,s)}
    parts=path.strip('/').split('/')
    require(len(parts)==4 and parts[:2]==['api','records'],'Unknown command.',404)
    rid, action=parts[2:]; r=get_record(db,rid)
    require(not r.get('settlement_children') or action in ['evidence','note','assign','request-evidence','scenario'],'Settlement legs must be followed independently; the original hold cannot be dispatched again.',409)
    if action=='counter-request':
        require(s['role']=='customer' and owner(r,s) and r['kind']=='shop','Private shop owner access required.',403)
        require(not r.get('paused') and settings(db,'route_open')=='true','Shop payments are paused.',409)
        net=amount(b.get('net'))
        data={k:r[k] for k in ['name','rail','destination','destination_mask','beneficiary_version','fee_version','accounting_version','merchant','settlement_model','provider_profile','environment'] if k in r}
        data.update(net=net,fee=fee(net),total=net+fee(net),shop_id=r['id'],state='open',collection='not_started',payout='not_started',scenario='success',expires=now()+1800,purpose=text(b.get('purpose') or 'Counter purchase','Purpose',1,100))
        order=insert(db,'request',actor,data)
        event(db,order['id'],actor,'counter.created','Fixed-amount browser checkout; no bank QR capability')
        return {'record':project(db,order,s)}
    if action=='pay-intent':
        require(s['role']=='customer','A private customer session is required.',403)
        require(r['kind'] in ['request','shop'],'Invalid payment source.')
        require(settings(db,'route_open')=='true','Collections are temporarily paused.',409)
        if r['kind']=='request':
            if r.get('payment_id'):
                existing=get_record(db,r['payment_id'])
                require(existing.get('payer')==actor,'This single-use request already has a payment in progress.',409)
                return {'record':project(db,existing,s)}
            require(now()<r['expires'],'This request expired. Ask the recipient for a new link.',409)
            net=r['net']
        else:
            require(not r.get('paused'),'This shop has paused new payments.',409)
            net=amount(b.get('net'))
        require(r.get('settlement_model')=='merchant_direct' or available_float(db)>=net,'This payout route has insufficient available float. No payment was taken.',409)
        p=insert(db,'payment',r['owner'],dict(name=r['name'],net=net,fee=fee(net),total=net+fee(net),rail=r['rail'],destination=r['destination'],destination_mask=r['destination_mask'],beneficiary_version=r['beneficiary_version'],fee_version=r.get('fee_version','demo-net-2pct-min100-v1'),accounting_version=2,source_id=rid,shop_id=rid if r['kind']=='shop' else r.get('shop_id'),payer=actor,state='awaiting_payment',collection='not_started',payout='not_started',quote_expires=now()+900,scenario=r.get('scenario','success')))
        for field in ['purpose','merchant','settlement_model','provider_profile','environment']:
            if field in r: p[field]=r[field]
        save(db,p)
        if r['kind']=='request': r['payment_id']=p['id'];save(db,r)
        return {'record':project(db,p,s)}
    if action=='join':
        require(s['role']=='customer','A private customer session is required.',403)
        require(r['kind']=='escrow' and not owner(r,s),'Open this deal in a different private browser session to join as buyer.',403)
        require(not r.get('buyer') or r['buyer']==actor,'This deal already has a buyer.',409)
        require(hmac.compare_digest(str(b.get('invitation','')),r['invitation']),'Ask the seller for the private buyer invitation key. The public payment code cannot join a buyer.',403)
        require(r['state'] in ['awaiting_buyer','awaiting_payment'],'This invitation is no longer open.',409)
        require(b.get('agree') is True,'Accept the delivery and release terms.')
        r.update(buyer=actor,state='awaiting_payment',accepted=True,quote_expires=now()+900)
        event(db,rid,actor,'agreement.accepted','Agreement version 1; buyer-authorized release only')
    elif action=='authorize':
        require((r['kind']=='escrow' and r.get('buyer')==actor) or r.get('payer')==actor,'Only the private buyer/payer can authorize payment.',403)
        require(r['state'] in ['awaiting_payment','payment_failed'],'Payment is already processing.',409)
        require(b.get('agree') is True,'Review and accept the payment total.')
        require(now()<r.get('quote_expires',0),'Your quote expired. Refresh the quote before paying.',409)
        if r['kind']=='payment':
            source=get_record(db,r['source_id'])
            require(not source.get('paused'),'This shop is paused.',409)
            require(source['kind']=='shop' or now()<source['expires'],'This request expired.',409)
        require(settings(db,'route_open')=='true','Collections are temporarily paused.',409)
        require(r.get('settlement_model')=='merchant_direct' or available_float(db)>=r['net'],'Payout float is unavailable; no collection was started.',409)
        method=b.get('method');require(method in METHODS,'Choose an available collection method.')
        r.update(state='collection_pending',collection='pending',accepted=True,method=method,collection_ref=uid('SIM-IN'))
        r['quote']=quote_snapshot(r,method)
        db.execute('INSERT INTO collection_attempts VALUES (?,?,?,?,?)',(r['collection_ref'],rid,method,encode(r['quote']),now()))
        event(db,rid,actor,'collection.authorized',method)
    elif action=='requote':
        require(member(r,s) and (r.get('buyer')==actor or r.get('payer')==actor),'Private payer access required.',403)
        require(r.get('collection') in ['not_started','failed'],'Cannot change an authorized quote.',409)
        r['quote_expires']=now()+900
        event(db,rid,actor,'quote.refreshed')
    elif action=='deliver':
        require(owner(r,s),'Only the seller can mark delivery.',403)
        require(r['kind']=='escrow' and r['state']=='held' and not r.get('case_open'),'This deal is not awaiting delivery.',409)
        r['delivery_note']=text(b.get('note') or 'Seller marked delivered','Delivery note',1,300)
        r['state']='delivered';event(db,rid,actor,'delivery.claimed','Buyer must still check and authorize release')
    elif action=='release':
        require(r.get('buyer')==actor,'Only the private buyer can release this payment.',403)
        require(r['state']=='delivered' and not r.get('case_open'),'Release is blocked or delivery has not been recorded.',409)
        require(b.get('agree') is True,'Confirm that you received and checked the item.')
        start_job(db,r);event(db,rid,actor,'escrow.release_authorized')
    elif action=='dispute':
        require(member(r,s) and s['role']=='customer','A private participant session is required.',403)
        require(r['kind']=='escrow' and r['state'] in ['held','delivered','release_pending','disputed'],'A dispute requires a held, unpaid escrow.',409)
        reason=text(b.get('reason'),'Problem description',8,1000)
        r.update(state='disputed',case_open=True,release_blocked=True,case_reason=reason,reviewed=False)
        for job in db.execute("SELECT * FROM jobs WHERE record_id=? AND state='pending'",(rid,)).fetchall(): reserve_job(db,r,job,True)
        db.execute("UPDATE jobs SET state='blocked' WHERE record_id=? AND state='pending'",(rid,))
        r['payout']='blocked';event(db,rid,actor,'escrow.dispute_opened',reason)
    elif action=='pause':
        require(owner(r,s),'Only the private shop owner can pause collections.',403)
        require(r['kind']=='shop','Only shops can be paused.')
        r['paused']=not r.get('paused');event(db,rid,actor,'shop.collections_paused' if r['paused'] else 'shop.collections_resumed')
    elif action=='destination':
        require(owner(r,s) and s['role']=='customer' and r['kind']=='shop','Private shop owner access required.',403)
        require(b.get('demo_verified') is True,'Confirm the new simulated beneficiary setup.')
        rail=b.get('rail');require(rail in METHODS,'Unsupported destination route.')
        destination=text(b.get('destination'),'Demo payout destination',5,30)
        r.update(rail=rail,destination=destination,destination_mask='•• '+destination[-4:],beneficiary_version=r['beneficiary_version']+1)
        event(db,rid,actor,'shop.beneficiary_version_created','Simulated verification; version '+str(r['beneficiary_version'])+'; existing quotes retain their original destination')
    elif action=='evidence':
        require(member(r,s),'Private participant or staff access is required.',403)
        require(r.get('case_open'),'Evidence belongs to an open case.',409)
        name=text(b.get('name'),'Filename',1,100)
        mime=b.get('mime');require(mime in ['image/png','image/jpeg','application/pdf','text/plain'],'Upload a PNG, JPEG, PDF, or text file.')
        try: content=base64.b64decode(b.get('content',''),validate=True)
        except Exception: raise DomainError('Invalid file data.')
        require(0<len(content)<=2*1024*1024,'Files must be between 1 byte and 2 MB.')
        db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?)',(uid('file'),rid,actor,name,mime,content))
        r['reviewed']=False
        event(db,rid,actor,'case.evidence_added',name)
    elif action=='consent-split':
        require(s['role']=='customer' and actor in [r['owner'],r.get('buyer')],'Private buyer or seller consent required.',403)
        require(r.get('case_open') and r.get('split_terms') and b.get('agree') is True and b.get('split_hash')==r['split_terms']['hash'],'Review and agree to the current exact settlement.',409)
        r['split_consents']=sorted(set(r.get('split_consents',[])+[actor]))
        event(db,rid,actor,'settlement.participant_consented',r['split_terms']['hash'])
    elif action in ['note','assign','request-evidence','pause-release','review','offer-split','propose','cancel','approve','submit','query','scenario']:
        staff(s)
        reason=text(b.get('reason'),'Staff reason',8,1000)
        if action=='note': event(db,rid,actor,'case.note_added',reason)
        elif action=='pause-release':
            require(r['kind']=='escrow' and r['state'] in ['held','delivered','release_pending'],'Only an unpaid held escrow can be paused.',409)
            for job in db.execute("SELECT * FROM jobs WHERE record_id=? AND state='pending'",(rid,)).fetchall(): reserve_job(db,r,job,True)
            db.execute("UPDATE jobs SET state='blocked' WHERE record_id=? AND state='pending'",(rid,))
            r.update(state='disputed',case_open=True,release_blocked=True,payout='blocked',case_reason=reason,reviewed=False)
            event(db,rid,actor,'case.release_paused',reason)
        elif action=='assign':
            assignee=b.get('assignee');require(assignee in STAFF,'Choose a valid staff assignee.')
            r['assignee']=assignee;event(db,rid,actor,'case.assigned',assignee+': '+reason)
        elif action=='request-evidence':
            require(r.get('case_open'),'An open case is required.',409)
            r['evidence_request']=reason;event(db,rid,actor,'case.evidence_requested',reason)
        elif action=='cancel':
            finance(s)
            changed=db.execute("UPDATE proposals SET state='canceled' WHERE record_id=? AND state IN ('proposed','approved')",(rid,)).rowcount
            require(changed>0,'There is no pending proposal to cancel.',409)
            event(db,rid,actor,'instruction.proposal_canceled',reason)
        elif action=='review':
            finance(s);require(r.get('case_open'),'No open case to review.',409)
            r['reviewed']=True;event(db,rid,actor,'case.human_review_recorded',reason)
        elif action=='offer-split':
            finance(s)
            require(r['kind']=='escrow' and r.get('case_open') and r.get('reviewed') and r.get('collection')=='confirmed' and r.get('accounting_version'),'Reviewed, funded escrow required.',409)
            require(not db.execute("SELECT 1 FROM jobs WHERE record_id=? AND state IN ('pending','unknown')",(rid,)).fetchone(),'Resolve the existing instruction first.',409)
            require(not db.execute("SELECT 1 FROM proposals WHERE record_id=? AND state IN ('proposed','approved')",(rid,)).fetchone(),'Cancel the existing proposal first.',409)
            seller_net=b.get('seller_net');require(type(seller_net) is int and 0<seller_net<r['net'],'Seller allocation must be a whole MMK amount between zero and the principal.')
            terms=dict(seller_net=seller_net,buyer_refund=r['net']-seller_net,fee=r['fee'],currency='MMK',fee_policy='Original service fee retained on an agreed partial settlement',agreement_version=r['agreement_version'])
            terms['hash']=digest(encode(terms));r.update(split_terms=terms,split_consents=[])
            event(db,rid,actor,'settlement.offered',reason)
        elif action=='scenario':
            finance(s);scenario=b.get('scenario');require(scenario in SCENARIOS,'Unknown simulation scenario.')
            r['scenario']=scenario;event(db,rid,actor,'simulator.scenario_changed',reason)
        elif action=='query':
            jobs=db.execute("SELECT * FROM jobs WHERE record_id=? AND state='unknown'",(rid,)).fetchall()
            require(bool(jobs),'There is no uncertain payout to query.',409)
            scenario=r.get('scenario')
            require(scenario in ['success','payout_failed'],'The simulated provider still has no final outcome. A retry is blocked.',409)
            event(db,rid,actor,'provider.status_queried',reason)
            for job in jobs: finish_job(db,job,scenario)
            return {'record':project(db,get_record(db,rid),s)}
        elif action=='propose':
            finance(s)
            decision=b.get('decision');require(decision in ['retry','refund','release','split'],'Choose retry, refund, release or agreed partial settlement.')
            require(not r.get('recovery_only') or decision in ['refund','retry'],'Receipt exceptions can only be refunded to their original source.',409)
            require(r.get('case_open') and r.get('collection')=='confirmed','An open funded case is required.',409)
            require(not db.execute("SELECT 1 FROM proposals WHERE record_id=? AND state IN ('proposed','approved')",(rid,)).fetchone(),'A proposal is already awaiting action.',409)
            require(not db.execute("SELECT 1 FROM jobs WHERE record_id=? AND state IN ('pending','unknown')",(rid,)).fetchone(),'Query the existing payout first. Pending or unknown instructions cannot be replaced.',409)
            if r['kind']=='escrow':require(r.get('reviewed'),'Record human review before deciding an escrow case.',409)
            if decision=='retry':require(r['payout']=='failed','Retry requires authoritative failure.',409)
            if decision=='release':require(r['kind']=='escrow' and r.get('payout') in ['blocked','failed','not_started'],'This case cannot release funds.',409)
            if decision=='split':require(r['kind']=='escrow' and r.get('split_terms') and set(r.get('split_consents',[]))=={r['owner'],r['buyer']},'Both participants must first consent to this exact split.',409)
            pid=uid('proposal')
            previous_job=db.execute("SELECT type FROM jobs WHERE record_id=? AND state='failed' ORDER BY rowid DESC LIMIT 1",(rid,)).fetchone()
            refund_instruction=decision=='refund' or (decision=='retry' and previous_job and previous_job['type']=='refund')
            # Approval is bound to the next immutable record version and amount.
            snapshot=dict(action='refund' if refund_instruction else 'payout',amount=r['total'] if refund_instruction else r['net'],currency='MMK',destination=('original-source:'+r['collection_ref']) if refund_instruction else r['destination'],beneficiary_version=r.get('beneficiary_version'),quote_hash=r.get('quote',{}).get('hash'),expires=now()+1800)
            if decision=='split':snapshot.update(action='split',split_hash=r['split_terms']['hash'],allocations=r['split_terms'])
            db.execute('INSERT INTO proposals(id,record_id,proposer,approver,action,reason,state,version,amount,snapshot) VALUES (?,?,?,?,?,?,?,?,?,?)',(pid,rid,actor,None,decision,reason,'proposed',r['version']+1,r['total'] if refund_instruction else r['net'],encode(snapshot)))
            event(db,rid,actor,'instruction.proposed',decision+': '+reason)
        elif action in ['approve','submit']:
            p=db.execute('SELECT * FROM proposals WHERE id=? AND record_id=?',(b.get('proposal'),rid)).fetchone()
            require(p is not None,'Proposal not found.',404)
            if p['snapshot']:require(json.loads(p['snapshot'])['expires']>now(),'Proposal expired. Cancel and review a new instruction.',409)
            if action=='approve':
                finance(s);require(p['proposer']!=actor,'A different finance staff member must approve.',403)
                require(p['state']=='proposed' and p['version']==r['version'],'Proposal changed or is no longer approvable.',409)
                db.execute("UPDATE proposals SET state='approved',approver=?,version=? WHERE id=?",(actor,r['version']+1,p['id']))
                event(db,rid,actor,'instruction.independently_approved',reason)
            else:
                require(s['role'] in ['operations','finance','admin'],'Operations or finance must submit.',403)
                require(p['state']=='approved' and p['approver'] and p['version']==r['version'],'Independent approval is required and must match the current record.',409)
                require(not db.execute("SELECT 1 FROM jobs WHERE record_id=? AND state IN ('pending','unknown')",(rid,)).fetchone(),'An instruction is already in progress.',409)
                if p['action']=='split':
                    start_split(db,r,json.loads(p['snapshot']))
                    db.execute("UPDATE proposals SET state='submitted' WHERE id=?",(p['id'],))
                    event(db,rid,actor,'instruction.submitted',reason);save(db,r)
                    return {'record':project(db,r,s)}
                r['case_open']=True
                r['release_blocked']=False
                retry_job=db.execute("SELECT type FROM jobs WHERE record_id=? AND state='failed' ORDER BY rowid DESC LIMIT 1",(rid,)).fetchone()
                instruction_type='refund' if p['action']=='refund' else retry_job['type'] if p['action']=='retry' and retry_job else 'payout'
                require(instruction_type=='refund' or available_float(db)>=r['net'],'Payout float remains unavailable.',409)
                start_job(db,r,instruction_type)
                db.execute("UPDATE proposals SET state='submitted' WHERE id=?",(p['id'],))
                event(db,rid,actor,'instruction.submitted',reason)
    else: raise DomainError('Unknown action.',404)
    save(db,r)
    if r.get('settlement_parent'): sync_settlement(db,r['settlement_parent'])
    return {'record':project(db,r,s)}

class Handler(SimpleHTTPRequestHandler):
    server_version='Handshake/1.0'
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(PUBLIC),**kwargs)
    def log_message(self, fmt, *args):
        if args and str(args[1] if len(args)>1 else '').startswith('5'): super().log_message(fmt,*args)
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','same-origin')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'")
        super().end_headers()
    def respond(self, value, status=200, cookie=None):
        if getattr(self,'defer_response',False):
            self.pending_response=(value,status,cookie)
            return
        data=encode(value).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(data)))
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(data)
    def session(self,db):
        c=SimpleCookie();c.load(self.headers.get('Cookie',''))
        token=c['handshake'].value if 'handshake' in c else ''
        row=db.execute('SELECT * FROM sessions WHERE token=? AND expires>?',(digest(token),now())).fetchone()
        return dict(row) if row else None
    def do_GET(self):
        self.defer_response=True
        try:self.handle_get()
        finally:self.defer_response=False
        if hasattr(self,'pending_response'):self.respond(*self.pending_response)
    def handle_get(self):
        path=urlparse(self.path).path
        try:
            if path.startswith('/api/mvp/'):
                with connection() as db:
                    self.respond(receipt_mvp.handle(db,path,None,self.session(db),require,event))
                return
            if path=='/api/merchant':
                with connection() as db:
                    s=self.session(db)
                    require(s and s['role']=='customer','Private customer access required.',401)
                    row=db.execute('SELECT data FROM merchants WHERE actor=?',(s['actor'],)).fetchone()
                    self.respond({'merchant':json.loads(row['data']) if row else None})
                return
            if path=='/api/session':
                with connection() as db:
                    s=self.session(db)
                    self.respond({'session':{'actor':s['actor'],'role':s['role']} if s else None,'mode':'simulation'})
                return
            if path=='/api/qr':
                value=parse_qs(urlparse(self.path).query).get('text',[''])[0]
                require(len(value)<1500 and value.startswith(('http://127.0.0.1:', 'http://localhost:')),'Only local browser-entry URLs are supported.')
                sys.path.insert(0,str(ROOT/'vendor'))
                import qrcode
                import qrcode.image.svg
                out=io.BytesIO();qrcode.make(value,image_factory=qrcode.image.svg.SvgPathImage,border=4).save(out)
                data=out.getvalue();self.send_response(200);self.send_header('Content-Type','image/svg+xml');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
                return
            if path.startswith('/api/'):
                with connection() as db:
                    s=self.session(db)
                    if path.startswith('/api/records/'):
                        r=get_record(db,path.rsplit('/',1)[1]);self.respond({'record':project(db,r,s)});return
                    if path=='/api/activity':
                        require(s and s['role']=='customer','Restore your private access to view activity.',401)
                        records=[project(db,get_record(db,x['id']),s) for x in db.execute('SELECT id FROM records ORDER BY rowid DESC') if member(get_record(db,x['id']),s)]
                        self.respond({'records':records});return
                    if path=='/api/drafts':
                        require(s and s['role']=='customer','Private customer access required.',401)
                        self.respond({'drafts':{x['kind']:json.loads(x['data']) for x in db.execute('SELECT kind,data FROM drafts WHERE actor=?',(s['actor'],))}});return
                    if path.startswith('/api/evidence/'):
                        file=db.execute('SELECT * FROM evidence WHERE id=?',(path.rsplit('/',1)[1],)).fetchone()
                        require(file is not None,'File not found.',404);r=get_record(db,file['record_id'])
                        require(member(r,s),'Private evidence access required.',403)
                        self.send_response(200);self.send_header('Content-Type',file['mime']);self.send_header('Content-Disposition','attachment; filename="'+file['id']+'"');self.send_header('Content-Length',str(len(file['content'])));self.end_headers();self.wfile.write(file['content']);return
                    if path=='/api/resolve':
                        code=parse_qs(urlparse(self.path).query).get('code',[''])[0].replace(' ','').upper()
                        key=self.client_address[0];lookup=self.server.lookups.setdefault(key,[]);lookup[:]=[x for x in lookup if x>now()-60]
                        require(len(lookup)<30,'Too many code lookups. Wait one minute.',429);lookup.append(now())
                        row=db.execute('SELECT id FROM records WHERE code=? AND kind!=?',(code,'payment')).fetchone()
                        require(row is not None,'Code not found. Check it and try again.',404)
                        self.respond({'id':row['id']});return
                    if path=='/api/admin':
                        require(s is not None,'Sign in as staff.',401);staff(s)
                        records=[project(db,get_record(db,x['id']),s) for x in db.execute('SELECT id FROM records ORDER BY rowid DESC')]
                        balances=[dict(x) for x in db.execute('SELECT account,SUM(amount) AS balance FROM ledger GROUP BY account')]
                        journals=[dict(x) for x in db.execute('SELECT journal,SUM(amount) AS difference FROM ledger GROUP BY journal HAVING SUM(amount)!=0')]
                        callbacks=[dict(x) for x in db.execute('SELECT c.record_id,c.amount,COALESCE(SUM(l.amount),0) AS ledger_amount FROM callbacks c LEFT JOIN ledger l ON l.record_id=c.record_id AND l.account IN (\'provider_cash\',\'merchant_provider_clearing\') AND l.journal LIKE \'collection:%\' GROUP BY c.receipt_id HAVING c.amount!=COALESCE(SUM(l.amount),0)')]
                        inbox=[dict(x) for x in db.execute('SELECT id,event_id,receipt_id,record_id,disposition,reason,recovery_id,created FROM provider_inbox ORDER BY id DESC LIMIT 200')]
                        unresolved=[x for x in inbox if x['disposition'] in ['unmatched','rejected']]
                        provider_differences=[dict(x) for x in db.execute("SELECT p.reference,p.outcome,j.state AS internal_state FROM provider_instructions p JOIN jobs j ON j.id=p.job_id WHERE p.outcome!=j.state AND NOT(p.outcome='confirmed' AND j.state='pending')")]
                        audit=[dict(x) for x in db.execute('SELECT * FROM events ORDER BY id DESC LIMIT 200')]
                        query=parse_qs(urlparse(self.path).query)
                        q=query.get('q',[''])[0].lower();assignee=query.get('assignee',[''])[0];kind=query.get('kind',[''])[0]
                        try:min_net=int(query.get('min_amount',['0'])[0]);min_age=int(query.get('min_age_hours',['0'])[0])
                        except ValueError:raise DomainError('Invalid queue filter.',400)
                        records=[r for r in records if (not q or q in encode(r).lower()) and (not assignee or r.get('assignee')==assignee) and (not kind or r['kind']==kind) and r.get('net',0)>=min_net and now()-r['created']>=min_age*3600]
                        capacity=int(settings(db,'float'));available=available_float(db)
                        self.respond({'records':records,'balances':balances,'differences':journals+callbacks+provider_differences+unresolved,'inbox':inbox,'audit':audit,'float':available,'liquidity':{'capacity':capacity,'reserved':capacity-available,'available':available},'capabilities':provider.capabilities,'route_open':settings(db,'route_open')=='true'});return
                    raise DomainError('API route not found.',404)
            if path in ['/','/index.html'] or '.' not in path.rsplit('/',1)[-1]: self.path='/index.html'
            super().do_GET()
        except DomainError as e:self.respond({'error':e.message},e.status)
        except Exception as e:
            print('GET error:',repr(e),flush=True);self.respond({'error':'Server error. Your saved records are preserved.'},500)
    def do_POST(self):
        # Never acknowledge a command before its transaction has committed and closed.
        self.defer_response=True
        try:self.handle_post()
        finally:self.defer_response=False
        if hasattr(self,'pending_response'):self.respond(*self.pending_response)
    def handle_post(self):
        try:
            path=urlparse(self.path).path
            length=int(self.headers.get('Content-Length','0'));require(0<length<=3000000,'Request size is invalid.',413)
            raw=self.rfile.read(length)
            if path=='/api/provider/callback':
                with connection(True) as db:
                    require(provider.verify_callback(settings(db,'callback_secret'),raw,self.headers.get('X-Provider-Signature','')),'Invalid provider signature.',403)
                    status,result=accept_callback(db,json.loads(raw))
                    self.respond(result,status)
                return
            require(self.headers.get('X-Handshake')=='1' and self.headers.get('Content-Type','').startswith('application/json'),'Same-origin JSON request required.',403)
            origin=self.headers.get('Origin')
            require(not origin or origin==f'http://{self.headers.get("Host")}','Cross-origin commands are blocked.',403)
            b=json.loads(raw)
            with connection(True) as db:
                if path=='/api/session/create':
                    secret=secrets.token_urlsafe(24);actor=uid('person')
                    db.execute('INSERT INTO accounts VALUES (?,?,?)',(actor,digest(secret),'You'))
                    token=create_session(db,actor,'customer')
                    self.respond({'recovery':secret,'session':{'actor':actor,'role':'customer'}},cookie=f'handshake={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800');return
                if path in ['/api/session/recover','/api/session/staff']:
                    key=self.client_address[0];attempts=self.server.logins.setdefault(key,[]);attempts[:]=[x for x in attempts if x>now()-60]
                    require(len(attempts)<20,'Too many sign-in attempts. Wait a minute.',429);attempts.append(now())
                    if path.endswith('recover'):
                        row=db.execute('SELECT id FROM accounts WHERE recovery_hash=?',(digest(str(b.get('recovery',''))),)).fetchone()
                        require(row is not None,'Private recovery key not recognized.',401);actor=row['id'];role='customer'
                    else:
                        actor=b.get('username');require(actor in STAFF and hmac.compare_digest(str(b.get('password','')),STAFF_PASSWORD),'Staff details not recognized.',401);role=STAFF[actor]
                    token=create_session(db,actor,role)
                    self.respond({'session':{'actor':actor,'role':role}},cookie=f'handshake={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800');return
                s=self.session(db);require(s is not None,'Start or restore your private session.',401)
                if path.startswith('/api/mvp/'):
                    self.respond(receipt_mvp.handle(db,path,b,s,require,event));return
                if path=='/api/session/logout':
                    db.execute('DELETE FROM sessions WHERE token=?',(s['token'],));self.respond({'ok':True},cookie='handshake=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0');return
                if path=='/api/merchant':
                    require(s['role']=='customer','Private customer access required.',403)
                    require(b.get('demo_verified') is True,'Confirm fictional merchant details.')
                    profile=b.get('profile','hosted');require(profile in ['hosted','qr'],'Choose hosted or QR demo checkout.')
                    rail=b.get('rail','KPay');require(rail in METHODS,'Unsupported demo account.')
                    previous=db.execute('SELECT data FROM merchants WHERE actor=?',(s['actor'],)).fetchone()
                    version=json.loads(previous['data'])['version']+1 if previous else 1
                    account=text(b.get('account'),'Fictional account',5,30)
                    m=dict(id='demo-merchant:'+s['actor'],display_name=text(b.get('display_name'),'Merchant name',1,60),payment_name=text(b.get('display_name'),'Merchant name',1,60),rail=rail,account=account,account_mask='•• '+account[-4:],profile=profile,status='approved',environment='simulation',version=version,settlement_timing='Automatic demo settlement after collection; no live schedule agreed')
                    db.execute('INSERT INTO merchants VALUES (?,?) ON CONFLICT(actor) DO UPDATE SET data=excluded.data',(s['actor'],encode(m)))
                    for row in db.execute("SELECT id FROM records WHERE owner=? AND kind='shop'",(s['actor'],)).fetchall():
                        shop=get_record(db,row['id'])
                        if shop.get('settlement_model')=='merchant_direct':
                            shop.update(rail=m['rail'],destination=m['account'],destination_mask=m['account_mask'],beneficiary_version=m['version'],merchant={k:v for k,v in m.items() if k!='account'},provider_profile=m['profile'])
                            save(db,shop)
                            event(db,shop['id'],s['actor'],'shop.receiving_version_updated','New orders use merchant configuration version '+str(m['version'])+'; authorized orders retain snapshots')
                    event(db,m['id'],s['actor'],'merchant.demo_approved','Fictional profile; verification is simulated')
                    self.respond({'merchant':m});return
                if path=='/api/drafts':
                    require(s['role']=='customer','Private customer access required.',403)
                    kind=b.get('kind');require(kind in ['escrow','request','shop'],'Invalid draft kind.')
                    allowed=['photo','_updated','kind','name','net','rail','destination','item','description','delivery','window','purpose','shop_name','merchant_setup','demo_verified','command_id']
                    draft={k:(b[k] is True or b[k]=='true' if k in ['demo_verified','merchant_setup'] else str(b[k])[:700000 if k=='photo' else 1000]) for k in allowed if k in b}
                    db.execute('INSERT INTO drafts VALUES (?,?,?,?) ON CONFLICT(actor,kind) DO UPDATE SET data=excluded.data,updated=excluded.updated',(s['actor'],kind,encode(draft),now()))
                    self.respond({'ok':True});return
                if path=='/api/admin/route':
                    require(s['role'] in ['operations','finance','admin'],'Operations or finance access required.',403)
                    reason=text(b.get('reason'),'Reason',8,300);require(type(b.get('open')) is bool,'Availability must be true or false.')
                    db.execute("UPDATE settings SET value=? WHERE key='route_open'",('true' if b['open'] else 'false',));event(db,'routes',s['actor'],'route.availability_changed',reason);self.respond({'ok':True});return
                if path.startswith('/api/simulate/'):
                    rid=path.rsplit('/',1)[1];r=get_record(db,rid)
                    require(r.get('payer')==s['actor'] or r.get('buyer')==s['actor'] or s['role'] in ['finance','admin'],'Private payer or finance session required.',403)
                    outcome=b.get('outcome');require(outcome in ['confirmed','failed','pending'],'Unknown provider result.')
                    if outcome=='confirmed':
                        # Same authoritative receiver used by authenticated callbacks.
                        require(r.get('collection') in ['pending','confirmed'],'No authorized collection is pending.',409)
                        receipt=provider.collection_result(r)
                        r=receive(db,rid,receipt['event_id'],receipt['receipt_id'],receipt['amount'])
                    elif outcome=='failed':
                        require(r.get('collection')=='pending','Collection is not pending.',409)
                        r.update(collection='failed',state='payment_failed');event(db,rid,'simulator','collection.failed');save(db,r)
                    self.respond({'record':project(db,r,s)});return
                command=b.get('command_id');require(isinstance(command,str) and 8<=len(command)<=100,'A command idempotency key is required.')
                body_hash=digest(path+encode(b));prior=db.execute('SELECT * FROM commands WHERE actor=? AND key=?',(s['actor'],command)).fetchone()
                if prior:
                    require(prior['body_hash']==body_hash,'This command key was already used for different input.',409);self.respond(json.loads(prior['result']));return
                rid=path.strip('/').split('/')
                if len(rid)==4 and rid[:2]==['api','records'] and b.get('expected_version') is not None:
                    require(get_record(db,rid[2])['version']==b['expected_version'],'This record changed. Refresh before trying again.',409)
                result=mutate(db,path,b,s)
                event(db,result['record']['id'],s['actor'],'command.committed',encode({'command_id':command,'action':path.rsplit('/',1)[-1],'role':s['role'],'body_hash':body_hash}))
                db.execute('INSERT INTO commands VALUES (?,?,?,?)',(s['actor'],command,body_hash,encode(result)))
                self.respond(result)
        except DomainError as e:
            if e.status in [403,409] and path.startswith('/api/records/'):
                with connection(True) as audit_db:
                    actor_session=self.session(audit_db)
                    event(audit_db,path.split('/')[3],actor_session['actor'] if actor_session else 'anonymous','command.denied',path.rsplit('/',1)[-1]+': '+e.message)
            self.respond({'error':e.message},e.status)
        except (ValueError,KeyError,TypeError) as e:self.respond({'error':'Invalid request fields.'},400)
        except Exception as e:
            print('POST error:',repr(e),flush=True);self.respond({'error':'Server error. No incomplete command was committed.'},500)

def worker(stop):
    while not stop.wait(.5):
        try: process_jobs()
        except Exception as e: print('Job retained for investigation:',repr(e),flush=True)

if __name__=='__main__':
    initialize();stop=threading.Event();threading.Thread(target=worker,args=(stop,),daemon=True).start()
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler);server.lookups={};server.logins={}
    print(f'FOM — Future of Myanmar: http://127.0.0.1:{PORT}\nLocal simulation only. Staff accounts: support, operations, finance-a, finance-b.\nSee README.md for the demo password and recovery instructions.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:stop.set();server.server_close()
