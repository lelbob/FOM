"""Receipt-submission MVP. No collection, custody or money movement is asserted here."""
import base64
import hashlib
import json
import secrets
import time

METHODS=['KPay','WavePay','AYA Pay','UAB Pay','CB Pay']

def pending_shop(data):
    return data.get('kind')=='shop' and data.get('inquiry_status', 'pending' if data.get('state')=='contact_team' else data.get('state'))=='pending'

def handle(db,path,body,session,require,event):
    def text(value,name,limit=300):
        require(isinstance(value,str) and 0<len(value.strip())<=limit,'Enter '+name+'.')
        return value.strip()
    def image(value,required=False):
        if not value:
            require(not required,'Add a photo or receipt image.')
            return None
        require(isinstance(value,str) and value.startswith(('data:image/png;base64,','data:image/jpeg;base64,')) and len(value)<1400000,'Use a PNG/JPEG up to 1 MB.')
        try:raw=base64.b64decode(value.split(',',1)[1],validate=True)
        except Exception:require(False,'Invalid image.')
        require(len(raw)<=1024*1024 and (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8')),'Invalid PNG/JPEG image.')
        return value
    def load(rid):
        row=db.execute('SELECT * FROM mvp_records WHERE id=?',(rid,)).fetchone()
        require(row is not None,'This code or page is unavailable.',404)
        return dict(row,id=row['id'],data=json.loads(row['data']))
    actor=session['actor'] if session else None
    def projection(row):
        d=dict(row['data']);owner=bool(actor and actor==row['owner']);buyer=bool(actor and actor==row['buyer']);staff=session and session['role']!='customer'
        d.update(id=row['id'],code=row['code'],is_owner=owner,is_buyer=buyer,private=bool(owner or buyer or staff))
        if d['kind']=='shop':d['inquiry_pending']=pending_shop(d)
        else:d['claimed']=row['buyer'] is not None
        if d['kind']=='payment' and d['state']=='requested' and int(time.time())>=d['expires']:d['state']='expired'
        if not d['private']:
            for k in ['receipt','delivery_photo','delivery_note','payer_method','submitted_at','phone','receiving_name','shop_id','contact','notes','reports','review_note']:d.pop(k,None)
        return d
    if body is None:
        if path=='/api/mvp/staff':
            require(session and session['role']!='customer','Staff access required.',403)
            return {'records':[projection(dict(x,data=json.loads(x['data']))) for x in db.execute('SELECT * FROM mvp_records ORDER BY rowid DESC')]}
        if path=='/api/mvp/list':
            require(session and session['role']=='customer','Private browser access required.',401)
            return {'records':[projection(dict(x,data=json.loads(x['data']))) for x in db.execute('SELECT * FROM mvp_records WHERE owner=? OR buyer=? ORDER BY rowid DESC',(actor,actor))]}
        if path.startswith('/api/mvp/resolve/'):
            code=path.rsplit('/',1)[1].replace(' ','').upper()
            row=db.execute('SELECT id FROM mvp_records WHERE code=?',(code,)).fetchone()
            require(row is not None,'Check the ES, PY or SP code and try again.',404)
            return {'record':projection(load(row['id']))}
        return {'record':projection(load(path.rsplit('/',1)[1]))}
    shop_review=path.endswith('/review-shop')
    require(session and (session['role']=='customer' or (shop_review and session['role'] in ['admin','operations'])),'Private browser access required.',403)
    key=body.get('command_id');require(isinstance(key,str) and 8<=len(key)<=100,'A saved operation reference is required.')
    encoded=json.dumps(body,sort_keys=True);digest=hashlib.sha256((path+encoded).encode()).hexdigest()
    prior=db.execute('SELECT * FROM mvp_commands WHERE actor=? AND key=?',(actor,key)).fetchone()
    if prior:
        require(prior['body_hash']==digest,'Operation reference already used with different input.',409)
        return json.loads(prior['result'])
    now=int(time.time())
    if path=='/api/mvp/create':
        kind=body.get('kind');require(kind in ['escrow','payment','shop'],'Choose a service.')
        d=dict(kind=kind,title=text(body.get('title'),'a title',100),state='contact_team' if kind=='shop' else 'requested',created=now)
        if kind=='shop':
            require(not any(pending_shop(json.loads(row['data'])) for row in db.execute('SELECT data FROM mvp_records WHERE owner=?',(actor,))),
                    'You already have a pending shop registration inquiry. Wait for its review before registering another shop.',409)
            d['inquiry_status']='pending'
            d.update(shop_id=text(body.get('shop_id'),'a shop ID',100),contact=text(body.get('contact'),'contact details',120),notes=str(body.get('notes',''))[:600])
        else:
            net=body.get('amount');require(type(net) is int and 500<=net<=1000000,'Enter a whole MMK amount from 500 to 1,000,000.')
            method=body.get('receiving_method');require(method in METHODS,'Choose a receiving account.')
            d.update(amount=net,receiving_method=method,phone=text(body.get('phone'),'the receiving phone or account',40),receiving_name=text(body.get('receiving_name'),'the receiving name',100))
            if kind=='payment':d['expires']=now+1800
            else:d.update(description=text(body.get('description'),'an item description',600),delivery=text(body.get('delivery'),'delivery details'),window=text(body.get('window'),'checking terms'),photo=image(body.get('photo')))
        rid='mvp-'+secrets.token_hex(12);code={'escrow':'ES','payment':'PY','shop':'SP'}[kind]+'-'+secrets.token_hex(4).upper()
        db.execute('INSERT INTO mvp_records VALUES (?,?,?,?,?)',(rid,code,actor,None,json.dumps(d)))
        row=load(rid);action='created'
    else:
        rid,action=path.split('/')[-2:];row=load(rid);d=row['data'];owner=row['owner']==actor;buyer=row['buyer']==actor
        require(d['kind']!='shop' or action=='review-shop','Shop applications await team contact.',409)
        if action in ['sent','dispatch','arrive','receive']:
            require(not d.get('report_open'),'A report is open. Resolve or withdraw it before continuing.',409)
        if action=='join':
            # A payment code deliberately starts the payer journey, even when this
            # browser created it. Escrow still requires a distinct buyer.
            require(not owner or d['kind']=='payment','This is your own escrow deal. Open it in the buyer’s browser.',403)
            require(row['buyer'] in [None,actor],'This code is already claimed by another account.',409)
            require(d['state']=='requested' and (d['kind']!='payment' or now<d['expires']),'This request is closed or expired.',409)
            require(body.get('agree') is True,'Review and accept the details first.')
            claim=db.execute('UPDATE mvp_records SET buyer=? WHERE id=? AND (buyer IS NULL OR buyer=?)',(actor,rid,actor))
            require(claim.rowcount==1,'This code is already claimed by another account.',409)
        elif action=='review-shop':
            require(session['role'] in ['admin','operations'] and d['kind']=='shop','Shop review permission required.',403)
            require(pending_shop(d),'This shop inquiry has already been reviewed.',409)
            decision=body.get('decision');require(decision in ['approved','declined'],'Choose approve or decline.')
            d.update(inquiry_status=decision,state='registered' if decision=='approved' else 'declined',review_note=text(body.get('reason'),'a review note',600),reviewed_at=now)
        elif action=='sent':
            require(buyer,'Only the private buyer/payer can submit this receipt.',403)
            require(d['state']=='requested','This submission is already saved.',409)
            require(d['kind']!='payment' or now<d['expires'],'This payment request has expired.',409)
            method=body.get('payer_method');require(method in METHODS,'Choose your payment method.')
            d.update(receipt=image(body.get('receipt'),True),payer_method=method,state='sent',submitted_at=now)
        elif action=='dispatch':
            require(owner and d['kind']=='escrow','Only the seller can record delivery.',403)
            require(d['state']=='sent','Wait for the buyer’s receipt submission.',409)
            d.update(delivery_photo=image(body.get('delivery_photo'),True),delivery_note=text(body.get('delivery_note'),'a delivery note'),state='delivering')
        elif action=='arrive':
            require(owner and d['kind']=='escrow','Only the seller can confirm delivery arrival.',403)
            require(d['state']=='delivering' and body.get('agree') is True,'Confirm arrival after the package has been sent.',409)
            d.update(state='arrived',arrived_at=now)
        elif action=='receive':
            require(buyer and d['kind']=='escrow','Only the buyer can confirm receipt.',403)
            require(d['state']=='arrived' and body.get('agree') is True,'Wait for seller arrival confirmation, then confirm you received and checked the item.',409)
            d.update(state='completed',completed_at=now)
        elif action=='report':
            require(d['kind']=='escrow' and (owner or buyer),'Only deal participants can report an issue.',403)
            require(d['state']!='completed','This deal is already complete.',409)
            reports=d.setdefault('reports',[])
            require(not any(x['actor']==actor and not x.get('resolved') for x in reports),'Your report is already open.',409)
            reports.append(dict(id=secrets.token_hex(8),actor=actor,role='seller' if owner else 'buyer',created=now,reason=text(body.get('reason'),'what happened',1200),photo=image(body.get('photo')),resolved=False))
            d['report_open']=True
        elif action=='withdraw-report':
            require(d['kind']=='escrow' and (owner or buyer),'Only deal participants can withdraw their report.',403)
            reports=d.get('reports',[])
            own_reports=[x for x in reports if x['actor']==actor and not x.get('resolved')]
            require(own_reports,'You have no open report to withdraw.',409)
            for report in own_reports:report.update(resolved=True,resolved_at=now)
            d['report_open']=any(not x.get('resolved') for x in reports)
        else:require(False,'Unknown action.',404)
        db.execute('UPDATE mvp_records SET data=? WHERE id=?',(json.dumps(d),rid));row=load(rid)
    event(db,row['id'],actor,'mvp.'+action,'Receipt-only MVP; no verified payment or money movement')
    result={'record':projection(row)}
    db.execute('INSERT INTO mvp_commands VALUES (?,?,?,?)',(actor,key,digest,json.dumps(result)))
    return result
