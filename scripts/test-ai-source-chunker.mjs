import {test} from 'node:test';
import assert from 'node:assert/strict';
import {chunkPages} from './ai-source-chunker.mjs';

test('empty and whitespace pages are ignored',()=>{
  assert.deepEqual(chunkPages([{physicalPage:1,text:'  '}]),[]);
});
test('printed and physical pages are preserved separately',()=>{
  const c=chunkPages([{physicalPage:12,printedPage:'3',sectionHeading:'Capnography',text:'Carbon dioxide monitoring'}]);
  assert.equal(c.length,1);
  assert.equal(c[0].physicalPage,12);
  assert.equal(c[0].printedPage,'3');
  assert.equal(c[0].sectionHeading,'Capnography');
});
test('long pages split without losing content or crossing page boundaries',()=>{
  const text='word '.repeat(1000).trim();
  const chunks=chunkPages([{physicalPage:2,text}],{maxChars:400,overlapChars:60});
  assert.ok(chunks.length>1);
  assert.ok(chunks.every(c=>c.physicalPage===2&&c.content.length<=400));
  assert.ok(chunks.every((c,i)=>c.chunkOrder===i));
  assert.equal(chunks[0].content.slice(0,4),'word');
  assert.equal(chunks.at(-1).content.slice(-4),'word');
});
test('invalid options and pages fail explicitly',()=>{
  assert.throws(()=>chunkPages(null),TypeError);
  assert.throws(()=>chunkPages([{physicalPage:0,text:'hi'}]),TypeError);
  assert.throws(()=>chunkPages([],{maxChars:200}),RangeError);
  assert.throws(()=>chunkPages([],{maxChars:400,overlapChars:400}),RangeError);
});

test('duplicate pages and nontext extraction are rejected',()=>{
  assert.throws(()=>chunkPages([{physicalPage:1,text:'a'},{physicalPage:1,text:'b'}]),/duplicate physicalPage/);
  assert.throws(()=>chunkPages([{physicalPage:1,text:{bad:true}}]),TypeError);
});
test('chunking is deterministic across repeated runs',()=>{
  const pages=[{physicalPage:4,text:'capnography '.repeat(300)}];
  assert.deepEqual(chunkPages(pages),chunkPages(pages));
});
