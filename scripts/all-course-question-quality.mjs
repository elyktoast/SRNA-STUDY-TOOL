import fs from 'node:fs';
import path from 'node:path';
const root=process.cwd();
const normalize=s=>String(s??'').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim();
const stop=new Set('the and for with from that this which what when where into while during patient patients anesthesia anesthetic'.split(' '));
const tokens=s=>new Set(normalize(s).split(' ').filter(t=>t.length>2&&!stop.has(t)));
const answerWords=q=>{
 if(q.type==='matching')return Object.entries(q.answer||{}).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>k+':'+normalize(v));
 const opts=q.options??q.c??[],raw=q.answer??q.correct??q.a??[];
 return (Array.isArray(raw)?raw:[raw]).map(i=>normalize(opts[Number(i)]??'')).sort();
};
const groups=[
 {course:'Equipment',base:'equipment/exam-1',sources:[{key:'bank1',data:'data/bank1.json',count:500},{key:'bank2',data:'data/bank2.json',count:500},{key:'bank3',data:'data/bank3.json',count:500},{key:'combined',data:'data/combined.json',count:150},{key:'hazards',data:'data/hazards.json',count:350}]},
 ...[['Basic Principles','basic-principles/exam-1'],['Clinical Pharm','pharm/clinical-pharm']].map(([course,base])=>({course,base,sources:JSON.parse(fs.readFileSync(path.join(root,base,'banks.json'),'utf8')).studioSources}))
];
const rows=[],failures=[],summary={};
for(const group of groups){
 let count=0;
 for(const source of group.sources){
  const data=JSON.parse(fs.readFileSync(path.join(root,group.base,source.data),'utf8'));
  const qs=Array.isArray(data)?data:(data.questions||[]);
  if(qs.length!==Number(source.count))failures.push(group.course+'/'+source.key+' count '+qs.length+' differs from manifest '+source.count);
  count+=qs.length;
  for(const q of qs){
   const stem=String(q.stem??q.q??''),opts=q.type==='matching'?(q.choices||[]):(q.options??q.c??[]);
   rows.push({course:group.course,source:source.key,id:String(q.id??''),set:Number(q.set??1),stem,normalized:normalize(stem),options:JSON.stringify(opts.map(normalize).sort()),answer:JSON.stringify(answerWords(q)),tokens:tokens(stem)});
  }
 }
 summary[group.course]={questions:count};
}
const expectedTotal=8000;
if(rows.length!==expectedTotal)failures.push('Expected '+expectedTotal+' questions; found '+rows.length);
if(Object.values(summary).some(s=>s.questions===0)||Object.keys(summary).length!==3)failures.push('All three courses must be present');
const findings=[],byStem=new Map(),byRecord=new Map();
const ref=r=>r.course+'/'+r.source+'/'+r.id;
for(const r of rows){
 const stemKey=r.course+'|'+r.normalized,recordKey=stemKey+'|'+r.options+'|'+r.answer;
 if(!byStem.has(stemKey))byStem.set(stemKey,[]);byStem.get(stemKey).push(r);
 if(!byRecord.has(recordKey))byRecord.set(recordKey,[]);byRecord.get(recordKey).push(r);
}
for(const g of byRecord.values())if(g.length>1)findings.push({severity:'review',type:'exact_duplicate',course:g[0].course,questions:g.map(ref).sort(),stem:g[0].stem});
for(const g of byStem.values())if(g.length>1){
 const options=new Map();
 for(const r of g){if(!options.has(r.options))options.set(r.options,[]);options.get(r.options).push(r)}
 for(const same of options.values())if(new Set(same.map(r=>r.answer)).size>1)findings.push({severity:'critical',type:'conflicting_answer_key',course:g[0].course,questions:same.map(ref).sort(),stem:g[0].stem});
}
const buckets=new Map();
for(const r of rows){const key=r.course+'|'+[...r.tokens].sort().slice(0,5).join('|');if(r.tokens.size<4)continue;if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(r)}
for(const group of buckets.values()){
 if(group.length>80)continue;
 for(let i=0;i<group.length;i++)for(let j=i+1;j<group.length;j++){
  const a=group[i],b=group[j];if(a.normalized===b.normalized)continue;
  const common=[...a.tokens].filter(t=>b.tokens.has(t)).length;
  const sim=common/(a.tokens.size+b.tokens.size-common);
  if(sim<.9)continue;
  findings.push({severity:'informational',type:'near_duplicate',course:a.course,questions:[ref(a),ref(b)].sort(),similarity:Number(sim.toFixed(3)),stems:[a.stem,b.stem]});
 }
}
findings.sort((a,b)=>a.course.localeCompare(b.course)||a.type.localeCompare(b.type)||a.questions.join('|').localeCompare(b.questions.join('|')));
for(const f of findings)summary[f.course][f.type]=(summary[f.course][f.type]||0)+1;
const report={schema:1,totalQuestions:rows.length,summary,failures,findings};
const file=path.join(root,'reports/all-course-question-quality.json');
if(process.argv.includes('--write')){fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(report,null,2)+'\n')}
if(process.argv.includes('--check')){
 if(!fs.existsSync(file)||fs.readFileSync(file,'utf8')!==JSON.stringify(report,null,2)+'\n')failures.push('All-course quality report stale: run npm run review:all:write');
}
console.log('All-course question quality: '+JSON.stringify(summary)+'; '+findings.length+' findings; '+failures.length+' failures');
if(failures.length){console.error(failures.join('\n'));process.exitCode=1}
