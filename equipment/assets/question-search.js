/* Universal question search. Builds a shared canonical index only when opened. */
(()=>{'use strict';
let indexPromise=null,modal=null,returnFocus=null;
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
const norm=s=>String(s??'').toLowerCase().replace(/₂/g,'2').replace(/[^a-z0-9%+./ -]+/g,' ').replace(/\s+/g,' ').trim();
function topicOf(q){
  const direct=String(q.topic||q.lec||q.concept||'').trim();if(direct)return direct;
  const src=norm(Array.isArray(q.ref)?q.ref.join(' '):(q.citation||q.src||''));
  if(src.includes('medical gas'))return 'Medical Gases';if(src.includes('airway'))return 'Airway';
  if(src.includes('co2')&&src.includes('scaveng'))return 'CO₂ & Scavenging';
  if(src.includes('monitoring')||src.includes('intraoperative'))return 'Monitoring';
  if(src.includes('hazard'))return 'Workstation Hazards';return 'Other'
}
function sourceText(q){const src=q.citation??q.src??q.ref??'';return Array.isArray(src)?src.join('; '):String(src||'')}
async function buildIndex(){
  const runtime=window.MBUBuild;if(!runtime)throw Error('SRNA Study Tool runtime is unavailable.');
  const roots=[
    {path:'equipment/exam-1/',course:'Equipment & Hazards'},
    {path:'basic-principles/exam-1/',course:'Basic Principles'},
    {path:'pharm/clinical-pharm/',course:'Clinical Pharmacology'}
  ],rows=[];
  for(const root of roots){
    const exam=new URL(root.path,runtime.appRoot||location.href),manifest=await runtime.fetchJSON(new URL('banks.json',exam),{cache:'no-store'}),sources=[],seen=new Set();
    for(const src of manifest.studioSources||[]){const key=src.data+'|'+(src.setFilter||'all');if(seen.has(key))continue;seen.add(key);sources.push(src)}
    const groups=await Promise.all(sources.map(async src=>{
      const payload=await runtime.fetchJSON(new URL(src.data,exam),{cache:'force-cache'}),all=Array.isArray(payload)?payload:(payload.questions||[]),raw=src.setFilter?all.filter(q=>Number(q.set)===Number(src.setFilter)):all;
      return raw.map(q=>{
        const bank=src.key,label=src.groupLabel||src.label,set=String(bank).startsWith('h')?1:Number(q.set||1),id=String(q.id??''),uid=bank+'-'+id,stem=String(q.stem||q.q||''),topic=topicOf(q),explanation=String(q.explanation||q.exp||q.why||''),source=sourceText(q),options=Array.isArray(q.options)?q.options:(Array.isArray(q.c)?q.c:[]);
        return{uid,bank,label,course:root.course,examPath:root.path,set,id,stem,topic,source,practiceUrl:new URL('studio.html?question='+encodeURIComponent(uid),exam).href,search:norm([root.course,label,stem,topic,source,explanation,...options].join(' '))}
      })
    }));rows.push(...groups.flat())
  }
  if(window.MBUQuestionGenerator?.enabled?.())for(const q of window.MBUQuestionGenerator.studioQuestions())rows.push({uid:'generated-'+q.id,bank:'generated',label:'Generated Bank',course:'Generated',set:1,id:String(q.id),stem:String(q.stem),topic:String(q.topic||'Generated'),source:String(q.citation||q.sourceName||''),practiceUrl:'',search:norm([q.stem,q.topic,q.citation,q.sourceName,q.explanation,...(q.options||[])].join(' '))});
  return rows
}
function getIndex(){return indexPromise??=(buildIndex().catch(e=>{indexPromise=null;throw e}))}
function close(){if(!modal)return;modal.classList.remove('open');modal.setAttribute('aria-hidden','true');returnFocus?.focus?.();returnFocus=null}
function ensure(){
  if(modal)return modal;
  const wrap=document.createElement('div');wrap.innerHTML='<div id="mbu-question-search" class="mbu-question-search" role="dialog" aria-modal="true" aria-labelledby="mbu-question-search-title" aria-hidden="true"><div class="mbu-question-search__card"><div class="mbu-app-tools__head"><div><div class="mbu-section-kicker">All question banks</div><h2 id="mbu-question-search-title">Question Search</h2></div><button type="button" data-search-close aria-label="Close question search">×</button></div><label class="mbu-search-field">Search questions, answers, topics, explanations, or sources<input type="search" data-search-input autocomplete="off" placeholder="e.g. soda lime, LMA, pipeline pressure"></label><div class="mbu-search-status" data-search-status role="status" aria-live="polite">Type at least 2 characters.</div><div class="mbu-search-results" data-search-results></div></div></div>';document.body.append(wrap);modal=document.getElementById('mbu-question-search');
  const input=modal.querySelector('[data-search-input]'),status=modal.querySelector('[data-search-status]'),results=modal.querySelector('[data-search-results]');
  let token=0;
  input.addEventListener('input',async()=>{const mine=++token,q=norm(input.value);if(q.length<2){results.innerHTML='';status.textContent='Type at least 2 characters.';return}status.textContent='Searching…';try{const rows=await getIndex();if(mine!==token)return;const terms=q.split(' ').filter(Boolean),matches=[];for(const row of rows){if(terms.every(t=>row.search.includes(t))){matches.push(row);if(matches.length===100)break}}status.textContent=matches.length+(matches.length===100?'+' :'')+' match'+(matches.length===1?'':'es');results.innerHTML=matches.map(r=>'<article class="mbu-search-result"><div class="mbu-search-result__meta">'+esc(r.label)+' · '+esc(r.topic)+'</div><div class="mbu-search-result__stem">'+esc(r.stem)+'</div><div class="mbu-search-result__source">'+esc(r.source)+'</div><a class="mbu-search-result__action" href="'+esc(r.practiceUrl||new URL('studio.html?question='+encodeURIComponent(r.uid),new URL('../exam-1/',MBUBuild.assetsBase)).href)+'">Practice in Studio</a></article>').join('')||'<div class="mbu-muted">No matching questions.</div>'}catch(e){status.textContent='Search could not load: '+e.message}});
  modal.querySelector('[data-search-close]').onclick=close;modal.onclick=e=>{if(e.target===modal)close()};modal.addEventListener('keydown',e=>{if(e.key==='Escape'){close();return}if(e.key!=='Tab')return;const f=[...modal.querySelectorAll('button,input,a[href]')].filter(x=>x.offsetParent!==null);if(!f.length)return;const first=f[0],last=f[f.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}});
  return modal
}
async function open(source){ensure();returnFocus=source||document.activeElement;modal.classList.add('open');modal.setAttribute('aria-hidden','false');const input=modal.querySelector('[data-search-input]');input.focus();if(!indexPromise){modal.querySelector('[data-search-status]').textContent='Loading question index…';try{const rows=await getIndex();modal.querySelector('[data-search-status]').textContent=rows.length+' questions ready. Type at least 2 characters.'}catch(e){modal.querySelector('[data-search-status]').textContent='Search could not load: '+e.message}}}
function reset(){indexPromise=null}
window.MBUQuestionSearch={open,close,getIndex,reset};
})();