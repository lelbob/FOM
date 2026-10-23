/* Finite, interruptible motion. Financial states always come from the app. */
(()=>{
  'use strict';
  const preference=matchMedia('(prefers-reduced-motion: reduce)');
  const reduced=()=>preference.matches||new URLSearchParams(location.search).get('motion')==='reduce';
  const ease='cubic-bezier(.23,1,.32,1)',glide='cubic-bezier(.77,0,.175,1)';
  let lastRoute='',lastHTML='',lastRecord='',keyboard=false;
  const animations=new Set();
  const seen=key=>{try{return sessionStorage.getItem('fom-motion:'+key)==='1';}catch{return true;}};
  const remember=key=>{try{sessionStorage.setItem('fom-motion:'+key,'1');}catch{}};
  function animate(el,frames,options){if(!el?.animate||reduced()||document.hidden)return;const a=el.animate(frames,options);animations.add(a);a.finished.catch(()=>{}).finally(()=>animations.delete(a));return a;}
  function cancel(){animations.forEach(a=>a.cancel());animations.clear();document.querySelectorAll('.screen-outgoing').forEach(e=>e.remove());document.querySelectorAll('[data-motion-state="playing"]').forEach(e=>e.dataset.motionState='settled');}
  function mascot(state='idle',badge=false){return `<div class="mascot-stage" data-mascot="${state}"><img class="original-mascot" src="${['hello','idle'].includes(state)?'/assets/elephant-welcome.png':'/assets/soft-elephant.png'}" alt="Our blue elephant mascot" width="138" height="126">${badge?'<span class="milestone" aria-hidden="true">✓</span>':''}</div>`;}
  function progress(record){if(record?.kind!=='escrow')return '';const index={requested:0,sent:1,delivering:2,arrived:3,completed:4}[record.state];if(index===undefined)return '';return `<ol class="deal-progress" aria-label="Deal progress">${['Deal ready','Payment sent','Package sent','Arrived','Received'].map((label,i)=>`<li class="${i<index?'done':i===index?'now':''}" ${i===index?'aria-current="step"':''}><span aria-hidden="true">${i<index?'✓':i+1}</span>${label}</li>`).join('')}</ol>`;}
  function momentSpec(type,r){return ({
    create:{eyebrow:'Ready to share',title:r.kind==='payment'?'Request ready':'Deal created',copy:'Your link and code are ready. Share them when you are.'},
    join:{eyebrow:'Your next step',title:r.kind==='payment'?'Request opened':'You’re connected',copy:r.kind==='payment'?'Choose how you would like to pay.':'Deal added to Buying. Choose how to pay.'},
    receipt:{eyebrow:'Submission saved',title:'Receipt saved',copy:'Submitted for review. Payment is not verified.'},
    dispatch:{eyebrow:'One step forward',title:'Package recorded',copy:'Your photo is saved. Confirm arrival when it gets there.'},
    arrived:{eyebrow:'Handoff recorded',title:'Arrival recorded',copy:'The buyer can now receive and check the package.'},
    complete:{eyebrow:'All done, together',title:'Deal complete',copy:'Received and checked. Saved in your History.'},
    shop:{eyebrow:'Application saved',title:'Details saved',copy:'Shop setup still needs the team. You can find your details here.'}
  })[type];}
  function mountMoment(root,context){
    const event=context.moment,r=context.record;if(!event||!r||event.recordId!==r.id)return false;
    const spec=momentSpec(event.type,r);if(!spec)return false;
    const key='action:'+event.key;if(seen(key))return false;remember(key);
    const host=event.type==='complete'?root.querySelector('section'):root.querySelector('.flow-card');if(!host)return false;
    const panel=document.createElement('section');panel.className='moment-panel moment-'+event.type;panel.dataset.moment=event.type;panel.dataset.motionState='settled';panel.setAttribute('aria-label',spec.title);
    const halves=event.type==='join'?'<span class="moment-half"></span><span class="moment-half"></span>':'<span class="moment-object"></span>';
    panel.innerHTML=`<div class="moment-art" aria-hidden="true"><span class="moment-halo"></span><span class="moment-ground"></span><span class="moment-ring"></span>${halves}<img class="moment-elephant" src="/assets/soft-elephant.png" alt="" width="139" height="127"><span class="moment-mark">✓</span>${Array.from({length:event.type==='complete'?8:4},()=>'<span class="moment-spark"></span>').join('')}</div><div class="moment-copy"><p class="moment-eyebrow">${spec.eyebrow}</p><h2>${spec.title}</h2><p>${spec.copy}</p></div>`;
    host.querySelectorAll(':scope>.mascot-stage,:scope>.state-caption').forEach(e=>e.remove());root.querySelector('.page-head .mascot-stage')?.remove();root.querySelector('.page-head')?.classList.remove('companion-heading','quiet-companion-heading');host.prepend(panel);
    if(reduced()||keyboard||document.hidden)return true;
    panel.dataset.motionState='playing';const active=[];
    const play=(selector,frames,duration,delay=0,easing=ease)=>{const a=animate(panel.querySelector(selector),frames,{duration,delay,easing,fill:'none'});if(a)active.push(a);};
    // Data is already in its final position; only the decorative stage performs.
    play('.moment-copy',[{opacity:0,transform:'translateY(5px)'},{opacity:1,transform:'translateY(0)'}],180);
    const tilt=[{transform:'rotate(0deg)'},{transform:'rotate(4deg)',offset:.4},{transform:'rotate(-2deg)',offset:.7},{transform:'rotate(0deg)'}];
    if(event.type==='create'){
      play('.moment-object',[{opacity:0,transform:'translate(-27px,19px) rotate(-32deg)'},{opacity:1,transform:'translate(12px,-10px) rotate(4deg)',offset:.56},{opacity:1,transform:'translate(0,0) rotate(-12deg)'}],600,30,glide);
      play('.moment-elephant',[{transform:'translateY(3px) scale(.98)'},{transform:'translateY(-11px) scale(1.035)',offset:.48},{transform:'translateY(2px) scale(.99)',offset:.78},{transform:'translateY(0) scale(1)'}],720,30,glide);
    }else if(event.type==='join'){
      const halves=panel.querySelectorAll('.moment-half');
      halves.forEach((el,i)=>{const a=animate(el,[{opacity:0,transform:`translateX(${i?28:-28}px) rotate(${i?20:-20}deg)`},{opacity:1,transform:`translateX(0) rotate(${i?10:-12}deg)`}],{duration:300,delay:i*50,easing:ease});if(a)active.push(a);});
      play('.moment-elephant',tilt,400,70,glide);
    }else if(event.type==='receipt'){
      play('.moment-object',[{opacity:0,transform:'translate(-35px,-24px) rotate(-30deg)'},{opacity:1,transform:'translate(13px,-8px) rotate(5deg)',offset:.56},{opacity:1,transform:'translate(0,0) rotate(-12deg)'}],600,0,glide);
      play('.moment-elephant',tilt,500,100,glide);
    }else if(event.type==='dispatch'){
      play('.moment-object',[{opacity:0,transform:'translate(-19px,14px) rotate(-22deg)'},{opacity:1,transform:'translate(40px,-26px) rotate(8deg)',offset:.5},{opacity:1,transform:'translate(0,0) rotate(-7deg)'}],650,0,glide);
      play('.moment-elephant',[{transform:'translateX(0) rotate(0deg)'},{transform:'translateX(9px) rotate(3deg)',offset:.5},{transform:'translateX(0) rotate(0deg)'}],600,70,glide);
    }else if(event.type==='arrived'){
      play('.moment-object',[{opacity:0,transform:'translateY(-15px) scale(.95)'},{opacity:1,transform:'translateY(0) scale(1)'}],250);
      play('.moment-elephant',tilt,400,40,glide);
    }else if(event.type==='complete'){
      play('.moment-elephant',[{transform:'translateY(0) scale(1)'},{transform:'translateY(4px) scale(.97)',offset:.16},{transform:'translateY(-19px) scale(1.04)',offset:.48},{transform:'translateY(2px) scale(.99)',offset:.78},{transform:'translateY(0) scale(1)'}],850,0,glide);
      play('.moment-object',[{opacity:0,transform:'translate(-20px,10px) rotate(-28deg)'},{opacity:1,transform:'translate(0,0) rotate(-12deg)'}],400,150);
      const row=[...root.querySelectorAll('.activity-row')].find(el=>el.getAttribute('href')==='#deal/'+r.id);
      const a=animate(row,[{opacity:.6,transform:'translateY(8px)'},{opacity:1,transform:'translateY(0)'}],{duration:250,delay:250,easing:ease});if(a)active.push(a);
    }else{
      play('.moment-object',[{opacity:0,transform:'translateY(10px) rotate(-12deg)'},{opacity:1,transform:'translateY(0) rotate(-12deg)'}],250);
    }
    const rich=['create','receipt','dispatch','complete'].includes(event.type),markDelay=rich?350:200;
    play('.moment-mark',[{opacity:0,transform:'scale(.9)'},{opacity:1,transform:'scale(1.08)',offset:.65},{opacity:1,transform:'scale(1)'}],250,markDelay);
    play('.moment-ring',[{opacity:0,transform:'scale(.95)'},{opacity:.65,transform:'scale(1.12)',offset:.3},{opacity:0,transform:'scale(1.55)'}],450,rich?220:80);
    if(rich){panel.querySelectorAll('.moment-spark').forEach((el,i)=>{
      const angle=(i/(event.type==='complete'?8:4))*Math.PI*2,radius=event.type==='complete'?70:49,tx=Math.cos(angle)*radius,ty=Math.sin(angle)*radius;
      const a=animate(el,[{opacity:0,transform:'translate(0,0) rotate(0deg)'},{opacity:.9,transform:`translate(${tx*.55}px,${ty*.55}px) rotate(${i*35}deg)`,offset:.32},{opacity:0,transform:`translate(${tx}px,${ty+13}px) rotate(${i*65}deg)`}],{duration:event.type==='complete'?650:450,delay:220+i*20,easing:ease});if(a)active.push(a);
    });}
    const node=root.querySelector('.deal-progress .now span');if(node){const a=animate(node,[{transform:'scale(.95)'},{transform:'scale(1.12)',offset:.55},{transform:'scale(1)'}],{duration:250,delay:250,easing:ease});if(a)active.push(a);}
    Promise.allSettled(active.map(a=>a.finished)).then(()=>{if(panel.isConnected)panel.dataset.motionState='settled';});
    return true;
  }
  function playMascot(root,context){
    const stage=root.querySelector('[data-mascot="hello"]');if(!stage||keyboard)return;
    const identity=(context.actor||'visitor')+':greeting';if(seen(identity))return;remember(identity);
    animate(stage.querySelector('img'),[{transform:'rotate(-3deg)'},{transform:'rotate(2deg)',offset:.6},{transform:'rotate(0deg)'}],{duration:250,easing:ease});
  }
  function mount(root,html,context={}){
    const route=location.hash.slice(1)||'home',changedRoute=route!==lastRoute;
    if(!changedRoute&&html===lastHTML&&!context.moment)return;
    const recordKey=context.record?.id+':'+context.record?.state;
    context.changed=!!lastRecord&&recordKey!==lastRecord&&lastRecord.split(':')[0]===context.record?.id;
    cancel();
    // Mount one accessible screen; never clone old forms or private receipt images.
    const oldRoute=lastRoute;lastRoute=route;lastHTML=html;lastRecord=recordKey;
    root.innerHTML=html;
    root.dataset.screenLabel=root.querySelector('h1')?.textContent||route;
    // The original elephant is a companion in the layout, without promotional banners.
    if(!root.querySelector('[data-mascot]')){
      const pageHead=root.querySelector('.page-head');
      if(pageHead){
        const isHub=['escrow','payment'].includes(route.split('/')[0]);
        pageHead.classList.add(isHub?'companion-heading':'quiet-companion-heading');
        pageHead.insertAdjacentHTML('beforeend',mascot(isHub?'idle':'quiet'));
      }
    }
    const card=root.querySelector('.flow-card'),r=context.record;
    if(card&&r&&['share','deal'].includes(route.split('/')[0])){
      let state=route.startsWith('share')?'ready':r.state;
      if(['ready','completed','sent','delivering','contact_team'].includes(state)){
        card.insertAdjacentHTML('afterbegin',mascot(state,['ready','completed'].includes(state)));
        const caption={ready:'Ready to share',completed:'Received and checked',sent:'Receipt submitted · awaiting review',delivering:'On its way',contact_team:'Shop details saved'}[state];
        if(caption)card.querySelector('.mascot-stage').insertAdjacentHTML('afterend',`<p class="state-caption">${caption}</p>`);
      }
      if(route.startsWith('deal')){const slot=card.querySelector('.escrow-progress-slot');if(slot)slot.innerHTML=progress(r);else card.insertAdjacentHTML('beforeend',progress(r));}
      const title=[...card.children].find(el=>el.tagName==='H2');if(title)title.classList.add('status-title');
    }
    root.querySelectorAll('.stage-nav span').forEach((el,i)=>{const active=[...el.parentElement.children].findIndex(e=>e.hasAttribute('aria-current'));el.classList.toggle('stage-done',i<active);});
    if(changedRoute&&!keyboard&&!reduced()){
      const back=route.split('/').length<oldRoute.split('/').length||(route.startsWith('create/')&&oldRoute.startsWith('create/')&&['item','amount','delivery','review'].indexOf(route.split('/')[2])<['item','amount','delivery','review'].indexOf(oldRoute.split('/')[2]));
      const tabs=['home','escrow','payment','code'];const lateral=tabs.includes(route)&&tabs.includes(oldRoute);
      const direction=lateral?(tabs.indexOf(route)>tabs.indexOf(oldRoute)?1:-1):back?-1:1;
      [...root.children].forEach((el,i)=>animate(el,[{opacity:.5,transform:`translate${lateral?'X':'Y'}(${lateral?direction*12:back?-5:8}px)`},{opacity:1,transform:'translate(0,0)'}],{duration:180,delay:Math.min(i,2)*30,easing:ease}));
    }
    if(!mountMoment(root,context))playMascot(root,context);
    if(changedRoute&&oldRoute)requestAnimationFrame(()=>{if(!root.contains(document.activeElement))root.focus({preventScroll:true});});
  }
  document.addEventListener('keydown',()=>{keyboard=true;},true);
  document.addEventListener('pointerdown',()=>{keyboard=false;},true);
  document.addEventListener('focusin',e=>{if(e.target.matches('input,textarea,select'))cancel();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)cancel();});
  preference.addEventListener('change',cancel);
  document.addEventListener('toggle',e=>{if(e.target.tagName==='DETAILS'&&e.target.open&&!keyboard){[...e.target.children].filter(el=>el.tagName!=='SUMMARY').forEach(el=>animate(el,[{opacity:0,transform:'translateY(-4px)'},{opacity:1,transform:'translateY(0)'}],{duration:180,easing:ease}));}},true);
  window.FomUI={mount,mascot,cancel,navigate:url=>location.assign(url)};
})();
