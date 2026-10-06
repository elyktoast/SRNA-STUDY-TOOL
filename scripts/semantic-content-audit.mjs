import fs from 'node:fs';
import path from 'node:path';
const root=process.cwd(),failures=[],warnings=[];
const files=['bank1.json','bank2.json','bank3.json','combined.json','hazards.json'];
const stop=new Set('a an the and or of to in on for with by is are was were be been being which what when where how why from as at that this these those patient patients anesthesia anesthetic'.split(' '));
const norm=s=>String(s??'').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim();
const tokens=s=>new Set(norm(s).split(' ').filter(x=>x.length>2&&!stop.has(x)));
const keyed=q=>{const opts=q.options??q.c??[],raw=q.answer??q.correct??q.a??[],ans=(Array.isArray(raw)?raw:[raw]).map(Number).filter(Number.isInteger);return ans.map(i=>norm(opts[i]||'')).filter(Boolean).sort()};
const rows=[];
for(const file of files){
 const p=JSON.parse(fs.readFileSync(path.join(root,'equipment/exam-1/data',file),'utf8')),qs=Array.isArray(p)?p:(p.questions||[]);
 for(const q of qs){const opts=(q.options??q.c??[]).map(norm),explanation=String(q.explanation??q.exp??q.rationale??'');if(/\[cite:/i.test(explanation))failures.push('Legacy citation artifact remains in '+file+' '+String(q.set??1)+'::'+String(q.id??''));rows.push({file,id:String(q.id??''),set:Number(q.set??1),stem:String(q.stem??q.q??''),norm:norm(q.stem??q.q??''),key:keyed(q),optionSig:JSON.stringify([...opts].sort()),tokens:tokens(q.stem??q.q??'')})}
}
const exact=new Map();
for(const r of rows){if(!r.norm)continue;if(!exact.has(r.norm))exact.set(r.norm,[]);exact.get(r.norm).push(r)}
let exactGroups=0,crossSetExact=0;
for(const group of exact.values()){
 if(group.length<2)continue;exactGroups++;
 if(new Set(group.map(x=>x.file+'::'+x.set)).size>1)crossSetExact++;
 const byOptions=new Map();
 for(const item of group){if(!byOptions.has(item.optionSig))byOptions.set(item.optionSig,[]);byOptions.get(item.optionSig).push(item)}
 for(const sameOptions of byOptions.values()){
  if(sameOptions.length<2)continue;
  const keyForms=new Set(sameOptions.map(x=>JSON.stringify(x.key)));
  if(keyForms.size>1)failures.push('Same stem and same answer choices have conflicting keyed answers: '+sameOptions.map(x=>x.file+' '+x.set+'::'+x.id).join(', '));
 }
 if(byOptions.size>1&&new Set(group.map(x=>JSON.stringify(x.key))).size>1)warnings.push('Exact stem is reused with different option pools/key wording: '+group.map(x=>x.file+' '+x.set+'::'+x.id).join(', '));
}
const buckets=new Map();
for(const r of rows){
 const sig=[...r.tokens].sort().slice(0,5).join('|');if(!sig)continue;
 if(!buckets.has(sig))buckets.set(sig,[]);buckets.get(sig).push(r)
}
const seen=new Set();let nearPairs=0;
for(const group of buckets.values()){
 if(group.length>80)continue;
 for(let i=0;i<group.length;i++)for(let j=i+1;j<group.length;j++){
  const a=group[i],b=group[j],pair=[a.file,a.set,a.id,b.file,b.set,b.id].join('|');if(seen.has(pair))continue;seen.add(pair);
  const union=new Set([...a.tokens,...b.tokens]),inter=[...a.tokens].filter(x=>b.tokens.has(x)).length,sim=union.size?inter/union.size:0;
  if(sim<0.9||a.norm===b.norm)continue;nearPairs++;
  if(JSON.stringify(a.key)!==JSON.stringify(b.key))warnings.push('Near-duplicate stems use different keyed wording ('+sim.toFixed(2)+'): '+a.file+' '+a.set+'::'+a.id+' vs '+b.file+' '+b.set+'::'+b.id);
 }
}
const hazards=rows.filter(r=>r.file==='hazards.json'),hazSet2=hazards.filter(r=>r.set===2),uniqueHaz2=new Set(hazSet2.map(r=>r.norm)).size;
if(hazSet2.length===100&&uniqueHaz2<95)failures.push('Hazards Set 2 regressed to only '+uniqueHaz2+' unique normalized stems across 100 questions.');

const bpManifest=JSON.parse(fs.readFileSync(path.join(root,'basic-principles/exam-1/banks.json'),'utf8')),bpRows=[],bpIds=new Set();
for(const source of bpManifest.studioSources||[]){
 const payload=JSON.parse(fs.readFileSync(path.join(root,'basic-principles/exam-1',source.data),'utf8')),qs=Array.isArray(payload)?payload:(payload.questions||[]);
 for(const q of qs){
  const id=String(q.id??''),globalId=source.key+'::'+id,opts=(q.options??q.c??[]).map(norm),stem=String(q.stem??q.q??''),answers=keyed(q);
  if(bpIds.has(globalId))failures.push('Basic Principles duplicate global id '+globalId);bpIds.add(globalId);
  bpRows.push({source:source.key,id,globalId,stem,norm:norm(stem),key:answers,optionSig:JSON.stringify([...opts].sort()),recordSig:JSON.stringify([norm(stem),[...opts].sort(),answers])});
 }
}
const bpExact=new Map(),bpRecords=new Map();
for(const r of bpRows){if(r.norm){if(!bpExact.has(r.norm))bpExact.set(r.norm,[]);bpExact.get(r.norm).push(r)}if(!bpRecords.has(r.recordSig))bpRecords.set(r.recordSig,[]);bpRecords.get(r.recordSig).push(r)}
let bpExactGroups=0,bpDuplicateRecords=0;
for(const group of bpExact.values()){
 if(group.length<2)continue;bpExactGroups++;
 const sameOptions=new Map();for(const item of group){if(!sameOptions.has(item.optionSig))sameOptions.set(item.optionSig,[]);sameOptions.get(item.optionSig).push(item)}
 for(const same of sameOptions.values())if(same.length>1&&new Set(same.map(x=>JSON.stringify(x.key))).size>1)failures.push('Basic Principles same stem/options have conflicting keyed answers: '+same.map(x=>x.globalId).join(', '));
}
for(const group of bpRecords.values())if(group.length>1){bpDuplicateRecords++;warnings.push('Basic Principles duplicate normalized record: '+group.map(x=>x.globalId).join(', '))}
if(bpRows.length!==4000)failures.push('Basic Principles semantic audit saw '+bpRows.length+' questions instead of 4000');

const pharmManifest=JSON.parse(fs.readFileSync(path.join(root,'pharm/clinical-pharm/banks.json'),'utf8')),pharmRows=[],pharmIds=new Set();
for(const source of pharmManifest.studioSources||[]){
 const payload=JSON.parse(fs.readFileSync(path.join(root,'pharm/clinical-pharm',source.data),'utf8')),qs=Array.isArray(payload)?payload:(payload.questions||[]);
 for(const q of qs){
  const id=String(q.id??''),globalId=source.key+'::'+id,stem=String(q.stem??''),opts=(q.options??[]).map(norm),answers=q.type==='matching'?Object.values(q.answer||{}).map(norm).sort():keyed(q),optionSig=q.type==='matching'?JSON.stringify([...(q.choices||[]).map(norm)].sort()):JSON.stringify([...opts].sort());
  if(pharmIds.has(id))failures.push('Clinical Pharm duplicate global id '+id);pharmIds.add(id);
  pharmRows.push({source:source.key,id,globalId,stem,norm:norm(stem),key:answers,optionSig,tokens:tokens(stem),recordSig:JSON.stringify([norm(stem),optionSig,answers])});
 }
}
const pharmExact=new Map(),pharmRecords=new Map();
for(const r of pharmRows){if(r.norm){if(!pharmExact.has(r.norm))pharmExact.set(r.norm,[]);pharmExact.get(r.norm).push(r)}if(!pharmRecords.has(r.recordSig))pharmRecords.set(r.recordSig,[]);pharmRecords.get(r.recordSig).push(r)}
let pharmExactGroups=0,pharmDuplicateRecords=0,pharmNearPairs=0;
for(const group of pharmExact.values()){
 if(group.length<2)continue;pharmExactGroups++;
 const byOptions=new Map();for(const item of group){if(!byOptions.has(item.optionSig))byOptions.set(item.optionSig,[]);byOptions.get(item.optionSig).push(item)}
 for(const same of byOptions.values())if(same.length>1&&new Set(same.map(x=>JSON.stringify(x.key))).size>1)failures.push('Clinical Pharm same stem/options have conflicting keyed answers: '+same.map(x=>x.globalId).join(', '));
 if(byOptions.size>1&&new Set(group.map(x=>JSON.stringify(x.key))).size>1)warnings.push('Clinical Pharm exact stem is reused with different option pools/key wording: '+group.map(x=>x.globalId).join(', '));
}
for(const group of pharmRecords.values())if(group.length>1){pharmDuplicateRecords++;warnings.push('Clinical Pharm duplicate normalized record: '+group.map(x=>x.globalId).join(', '))}
const pharmBuckets=new Map();for(const r of pharmRows){const sig=[...r.tokens].sort().slice(0,5).join('|');if(!sig)continue;if(!pharmBuckets.has(sig))pharmBuckets.set(sig,[]);pharmBuckets.get(sig).push(r)}
const pharmSeenPairs=new Set();for(const group of pharmBuckets.values()){if(group.length>80)continue;for(let i=0;i<group.length;i++)for(let j=i+1;j<group.length;j++){const a=group[i],b=group[j],pair=a.globalId+'|'+b.globalId;if(pharmSeenPairs.has(pair))continue;pharmSeenPairs.add(pair);const union=new Set([...a.tokens,...b.tokens]),inter=[...a.tokens].filter(x=>b.tokens.has(x)).length,sim=union.size?inter/union.size:0;if(sim<.9||a.norm===b.norm)continue;pharmNearPairs++;if(JSON.stringify(a.key)!==JSON.stringify(b.key))warnings.push('Clinical Pharm near-duplicate stems use different keyed wording ('+sim.toFixed(2)+'): '+a.globalId+' vs '+b.globalId)}}
const pharmExpected=(pharmManifest.studioSources||[]).reduce((n,s)=>n+Number(s.count||0),0);if(pharmRows.length!==pharmExpected)failures.push('Clinical Pharm semantic audit saw '+pharmRows.length+' questions instead of '+pharmExpected);

for(const w of warnings.slice(0,50))console.warn('SEMANTIC WARNING: '+w);
if(failures.length){console.error('\nSEMANTIC CONTENT AUDIT FAILED\n- '+failures.join('\n- '));process.exit(1)}
console.log('Semantic content audit passed across '+rows.length+' Equipment, '+bpRows.length+' Basic Principles, and '+pharmRows.length+' Clinical Pharm questions: Basic Principles '+bpExactGroups+' exact-stem groups/'+bpDuplicateRecords+' duplicate normalized records; Clinical Pharm '+pharmExactGroups+' exact-stem groups/'+pharmDuplicateRecords+' duplicate normalized records/'+pharmNearPairs+' near-duplicate pairs; '+warnings.length+' total warnings; no conflicting exact-answer keys.');
