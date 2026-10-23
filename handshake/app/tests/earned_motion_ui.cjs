/* Protect truthful, once-per-command rewards and their static alternatives. */
const {JSDOM}=require(process.env.FOM_JSDOM||'jsdom');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../public/escrow-motion.js'),'utf8');
function setup(reduced=false,query=''){
  const dom=new JSDOM('<main id="app" tabindex="-1"></main>',{url:'http://localhost:8820/index.html'+query,runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window,calls=[];w.matchMedia=()=>({matches:reduced,addEventListener(){}});
  w.Element.prototype.animate=function(frames,options){const a={frames,options,target:this,cancelled:false,finished:new Promise(()=>{}),cancel(){this.cancelled=true;}};calls.push(a);return a;};
  w.eval(source);return {dom,w,calls,root:w.document.getElementById('app')};
}
function render(t,type,kind='escrow',key=type,state){
  const r={id:'mvp-motion',kind,state:state||({create:'requested',join:'requested',receipt:'sent',dispatch:'delivering',arrived:'arrived',complete:'completed',shop:'pending'})[type]};
  t.w.location.hash=type==='complete'?'escrow/history':type==='create'?'share/'+r.id:type==='join'?'pay/'+r.id:'deal/'+r.id;
  const body=type==='complete'?'<section><h2>History</h2><a class="activity-row" href="#deal/mvp-motion">Saved result</a></section>':'<section class="flow-card"><h1>Test title</h1><div class="escrow-progress-slot"></div><button>Continue</button></section>';
  t.w.FomUI.mount(t.root,'<div class="page-head"><h1>Screen</h1></div>'+body,{actor:'tester',record:r,moment:{type,key,recordId:r.id}});
  return t.root.querySelector('[data-moment]');
}
for(const [type,kind] of [['create','escrow'],['create','payment'],['join','escrow'],['join','payment'],['receipt','escrow'],['receipt','payment'],['dispatch','escrow'],['arrived','escrow'],['complete','escrow'],['shop','shop']]){
  const t=setup(),panel=render(t,type,kind);
  assert.ok(panel,`${kind}/${type}: milestone mounted`);assert.equal(panel.dataset.motionState,'playing');
  assert.ok(t.calls.length>0);assert.equal(panel.querySelector('.moment-art').getAttribute('aria-hidden'),'true');
  assert.equal(t.root.querySelectorAll('.screen-outgoing').length,0);
  assert.ok(t.root.querySelector('button,a.activity-row'),'underlying action/result remains available');
  if(type==='receipt'){assert.match(panel.textContent,/Payment is not verified/);assert.doesNotMatch(panel.textContent,/payment successful|funds secured/i);}
  if(type==='complete')assert.ok(t.root.querySelector('a[href="#deal/mvp-motion"]'));
  const count=t.calls.length;render(t,type,kind);assert.equal(t.calls.length,count,'replayed command must not animate again');
  t.w.FomUI.cancel();assert.ok(t.calls.every(a=>a.cancelled));t.dom.window.close();
}
for(const query of ['', '?motion=reduce']){
  const t=setup(query==='',query),panel=render(t,'complete');assert.ok(panel);assert.equal(panel.dataset.motionState,'settled');assert.equal(t.calls.length,0);assert.match(panel.textContent,/Received and checked/);t.dom.window.close();
}
{
  const t=setup();t.w.document.dispatchEvent(new t.w.KeyboardEvent('keydown',{key:'Enter'}));
  const panel=render(t,'receipt');assert.ok(panel);assert.equal(t.calls.length,0,'keyboard action retains a static acknowledgment');t.dom.window.close();
}
{
  const t=setup();Object.defineProperty(t.w.document,'hidden',{value:true,configurable:true});
  const panel=render(t,'create');assert.ok(panel);assert.equal(t.calls.length,0,'hidden documents never play');
  Object.defineProperty(t.w.document,'hidden',{value:false});render(t,'create');assert.equal(t.calls.length,0,'returning to tab does not replay the same action');t.dom.window.close();
}
{
  const t=setup();const panel=render(t,'receipt');t.w.FomUI.cancel();assert.equal(panel.dataset.motionState,'settled');assert.match(panel.textContent,/Receipt saved/);assert.equal(t.root.querySelectorAll('.moment-panel').length,1);t.dom.window.close();
}
{
  const t=setup();t.w.FomUI.mount(t.root,'<section class="flow-card">Existing record</section>',{record:{id:'a',kind:'escrow',state:'sent'},moment:{type:'receipt',key:'wrong-record',recordId:'b'}});assert.equal(t.root.querySelector('[data-moment]'),null);t.dom.window.close();
}
console.log('Earned motion passed: ten service/milestone variants, exact unverified copy, History completion, once-per-command replay, static reduced/query/keyboard/hidden modes, interruption, wrong-record guard and one-screen mounting.');
