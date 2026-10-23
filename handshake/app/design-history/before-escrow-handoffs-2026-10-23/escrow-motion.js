/* Finite, interruptible motion. Financial states always come from the app. */
(()=>{
  'use strict';
  const preference=matchMedia('(prefers-reduced-motion: reduce)');
  const reduced=()=>preference.matches||new URLSearchParams(location.search).get('motion')==='reduce';
  const ease='cubic-bezier(.23,1,.32,1)';
  let lastRoute='',lastHTML='',lastRecord='',keyboard=false;
  const animations=new Set();
  const seen=key=>{try{return sessionStorage.getItem('fom-motion:'+key)==='1';}catch{return true;}};
  const remember=key=>{try{sessionStorage.setItem('fom-motion:'+key,'1');}catch{}};
  function animate(el,frames,options){if(!el||reduced()||document.hidden)return;const a=el.animate(frames,options);animations.add(a);a.finished.catch(()=>{}).finally(()=>animations.delete(a));return a;}
  function cancel(){animations.forEach(a=>a.cancel());animations.clear();document.querySelectorAll('.screen-outgoing').forEach(e=>e.remove());}
  function mascot(state='idle',badge=false){return `<div class="mascot-stage" data-mascot="${state}"><img class="original-mascot" src="${['hello','idle'].includes(state)?'/assets/elephant-welcome.png':'/assets/soft-elephant.png'}" alt="Our blue elephant mascot" width="138" height="126">${badge?'<span class="milestone" aria-hidden="true">✓</span>':''}</div>`;}
  function progress(record){if(record?.kind!=='escrow')return '';const index={requested:0,sent:1,delivering:2,completed:3}[record.state];if(index===undefined)return '';return `<ol class="deal-progress" aria-label="Deal progress">${['Deal ready','Receipt sent','Delivery','Received'].map((label,i)=>`<li class="${i<index?'done':i===index?'now':''}" ${i===index?'aria-current="step"':''}><span aria-hidden="true">${i<index?'✓':i+1}</span>${label}</li>`).join('')}</ol>`;}
  function playMascot(root,context){const stage=root.querySelector('[data-mascot]');if(!stage||stage.dataset.mascot==='quiet')return;const img=stage.querySelector('img');let state=stage.dataset.mascot;const identity=(context.actor||'visitor')+':'+(context.record?.id||location.hash.split('/')[0]||'home')+':'+state;
    // New committed actions may perform once. Opening an old record stays still.
    const fresh=state==='hello'?!seen(identity):context.fresh||context.changed;
    if(seen(identity)||!fresh||keyboard){state='idle';}else remember(identity);
    const gestures={hello:[{transform:'rotate(0deg)'},{transform:'rotate(-4deg)',offset:.3},{transform:'rotate(3deg)',offset:.6},{transform:'rotate(0deg)'}],ready:[{transform:'translateY(0) scale(1)'},{transform:'translateY(-5px) scale(1.025)',offset:.45},{transform:'translateY(0) scale(1)'}],completed:[{transform:'translateY(0) scale(1)'},{transform:'translateY(2px) scale(.98)',offset:.2},{transform:'translateY(-9px) scale(1.025)',offset:.55},{transform:'translateY(0) scale(1)'}],sent:[{transform:'rotate(0deg)'},{transform:'rotate(3deg)',offset:.45},{transform:'rotate(0deg)'}],delivering:[{transform:'translateX(0)'},{transform:'translateX(5px) rotate(2deg)',offset:.5},{transform:'translateX(0) rotate(0deg)'}]};
    if(gestures[state])animate(img,gestures[state],{duration:state==='completed'?850:700,easing:ease});
    else if(state==='idle'&&!seen(identity+':rest')){remember(identity+':rest');animate(img,[{transform:'scale(1)'},{transform:'scale(1.012)',offset:.5},{transform:'scale(1)'}],{duration:2200,iterations:2,easing:'ease-in-out'});}
  }
  function mount(root,html,context={}){
    const route=location.hash.slice(1)||'home',changedRoute=route!==lastRoute;
    if(!changedRoute&&html===lastHTML)return;
    const recordKey=context.record?.id+':'+context.record?.state;
    context.changed=!!lastRecord&&recordKey!==lastRecord&&lastRecord.split(':')[0]===context.record?.id;
    cancel();
    const old=changedRoute&&lastRoute&&!reduced()&&!keyboard?root.cloneNode(true):null;
    if(old){old.removeAttribute('id');old.removeAttribute('aria-live');old.removeAttribute('tabindex');old.setAttribute('aria-hidden','true');old.inert=true;old.className='screen-outgoing';old.querySelectorAll('[id]').forEach(e=>e.removeAttribute('id'));}
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
      if(route.startsWith('deal'))card.insertAdjacentHTML('beforeend',progress(r));
      const title=[...card.children].find(el=>el.tagName==='H2');if(title)title.classList.add('status-title');
    }
    root.querySelectorAll('.stage-nav span').forEach((el,i)=>{const active=[...el.parentElement.children].findIndex(e=>e.hasAttribute('aria-current'));el.classList.toggle('stage-done',i<active);});
    if(changedRoute&&!keyboard&&!reduced()){
      const back=route.split('/').length<oldRoute.split('/').length||(route.startsWith('create/')&&oldRoute.startsWith('create/')&&['item','amount','delivery','review'].indexOf(route.split('/')[2])<['item','amount','delivery','review'].indexOf(oldRoute.split('/')[2]));
      const tabs=['home','escrow','payment','code'];const lateral=tabs.includes(route)&&tabs.includes(oldRoute);
      const direction=lateral?(tabs.indexOf(route)>tabs.indexOf(oldRoute)?1:-1):back?-1:1;
      if(old){root.append(old);const exit=animate(old,[{opacity:1,transform:'translateX(0)'},{opacity:0,transform:`translateX(${-direction*14}px)`}],{duration:160,easing:ease});exit?.finished.catch(()=>{}).finally(()=>old.remove());}
      [...root.children].filter(el=>el!==old).forEach(el=>animate(el,[{opacity:0,transform:`translate${lateral?'X':'Y'}(${lateral?direction*18:back?-8:12}px)`},{opacity:1,transform:'translate(0,0)'}],{duration:250,easing:ease}));
    }
    playMascot(root,context);
    if(changedRoute&&oldRoute)requestAnimationFrame(()=>{root.focus({preventScroll:true});});
  }
  document.addEventListener('keydown',()=>{keyboard=true;},true);
  document.addEventListener('pointerdown',()=>{keyboard=false;},true);
  document.addEventListener('focusin',e=>{if(e.target.matches('input,textarea,select'))cancel();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)cancel();});
  preference.addEventListener('change',cancel);
  document.addEventListener('toggle',e=>{if(e.target.tagName==='DETAILS'&&e.target.open&&!keyboard){[...e.target.children].filter(el=>el.tagName!=='SUMMARY').forEach(el=>animate(el,[{opacity:0,transform:'translateY(-4px)'},{opacity:1,transform:'translateY(0)'}],{duration:180,easing:ease}));}},true);
  window.FomUI={mount,mascot,cancel};
})();
