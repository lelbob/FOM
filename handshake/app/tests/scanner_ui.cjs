const {JSDOM}=require(process.env.FOM_JSDOM||'jsdom');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const dom=new JSDOM(fs.readFileSync(require('node:path').join(__dirname,'../public/index.html'),'utf8'),{url:'http://localhost:8800/index.html#code',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;let qr=null,stops=0,closes=0,requests=0,deferCamera=null,rejectCamera=false;
 const stream=()=>({getTracks:()=>[{stop(){stops++;}}]});const errors=[];
 w.matchMedia=()=>({matches:true,addEventListener(){}});w.scrollTo=()=>{};w.HTMLMediaElement.prototype.pause=function(){};w.HTMLMediaElement.prototype.play=async()=>{};
 Object.defineProperty(w.HTMLMediaElement.prototype,'readyState',{get:()=>2});Object.defineProperty(w.HTMLVideoElement.prototype,'videoWidth',{get:()=>2});Object.defineProperty(w.HTMLVideoElement.prototype,'videoHeight',{get:()=>2});
 w.HTMLCanvasElement.prototype.getContext=()=>({drawImage(){},getImageData:()=>({data:new Uint8ClampedArray(16)})});
 w.createImageBitmap=async()=>({width:2,height:2,close(){closes++;}});w.jsQR=()=>qr;
 Object.defineProperty(w.navigator,'mediaDevices',{value:{getUserMedia:async()=>{requests++;if(rejectCamera)throw Error('denied');if(deferCamera)return await deferCamera;return stream();}}});
 w.requestAnimationFrame=()=>1;w.cancelAnimationFrame=()=>{};
 w.addEventListener('error',e=>errors.push(e.message));
 const rec={id:'mvp-scanned',kind:'escrow',title:'Scanned deal',state:'requested',amount:5000,is_owner:true,code:'ES-TEST'};
 w.fetch=async(path)=>({ok:true,json:async()=>path==='/api/session'?{session:{role:'customer',actor:'tester'}}:path.startsWith('/api/mvp/resolve/')?{record:rec}:path.startsWith('/api/mvp/record/')?{record:rec}:path==='/api/mvp/list'?{records:[]}:path==='/api/activity'?{records:[]}: {}});
 w.eval(fs.readFileSync(require('node:path').join(__dirname,'../public/escrow-motion.js'),'utf8'));let buyerTarget;w.FomUI.navigate=url=>{buyerTarget=url;};w.eval(fs.readFileSync(require('node:path').join(__dirname,'../public/receipt-app.js'),'utf8'));
 const wait=()=>new Promise(r=>setTimeout(r,35)),app=w.document.querySelector('#app');await wait();
 assert.ok(app.querySelector('[data-action=camera]'));assert.ok(app.querySelector('#qr-file'));assert.ok(app.querySelector('#code-form'));
 app.querySelector('[data-action=camera]').click();await wait();assert.equal(app.querySelector('#camera').hidden,false);assert.equal(app.querySelector('[data-action=stop-camera]').hidden,false);app.querySelector('[data-action=stop-camera]').click();await wait();assert.equal(stops,1);assert.equal(app.querySelector('#camera').hidden,true);
 async function upload(){const input=app.querySelector('#qr-file');Object.defineProperty(input,'files',{configurable:true,value:[new w.File(['x'],'qr.png',{type:'image/png'})]});input.dispatchEvent(new w.Event('change',{bubbles:true}));await wait();}
 await upload();assert.match(app.querySelector('#error').textContent,/No readable QR/);assert.equal(closes,1);
 qr={data:'ES-TEST'};await upload();assert.equal(new URL(buyerTarget).hash,'#buy/mvp-scanned');assert.equal(closes,2);
 w.location.hash='home';await wait();w.location.hash='code';await wait();qr={data:'ES-TEST'};app.querySelector('[data-action=camera]').click();await wait();assert.equal(new URL(buyerTarget).hash,'#buy/mvp-scanned');assert.equal(stops,2);
 w.location.hash='home';await wait();w.location.hash='code';await wait();qr=null;rejectCamera=true;app.querySelector('[data-action=camera]').click();await wait();assert.match(app.querySelector('#error').textContent,/not granted/);assert.ok(app.querySelector('#code-form'));rejectCamera=false;
 let grant;deferCamera=new Promise(r=>grant=r);app.querySelector('[data-action=camera]').click();await wait();w.location.hash='home';await wait();grant(stream());await wait();assert.equal(stops,3);assert.equal(app.querySelector('#camera'),null);deferCamera=null;
 w.location.hash='home';await wait();w.location.hash='code';await wait();app.querySelector('[data-action=camera]').click();await wait();assert.equal(app.querySelector('#camera').hidden,false);w.location.hash='home';await wait();assert.equal(stops,4);
 assert.deepEqual(errors,[]);assert.equal(requests,5);dom.window.close();console.log('Scanner regression checks passed: camera start/stop, uploaded QR success/failure, live scan resolution, denied permission fallback, late permission cleanup, navigation cleanup. Camera/decoder are mocked; no hardware permission requested.');
})().catch(e=>{console.error(e);process.exit(1)});
