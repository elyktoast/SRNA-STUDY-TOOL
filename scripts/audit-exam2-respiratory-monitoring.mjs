/* Audits every Equipment Exam 2 respiratory-monitoring question without rewriting content.
   Run: node scripts/audit-exam2-respiratory-monitoring.mjs */
import fs from 'node:fs';
import assert from 'node:assert/strict';
const root=new URL('../equipment/exam-2/',import.meta.url);
const banks=['questions.json','questions-set2-1.json','questions-set2-2.json'];
const list=[];
for(const path of banks){
  const payload=JSON.parse(fs.readFileSync(new URL(path,root),'utf8'));
  for(const q of payload.questions||[]){
    if(String(q.topic).toLowerCase()!=='respiratory monitoring') continue;
    assert.ok(typeof q.id==='string' && typeof q.stem==='string',path+' invalid respiratory question');
    assert.ok(Array.isArray(q.options) && q.options.length>=2,path+': '+q.id+' missing options');
    assert.ok(Array.isArray(q.answer) && q.answer.length>0
       && q.answer.every(i=>Number.isInteger(i)&&i>=0&&i<q.options.length),
       path+': '+q.id+' invalid answer index');
    list.push({
      id:q.id,bank:path,
      franck: /franck/i.test([q.stem,q.explanation,q.citation].join(' ')),
      figure: Boolean(q.image),
      lecture_language:/per (the )?(lecture|instructor)|from the lecture|according to the lecture|in this lecture/i.test(q.stem),
      citation_present:typeof q.citation==='string' && q.citation.trim().length>0,
    });
  }
}
assert.equal(new Set(list.map(q=>q.bank+':'+q.id)).size,list.length,'duplicate respiratory IDs');
const franck=list.filter(q=>q.franck);
const unresolved=list.filter(q=>q.lecture_language);
const missing=list.filter(q=>!q.citation_present);
const summary={total:list.length,franck_count:franck.length,
  franck_ids:franck.map(q=>q.id),image_dependent_count:list.filter(q=>q.figure).length,
  lecture_wording_count:unresolved.length,lecture_wording_ids:unresolved.map(q=>q.id),
  missing_citation_count:missing.length};
console.log(JSON.stringify(summary,null,2));
if(process.argv.includes('--baseline-check')){
  assert.equal(summary.total,224,'Respiratory pool changed, re-audit required');
  assert.equal(summary.franck_count,16,'Franck count changed, re-audit citations');
}
