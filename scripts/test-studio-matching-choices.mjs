import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const runtime=fs.readFileSync(new URL('../equipment/assets/studio-runtime.js',import.meta.url),'utf8');
const start=runtime.indexOf('function updateMatchingSubmit(){');
const end=runtime.indexOf('\nfunction ',start+1);
assert.ok(start>=0&&end>start,'Matching handler must exist');
const handler=runtime.slice(start,end);
const makeSelect=(value,values)=>({value,options:values.map(value=>({value,disabled:false,hidden:false,style:{display:''}}))});
const choices=['','A','B','C','D'];
const selects=[makeSelect('A',choices),makeSelect('',choices),makeSelect('',choices),makeSelect('',choices)];
const submit={disabled:true};
const context={session:[{matching:{prompts:['1','2','3','4']}}],pos:0,
 document:{querySelectorAll:()=>selects},byId:()=>submit,matchingComplete:()=>selects.every(s=>!!s.value)};
vm.runInNewContext(handler,context);
context.updateMatchingSubmit();
assert.equal(submit.disabled,true);
for(const s of selects.slice(1)){
 const taken=s.options.find(o=>o.value==='A');
 assert.equal(taken.disabled,true);
 assert.equal(taken.hidden,true);
 assert.equal(taken.style.display,'none');
}
selects[0].value='';
context.updateMatchingSubmit();
assert.equal(selects[1].options.find(o=>o.value==='A').hidden,false);
selects[0].value='A';
selects[1].value='B';
selects[2].value='C';
selects[3].value='D';
context.updateMatchingSubmit();
assert.equal(submit.disabled,false);
for(const s of selects)assert.equal(s.options.filter(o=>o.value&& !o.hidden).length,1);
console.log('Matching options progressively disappear and restore correctly');
