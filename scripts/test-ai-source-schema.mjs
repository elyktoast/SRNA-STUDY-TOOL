import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { test } from 'node:test';

const sql = [1,2,3,4].map((n) => {
  const name = [
    '001_private_bank_draft.sql',
    '002_source_library_draft.sql',
    '003_source_retrieval_draft.sql',
    '004_hybrid_retrieval_draft.sql'
  ][n-1];
  return readFileSync(new URL('../supabase/ai-adaptive/'+name,import.meta.url),'utf8');
});
test('every new table has RLS and no browser grants',()=>{
  for(const text of sql){
    const tables=[...text.matchAll(/create table if not exists private\.(\w+)/gi)].map(x=>x[1]);
    for(const table of tables){
      assert.match(text,new RegExp('alter table private\\.'+table+' enable row level security','i'));
      assert.match(text,new RegExp('revoke all on private\\.'+table+' from public\\s*,\\s*anon\\s*,\\s*authenticated','i'));
    }
  }
});
test('retrieval functions are invoker-only and private',()=>{
  for(const text of sql.slice(2)){
    assert.match(text,/security invoker/i);
    assert.doesNotMatch(text,/security definer/i);
    assert.match(text,/revoke all on function private\./i);
  }
});
test('search results retain source and page references',()=>{
  for(const text of sql.slice(2)){
    for(const field of ['document_title','section_heading','page_start','page_end','passage'])
      assert.ok(text.includes(field),field);
  }
});
test('documents use checksums and chunks have stable order',()=>{
  assert.match(sql[1],/sha256 text not null/i);
  assert.match(sql[1],/unique\(document_id,chunk_order\)/i);
  assert.match(sql[1],/processing_status='ready'|processing_status text/i);
});
test('no draft mutates existing student CAT tables',()=>{
  for(const text of sql){
    assert.doesNotMatch(text,/\b(?:alter|drop|truncate|delete from|update)\s+(?:table\s+)?(?:public\.)?mbu_/i);
  }
});
