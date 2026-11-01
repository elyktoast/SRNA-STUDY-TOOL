/* Targeted guard for reviewed admin-reported Equipment Exam 2 questions. */
import fs from 'node:fs';
import assert from 'node:assert/strict';
const base=new URL('../equipment/exam-2/',import.meta.url);
const sourceFiles=['questions.json','questions-set2-1.json','questions-set2-2.json'];
const all=sourceFiles.flatMap(name=>{
 const payload=JSON.parse(fs.readFileSync(new URL(name,base),'utf8'));
 return payload.questions||[];
});
assert.equal(all.length,1000,'Equipment Exam 2 bank total must remain 1000');
const byId=new Map(all.map(q=>[q.id,q]));
assert.equal(byId.size,all.length,'Question IDs must remain unique');
const keys={
 'NUR868-T059':[0], 'NUR868-V016':[0], 'NUR868-V019':[1],
 'NUR868-V034':[0], 'NUR868-S2-R280':[0], 'NUR868-S2-R295':[3],
 'NUR868-S2-B283':[2], 'NUR868-S2-T250':[0],
 'NUR868-S2-T207':[3], 'NUR868-R054':[2,3],
 'NUR868-T058':[0], 'NUR868-S2-M208':[2,5],
};
for(const [id,answer] of Object.entries(keys)){
 const q=byId.get(id);
 assert.ok(q,id+' missing from bank');
 assert.deepEqual(q.answer,answer,id+' answer index mismatch');
 assert.ok(!/\b(?:per (?:the )?(?:lecture|instructor)|the instructor suggests)\b/i.test(q.stem),
           id+' still refers to unprovided lecture authority');
}
const flow=byId.get('NUR868-R054');
assert.equal(flow.type,'multi');
assert.match(flow.stem,/select 2/i);
assert.ok(flow.image?.startsWith('data:image/png;base64,'));
const temp=byId.get('NUR868-S2-T207');
assert.ok(temp.image?.startsWith('data:image/png;base64,'));
assert.doesNotMatch(byId.get('NUR868-T058').stem,/55%/);
assert.doesNotMatch(byId.get('NUR868-S2-M208').citation,/course lecture/i);
assert.match(byId.get('NUR868-S2-M208').stem,/select 2/i);
console.log('12 reported-question revisions verified: stable IDs, expected answer keys and figure presence');
